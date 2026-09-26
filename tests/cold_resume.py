"""Synthetic app-server cold resume with the retained desktop task settings."""
import hashlib,json,os,queue,subprocess,sys,threading,time,uuid
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer

binary=Path(sys.argv[1]).resolve()
root=Path(__file__).resolve().parents[1]/'replay-results'/('cold-'+uuid.uuid4().hex)
home=root/'home';home.mkdir(parents=True);workspace=root/'workspace';workspace.mkdir()
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_POST(self):
        self.rfile.read(int(self.headers.get('Content-Length',0)))
        events=[{'type':'response.created','response':{'id':'synthetic-response'}},
            {'type':'response.output_item.done','item':{'type':'message','role':'assistant','id':'synthetic-message','content':[{'type':'output_text','text':'Synthetic completed.'}]}},
            {'type':'response.completed','response':{'id':'synthetic-response','usage':{'input_tokens':0,'output_tokens':0,'total_tokens':0}}}]
        raw=''.join('event: '+e['type']+'\ndata: '+json.dumps(e)+'\n\n' for e in events).encode()
        self.send_response(200);self.send_header('Content-Type','text/event-stream');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
server=ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
def config(model,effort):
    return f'''model_provider = "fixture"
model = "{model}"
model_reasoning_effort = "{effort}"
[model_providers.fixture]
name = "Synthetic loopback"
base_url = "http://127.0.0.1:{server.server_port}/v1"
wire_api = "responses"
requires_openai_auth = false
'''
(home/'config.toml').write_text(config('fixture-old','high'))
env=os.environ.copy();env.update(CODEX_HOME=str(home),CODEX_SQLITE_HOME=str(home))
for key in ('OPENAI_API_KEY','CODEX_API_KEY','DEEPSEEK_API_KEY'):env.pop(key,None)
class Client:
    def __init__(self):
        self.log=(root/('stderr-'+uuid.uuid4().hex+'.log')).open('w')
        self.p=subprocess.Popen([str(binary),'app-server'],env=env,cwd=workspace,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,text=True,encoding='utf8',creationflags=0x08000000)
        self.q=queue.Queue();self.id=0
        threading.Thread(target=lambda:[self.q.put(json.loads(line)) for line in self.p.stdout if line.strip()],daemon=True).start()
        self.call('initialize',{'clientInfo':{'name':'synthetic-test','version':'1'},'capabilities':{'experimentalApi':True}})
        self.p.stdin.write(json.dumps({'method':'initialized','params':{}})+'\n');self.p.stdin.flush()
    def call(self,method,params):
        self.id+=1;request_id=self.id
        self.p.stdin.write(json.dumps({'id':request_id,'method':method,'params':params})+'\n');self.p.stdin.flush()
        deadline=time.monotonic()+60
        while time.monotonic()<deadline:
            message=self.q.get(timeout=max(0.1,deadline-time.monotonic()))
            if message.get('id')==request_id:
                if 'error' in message:raise RuntimeError(message['error'])
                return message['result']
        raise TimeoutError(method)
    def finish_turn(self):
        deadline=time.monotonic()+60
        while time.monotonic()<deadline:
            message=self.q.get(timeout=max(0.1,deadline-time.monotonic()))
            if message.get('method')=='turn/completed':return
        raise TimeoutError('turn/completed')
    def close(self):
        self.p.stdin.close();self.p.wait(timeout=30);self.log.close()
try:
    first=Client();started=first.call('thread/start',{'cwd':str(workspace),'approvalPolicy':'never','sandbox':'read-only','model':'fixture-old','modelProvider':'fixture','persistExtendedHistory':True})
    task=started['thread']['id']
    first.call('turn/start',{'threadId':task,'input':[{'type':'text','text':'Synthetic task.','textElements':[]}],'effort':'high'})
    first.finish_turn();first.close()
    before={p.name:p.read_bytes() for p in home.rglob('*.jsonl')}
    (home/'config.toml').write_text(config('fixture-new','low'))
    second=Client();resumed=second.call('thread/resume',{'threadId':task,'model':started['model'],'modelProvider':started['modelProvider'],'config':{'model_reasoning_effort':'high'}});second.close()
    after={p.name:p.read_bytes() for p in home.rglob('*.jsonl')}
    preserved=bool(before) and all(after.get(name,b'').startswith(raw) for name,raw in before.items())
    passed=resumed['model']=='fixture-old' and resumed['modelProvider']=='fixture' and resumed.get('reasoningEffort')=='high' and preserved
    result={'status':'passed' if passed else 'failed','backend_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'global_model_changed':True,'retained_model':resumed['model'],'retained_effort':resumed.get('reasoningEffort'),'resume_uses_saved_task_settings':True,'existing_history_bytes_preserved':preserved,'real_task_data':False}
    (root/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result));sys.exit(0 if passed else 1)
finally:server.shutdown();server.server_close()
