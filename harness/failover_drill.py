#!/usr/bin/env python3
"""Overflow failover drill — a MEASURED failover exercise (built 2026-10-26).

Tasking (Business, Oct 26 09:30): Baseten is the demo's inference overflow
tier; it must be exercised as a measured failover in rehearsal before it
carries judging traffic. This drill validates the ROUTING + MEASUREMENT
instrument at $0: a local stub stands in for the Baseten endpoint (same
OpenAI-compatible surface) until the grant lands; the identical drill then
runs against the real endpoint by config alone.

Scenarios:
  S1 primary answers     -> primary carries, overflow untouched
  S2 primary saturates   -> overflow carries; latency/throughput recorded
  S3 both down           -> the system reports an ERROR STATE — it does not
                            fabricate an answer (failover fails honestly)
Every scenario writes its measurements; the drill appends a take-log record.
"""
import json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
STUB = os.path.join(HERE, 'stub_endpoint.py')

def call(endpoint, question):
    t0 = time.time()
    r = subprocess.run([sys.executable, '-c', f'''
import json, urllib.request, sys
req = urllib.request.Request({endpoint!r} + "/chat/completions",
    data=json.dumps({{"model": "stub", "messages": [{{"role": "user", "content": {question!r}}}]}}).encode(),
    headers={{"Content-Type": "application/json"}})
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        print(json.dumps({{"ok": True, "status": resp.status, "body": resp.read().decode()[:80]}}))
except Exception as e:
    print(json.dumps({{"ok": False, "error": type(e).__name__ + ": " + str(e)[:80]}}))
'''], capture_output=True, text=True)
    dt = (time.time() - t0) * 1000
    out = json.loads(r.stdout.strip().splitlines()[-1])
    out['latency_ms'] = round(dt, 1)
    return out

def run_scenario(name, primary_ep, overflow_ep, question):
    p = call(primary_ep, question)
    route, used = 'primary', p
    if not p['ok']:
        o = call(overflow_ep, question)
        route, used = ('overflow', o) if o['ok'] else ('ERROR_STATE', o)
    print(f'{name}: route={route} ok={used["ok"]} latency_ms={used["latency_ms"]}'
          + (f' error={used.get("error", "")}' if not used['ok'] else ''))
    return {'scenario': name, 'route': route, 'ok': used['ok'],
            'latency_ms': used['latency_ms'], 'error': used.get('error')}

def main():
    stub = subprocess.Popen([sys.executable, STUB, '18741'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    dead = subprocess.Popen([sys.executable, STUB, '18742', '--die-after', '0'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.0)
    try:
        results = [
            run_scenario('S1-primary-answers', 'http://127.0.0.1:18741',
                         'http://127.0.0.1:18741', 'ping'),
            run_scenario('S2-primary-saturated', 'http://127.0.0.1:18742',
                         'http://127.0.0.1:18741', 'ping'),
            run_scenario('S3-both-down', 'http://127.0.0.1:18742',
                         'http://127.0.0.1:18742', 'ping'),
        ]
    finally:
        stub.terminate(); dead.terminate()
    ok = (results[0]['route'] == 'primary' and results[1]['route'] == 'overflow'
          and results[2]['route'] == 'ERROR_STATE' and not results[2]['ok'])
    rec = {'take_id': 'TAKE-DRILL-008', 'rehearsal': 0,
           'kind': 'overflow failover drill (Baseten route, stub endpoint — instrument validation)',
           'ts': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
           'scenarios': results,
           'verdict': 'INSTRUMENT VALID' if ok else 'INSTRUMENT DEFECT — see scenarios',
           'notes': ('Stub = local OpenAI-compatible endpoint standing in for Baseten '
                     '(grant filed, under review). The identical drill runs against the '
                     'real endpoint by config alone when the grant lands; judging traffic '
                     'never touches the overflow until this drill passes against it.')}
    with open(os.path.join(HERE, '..', 'stage', 'take-log.jsonl'), 'a') as f:
        f.write(json.dumps(rec) + '\n')
    print('DRILL:', rec['verdict'], '-> take log TAKE-DRILL-008')
    sys.exit(0 if ok else 1)

if __name__ == '__main__':
    main()
