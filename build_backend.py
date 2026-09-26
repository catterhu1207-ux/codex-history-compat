"""Build the pinned compatibility backend in a fresh, independent source tree."""
from __future__ import annotations
import argparse, hashlib, json, os, re, shutil, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()

def checked(args, cwd=None, env=None):
    return subprocess.check_output(args,cwd=cwd,env=env,text=True,encoding='utf8',errors='replace').strip()

def load_profile(profile):
    folder=ROOT/'profiles'/profile
    if not folder.resolve().is_relative_to((ROOT/'profiles').resolve()):
        raise ValueError('profile_path_must_be_contained')
    data=json.loads((folder/'profile.json').read_text())
    for name,digest in data['files'].items():
        path=(folder/name).resolve()
        if not path.is_relative_to(folder.resolve()) or sha(path)!=digest:
            raise ValueError('profile_file_identity_mismatch:'+name)
    return folder,data

def apply(codex_root, profile):
    folder,data=load_profile(profile);source=codex_root.resolve()
    if checked(['git','rev-parse','HEAD'],source)!=data['upstream_commit']:
        raise ValueError('upstream_commit_mismatch')
    if checked(['git','status','--porcelain'],source):
        raise ValueError('upstream_tree_must_be_clean')
    checked(['git','apply','--check',str(folder/'integration.patch')],source)
    checked(['git','apply',str(folder/'integration.patch')],source)
    core=source/'codex-rs/core/src'
    shutil.copy2(folder/'prompt_history_compat.rs',core/'prompt_history_compat.rs')
    (core/'prompt_history_compat_fixtures').mkdir(exist_ok=True)
    shutil.copy2(folder/'deepseek_notice_batch.json',core/'prompt_history_compat_fixtures/deepseek_notice_batch.json')
    return data

def build(source,target,profile,official_backend=None,target_cache=None,dry_run=False,reuse_verified_source=False):
    folder,data=load_profile(profile)
    profile_digest=sha(folder/'profile.json')
    if sys.version_info < (3,11):raise ValueError('python_3_11_required_for_source_build')
    recipe_sha256=sha(Path(__file__))
    compat_commit=checked(['git','rev-parse','HEAD'],ROOT)
    if os.name!='nt':raise ValueError('windows_build_required')
    if target.exists() and not reuse_verified_source:raise ValueError('target_must_not_exist')
    if not shutil.which('git') or not shutil.which('cargo') or not shutil.which('rustc') or not shutil.which('rustup'):
        raise ValueError('git_and_rust_toolchain_required')
    installed=checked(['rustup','toolchain','list'])
    if not any(line.startswith(data['rust_toolchain']+'-x86_64-pc-windows-msvc ') or line==data['rust_toolchain']+'-x86_64-pc-windows-msvc' for line in installed.splitlines()):
        raise ValueError('pinned_Rust_toolchain_not_installed_no_automatic_install')
    toolchain=checked(['rustc','+'+data['rust_toolchain'],'--version'])
    if not shutil.which('cl'):
        raise ValueError('run_from_x64_MSVC_developer_environment_with_Windows_SDK')
    sdk_version=os.environ.get('WindowsSDKVersion','').rstrip('\\/')
    sdk_root=Path(os.environ.get('WindowsSdkDir',''))
    if not sdk_version or not (sdk_root/'Include'/sdk_version/'um/Windows.h').is_file() or os.environ.get('VSCMD_ARG_TGT_ARCH')!='x64':
        raise ValueError('x64_MSVC_and_Windows_SDK_required')
    if official_backend and sha(official_backend)!=data['official_backend_sha256']:
        raise ValueError('official_backend_identity_mismatch')
    if dry_run:
        return {'status':'dry_run','profile':profile,'upstream_commit':data['upstream_commit'],'rustc':toolchain}
    target.mkdir(parents=True,exist_ok=reuse_verified_source)
    src=target/'source'
    if not reuse_verified_source:
        checked(['git','clone','--no-checkout',str(source or data['upstream_repository']),str(src)])
        checked(['git','config','core.longpaths','true'],src)
        checked(['git','-c','core.autocrlf=false','checkout','--detach',data['upstream_commit']],src)
    if checked(['git','rev-parse','HEAD'],src)!=data['upstream_commit']:raise ValueError('upstream_commit_mismatch')
    upstream_lock=subprocess.check_output(['git','show','HEAD:codex-rs/Cargo.lock'],cwd=src)
    upstream_lock_data=__import__('tomllib').loads(upstream_lock.decode())
    if not reuse_verified_source:apply(src,profile)
    for name,digest in data['source_files'].items():
        path=(src/name).resolve()
        if not path.is_relative_to(src.resolve()) or hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()!=digest:
            raise ValueError('patched_source_identity_mismatch:'+name)
    if reuse_verified_source:
        allowed=set(data['source_files'])|{'codex-rs/Cargo.toml','codex-rs/Cargo.lock'}
        allowed.update('codex-rs/state/migrations/'+row['path'] for row in json.loads((folder/'migrations.json').read_text())['migrations'])
        changed=checked(['git','diff','HEAD','--name-only'],src).splitlines()
        if any(name not in allowed for name in changed):
            raise ValueError('unrelated_source_change_in_cached_build')
        untracked=checked(['git','ls-files','--others','--exclude-standard'],src).splitlines()
        if any(name not in data['source_files'] for name in untracked):
            raise ValueError('unrelated_untracked_source_in_cached_build')
    # The official Windows release embeds CRLF SQL migrations. Treat bytes as data.
    migrations=json.loads((folder/'migrations.json').read_text())['migrations']
    if {p.name for p in (src/'codex-rs/state/migrations').glob('*.sql')}!={row['path'] for row in migrations}:
        raise ValueError('migration_inventory_mismatch')
    for row in migrations:
        p=src/'codex-rs/state/migrations'/row['path']
        raw=p.read_bytes().replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')
        if hashlib.sha256(raw).hexdigest()!=row['sha256'] or hashlib.sha384(raw).hexdigest()!=row['sqlx_sha384']:
            raise ValueError('migration_identity_mismatch:'+row['path'])
        if p.read_bytes()!=raw:p.write_bytes(raw)
    cargo=src/'codex-rs/Cargo.toml'
    text=subprocess.check_output(['git','show','HEAD:codex-rs/Cargo.toml'],cwd=src).decode().replace('\r\n','\n')
    text,count=re.subn(r'(?m)^version = "0\.0\.0"$', 'version = "'+data['version']+'"',text)
    if count not in (0,1) or __import__('tomllib').loads(text)['workspace']['package']['version']!=data['version']:
        raise ValueError('workspace_version_injection_ambiguous')
    if reuse_verified_source and cargo.read_text()!=text:raise ValueError('cached_workspace_manifest_mismatch')
    if cargo.read_bytes()!=text.encode():cargo.write_text(text,encoding='utf8',newline='\n')
    lock=src/'codex-rs/Cargo.lock'
    desired_lock=upstream_lock.decode().replace('version = "0.0.0"','version = "'+data['version']+'"')
    if reuse_verified_source and lock.read_bytes()!=desired_lock.encode():raise ValueError('cached_dependency_lock_mismatch')
    if lock.read_bytes()!=desired_lock.encode():lock.write_text(desired_lock,encoding='utf8',newline='\n')
    after_lock=__import__('tomllib').loads(lock.read_text())
    before_external=[v for v in upstream_lock_data['package'] if 'source' in v]
    after_external=[v for v in after_lock['package'] if 'source' in v]
    if before_external!=after_external:raise ValueError('external_dependencies_changed')
    env=os.environ.copy();env['CARGO_TARGET_DIR']=str((target_cache or Path(env.get('CARGO_TARGET_DIR',str(target/'target')))).resolve())
    env['CARGO_BUILD_JOBS']='1';env['CARGO_PROFILE_DEV_DEBUG']='0';env['CARGO_PROFILE_TEST_DEBUG']='0'
    env['CARGO_PROFILE_RELEASE_LTO']='false';env['CARGO_PROFILE_RELEASE_DEBUG']='0';env['CARGO_PROFILE_RELEASE_STRIP']='symbols'
    commands=[['cargo','+'+data['rust_toolchain'],'test','--locked','-p','codex-core','--lib','prompt_history_compat','--','--test-threads','1'],['cargo','+'+data['rust_toolchain'],'build','--locked','-p','codex-cli','--bin','codex','--release','-j','1']]
    for index,command in enumerate(commands):
        with (target/('test.log' if index==0 else 'build.log')).open('wb') as log:
            cp=subprocess.run(command,cwd=src/'codex-rs',env=env,stdout=log,stderr=subprocess.STDOUT)
        if cp.returncode:raise ValueError('backend_'+('tests' if index==0 else 'build')+'_failed:'+str(cp.returncode))
    binary=Path(env['CARGO_TARGET_DIR'])/'release/codex.exe'
    raw=binary.read_bytes()
    pe_offset=int.from_bytes(raw[60:64],'little')
    if raw[:2]!=b'MZ' or raw[pe_offset:pe_offset+4]!=b'PE\0\0' or int.from_bytes(raw[pe_offset+4:pe_offset+6],'little')!=0x8664:
        raise ValueError('compiled_backend_must_be_windows_x64')
    for row in migrations:
        if bytes.fromhex(row['sqlx_sha384']) not in raw:raise ValueError('compiled_migration_missing:'+row['path'])
    shutil.copy2(binary,target/'codex.exe')
    version=checked([str(target/'codex.exe'),'--version'])
    if version!='codex-cli '+data['version']:raise ValueError('backend_version_mismatch')
    if sha(folder/'profile.json')!=profile_digest or load_profile(profile)[1]!=data:
        raise ValueError('build_profile_changed_during_build')
    for name,digest in data['source_files'].items():
        if hashlib.sha256((src/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()!=digest:
            raise ValueError('patched_source_changed_during_build:'+name)
    if cargo.read_bytes()!=text.encode() or lock.read_bytes()!=desired_lock.encode():
        raise ValueError('workspace_version_or_lock_changed_during_build')
    for row in migrations:
        if sha(src/'codex-rs/state/migrations'/row['path'])!=row['sha256']:
            raise ValueError('migration_source_changed_during_build:'+row['path'])
    manifest={'schema_version':2,'mode':'patched','patch_id':'public-source-'+profile,'compatibility':{'packages':[{'package_version':data['desktop_version'],'package_full_name':'OpenAI.Codex_'+data['desktop_version']+'_x64__2p2nqsd0c76g0'}]},
        'official':{'sha256':data['official_backend_sha256'],'size':official_backend.stat().st_size if official_backend else data.get('official_backend_size',321969456),'pe_machine':'amd64'},
        'patched':{'file':'codex.exe','sha256':sha(target/'codex.exe'),'size':(target/'codex.exe').stat().st_size,'pe_machine':'amd64','authenticode_status':'NotSigned','version_output':version},
        'provenance':{'repository':data['upstream_repository'],'source_commit':data['upstream_commit'],'profile_sha256':sha(folder/'profile.json'),'patch_files':data['files'],'rustc':toolchain,'cargo_lock_sha256':sha(lock),'external_dependencies_unchanged':True,'migration_sha384':{r['path']:r['sqlx_sha384'] for r in migrations},'source_snapshots':{str(p.relative_to(src)):{'sha256':sha(p)} for p in [cargo,lock,*[src/'codex-rs/core/src'/name for name in ['lib.rs','session/turn.rs','compact.rs','compact_remote_v2_attempt.rs','prompt_history_compat.rs']]]}}}
    manifest['provenance'].update({'compat_repository':'https://github.com/catterhu1207-ux/codex-history-compat.git','compat_commit':compat_commit,'build_recipe_sha256':recipe_sha256,'windows_sdk_version':sdk_version,'msvc_tools_version':os.environ.get('VCToolsVersion')})
    if sha(Path(__file__))!=recipe_sha256:raise ValueError('build_recipe_changed_during_build')
    (target/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
    return {'status':'built','manifest':str(target/'manifest.json'),'backend_sha256':manifest['patched']['sha256']}

def main():
    p=argparse.ArgumentParser();p.add_argument('--profile',default='0.158.0-alpha.2');p.add_argument('--source',type=Path);p.add_argument('--target',type=Path);p.add_argument('--official-backend',type=Path);p.add_argument('--target-cache',type=Path);p.add_argument('--apply',type=Path);p.add_argument('--dry-run',action='store_true');p.add_argument('--reuse-verified-source',action='store_true');a=p.parse_args()
    try:
        if a.apply:result=apply(a.apply,a.profile);print(json.dumps({'status':'applied','profile':result['id']}))
        else:
            if not a.target:raise ValueError('target_required')
            print(json.dumps(build(a.source,a.target.resolve(),a.profile,a.official_backend,a.target_cache,a.dry_run,a.reuse_verified_source)))
        return 0
    except (ValueError,OSError,subprocess.CalledProcessError) as error:
        print(json.dumps({'status':'blocked','reason':str(error)}),file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
