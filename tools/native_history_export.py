"""Read-only, explicitly partial native-history export. Never creates rollout files."""
import collections,datetime,hashlib,html,json,re,sqlite3
from pathlib import Path

LABEL='PARTIAL_NATIVE_HISTORY_RECOVERY'
# Fail closed for whole items referring to credentials, not just matching values.
SENSITIVE=re.compile(r'(?i)auth\.json|(?:^|[\\/\s])\.env(?:\b|[.])|authorization|access[_ -]?token|refresh[_ -]?token|id_token|api[_ -]?key|client[_ -]?secret|password|passwd|\bpwd\b|private[_ -]?key|BEGIN [A-Z ]*PRIVATE KEY|\bbearer\b|\bcookie\b|\b(?:sk-|ghp_|gho_|github_pat_|AIza)[A-Za-z0-9_-]{12,}|\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+|[?&](?:token|key|secret|sig|credential)=|AWS_SECRET|connection[_ -]?string')

def guarded_payload(raw):
    """Unrecognized opaque secrets cannot be certified; suspicious items are withheld."""
    if SENSITIVE.search(raw):return None,'WITHHELD_POTENTIAL_CREDENTIAL_CONTENT'
    try:return json.loads(raw),'RECOVERED_NATIVE_PROJECTION'
    except (ValueError,TypeError):return None,'UNPARSEABLE_NATIVE_ITEM'

def readonly(path):
    c=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True,timeout=5)
    c.execute('pragma query_only=on')
    denied={sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE,sqlite3.SQLITE_CREATE_TABLE,sqlite3.SQLITE_DROP_TABLE,sqlite3.SQLITE_ALTER_TABLE,sqlite3.SQLITE_ATTACH,sqlite3.SQLITE_DETACH}
    c.set_authorizer(lambda action,*_:sqlite3.SQLITE_DENY if action in denied else sqlite3.SQLITE_OK)
    c.row_factory=sqlite3.Row;c.execute('begin')
    return c

def export_native(state_path,history_path,ids,destination):
    dest=Path(destination)
    if any(dest.iterdir()):raise ValueError('Recovery destination must be empty')
    state=readonly(state_path);history=readonly(history_path);coverage=[]
    try:
        for sid in ids:
            if not re.fullmatch('[A-Za-z0-9-]+',sid):raise ValueError('Unsafe thread ID')
            metadata=state.execute('select id,created_at,updated_at,tokens_used,rollout_path from threads where id=?',(sid,)).fetchone()
            if metadata is None:raise ValueError('Expected native thread is missing: '+sid)
            cols={r[1] for r in history.execute('pragma table_info(thread_items)')}
            wanted=[k for k in ['thread_id','turn_id','item_id','rollout_ordinal','created_at_ms','item_type','started_at_ms','completed_at_ms','updated_at_ordinal','item_json'] if k in cols]
            rows=history.execute('select '+','.join(wanted)+' from thread_items where thread_id=? order by rollout_ordinal,item_id',(sid,)).fetchall()
            folder=dest/sid;folder.mkdir();items=[];types=collections.Counter();states=collections.Counter();ordinals=[]
            for row in rows:
                v=dict(row);raw=v.pop('item_json');payload,status=guarded_payload(raw);states[status]+=1;types[v.get('item_type','unknown')]+=1
                ordinals.append(v['rollout_ordinal'])
                items.append(dict(label=LABEL,native_metadata=v,recovery_status=status,payload=payload,provenance=dict(database=str(Path(history_path).resolve()),table='thread_items',thread_id=sid,item_id=v['item_id'],rollout_ordinal=v['rollout_ordinal'],source_item_sha256=hashlib.sha256(raw.encode('utf8')).hexdigest())))
            turns=[]
            for row in history.execute('select * from thread_turns where thread_id=? order by rollout_ordinal,turn_id',(sid,)):
                v=dict(row)
                if 'error_json' in v and v['error_json']:
                    _payload,status=guarded_payload(v['error_json'])
                    if status!='RECOVERED_NATIVE_PROJECTION':v['error_json']='[WITHHELD]'
                turns.append(v)
            assess=dict(label=LABEL,thread_id=sid,native_items=len(items),item_types=dict(types),content_status=dict(states),native_turns=len(turns),available_user_messages=types['userMessage'],available_assistant_items=types['agentMessage'],unfinished_items=sum(x['native_metadata'].get('completed_at_ms') is None for x in items),ordinal_gaps=sum(b>a+1 for a,b in zip(sorted(set(ordinals)),sorted(set(ordinals))[1:])),ordinal_gap_interpretation='Projection ordinals skip non-item rollout records; gaps alone do not prove missing messages.',original_rollout_available=Path(metadata['rollout_path']).exists(),original_thread_id_preserved=True,completeness='PARTIAL; native projection only; original event boundaries and original token usage are unavailable',not_recovered=['original rollout JSONL','original per-event token counts','input/cache/output splits','missing or withheld content'],native_tokens_used_metadata=metadata['tokens_used'],included_in_dashboard_totals=False)
            document=dict(label=LABEL,thread_metadata=dict(metadata),assessment=assess,turns=turns,items=items)
            (folder/'native-history.json').write_text(json.dumps(document,ensure_ascii=False,indent=2),encoding='utf8')
            sections=['<h1>'+LABEL+'</h1><p>Thread '+html.escape(sid)+'</p><p>Partial native projection; excluded from Dashboard usage. Credential-related items are withheld.</p>']
            for item in items:
                v=item['native_metadata'];body=json.dumps(item['payload'],ensure_ascii=False,indent=2) if item['payload'] is not None else item['recovery_status']
                sections.append('<section><h2>'+html.escape(str(v.get('rollout_ordinal'))+' · '+str(v.get('item_type'))+' · '+str(v.get('item_id')))+'</h2><p>'+html.escape(str(v.get('created_at_ms')))+' · '+html.escape(item['recovery_status'])+'</p><pre>'+html.escape(body)+'</pre></section>')
            (folder/'index.html').write_text(page('Native history '+sid,''.join(sections)),encoding='utf8')
            coverage.append(assess)
        index=dict(label=LABEL,threads=coverage,source_databases=[str(Path(state_path).resolve()),str(Path(history_path).resolve())],source_read_mode='mode=ro; query_only; explicit read transaction; authorizer denies writes',source_total_changes=state.total_changes+history.total_changes,contains_original_token_events=False)
        (dest/'INDEX.json').write_text(json.dumps(index,ensure_ascii=False,indent=2),encoding='utf8')
        links='<h1>'+LABEL+'</h1><p>Local private archive. Native token metadata is not Dashboard consumption.</p><ul>'+''.join('<li><a href="'+x['thread_id']+'/index.html">'+x['thread_id']+'</a> · '+str(x['native_items'])+' native items</li>' for x in coverage)+'</ul>'
        (dest/'index.html').write_text(page('Partial native history recovery',links),encoding='utf8')
        return index
    finally:state.close();history.close()

def page(title,body):
    return '<!doctype html><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; img-src \'none\'"><title>'+html.escape(title)+'</title><style>body{font:15px/1.6 system-ui;max-width:1100px;margin:30px auto;padding:20px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f5f8;padding:16px}section{border-top:1px solid #ddd}h2{font-size:15px}</style>'+body
