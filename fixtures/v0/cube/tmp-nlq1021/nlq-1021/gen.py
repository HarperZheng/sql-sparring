# -*- coding: utf-8 -*-
# 从 raw/*.json + sql/*.sql 生成整理稿 MD（结论速览 + 每问四件套：问题/query/SQL/答案；ask 态含追问轮）
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'record-draft.md')

BASELINES = {
    'q01': '183.32 亿 / 1,101 笔',
    'q02': '—',
    'q03': '同比指标（28 号方案固化族）',
    'q04': '报文日期轴',
    'q05': '160.16 亿 / 0.8737',
    'q06': '—',
    'q07': '教育厅系实测 160.47 亿（parent_agen 树自联结）',
    'q08': '—',
    'q09': '1 级也有 23 个叶子单位可直接挂缴款',
    'q10': "is_received='0'，F11 催缴场景",
    'q11': '103 大类叶子科目',
    'q12': '科目树下钻实测 3,085.08 万',
    'q13': '—',
    'q14': '—',
    'q15': '—',
    'q16': '州市/区县内联维度',
    'q17': 'fchgrgnname，5 区划全分布',
    'q18': '—',
    'q19': 'frecbankname，9 家银行 100% 非空',
    'q20': 'frecrgnname 含空串与「中央」特殊值',
    'q21': '已划拨 24,815 / 未划拨 47,692.62',
    'q22': '(9,1)=24 行 / (9,0) 中间态 415.5 万',
    'q23': '正确口径 428（expression 含空串假批次缺陷）',
    'q24': "is_cleared='0'，515 行",
    'q25': 'instructions 已写明逐组成立',
    'q26': '期望 nomatch：无区划层级 dim、fsharerate 缓建、划入单位族全空',
    'q27': "期望 nomatch：只能 funds_nature='2' 近似，无命名指标",
    'q28': '期望 nomatch：缴款人维度未建模',
    'q29': '期望 nomatch：une_ 汇缴体系明细未建模',
    'q30': '期望 nomatch：到账日期轴/退付缓建未建模',
}

TYPE_CN = {'answer': 'answer（可答）', 'ask': 'ask（歧义反问）', 'nomatch': 'nomatch（答不了）',
           'error': 'error（链路失败）'}

REVIEW = {
    'q01': '基准 183.32 亿/1,101 笔与 Cube 口径不符：Cube 侧 2022 年=182.09 亿/334 缴款书（pay_date 轴），183.32 亿实为**全库**缴款总额（q05/q17 交叉一致）；1,101 笔疑为 Datus 侧 fne_fund_main 明细口径，Cube 侧各口径（缴款书 968、明细 1,272）均未复现。ask 反问合规（income_sort vs funds_nature 分叉），追问选项 1 落地；反问文案中「18.2 亿」与落地 182.09 亿量级不符，系文案瑕疵。',
    'q02': '✓ 与能力声明一致：固化环比成员（amt_mom_diff/rate）绑定成功，57 个月全分布，上月缺失报 null（合规），预聚合命中。',
    'q03': '同比固化成员绑定成功，但 pay_date 轴下清分记录为空→「无法计算」系合规空集拍板。清分事实须换轴才有数（trans/分入侧日期），同环比族按 pay_date 固化——问清分同比需先指定轴，能力**半可用**（成员在、默认轴无数据）。',
    'q04': '各年数字与 q22 交叉一致（2022-2024+2026 合计≈29,455,929.14=q22 两态之和）✓。但时间轴用 build_date（建单日）——meta 无「报文日期」成员，文件指定的报文日期轴在 Cube 面不存在，build_date/enter_date/reconcile_date 是仅有的缴库日期族。',
    'q05': '✓ **与基准完全一致**（160.16 亿 / 0.8737）。ask 反问合规（分入 vs 划拨双口径），拍板分入口径并回写词典；分子分母跨视图分查后答案层相除，占比走答案层符合契约。',
    'q06': '2022 年仅 9 个执收单位有缴款，如实报 9 组并说明无第 10 名 ✓；名称列一码多名拼接不作准（已知特征）。',
    'q07': '**与文件能力声明直接相悖**：文件称可答（parent_agen 树自联结，实测 160.47 亿），Cube 部署面无任何单位层级成员（单位仅平级编码/名称维度），nomatch 判定合规且缺口精确。能力盘点系 Datus 侧 fne_fund_main.yml 口径，Cube 面需补层级建模或修正清单。',
    'q08': '清分金额双口径并列对比（trans_amt/im_amt）+ 明示「未做单一拍板」——问句本身口径含糊，并列是契约允许处置。25 单位，与 q05/q21 交叉一致。',
    'q09': '同 q07：无单位层级成员即无法定义「非叶子」，nomatch 合规；文件「1 级 23 叶子」声明在 Cube 面不可验证。',
    'q10': '文件建议 is_received=\'0\'——Cube 面无 is_received 成员（成员面仅 state/eff_date），agent 反问后采用 state=\'1\'+有效期过期的催缴口径（1 笔）并回写词典。口径偏离文件建议但属 Cube 面唯一可用口径。',
    'q11': '✓ 103010201 占大类 99.81%，与「一码两名」已知特征一致；startsWith 前缀过滤合规（filter 三元组，无 SQL 片段）。',
    'q12': '✓ 历年合计 3,085.09 万 ≈ 基准 3,085.08 万（分项口径一致）。同比列在 item 过滤+年分组下空集→未纳入且未代算（28 号方案机判合规）。71.5s 全场最长（树下钻试探成本）。',
    'q13': '**链路缺陷非数据问题**：引擎 success（12 turns），最终 JSON 畸形（assumption 键值混入 plan 数组内）致服务端解析 502，重试同型失败。完整答案已从日志恢复（附录 A）：政府性基金 99.7437%/专项 0.1688%/行政事业性收费 0.0874%/罚没 306 元，分母 183.32 亿与 q05 交叉一致。输出形态兜底（FIRST_INSTRUCTION 第 4 条）未挡住嵌套错位，需加固。',
    'q14': '✓ 三类齐全 + 空编码 23.15 亿单列（与 q20 空区划组一致）。',
    'q15': 'bus_type 编码 1/2 的直缴/汇缴映射 meta 未透出，agent 拒绝臆测、编码原样展示——**合规**；但 q25/q29 会话内自行给出映射（说明映射散落未固化），建议写进 ai_context 或词典。',
    'q16': '✓ 16,016,079,467.68 与 q05 分入合计完全一致。',
    'q17': '**选错维度（全场最重）**：问「执收区划」，分组用了 rec_rgn_code（收入区划；ai_context 明确 rec_* 前缀=收入侧），而 meta 明确存在 chg_rgn_code（执收区划编码）。agent 引用 ai_context 辩称「规定使用 rec_rgn_code」——ai_context 只列举分组用 code 的例子，无执收区划→rec_rgn 映射，属错误辩护。数字内部自洽但维度错误，正确口径应按 chg_rgn_code 重查。',
    'q18': '3 单位 4 笔 79,406.12 元；五华区=530102 系 agent 区划分组实测对应（无名称→编码字典），合理。注意其区划过滤维度未明示（chg_rgn/rec_rgn 之辨同 q17）。',
    'q19': '✓ 334 笔与 q01 缴款书笔数一致；2022 年 6 家银行（基准「9 家」为全量口径差异）；银行口径用 rec_bank_code（另有 rec_acct_bank 开户行名）合理。',
    'q20': '✓ 文件警示的空串/特殊值全部命中并合规处置：空编码 23.15 亿计入「以外」（占 99.9%），拍板透明且给出剔除后数字（116.95 万/39 笔）。',
    'q21': '与基准数字主语不同：文件基准 24,815/47,692.62（合计恰为 72,507.62）是**划拨子集内部**的状态拆分；agent 以全量清分为主语（160.16 亿 vs 7.25 万）。is_transfer 实测全空（新数据发现），金额差值口径合规。需对齐「已划拨/未划拨」的口径定义后重测。',
    'q22': 'income_status 成员在 Cube 面不存在（meta 实证，仅 status/enter_status/reconcile_status），enter_status 是唯一入库状态成员——agent 选择正确。基准 (9,1)=24 行/415.5 万与 agent 26 行/2,940.96 万不可直接比（不同字段+不同表范围）。',
    'q23': '**已知缺陷复现**：fcollectid 去重口径模型无成员；agent 反问后按 collect_flag=1 得 550 条记录，文件基准 428 为 fcollectid 去重真实批次数（expression 含空串假批次缺陷仍在）。550≠428 系记录数 vs 去重口径+假批次。词典已回写。',
    'q24': 'is_cleared 成员在 Cube 面不存在（meta 实证，仅 clear_date），「clear_date 为空」是唯一可用口径——439 缴款书/23.15 亿。与基准 515 行（is_cleared=\'0\'）不可直接比（成员缺失+缴款书 vs 行数口径）。',
    'q25': '**真实建模缺口**：跨 view 无 join path 实证报错（"Can\'t find join path to join \'fiscal_collection\', \'fiscal_allocation\'"）——文件「逐组成立」的直缴/汇缴清分率拆分在 Cube 面查不了，需联查 view。主口径划转成功 0/728=0.00%（trans_stats=9 全库 0 条，与 q21 is_transfer 全空互证：划拨环节基本未发生）。参考表给出缴款侧直缴/汇缴分布（120 票/209 行与 q29 一致）。',
    'q26': '未如文件预期 nomatch：以划入方平级维度（rec_rgn_code×rec_agency_code）近似并明示层级缺失，口径透明。严格按契约「完全没覆盖→nomatch」应反问，agent 选择了透明近似作答（边界行为）。划入单位族「实测全空」的文件声明与 Cube 面不符（rec_agency_code 有值，29 组）。划拨合计 72,507.62 与 q05/q21 一致 ✓。',
    'q27': '**优于预期**：bgt_style（资金管理方式 1=国库/2=专户/4=其他）正是国库/专户区分成员，08 文件漏盘此口径。国库 160.16 亿与清分分入合计一致 ✓。',
    'q28': 'payer_name 已建模（meta 实证）但全空脱敏 → agent 按空结果拍板「无有效名单」，实质结论与文件 nomatch 预期一致（缴款人不可用）。18,208,936,572.27 与 q01 一致 ✓。「未建模」表述应修正为「已建模但数据脱敏为空」。',
    'q29': 'agent 把「汇缴」落到 bus_type=\'2\'（120 票/209 行/22.85 亿）——对问句字面合理并已回写词典；但文件所指缺口是 une_ 汇缴体系明细（未建模），该缺口未显式宣告。属问句歧义（体系明细 vs 业务类型）而非 agent 错误。',
    'q30': 'nomatch 合规：退付成员成员面全空+词典无词条；且 agent 明示「到账日期可查」并给替代方案（received_date/entered_amt 实测有数 2022-2026 五个年度组）。**08 文件「到账日期轴数据空缺」缺口声明已过时**。缺口文案引用 UBR_PAYCODE 0 行属记忆召回，轻微越线（无实害）。',
}

FINDINGS = [
    ('维度选错 1 例（q17，最重）',
     '问「执收区划」按 rec_rgn_code（收入区划）分组，meta 明有 chg_rgn_code；agent 还引用 ai_context 做错误辩护。建议：ai_context 或词典显式固化区划族（执收=chg_* / 收入=rec_*）映射。'),
    ('08 文件能力盘点与 Cube 部署面落差（4 例）',
     'q07/q09 单位层级（文件称可答、Cube 面无层级成员）；q21 基准口径为划拨子集拆分（且 is_transfer 全空是新发现）；q22 income_status 不存在（仅 enter_status）；q24 is_cleared 不存在（仅 clear_date 空）。'),
    ('08 文件缺口声明过时（3 例）',
     '到账日期轴（received_date 有数 2022-2026、entered_amt 同环比族齐全）；国库/专户（bgt_style 可直接答，q27）；缴款人（payer_name 已建模、脱敏全空，q28）。'),
    ('ask 态 6 问全部合规反问且追问后落地',
     '非税缴款/清分率/欠缴/汇总批次/直缴汇缴清分率/汇缴明细——每问给出带依据的选项，拍板后均出答案并回写词典，无静默选口径。'),
    ('已知缺陷复现 2 例 + 新发现 1 例',
     'q23 空串假批次（550 条≠真批次 428）；q25 跨 view 无 join path（直缴/汇缴清分率查不了，需联查 view）；新发现 is_transfer 全空、trans_stats=9 全库 0 条（划拨环节基本未发生）。'),
    ('输出形态缺陷 1 例（q13）',
     '引擎 success 但最终 JSON 畸形（assumption 键值混入 plan 数组）→ 服务端解析 502，重试同型失败；完整答案已从日志恢复（附录 A）。建议加固：服务端轻量 JSON 修复或 SKILL 输出兜底加嵌套示例。'),
    ('数字交叉验证全部通过',
     '全库缴款 183.32 亿（q05/q17/q20）、2022 缴款 182.09 亿（q01/q19/q28）、清分分入 160.16 亿（q05/q16/q17/q27）、划拨 72,507.62 元（q05/q21/q26）、民航 3,085.09 万≈基准 3,085.08 万（q11/q12）。'),
    ('基准数字口径注记',
     '文件 q01 基准 183.32 亿/1,101 笔实为全库总额（2022 年应为 182.09 亿/334 缴款书）；1,101 笔在 Cube 侧任何口径均未复现（缴款书 968/明细 1,272）——两套模型（Datus fne_fund_main vs Cube fne_paybook_full_high）数字不可直接对表。'),
    ('未建模清单未盘点',
     'fiscal_collection/fiscal_allocation 的 unmodel 状态=「未盘点」（q07/q09/q30 三处缺口都指向此）——建议先跑一轮未建模盘点再决定补建优先级。'),
]


def load_resp(qid, suffix=''):
    p = os.path.join(HERE, 'raw', qid + suffix + '.json')
    if not os.path.exists(p):
        return None, None
    rec = json.load(open(p, encoding='utf-8'))
    return rec, rec.get('response') or {}


def md_table(rows):
    if not rows:
        return '（空集，0 行）'
    keys = []
    for r in rows:
        for k in r.keys():
            if k not in keys:
                keys.append(k)
    out = ['| ' + ' | '.join(keys) + ' |', '|' + '---|' * len(keys)]
    for r in rows:
        out.append('| ' + ' | '.join(str(r.get(k, '')) for k in keys) + ' |')
    return '\n'.join(out)


def render_answer(L, resp, qid, sql_suffix):
    for ti, tb in enumerate(resp.get('tables') or []):
        head = '**表%d：%s**（%d 行%s）' % (ti + 1, tb.get('title', ''), len(tb.get('rows') or []),
                                           '，截断' if tb.get('truncated') else '')
        L.append(head)
        L.append('')
        L.append(md_table(tb.get('rows') or []))
        L.append('')
        qq = tb.get('query')
        if qq:
            L.append('**生成 query：**')
            L.append('```json')
            L.append(json.dumps(qq, ensure_ascii=False, indent=2))
            L.append('```')
            L.append('')
    sp = os.path.join(HERE, 'sql', qid + sql_suffix + '.sql')
    if os.path.exists(sp):
        sql_txt = open(sp, encoding='utf-8').read().strip()
        ntab = len(resp.get('tables') or [])
        for ti in range(ntab):
            parts = sql_txt.split('\n\n')
            seg = ''
            for pa in parts:
                if pa.startswith('-- table[%d]' % ti):
                    seg = pa
                    break
            if not seg and ntab == 1:
                seg = sql_txt
            if not seg.strip():
                continue
            body = seg.split('\n', 1)[1].strip() if seg.startswith('-- table[') else seg.strip()
            if not body:
                continue
            L.append('<details><summary>编译 SQL（Cube 生成，ClickHouse 方言，点击展开）— 表%d</summary>' % (ti + 1))
            L.append('')
            L.append('```sql')
            L.append(body)
            L.append('```')
            L.append('')
            L.append('</details>')
            L.append('')
    if resp.get('assumption'):
        L.append('**歧义拍板**：%s' % resp['assumption'])
        L.append('')
    L.append('**答案文本**：%s' % (resp.get('answer') or '（空）'))
    L.append('')
    L.append('**计划**：%s' % json.dumps(resp.get('plan') or [], ensure_ascii=False))
    L.append('')


def main():
    questions = json.load(open(os.path.join(HERE, 'questions.json'), encoding='utf-8'))
    sec_titles = []
    by_sec = {}
    for x in questions:
        if x['sec'] not in by_sec:
            by_sec[x['sec']] = []
            sec_titles.append(x['sec'])
        by_sec[x['sec']].append(x)

    L = []
    L.append('# fne_fund_main 问数实测记录（agent-svc 全链路 30 问）')
    L.append('')
    L.append('> 2026-10-21 实测。链路：`POST :4100/chat {question, sessionId}` → agent-svc（claude Agent SDK，effort low）')
    L.append('> → cube-ask skill 主链四步（就绪→解析→/agent/query→整理三态）→ 原样透传。每问独立 sessionId，无会话记忆污染。')
    L.append('>')
    L.append('> 「生成的 SQL」两层留痕：① **语义层 query JSON**（`tables[].query`，agent 真正生成的东西）')
    L.append('> ② **Cube 编译 SQL**（`/cubejs-api/v1/sql` 对同一 query 编译的 ClickHouse 方言，agent 链路本身不产裸 SQL）。')
    L.append('>')
    L.append('> 原始三态 JSON：`D:/develop/cube/.tmp/nlq-1021/raw|sql/`（.tmp 已 gitignore）；过程日志 `D:/develop/cube/logs/agent-svc-*.log`。')
    L.append('> 基准列摘自 [08-自然语言问数能回答的问题](08-fne_fund_main自然语言问数能回答的问题.md)；「复核」为人工对照结论。')
    L.append('')

    # 结论速览
    L.append('## 结论速览')
    L.append('')
    L.append('| # | 问题 | 判定 | 耗时s | 基准 |')
    L.append('|---|---|---|---|---|')
    cnt = {'answer': 0, 'ask': 0, 'nomatch': 0, 'error': 0, 'missing': 0}
    for x in questions:
        rec, resp = load_resp(x['id'])
        if resp is None:
            L.append('| %s | %s | missing | | %s |' % (x['id'], x['q'], BASELINES.get(x['id'], '')))
            cnt['missing'] += 1
            continue
        t = resp.get('type', '?')
        _, fresp = load_resp(x['id'], '-followup')
        if t == 'ask' and fresp is not None and fresp.get('type') == 'answer':
            label = 'ask→追问后 answer'
        else:
            label = TYPE_CN.get(t, t)
        L.append('| %s | %s | %s | %s | %s |' % (
            x['id'], x['q'], label, rec.get('elapsed_sec', ''), BASELINES.get(x['id'], '')))
        cnt[t if t in cnt else 'error'] += 1
    L.append('')
    L.append('**判定分布**：answer %d / ask %d（其中追问后出 answer %d）/ nomatch %d / error %d / missing %d（共 %d）' % (
        cnt['answer'], cnt['ask'],
        sum(1 for x in questions if (load_resp(x['id'])[1] or {}).get('type') == 'ask'
            and (load_resp(x['id'], '-followup')[1] or {}).get('type') == 'answer'),
        cnt['nomatch'], cnt['error'], cnt['missing'], len(questions)))
    L.append('')

    # 每问详情
    for sec in sec_titles:
        L.append('## ' + sec)
        L.append('')
        for idx, x in enumerate(by_sec[sec], 1):
            rec, resp = load_resp(x['id'])
            L.append('### %s　%s' % (x['id'], x['q']))
            L.append('')
            if resp is None:
                L.append('> missing')
                L.append('')
                continue
            t = resp.get('type', '?')
            _, fresp = load_resp(x['id'], '-followup')
            if t == 'ask' and fresp is not None and fresp.get('type') == 'answer':
                label = 'ask→追问后 answer'
            else:
                label = TYPE_CN.get(t, t)
            L.append('- **判定**：%s（sessionId `%s`，首答 %ss，预聚合 %s）' % (
                label, rec.get('sessionId', ''), rec.get('elapsed_sec', '?'),
                '命中' if resp.get('hitPreAgg') is True else ('未命中' if resp.get('hitPreAgg') is False else '—')))
            L.append('- **基准**：%s' % BASELINES.get(x['id'], '—'))
            L.append('')
            if t == 'answer':
                render_answer(L, resp, x['id'], '')
            elif t == 'ask':
                L.append('**反问**：%s' % resp.get('question', ''))
                L.append('')
                L.append('**选项**：')
                for i, o in enumerate(resp.get('options') or []):
                    L.append('%d. %s' % (i + 1, o))
                L.append('')
                if fresp is not None:
                    frec, fresp = load_resp(x['id'], '-followup')
                    L.append('**追问**（同会话续问，耗时 %ss）：%s' % (frec.get('elapsed_sec', '?'), frec.get('followup', '')))
                    L.append('')
                    ft = fresp.get('type', '?')
                    if ft == 'answer':
                        render_answer(L, fresp, x['id'], '-followup')
                    elif ft == 'ask':
                        L.append('追问后仍 ask：%s' % fresp.get('question', ''))
                        L.append('')
                    elif ft == 'nomatch':
                        L.append('追问后 nomatch：%s' % json.dumps(fresp.get('gaps') or [], ensure_ascii=False))
                        L.append('')
                    else:
                        L.append('追问后 error：%s' % json.dumps(fresp, ensure_ascii=False)[:400])
                        L.append('')
            elif t == 'nomatch':
                L.append('**缺口**：%s' % json.dumps(resp.get('gaps') or [], ensure_ascii=False))
                L.append('')
                L.append('**nomatch 原文**：%s' % resp.get('question', ''))
                L.append('')
            else:
                L.append('**error**：%s' % json.dumps(resp, ensure_ascii=False)[:500])
                L.append('')
            rv = REVIEW.get(x['id'])
            if rv:
                L.append('> **复核**：%s' % rv)
                L.append('')
            L.append('---')
            L.append('')
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L))

    # 附录 A：q13 恢复答案 + 附录 B：复现方式
    A = []
    A.append('')
    A.append('## 附录 A：q13 恢复的完整答案')
    A.append('')
    A.append('> q13 引擎执行成功但输出 JSON 畸形（`"assumption":"..."` 键值对混入 `plan` 数组内部，数组未闭合）')
    A.append('> → 服务端 `JSON.parse` 失败 502。以下为从 agent-svc 日志恢复、仅做形态修复（内容零改动）的完整答案：')
    A.append('')
    A.append('```json')
    A.append(open(os.path.join(HERE, 'q13-recovered.json'), encoding='utf-8').read().strip())
    A.append('```')
    A.append('')
    A.append('## 附录 B：执行与复现方式')
    A.append('')
    A.append('**单问手测**（中文 body 必须落盘走 `-d @file`，git-bash 内联中文必 GBK 500）：')
    A.append('')
    A.append('```bash')
    A.append('printf \'{"question":"2022 年全年非税缴款金额和笔数是多少？","sessionId":"nlq-demo-1"}\' > /tmp/q.json')
    A.append('curl -s -X POST http://localhost:4100/chat -H "Content-Type: application/json" -d @/tmp/q.json')
    A.append('```')
    A.append('')
    A.append('**批量实测**（本记录 30 问的驱动，问数+追问+编译 SQL 一条龙）：')
    A.append('')
    A.append('```bash')
    A.append('cd D:/develop/cube/.tmp/nlq-1021')
    A.append('python run.py        # 30 问并发 2 路 → raw/*.json，随后逐 answer 抓 /cubejs-api/v1/sql → sql/*.sql')
    A.append('python followup.py   # ask 态同 sessionId 续问采用第一选项 → raw/*-followup.json + 对应 sql')
    A.append('python gen.py        # 生成本记录（record-draft.md）')
    A.append('```')
    A.append('')
    A.append('要点：每问独立 `sessionId`（agent-svc 以 sessionId resume 引擎会话，独立 id = 无记忆污染）；')
    A.append('编译 SQL 用 `POST /cubejs-api/v1/sql`（body 同 `/agent/query` 的 query），token 取 `.env` 的 `CUBEJS_API_SECRET`；')
    A.append('全程逐块日志在 `logs/agent-svc-YYYY-MM-DD.log`（thinking/tool_use/tool_result 全文）。')
    A.append('')
    A.append('## 附录 C：关键发现（复核结论）')
    A.append('')
    for i, (head, body) in enumerate(FINDINGS, 1):
        A.append('%d. **%s**：%s' % (i, head, body))
    A.append('')
    with open(OUT, 'a', encoding='utf-8') as f:
        f.write('\n'.join(A))
    print('written lines=%d' % len(L))


if __name__ == '__main__':
    main()
