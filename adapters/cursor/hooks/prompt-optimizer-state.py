#!/usr/bin/env python3
import json, os, sys, tempfile, time
from contextlib import contextmanager
from pathlib import Path

STATE_TTL_SECONDS = 30 * 24 * 60 * 60
STATE_LIMIT = 200
QUALITY_GATES = {'pass', 'light', 'full', 'adaptive'}

def normalize_quality_gate(value):
    if isinstance(value, bool):
        return 'adaptive' if value else 'pass'
    return value if isinstance(value, str) and value in QUALITY_GATES else None

def read_json(path: Path, default):
    try:
        if path.exists():
            value=json.loads(path.read_text(encoding='utf-8'))
            return value if isinstance(value, dict) else default
    except Exception:
        pass
    return default

@contextmanager
def state_lock(path: Path):
    lock = path.with_name(path.name + '.lock')
    path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + 5
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            break
        except FileExistsError:
            try:
                if time.time() - lock.stat().st_mtime > 30:
                    lock.unlink()
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() >= deadline:
                raise TimeoutError(f'Could not acquire state lock: {path}')
            time.sleep(0.02)
    try:
        yield
    finally:
        try:
            lock.unlink()
        except FileNotFoundError:
            pass

def write_json_atomic(path: Path, value):
    fd, temp_name = tempfile.mkstemp(prefix=f'.{path.name}.', suffix='.tmp', dir=str(path.parent))
    temp = Path(temp_name)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()

def normalized_config(value):
    if not isinstance(value, dict):
        return {}
    out = {}
    if value.get('behavior') in {'auto', 'preview', 'off'}:
        out['behavior'] = value['behavior']
    if value.get('scope') in {'first', 'all'}:
        out['scope'] = value['scope']
    quality_gate = normalize_quality_gate(value.get('qualityGate'))
    if quality_gate is not None:
        out['qualityGate'] = quality_gate
    if value.get('unsupportedModel') in {'skip', 'generic'}:
        out['unsupportedModel'] = value['unsupportedModel']
    return out

def config_has_invalid_managed_fields(value):
    if not isinstance(value, dict):
        return True
    return (
        ('schemaVersion' in value and (not isinstance(value['schemaVersion'], int) or isinstance(value['schemaVersion'], bool) or value['schemaVersion'] != 1))
        or ('behavior' in value and (not isinstance(value['behavior'], str) or value['behavior'] not in {'auto', 'preview', 'off'}))
        or ('scope' in value and (not isinstance(value['scope'], str) or value['scope'] not in {'first', 'all'}))
        or ('qualityGate' in value and normalize_quality_gate(value['qualityGate']) is None)
        or ('unsupportedModel' in value and (not isinstance(value['unsupportedModel'], str) or value['unsupportedModel'] not in {'skip', 'generic'}))
    )

def read_cfg(root: Path):
    cfg={'behavior':'auto','scope':'all','qualityGate':'adaptive','unsupportedModel':'skip'}
    invalid_config=False
    for p in [Path.home()/'.config/prompt-optimizer/config.json', root/'.prompt-optimizer.json']:
        if not p.exists():
            continue
        try:
            raw=json.loads(p.read_text(encoding='utf-8'))
        except (OSError, UnicodeError, json.JSONDecodeError):
            invalid_config=True
            continue
        if config_has_invalid_managed_fields(raw):
            invalid_config=True
            continue
        value=normalized_config(raw)
        cfg.update(value)
    if invalid_config:
        cfg['behavior']='off'
    return cfg

try:
    inp=json.load(sys.stdin)
except (json.JSONDecodeError, OSError, UnicodeError):
    # A malformed hook payload must not block the user's request.
    print(json.dumps({'continue': True}))
    raise SystemExit
roots=inp.get('workspace_roots') or [os.getcwd()]
root=Path(roots[0])
cfg=read_cfg(root)
conversation=str(inp.get('conversation_id') or '').strip()
generation=str(inp.get('generation_id') or '')
state_path=root/'.cursor/.prompt-optimizer-session-state.json'
first_generation=None
if conversation:
    try:
        with state_lock(state_path):
            sessions=read_json(state_path,{})
            cutoff=time.time()-STATE_TTL_SECONDS
            sessions={key:value for key,value in sessions.items() if not isinstance(value,dict) or not isinstance(value.get('updated_at'),(int,float)) or value['updated_at']>=cutoff}
            entry=sessions.get(conversation) if isinstance(sessions.get(conversation),dict) else {}
            first_generation=entry.get('first_generation') or generation or '__first__'
            sessions[conversation]={'first_generation':first_generation,'updated_at':int(time.time())}
            if len(sessions)>STATE_LIMIT:
                sessions=dict(sorted(sessions.items(),key=lambda item:item[1].get('updated_at',0) if isinstance(item[1],dict) else 0,reverse=True)[:STATE_LIMIT//2])
            write_json_atomic(state_path, sessions)
    except Exception:
        pass
active=cfg.get('behavior')!='off' and (
    cfg.get('scope')!='first'
    or not conversation
    or generation==first_generation
    or not generation
)
state={
  'conversation_id': inp.get('conversation_id'),
  'generation_id': inp.get('generation_id'),
  'model': inp.get('model'),
  'model_id': inp.get('model_id'),
  'model_params': inp.get('model_params') or [],
  **cfg,
  'active': active,
  'updated_at': int(time.time()),
}
out=root/'.cursor/.prompt-optimizer-runtime.json'
with state_lock(out):
    previous=read_json(out,{})
    runtime_sessions=previous.get('sessions') if isinstance(previous.get('sessions'),dict) else {}
    if conversation:
        runtime_sessions[conversation]=state
        cutoff=time.time()-STATE_TTL_SECONDS
        runtime_sessions={key:value for key,value in runtime_sessions.items() if not isinstance(value,dict) or not isinstance(value.get('updated_at'),(int,float)) or value['updated_at']>=cutoff}
        if len(runtime_sessions)>STATE_LIMIT:
            runtime_sessions=dict(sorted(runtime_sessions.items(),key=lambda item:item[1].get('updated_at',0) if isinstance(item[1],dict) else 0,reverse=True)[:STATE_LIMIT//2])
    payload={**state, 'schema': 1, 'sessions': runtime_sessions}
    write_json_atomic(out, payload)
print(json.dumps({'continue': True}))
