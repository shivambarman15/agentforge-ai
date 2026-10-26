from flask import Flask, request, jsonify, render_template
from pathlib import Path
import json, os, sys, platform, subprocess, datetime, urllib.request, urllib.error

app = Flask(__name__)
BASE = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get('AGENTFORGE_DATA_DIR', BASE / 'data'))
DATA_DIR.mkdir(parents=True, exist_ok=True)
AGENTS_FILE = DATA_DIR / 'agents.json'
SETTINGS_FILE = DATA_DIR / 'settings.json'

DEFAULT_SETTINGS = {"provider_url": "https://api.openai.com/v1", "api_key": "", "model_fast": "gpt-4o-mini", "model_pro": "gpt-4o", "model_max": "gpt-4.1"}

def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default

def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)

def get_settings():
    current = DEFAULT_SETTINGS.copy()
    current.update(read_json(SETTINGS_FILE, {}))
    if os.environ.get('LLM_API_KEY'):
        current['api_key'] = os.environ['LLM_API_KEY']
    if os.environ.get('LLM_BASE_URL'):
        current['provider_url'] = os.environ['LLM_BASE_URL']
    return current

def public_settings(settings):
    result = settings.copy()
    result['api_key'] = '••••••••' if result.get('api_key') else ''
    return result

@app.get('/')
def index():
    return render_template('index.html')

@app.get('/api/agents')
def list_agents():
    return jsonify(read_json(AGENTS_FILE, []))

@app.post('/api/agents')
def create_agent():
    body = request.get_json(silent=True) or {}
    name = str(body.get('name', '')).strip()
    if not name:
        return jsonify(error='Agent name is required.'), 400
    agents = read_json(AGENTS_FILE, [])
    agent = {
        'id': 'ag_' + os.urandom(5).hex(), 'name': name,
        'description': str(body.get('description', '')).strip(),
        'model': body.get('model', 'Fast') if body.get('model') in ['Fast','Pro','Max'] else 'Fast',
        'instructions': str(body.get('instructions', '')), 'tools': body.get('tools', []),
        'connections': body.get('connections', []), 'skills': body.get('skills', []),
        'memory': str(body.get('memory', '')), 'channels': body.get('channels', []),
        'schedules': body.get('schedules', []), 'created_at': datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    agents.insert(0, agent)
    write_json(AGENTS_FILE, agents)
    return jsonify(agent), 201

@app.put('/api/agents/<agent_id>')
def update_agent(agent_id):
    body = request.get_json(silent=True) or {}
    agents = read_json(AGENTS_FILE, [])
    for i, agent in enumerate(agents):
        if agent['id'] == agent_id:
            for key in ['name','description','model','instructions','tools','connections','skills','memory','channels','schedules']:
                if key in body: agent[key] = body[key]
            agents[i] = agent
            write_json(AGENTS_FILE, agents)
            return jsonify(agent)
    return jsonify(error='Agent not found.'), 404

@app.delete('/api/agents/<agent_id>')
def delete_agent(agent_id):
    agents = read_json(AGENTS_FILE, [])
    updated = [a for a in agents if a['id'] != agent_id]
    if len(updated) == len(agents): return jsonify(error='Agent not found.'), 404
    write_json(AGENTS_FILE, updated)
    return jsonify(ok=True)

@app.get('/api/settings')
def settings_get():
    return jsonify(public_settings(get_settings()))

@app.post('/api/settings')
def settings_save():
    body = request.get_json(silent=True) or {}
    old = read_json(SETTINGS_FILE, {})
    for key in ['provider_url','model_fast','model_pro','model_max']:
        if key in body: old[key] = str(body[key]).strip()
    if body.get('api_key') and body['api_key'] != '••••••••': old['api_key'] = str(body['api_key']).strip()
    write_json(SETTINGS_FILE, old)
    return jsonify(ok=True, settings=public_settings(get_settings()), note='For production, set LLM_API_KEY as a hosting secret instead of saving keys in files.')

@app.post('/api/run')
def run_agent():
    body = request.get_json(silent=True) or {}
    agent_id = body.get('agent_id')
    prompt = str(body.get('prompt', '')).strip()
    if not prompt: return jsonify(error='Enter a task or message first.'), 400
    agents = read_json(AGENTS_FILE, [])
    agent = next((a for a in agents if a['id'] == agent_id), None)
    if not agent: return jsonify(error='Select an agent first.'), 404
    settings = get_settings()
    if not settings.get('api_key'):
        return jsonify(error='No LLM API key configured. Open API Keys / LLM Gateway and add a compatible provider key, or set LLM_API_KEY in your hosting environment.'), 400
    model_key = {'Fast':'model_fast','Pro':'model_pro','Max':'model_max'}.get(agent.get('model'), 'model_fast')
    model = settings.get(model_key) or settings['model_fast']
    messages = []
    if agent.get('instructions'): messages.append({'role':'system','content':agent['instructions']})
    if agent.get('memory'): messages.append({'role':'system','content':'Workspace memory / context:\n' + agent['memory']})
    messages.append({'role':'user','content':prompt})
    url = settings.get('provider_url','').rstrip('/') + '/chat/completions'
    payload = json.dumps({'model': model, 'messages': messages}).encode('utf-8')
    req = urllib.request.Request(url, data=payload, headers={'Authorization':'Bearer '+settings['api_key'], 'Content-Type':'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=90) as response:
            data = json.loads(response.read().decode('utf-8'))
        answer = data.get('choices',[{}])[0].get('message',{}).get('content','No text returned by model.')
        return jsonify(answer=answer, model=model, agent=agent['name'])
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='replace')[:1200]
        return jsonify(error=f'LLM provider returned HTTP {exc.code}: {detail}'), 502
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return jsonify(error=f'Could not reach the LLM provider: {exc}'), 502

@app.get('/api/system')
def system_info():
    agents = read_json(AGENTS_FILE, [])
    try:
        import importlib.metadata as md
        packages = sorted([f'{d.metadata.get("Name", "unknown")}=={d.version}' for d in md.distributions()], key=str.lower)
    except Exception: packages = []
    return jsonify({
        'app':'AgentForge Workspace', 'version':'0.1.0', 'python':sys.version.split()[0],
        'platform':platform.platform(), 'agent_count':len(agents), 'storage_dir':str(DATA_DIR),
        'storage_exists':DATA_DIR.exists(), 'packages':packages,
        'update_note':'This panel reports environment details. It does not automatically rewrite or upgrade application code.'
    })

@app.get('/health')
def health(): return jsonify(status='ok', app='AgentForge Workspace')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', '8000')), debug=False)
