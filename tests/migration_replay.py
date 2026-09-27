"""Initialize the real backend against six purely synthetic migrated databases."""
import hashlib,json,os,queue,sqlite3,subprocess,sys,threading,time
from pathlib import Path

binary,source,home=map(lambda s:Path(s).resolve(),sys.argv[1:4])
root=Path(__file__).resolve().parents[1]
rows=json.loads((root/'profiles/desktop-26.924.2738.0-sqlite-v2/sqlite-migrations.json').read_text())['migrations']
home.mkdir(parents=True,exist_ok=False)
names=list(dict.fromkeys(row['database'] for row in rows))
def snapshot():
    result={}
    for name in names:
        with sqlite3.connect((home/name).as_uri()+'?mode=ro',uri=True) as db:
            result[name]=[(v,bool(ok),bytes(checksum).hex()) for v,ok,checksum in db.execute('SELECT version,success,checksum FROM _sqlx_migrations ORDER BY version')]
    return result
for name in names:
    with sqlite3.connect(home/name) as db:
        db.execute('CREATE TABLE _sqlx_migrations(version BIGINT PRIMARY KEY,description TEXT NOT NULL,installed_on TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,success BOOLEAN NOT NULL,checksum BLOB NOT NULL,execution_time BIGINT NOT NULL)')
        for row in (r for r in rows if r['database']==name):
            raw=(source/row['path']).read_bytes()
            assert hashlib.sha256(raw).hexdigest()==row['sha256']
            assert hashlib.sha384(raw).hexdigest()==row['sqlx_sha384']
            db.executescript(raw.decode())
            db.execute('INSERT INTO _sqlx_migrations(version,description,success,checksum,execution_time) VALUES(?,?,1,?,0)',(row['version'],'synthetic migration',bytes.fromhex(row['sqlx_sha384'])))
before=snapshot()
env=os.environ.copy();env.update(CODEX_HOME=str(home),CODEX_SQLITE_HOME=str(home))
for key in list(env):
    if key.endswith('_API_KEY') or key.endswith('_TOKEN'):env.pop(key,None)
(home/'config.toml').write_text('model_provider="fixture"\n[model_providers.fixture]\nname="Offline fixture"\nbase_url="http://127.0.0.1:1/v1"\nwire_api="responses"\nrequires_openai_auth=false\n')
with (home/'stderr.log').open('w',encoding='utf8') as log:
    p=subprocess.Popen([str(binary),'app-server'],env=env,cwd=home,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,text=True,encoding='utf8',creationflags=0x08000000)
    messages=queue.Queue()
    threading.Thread(target=lambda:[messages.put(json.loads(line)) for line in p.stdout if line.strip()],daemon=True).start()
    def call(i,method,params):
        p.stdin.write(json.dumps(dict(id=i,method=method,params=params))+'\n');p.stdin.flush()
        deadline=time.monotonic()+60
        while time.monotonic()<deadline:
            response=messages.get(timeout=max(.1,deadline-time.monotonic()))
            if response.get('id')==i:
                assert 'error' not in response,response
                return response['result']
        raise TimeoutError(method)
    try:
        call(1,'initialize',{'clientInfo':{'name':'synthetic-migration-replay','version':'1'}})
        p.stdin.write('{"method":"initialized","params":{}}\n');p.stdin.flush()
        assert call(2,'thread/list',{'limit':10})['data']==[]
        p.stdin.close();p.wait(timeout=30)
        assert p.returncode==0
    finally:
        if p.poll() is None:p.terminate();p.wait(timeout=10)
assert snapshot()==before
errors=(home/'stderr.log').read_text()
assert not any(s in errors for s in ('was previously applied but has been modified','migration checksum mismatch','VersionMismatch'))
report=dict(status='passed',database_count=len(names),migration_count=len(rows),migration_records_unchanged=True,real_data_used=False,normal_exit=True,backend_sha256=hashlib.sha256(binary.read_bytes()).hexdigest())
(home/'result.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
