"""Replay four synthetic image calls through the real binary and loopback HTTP.

No provider credentials or external model service is used. Request bodies stay
in memory; the evidence contains only request shape and fixture hashes.
"""
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from threading import Thread
import os,json,sys,subprocess,hashlib,uuid
import base64,struct
websocket_mode=len(sys.argv)>3 and sys.argv[3]=='websocket'
W=Path(__file__).parent;binary=Path(sys.argv[1]).resolve();label=sys.argv[2]
run=W.parent/'replay-results'/f'{label}-{uuid.uuid4().hex[:8]}';run.mkdir(parents=True)
home=run/'home';home.mkdir();cwd=run/'workspace';cwd.mkdir()
paths=[]
from PIL import Image
for name in ('sample-a.png','sample-b.png','sample-c.png','sample-d.png'):
    path=cwd/name;Image.new('RGB',(4096,4096),(32,64,96)).save(path);paths.append(path)
requests=[];transports=[]
def event(kind,**kwargs):return {'type':kind,**kwargs}
class Handler(BaseHTTPRequestHandler):
    protocol_version='HTTP/1.1'
    def log_message(self,*args):pass
    def do_POST(self):
        body=json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))))
        events=self.events(body,'http')
        data=''.join('event: '+e['type']+'\ndata: '+json.dumps(e)+'\n\n' for e in events).encode()
        self.send_response(200);self.send_header('Content-Type','text/event-stream');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
    def do_GET(self):
        if self.headers.get('Upgrade','').lower()!='websocket':self.send_error(400);return
        accept=base64.b64encode(hashlib.sha1((self.headers['Sec-WebSocket-Key']+'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()).decode()
        self.send_response(101);self.send_header('Upgrade','websocket');self.send_header('Connection','Upgrade');self.send_header('Sec-WebSocket-Accept',accept);self.end_headers()
        self.connection.settimeout(60)
        try:
            while True:
                header=self.rfile.read(2)
                if len(header)!=2 or header[0]&15==8:return
                length=header[1]&127
                if length==126:length=struct.unpack('!H',self.rfile.read(2))[0]
                elif length==127:length=struct.unpack('!Q',self.rfile.read(8))[0]
                mask=self.rfile.read(4) if header[1]&128 else b''
                payload=self.rfile.read(length)
                if mask:payload=bytes(v^mask[i%4] for i,v in enumerate(payload))
                if header[0]&15!=1:continue
                for event_data in self.events(json.loads(payload),'websocket'):
                    raw=json.dumps(event_data).encode();count=len(raw)
                    prefix=bytes([0x81,count]) if count<126 else b'\x81\x7e'+struct.pack('!H',count)
                    self.wfile.write(prefix+raw);self.wfile.flush()
        except (OSError,ValueError):return
    def events(self,body,transport):
        if body.get('generate') is False:
            return [event('response.created',response={'id':'warmup'}),event('response.completed',response={'id':'warmup','usage':{'input_tokens':0,'output_tokens':0,'total_tokens':0}})]
        requests.append(body)
        transports.append(transport)
        seq=len(requests)
        events=[event('response.created',response={'id':f'resp-{seq}'})]
        if seq==1:
            for index,path in enumerate(paths):
                events.append(event('response.output_item.done',item={'type':'function_call','call_id':f'fixture_call_{index}','name':'view_image','arguments':json.dumps({'path':str(path)})}))
        else:
            events.append(event('response.output_item.done',item={'type':'message','role':'assistant','id':'fixture-message','content':[{'type':'output_text','text':'Synthetic four-image replay completed.'}]}))
        events.append(event('response.completed',response={'id':f'resp-{seq}','usage':{'input_tokens':0,'output_tokens':0,'total_tokens':0}}))
        return events
server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=Thread(target=server.serve_forever,daemon=True);thread.start()
config=f'''model_provider = "fixture"
model = "fixture-model"
model_reasoning_effort = "low"
[features]
image_resize_notice = true
responses_websockets_v2 = {str(websocket_mode).lower()}
[model_providers.fixture]
name = "Local synthetic fixture"
base_url = "http://127.0.0.1:{server.server_port}/v1"
wire_api = "responses"
requires_openai_auth = false
supports_websockets = {str(websocket_mode).lower()}
'''
(home/'config.toml').write_text(config,encoding='utf8')
env=os.environ.copy();env['CODEX_HOME']=str(home.resolve());env['CODEX_SQLITE_HOME']=str(home.resolve());env['RUST_LOG']='codex_core::prompt_history_compat=debug'
for key in ('OPENAI_API_KEY','CODEX_API_KEY','DEEPSEEK_API_KEY'):env.pop(key,None)
command=[str(binary),'exec','--ephemeral','--skip-git-repo-check','--json','-s','read-only','Inspect the four synthetic local image fixtures and finish.']
try:
    cp=subprocess.run(command,cwd=cwd,env=env,capture_output=True,text=True,encoding='utf8',errors='replace',timeout=180,creationflags=0x08000000)
finally:server.shutdown();server.server_close()
(run/'events.jsonl').write_text(cp.stdout,encoding='utf8');(run/'stderr.log').write_text(cp.stderr,encoding='utf8')
items=requests[-1].get('input',[]) if len(requests)>1 else []
if websocket_mode:
    by_id={}
    items=[]
    for request in requests:
        for item in request.get('input',[]):
            key=item.get('call_id') or item.get('id') or json.dumps(item,sort_keys=True)
            key=(item.get('type'),key)
            if key not in by_id:by_id[key]=True;items.append(item)
calls=[(i,x.get('call_id')) for i,x in enumerate(items) if x.get('type')=='function_call']
outputs=[(i,x.get('call_id')) for i,x in enumerate(items) if x.get('type')=='function_call_output']
notices=[i for i,x in enumerate(items) if x.get('type')=='message' and '<image_resize_notice>' in json.dumps(x)]
bad_preceding=[i for i,_ in outputs if i>0 and items[i-1].get('type')=='message']
folded=sum('<image_resize_notice>' in json.dumps(items[i]) for i,_ in outputs)
paired=len(calls)==4 and sorted(x[1] for x in calls)==sorted(x[1] for x in outputs)
report={'status':'passed' if cp.returncode==0 and len(requests)==2 and paired and (len(notices)==4 if label.startswith("official-control") else not notices and not bad_preceding) and (not websocket_mode or set(transports)=={"websocket"}) else 'failed','binary':str(binary),'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'binary_version':subprocess.check_output([str(binary),'--version'],text=True).strip(),'exit_code':cp.returncode,'request_count':len(requests),'call_count':len(calls),'output_count':len(outputs),'call_output_pairing':'complete' if paired else 'incomplete','call_positions':[x[0] for x in calls],'output_positions':[x[0] for x in outputs],'notice_message_positions':notices,'message_immediately_before_output':bad_preceding,'folded_notice_output_count':folded,'recorded_items':len(items),'content_logged':False,'transport': sorted(set(transports)),'run':str(run),'fixture_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
(run/'result.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
sys.exit(0 if report['status']=='passed' else 1)
