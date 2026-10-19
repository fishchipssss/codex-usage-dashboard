import contextlib,copy,json,os,sqlite3,sys,tempfile,unittest
from pathlib import Path
from unittest import mock
import test_codex_usage_dashboard as existing
d=existing.dashboard
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools import native_history_export as nr

class RecoveryRegressionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.f=existing.CodexUsageDashboardTests()
 def analyzer(self,homes,shared=True,cache=None):
  a=d.CodexUsageAnalyzer(homes,resolve_project_info=False,persistent_cache=cache,source_origins={str(h):'same-machine' for h in homes} if shared else None);self.addCleanup(a.close);return a
 def event(self,t,c,last,model=None):
  x=self.f.total_only_token_event(t,c,last)
  if model:x['payload']['info']['model']=model
  return x
 def test_signed_unsigned_arbitrary_filesystem_id_roundtrip(self):
  cache=d.PersistentParseCache(self.root/'cache.sqlite');self.addCleanup(cache.close)
  for n in [-2**100,-2**63,0,2**63-1,2**63,2**64-1,2**128+13]:
   entry=d.FileParseCacheEntry(1,2,n,n,{},{},False,'','');cache.put(str(n),entry);got=cache.get(str(n));self.assertIsNotNone(got);self.assertEqual((got.device,got.inode),(n,n))
 def test_legacy_signed_cache_compatibility(self):
  c=d.PersistentParseCache(self.root/'legacy.sqlite');self.addCleanup(c.close);c.put('x',d.FileParseCacheEntry(1,2,7,8,{},{},False,'',''));self.assertEqual(c.connection().execute('select typeof(device) from parsed_files').fetchone()[0],'integer');self.assertEqual(c.get('x').device,7)
 def test_cache_failure_falls_back_without_crash(self):
  c=d.PersistentParseCache(self.root/'fallback.sqlite');self.addCleanup(c.close)
  with mock.patch.object(c,'connection') as conn:
   conn.return_value.executemany.side_effect=OverflowError('exact SQLite integer failure');c.put('x',d.FileParseCacheEntry(1,2,2**64,2**128,{},{},False,'',''));conn.return_value.rollback.assert_called_once()
 def test_lossy_real_identity_rejected(self):
  with self.assertRaises(ValueError):d.decode_fs_identity(float(2**64))
 def test_real_windows_cache_hits_and_growth_invalidate(self):
  h=self.root/'home';p=self.f.write_usage_file(h,'active',100,'2026-07-10T10:00:00Z');cp=self.root/'cache.sqlite';cache=d.PersistentParseCache(cp);a=self.analyzer([h],cache=cache);self.assertEqual(a.scan('all')['summary']['usage']['total_tokens'],100);a.close()
  c2=d.PersistentParseCache(cp);b=self.analyzer([h],cache=c2);b.scan('all');self.assertEqual(b.cache_metrics['persistent_hits'],1)
  with p.open('a',encoding='utf8',newline='\n') as f:f.write('\n'+json.dumps(self.event('2026-07-10T10:01:00Z',150,50))+'\n')
  self.assertEqual(b.scan('all')['summary']['usage']['total_tokens'],150)
 def test_explicit_source_configuration_and_missing_home(self):
  cfg=self.root/'sources.json';h=self.root/'absent';cfg.write_text(json.dumps({'version':1,'sources':[{'id':'archive','label':'Archive','codex_home':str(h),'origin_id':'same-machine'}]}));sources,origins=d.source_configuration(cfg);a=d.CodexUsageAnalyzer(sources,resolve_project_info=False,source_origins=origins);self.addCleanup(a.close);s=a.scan('all');self.assertEqual(s['summary']['session_count'],0);self.assertEqual(s['codex_sources'][0]['status'],'unavailable')
 def test_identical_copies_merge_with_provenance(self):
  homes=[self.root/'a',self.root/'b'];p=self.f.write_usage_file(homes[0],'shared',100,'2026-07-10T10:00:00Z');q=homes[1]/'sessions'/p.name;q.parent.mkdir(parents=True);q.write_bytes(p.read_bytes());s=self.analyzer(homes).scan('all');self.assertEqual((s['summary']['session_count'],s['summary']['usage']['total_tokens']),(1,100));self.assertEqual(len(s['sessions'][0]['provenance']),2)
 def test_independent_devices_not_automatically_merged(self):
  homes=[self.root/'a',self.root/'b'];[self.f.write_usage_file(h,'same-id',100,'2026-07-10T10:00:00Z') for h in homes];s=self.analyzer(homes,shared=False).scan('all');self.assertEqual(s['summary']['session_count'],2)
 def test_merged_uid_survives_temporary_copy_unavailability(self):
  homes=[self.root/'a',self.root/'b'];p=self.f.write_usage_file(homes[0],'shared',100,'2026-07-10T10:00:00Z');q=homes[1]/'sessions'/p.name;q.parent.mkdir(parents=True);q.write_bytes(p.read_bytes());a=self.analyzer(homes);uid=a.scan('all')['sessions'][0]['uid'];q.unlink();self.assertEqual(a.scan('all')['sessions'][0]['uid'],uid)
 def test_bounded_crosshome_parent_dependency(self):
  homes=[self.root/'current',self.root/'backup'];parent=self.f.write_usage_file(homes[1],'parent',100,'2026-05-01T10:00:00Z');child=self.f.write_rollout_rows(homes[0],'child',[{'type':'session_meta','payload':{'id':'child','forked_from_id':'parent'}},self.event('2026-07-10T10:00:00Z',150,50)]);a=self.analyzer(homes);allfiles=a.iter_session_files();chosen=[x for x in allfiles if x[1]==child];self.assertIn(parent,[x[1] for x in a.files_with_fork_dependencies(chosen,allfiles)])
 def test_model_breakdown_preserves_cache_reasoning_subsets_and_period(self):
  h=self.root/'h';events=[]
  for ts,model,usage,tier in [('2026-07-10T10:00:00Z','gpt-5',dict(input_tokens=100,cached_input_tokens=80,output_tokens=10,reasoning_output_tokens=4,total_tokens=110),'default'),('2026-07-11T10:00:00Z','gpt-6-sol',dict(input_tokens=200,cached_input_tokens=150,output_tokens=30,reasoning_output_tokens=15,total_tokens=230),'priority')]:
   events.append({'timestamp':ts,'type':'event_msg','payload':{'type':'token_count','info':{'model':model,'service_tier':tier,'total_token_usage':usage,'last_token_usage':usage if not events else dict(input_tokens=100,cached_input_tokens=70,output_tokens=20,reasoning_output_tokens=11,total_tokens=120)}}})
  self.f.write_rollout_rows(h,'mixed',[{'type':'session_meta','payload':{'id':'mixed'}},*events]);a=self.analyzer([h]);s=a.scan('all');by={x['model']:x['usage'] for x in s['summary']['by_model']};self.assertEqual(by['gpt-6-sol']['cached_input_tokens'],70);self.assertEqual(by['gpt-6-sol']['reasoning_output_tokens'],11);self.assertEqual(sum(v['total_tokens'] for v in by.values()),230);self.assertEqual(a.scan('custom','2026-07-11','2026-07-11')['summary']['usage']['total_tokens'],120)
 def test_continuations_reset_and_equal_token_events_are_kept(self):
  homes=[self.root/'a',self.root/'b'];meta={'type':'session_meta','payload':{'id':'continued'}}
  self.f.write_rollout_rows(homes[0],'continued',[meta,self.event('2026-07-10T10:00:00Z',100,100)])
  self.f.write_rollout_rows(homes[1],'continued',[meta,self.event('2026-07-10T10:01:00Z',50,50),self.event('2026-07-10T10:02:00Z',100,50)])
  s=self.analyzer(homes).scan('all');self.assertEqual(s['summary']['usage']['total_tokens'],200);self.assertEqual(len(s['sessions'][0]['counter_resets']),1)
 def test_distinct_session_ids_similar_times_survive(self):
  h=self.root/'h';[self.f.write_usage_file(h,s,100,'2026-07-10T10:00:00Z') for s in ['one','two']];self.assertEqual(self.analyzer([h]).scan('all')['summary']['session_count'],2)
 def test_model_usage_uses_event_model_not_final_model(self):
  h=self.root/'h';self.f.write_rollout_rows(h,'mixed',[{'type':'session_meta','payload':{'id':'mixed'}},self.event('2026-07-10T10:00:00Z',100,100,'gpt-5'),self.event('2026-07-10T10:01:00Z',150,50,'gpt-6-sol')]);s=self.analyzer([h]).scan('all');by={x['model']:x['usage']['total_tokens'] for x in s['summary']['by_model']};self.assertEqual(by,{'gpt-5':100,'gpt-6-sol':50})
 def test_unknown_model_does_not_use_session_final(self):
  detail={'timeline':[{'timestamp':'2026-07-10T10:00:00Z','total_token_usage':{'total_tokens':50},'last_token_usage':{'total_tokens':50}}],'model':'final-model','total_token_usage':{'total_tokens':50}};d.attach_model_usage(detail);self.assertIn('unknown',detail['model_usage'])
 def test_multiple_same_fingerprint_occurrences_preserved_within_fragment(self):
  row={'timestamp':'2026-07-10T10:00:00Z','model':'gpt-5','total_token_usage':{'total_tokens':100},'last_token_usage':{'total_tokens':100}}
  detail={'session_id':'x','environment_id':'o','path':'a','timeline':[row,row]};other={**detail,'path':'b'};merged=d.CodexUsageAnalyzer.merge_continued_session_fragments([({},detail),({},other)]);self.assertEqual(len(merged[0][1]['timeline']),2)
 def test_native_partial_export_preserves_ids_and_withholds_secret_content(self):
  state=self.root/'state.sqlite';hist=self.root/'history.sqlite';dest=self.root/'recovery';dest.mkdir()
  with contextlib.closing(sqlite3.connect(state)) as c,c:
   c.execute('create table threads(id text,created_at integer,updated_at integer,tokens_used integer,rollout_path text)');c.execute('insert into threads values(?,?,?,?,?)',('test-id',1,2,999,'absent.jsonl'))
  with contextlib.closing(sqlite3.connect(hist)) as c,c:
   c.execute('create table thread_items(thread_id text,turn_id text,item_id text,rollout_ordinal integer,created_at_ms integer,item_type text,item_json text)');c.execute('create table thread_turns(thread_id text,turn_id text,rollout_ordinal integer,status text)')
   for i,payload in enumerate([{'text':'hello'},{'api_key':'synthetic-sensitive-value'}]):c.execute('insert into thread_items values(?,?,?,?,?,?,?)',('test-id','turn','item-'+str(i),i,10+i,'userMessage',json.dumps(payload)))
  before=(state.read_bytes(),hist.read_bytes());index=nr.export_native(state,hist,['test-id'],dest);self.assertEqual(index['source_total_changes'],0);self.assertEqual(before,(state.read_bytes(),hist.read_bytes()));text=(dest/'test-id/native-history.json').read_text('utf8');self.assertNotIn('synthetic-sensitive-value',text);self.assertIn('item-1',text);self.assertEqual(index['threads'][0]['content_status']['WITHHELD_POTENTIAL_CREDENTIAL_CONTENT'],1)
 def test_readonly_native_connection_rejects_writes(self):
  p=self.root/'db';sqlite3.connect(p).close();c=nr.readonly(p)
  try:
   with self.assertRaises(sqlite3.DatabaseError):c.execute('create table nope(x)')
  finally:c.close()
 def test_source_permissions_corruption_and_period_totals(self):
  h=self.root/'h';p=self.f.write_usage_file(h,'x',100,'2026-07-10T10:00:00Z')
  with p.open('ab') as f:f.write(b'\nnot-json\n{incomplete')
  p.chmod(0o444)
  try:
   a=self.analyzer([h]);s=a.scan('all');r=a.scan('custom','2026-07-10','2026-07-10');self.assertEqual(r['summary']['usage']['total_tokens'],100);self.assertGreater(s['sessions'][0]['parse_errors'],0);self.assertEqual(sum(x['usage']['total_tokens'] for x in s['daily_usage']),100)
  finally:p.chmod(0o666)

if __name__=='__main__':unittest.main()
