# -*- coding: utf-8 -*-
# 30 问实测驱动：POST :4100/chat（agent-svc）→ raw JSON 落盘 → /v1/sql 抓编译 SQL
# 用法: python run.py            # 问数 + 抓 SQL
#       python run.py --sql     # 只补抓 SQL（问数已完成时）
import json, os, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'raw')
SQLDIR = os.path.join(HERE, 'sql')
CHAT = 'http://localhost:4100/chat'
SQL_API = 'http://localhost:4000/cubejs-api/v1/sql'
CUBEJS_SECRET = None  # 延迟读 .env


def token():
    global CUBEJS_SECRET
    if not CUBEJS_SECRET:
        env = os.path.join(HERE, '..', '..', '.env')
        with open(env, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if line.startswith('CUBEJS_API_SECRET='):
                    CUBEJS_SECRET = line.split('=', 1)[1].strip().strip('"').strip('\r')
                    break
    return CUBEJS_SECRET


def post_json(url, body, timeout, auth=None):
    headers = {'Content-Type': 'application/json'}
    if auth:
        headers['Authorization'] = 'Bearer ' + auth
    req = urllib.request.Request(url, data=json.dumps(body).encode('utf-8'), headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def ask_once(q, sid, timeout=660):
    t0 = time.time()
    try:
        out = post_json(CHAT, {'question': q, 'sessionId': sid}, timeout)
        return out, time.time() - t0, None
    except Exception as e:
        return None, time.time() - t0, str(e)[:300]


def ask(qid, q):
    sid = 'nlq1021-' + qid
    out, dt, err = ask_once(q, sid)
    if err or not isinstance(out, dict) or out.get('error'):
        # 失败重试一次（新 sessionId，避免 resume 到坏上下文）
        sid2 = sid + '-r2'
        out2, dt2, err2 = ask_once(q, sid2)
        if not err2 and isinstance(out2, dict) and not out2.get('error'):
            return qid, out2, dt2, sid2, None
        return qid, {'type': 'error', 'error': (err or (out or {}).get('error') or err2)}, dt + dt2, sid2, (err or '') + ' | ' + (err2 or '')
    return qid, out, dt, sid, None


def flatten(x):
    if isinstance(x, str):
        return x
    if isinstance(x, list):
        return ''.join(flatten(i) for i in x)
    return str(x)


def fetch_sql(qid, query):
    try:
        resp = post_json(SQL_API, {'query': query}, 60, auth=token())
        if 'sql' in resp and resp['sql'].get('sql'):
            return flatten(resp['sql']['sql'])
        return '-- /v1/sql 无 sql 字段: ' + json.dumps(resp, ensure_ascii=False)[:400]
    except Exception as e:
        return '-- /v1/sql 失败: ' + str(e)[:300]


def main():
    only_sql = '--sql' in sys.argv
    os.makedirs(RAW, exist_ok=True)
    os.makedirs(SQLDIR, exist_ok=True)
    with open(os.path.join(HERE, 'questions.json'), encoding='utf-8') as f:
        questions = json.load(f)

    if not only_sql:
        todo = [x for x in questions if not os.path.exists(os.path.join(RAW, x['id'] + '.json'))]
        print('todo %d questions' % len(todo), flush=True)
        results = {}
        with ThreadPoolExecutor(max_workers=2) as ex:
            futs = {ex.submit(ask, x['id'], x['q']): x for x in todo}
            for fu in as_completed(futs):
                qid, out, dt, sid, err = fu.result()
                with open(os.path.join(RAW, qid + '.json'), 'w', encoding='utf-8') as f:
                    json.dump({'sessionId': sid, 'elapsed_sec': round(dt, 1),
                               'question': futs[fu]['q'], 'response': out}, f, ensure_ascii=False, indent=2)
                print('%s %s %.1fs %s' % (qid, (err or 'err') if err else out.get('type', '?'), dt, sid), flush=True)

    # 逐问抓编译 SQL（answer 态才有 query）
    with open(os.path.join(HERE, 'status.json'), 'w', encoding='utf-8') as f:
        pass
    summary = []
    for x in questions:
        p = os.path.join(RAW, x['id'] + '.json')
        if not os.path.exists(p):
            summary.append({'id': x['id'], 'type': 'missing'})
            continue
        rec = json.load(open(p, encoding='utf-8'))
        resp = rec.get('response') or {}
        entry = {'id': x['id'], 'type': resp.get('type', '?'), 'elapsed': rec.get('elapsed_sec')}
        if resp.get('type') == 'answer':
            sp = os.path.join(SQLDIR, x['id'] + '.sql')
            if not os.path.exists(sp):
                queries = (resp.get('tables') or [])
                sqls = []
                for i, t in enumerate(queries):
                    qq = t.get('query')
                    if qq:
                        sqls.append('-- table[%d] %s\n%s' % (i, t.get('title', ''), fetch_sql(x['id'], qq)))
                with open(sp, 'w', encoding='utf-8') as f:
                    f.write('\n\n'.join(sqls))
            entry['sql'] = True
        summary.append(entry)
    with open(os.path.join(HERE, 'status.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print('ALL DONE: %d entries' % len(summary), flush=True)


if __name__ == '__main__':
    main()
