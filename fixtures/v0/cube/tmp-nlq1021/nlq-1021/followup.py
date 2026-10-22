# -*- coding: utf-8 -*-
# 追问轮：对 ask 态的问题，同 sessionId 续问「采用第一选项」，拿落地答案
import json, os, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'raw')
SQLDIR = os.path.join(HERE, 'sql')
CHAT = 'http://localhost:4100/chat'
SQL_API = 'http://localhost:4000/cubejs-api/v1/sql'


def token():
    env = os.path.join(HERE, '..', '..', '.env')
    with open(env, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if line.startswith('CUBEJS_API_SECRET='):
                return line.split('=', 1)[1].strip().strip('"').strip('\r')
    return ''


def fetch_sql(query):
    try:
        req = urllib.request.Request(SQL_API, data=json.dumps({'query': query}).encode('utf-8'),
                                     headers={'Content-Type': 'application/json',
                                              'Authorization': 'Bearer ' + token()})
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = json.loads(r.read().decode('utf-8'))
        sql = resp.get('sql', {}).get('sql')
        return sql if isinstance(sql, str) else '\n'.join(sql or [])
    except Exception as e:
        return '-- /v1/sql 失败: ' + str(e)[:300]


def post_chat(body, timeout=660):
    req = urllib.request.Request(CHAT, data=json.dumps(body).encode('utf-8'),
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def main():
    for fn in sorted(os.listdir(RAW)):
        if not fn.endswith('.json') or fn.endswith('-followup.json'):
            continue
        qid = fn[:-5]
        fp = os.path.join(RAW, qid + '-followup.json')
        if os.path.exists(fp):
            continue
        rec = json.load(open(os.path.join(RAW, fn), encoding='utf-8'))
        resp = rec.get('response') or {}
        if resp.get('type') != 'ask':
            continue
        opts = resp.get('options') or []
        pick = opts[0] if opts else '按最常见口径直接出答案'
        msg = '就按第一个选项的口径来（%s），直接出答案。' % pick
        t0 = time.time()
        try:
            out = post_chat({'question': msg, 'sessionId': rec['sessionId']})
        except Exception as e:
            out = {'type': 'error', 'error': str(e)[:300]}
        dt = time.time() - t0
        with open(fp, 'w', encoding='utf-8') as f:
            json.dump({'sessionId': rec['sessionId'], 'followup': msg,
                       'elapsed_sec': round(dt, 1), 'response': out}, f, ensure_ascii=False, indent=2)
        # 追问出 answer 时抓编译 SQL
        if out.get('type') == 'answer':
            sp = os.path.join(SQLDIR, qid + '-followup.sql')
            segs = []
            for i, tb in enumerate(out.get('tables') or []):
                if tb.get('query'):
                    segs.append('-- table[%d] %s\n%s' % (i, tb.get('title', ''), fetch_sql(tb['query'])))
            if segs:
                with open(sp, 'w', encoding='utf-8') as f:
                    f.write('\n\n'.join(segs))
        print('%s followup %s %.1fs' % (qid, out.get('type', '?'), dt), flush=True)
    print('FOLLOWUP DONE', flush=True)


if __name__ == '__main__':
    main()
