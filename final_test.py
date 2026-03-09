import requests, json
from pathlib import Path
from datetime import datetime

BASE = 'http://localhost:8000'
USER = 'final_test'
PROVIDER = 'openai'
PASS = []
FAIL = []

def ok(label): PASS.append(label); print(f'  PASS  {label}')
def fail(label, reason): FAIL.append(label); print(f'  FAIL  {label}: {reason}')

print()
print('=' * 65)
print('ExaCraft Final End-to-End Test')
print('=' * 65)


# ── 1. Health ──────────────────────────────────────────────────────
print('\n1. Health check')
r = requests.get(f'{BASE}/health')
d = r.json()
if d.get('status') == 'healthy' and d.get('workflow_manager_status') == 'active':
    ok('health endpoint')
else:
    fail('health endpoint', d)


# ── 2. Validate profile ────────────────────────────────────────────
print('\n2. Profile validation')
r = requests.post(f'{BASE}/validate-profile', json={'profile': {
    'name': USER, 'education': 'graduate', 'profession': 'data scientist',
    'cultural_background': 'South Asian', 'complexity': 'high'
}})
d = r.json()
if d.get('success') and d.get('valid'):
    ok('validate-profile')
else:
    fail('validate-profile', d)


# ── 3. Sync profile ────────────────────────────────────────────────
print('\n3. Profile sync')
r = requests.post(f'{BASE}/sync-profile', json={'profile': {
    'name': USER, 'education': 'graduate', 'profession': 'data scientist',
    'cultural_background': 'South Asian', 'complexity': 'high', 'location': 'Bangalore'
}})
d = r.json()
if d.get('success') and Path(f'user_profiles/{USER}.json').exists():
    ok('sync-profile + file written')
else:
    fail('sync-profile', d)


# ── 4. Validation errors ───────────────────────────────────────────
print('\n4. Input validation')
r1 = requests.post(f'{BASE}/workflows/feedback/start', json={'topic': 'test'})
r2 = requests.post(f'{BASE}/workflows/feedback/start', json={'user_id': USER})
r3 = requests.post(f'{BASE}/workflows/fake/resume', json={})
if r1.status_code == 400 and 'user_id' in r1.json().get('error', ''):
    ok('missing user_id -> 400')
else:
    fail('missing user_id', r1.json())
if r2.status_code == 400 and 'topic' in r2.json().get('error', ''):
    ok('missing topic -> 400')
else:
    fail('missing topic', r2.json())
if r3.status_code == 400 and 'user_feedback_text' in r3.json().get('error', ''):
    ok('missing feedback_text -> 400')
else:
    fail('missing feedback_text', r3.json())


# ── 5. Cold-start workflow ─────────────────────────────────────────
print('\n5. Cold-start workflow generation')
r = requests.post(f'{BASE}/workflows/feedback/start',
    json={'user_id': USER, 'topic': 'gradient descent', 'provider': PROVIDER})
d = r.json()
tid1 = d.get('thread_id')
if (d.get('success') and d.get('generated_example') and
        d.get('status') == 'awaiting_feedback' and tid1):
    ok('generation + interrupt (cold start)')
    print(f'         example[:90]: {d["generated_example"][:90]}')
else:
    fail('cold-start generation', d.get('error_message') or d)


# ── 6. Accept feedback ─────────────────────────────────────────────
print('\n6. Positive feedback -> accept tool')
r = requests.post(f'{BASE}/workflows/{tid1}/resume',
    json={'user_feedback_text': 'Great example, very clear and relevant!'})
d = r.json()
if d.get('success') and d.get('status') == 'completed' and not d.get('error_occurred'):
    ok('accept feedback -> completed')
else:
    fail('accept feedback', d)

fb = Path(f'data/feedback_history/{USER}.json')
entries = json.loads(fb.read_text()).get('entries', []) if fb.exists() else []
e = next((x for x in entries if 'Great example' in x.get('user_feedback_text', '')), None)
if e and e.get('agent_decision') == 'accept':
    ok(f'accept stored (decision={e["agent_decision"]}, subject_tag={e.get("subject_tag")})')
else:
    fail('accept not stored', entries[-2:] if entries else 'no file')

insights_path = Path(f'data/accept_insights/{USER}.json')
insights = json.loads(insights_path.read_text()).get('insights', []) if insights_path.exists() else []
if insights:
    ok(f'accept insight persisted: "{insights[-1]["insight"][:60]}"')
else:
    fail('accept insight not written', 'file empty or missing')


# ── 7. Regeneration: too hard ──────────────────────────────────────
print('\n7. Critical feedback -> regenerate + new example')
r = requests.post(f'{BASE}/workflows/feedback/start',
    json={'user_id': USER, 'topic': 'gradient descent', 'provider': PROVIDER})
d = r.json(); tid2 = d.get('thread_id'); ex1 = d.get('generated_example', '')
r2 = requests.post(f'{BASE}/workflows/{tid2}/resume',
    json={'user_feedback_text': 'Too abstract and confusing, I dont get it at all'})
d2 = r2.json(); ex2 = d2.get('generated_example', '')
if (d2.get('success') and d2.get('status') == 'awaiting_feedback'
        and d2.get('regeneration_requested') and ex2 and ex2 != ex1):
    ok(f'regenerate triggered, new example returned (loop_count={d2.get("loop_count")})')
    print(f'         new[:90]: {ex2[:90]}')
else:
    fail('regeneration', d2.get('error_message') or d2)
r3 = requests.post(f'{BASE}/workflows/{tid2}/resume',
    json={'user_feedback_text': 'Much better now!'})
d3 = r3.json()
if d3.get('success') and d3.get('status') == 'completed':
    ok('second accept -> workflow completed')
else:
    fail('second accept', d3)


# ── 8. Domain mismatch -> regenerate + flag_pattern ───────────────
print('\n8. Domain mismatch -> regenerate + flag_pattern(domain_preference)')
r = requests.post(f'{BASE}/workflows/feedback/start',
    json={'user_id': USER, 'topic': 'neural networks', 'provider': PROVIDER})
d = r.json(); tid3 = d.get('thread_id')
r2 = requests.post(f'{BASE}/workflows/{tid3}/resume',
    json={'user_feedback_text': 'I am a data scientist, use a data pipeline / MLOps example'})
d2 = r2.json()
entries = json.loads(fb.read_text()).get('entries', []) if fb.exists() else []
e = next((x for x in entries if 'data scientist' in x.get('user_feedback_text', '')), None)
if e:
    log = e.get('agent_decisions_log', [])
    tools = [x.get('tool') for x in log]
    fp = next((x for x in log if x.get('tool') == 'flag_pattern'), None)
    if 'regenerate' in tools and 'flag_pattern' in tools:
        ok(f'regenerate + flag_pattern | type={fp.get("pattern_type")} obs="{fp.get("observation","")[:50]}"')
    else:
        fail('domain flag_pattern', f'tools: {tools}')
else:
    fail('domain entry not found', str([x.get('user_feedback_text', '')[:30] for x in entries[-3:]]))

patterns_path = Path(f'data/learning_patterns/{USER}.json')
patterns = json.loads(patterns_path.read_text()).get('patterns', []) if patterns_path.exists() else []
if patterns:
    ok(f'pattern persisted: [{patterns[-1]["pattern_type"]}] {patterns[-1]["observation"][:55]}')
else:
    fail('learning pattern not written', 'file missing or empty')

if d2.get('status') == 'awaiting_feedback':
    requests.post(f'{BASE}/workflows/{tid3}/resume', json={'user_feedback_text': ''})


# ── 9. Warm-start context injection ───────────────────────────────
print('\n9. Warm-start: context_instruction injected from patterns+insights')
r = requests.post(f'{BASE}/workflows/feedback/start',
    json={'user_id': USER, 'topic': 'overfitting', 'provider': PROVIDER})
d = r.json(); tid4 = d.get('thread_id')
snap = requests.get(f'{BASE}/workflows/{tid4}/state').json().get('state', {})
ci = snap.get('context_instruction', '')
if ci:
    ok(f'context_instruction built: "{ci[:80]}"')
else:
    fail('context_instruction empty on warm start', 'expected patterns+insights to be used')
requests.post(f'{BASE}/workflows/{tid4}/resume', json={'user_feedback_text': ''})


# ── 10. Max loop guard ─────────────────────────────────────────────
print('\n10. Regeneration loop guard (max 3 cycles)')
r = requests.post(f'{BASE}/workflows/feedback/start',
    json={'user_id': USER, 'topic': 'entropy', 'provider': PROVIDER})
d = r.json(); tid5 = d.get('thread_id')
loop = 0; status = 'awaiting_feedback'
while status == 'awaiting_feedback' and loop < 5:
    feedback = 'Still confusing, try again' if loop < 4 else ''
    r2 = requests.post(f'{BASE}/workflows/{tid5}/resume', json={'user_feedback_text': feedback})
    d2 = r2.json(); status = d2.get('status'); loop += 1
    if status == 'awaiting_feedback':
        print(f'         loop {loop}: regen, loop_count={d2.get("loop_count")}')
if loop <= 4 and status == 'completed':
    ok(f'workflow terminated after {loop} feedback rounds (MAX_REGENERATION_LOOPS=3 respected)')
else:
    fail('loop guard', f'loop={loop} status={status}')


# ── 11. Empty feedback skip ────────────────────────────────────────
print('\n11. Empty feedback -> short-circuit skip')
r = requests.post(f'{BASE}/workflows/feedback/start',
    json={'user_id': USER, 'topic': 'bayes theorem', 'provider': PROVIDER})
d = r.json(); tid6 = d.get('thread_id')
r2 = requests.post(f'{BASE}/workflows/{tid6}/resume', json={'user_feedback_text': ''})
d2 = r2.json()
if d2.get('success') and d2.get('status') == 'completed' and d2.get('feedback_processed'):
    ok('empty feedback -> skipped, completed cleanly')
else:
    fail('empty feedback skip', d2)


# ── 12. Workflow management ────────────────────────────────────────
print('\n12. Workflow management endpoints')
r_state = requests.get(f'{BASE}/workflows/{tid1}/state')
d_state = r_state.json()
if d_state.get('success') and not d_state.get('is_interrupted'):
    ok('GET /workflows/{id}/state on completed thread')
else:
    fail('GET state', d_state)

r_list = requests.get(f'{BASE}/workflows?user_id={USER}')
d_list = r_list.json()
if d_list.get('success') and d_list.get('count', 0) > 0:
    ok(f'GET /workflows?user_id lists {d_list["count"]} threads')
else:
    fail('GET workflows list', d_list)

r_del = requests.delete(f'{BASE}/workflows/{tid1}')
if r_del.json().get('success'):
    ok('DELETE /workflows/{id}')
else:
    fail('DELETE workflow', r_del.json())


# ── 13. Error honesty: success=false when generation fails ─────────
print('\n13. Error honesty: success=false when node_generate fails')
from core.workflow_nodes import node_process_feedback
from core.workflow_state import PersonalizedGenerationState
state = PersonalizedGenerationState(
    user_id='test', topic='test', thread_id='t1', provider='openai',
    generated_example=None, error_occurred=True,
    error_message='node_generate error: 429 RESOURCE_EXHAUSTED',
    user_feedback_text='make it simpler', loop_count=0, feedback_processed=False,
)
result = node_process_feedback(state)
if (result.get('error_occurred') and
        not result.get('regeneration_requested') and
        not result.get('feedback_processed')):
    ok('node_process_feedback guard: no crash on None example, skips agent')
else:
    fail('node_process_feedback guard', result)

from core.workflow_manager import WorkflowManager
from langgraph.checkpoint.memory import MemorySaver
wm = WorkflowManager(MemorySaver())
result_field = wm.start_feedback_workflow.__doc__
# Verify the success field is driven by error_occurred (code inspection)
import inspect
src = inspect.getsource(wm.start_feedback_workflow)
if 'not error_occurred' in src:
    ok('workflow_manager: success = not error_occurred (honest error reporting)')
else:
    fail('workflow_manager success flag', 'hardcoded True not replaced')


# ── 14. Data file audit ────────────────────────────────────────────
print('\n14. Data persistence audit')
fb_entries = json.loads(fb.read_text()).get('entries', []) if fb.exists() else []
insights = json.loads(insights_path.read_text()).get('insights', []) if insights_path.exists() else []
patterns = json.loads(patterns_path.read_text()).get('patterns', []) if patterns_path.exists() else []
subject_stats = json.loads(fb.read_text()).get('subject_tag_statistics', {}) if fb.exists() else {}

print(f'         feedback entries : {len(fb_entries)}')
print(f'         accept insights  : {len(insights)}')
print(f'         learning patterns: {len(patterns)}')
print(f'         subject tags     : {list(subject_stats.keys())}')

if len(fb_entries) >= 5:
    ok(f'feedback_history has {len(fb_entries)} entries')
else:
    fail('feedback_history too few entries', len(fb_entries))
if insights:
    ok(f'accept_insights has {len(insights)} entries')
else:
    fail('accept_insights empty', 'expected at least 1')
if patterns:
    ok(f'learning_patterns has {len(patterns)} entries')
else:
    fail('learning_patterns empty', 'expected at least 1')
if subject_stats:
    ok(f'subject_tag_statistics populated: {list(subject_stats.keys())}')
else:
    fail('subject_tag_statistics empty', 'expected tags')


# ── Summary ────────────────────────────────────────────────────────
print()
print('=' * 65)
total = len(PASS) + len(FAIL)
print(f'RESULT: {len(PASS)}/{total} passed, {len(FAIL)} failed')
if FAIL:
    print('FAILURES:')
    for f in FAIL:
        print(f'  - {f}')
print('=' * 65)
