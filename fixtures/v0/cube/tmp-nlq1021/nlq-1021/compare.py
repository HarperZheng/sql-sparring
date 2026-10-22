# -*- coding: utf-8 -*-
"""合并 09-datus 与 09-cube 两份实测记录 → 对账文件（2026-10-21）。

格式（已与用户确认）：
  一、对账总表（对照 | 问题 | datus 结果 | cube 结果 | 对照关系）
  二、逐题对照（双方核心数字 + 对账注记只写客观差异不预判 + details 折叠原文）
  三、cube 独有验证题（q26-q30）
注记原则：只陈述双方数字与口径的客观事实差异，不写谁对谁错。
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
NON_TAX = r'D:\develop\datus\Datus-agent\development_process_record\non_tax'
DATUS_MD = os.path.join(NON_TAX, '09-datus-票据链路问数实测记录.md')
OUT_MD = os.path.join(NON_TAX, '10-票据链路问数对账（datus-vs-cube）.md')

PAIRS = ['q%02d' % i for i in range(1, 26)]


# ---------------------------------------------------------------- datus 解析
def parse_datus():
    text = open(DATUS_MD, encoding='utf-8').read()
    ov = {}
    for m in re.finditer(r'^\| (q\d{2}) \| ([^|]*) \| ([^|]*) \| ([^|]*) \| ([^|]*) \|$', text, re.M):
        ov[m.group(1)] = {'cat': m.group(2).strip(), 'status': m.group(4).strip(), 'secs': m.group(5).strip()}
    blocks = {}
    heads = list(re.finditer(r'^## (q\d{2}) (.+)$', text, re.M))
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        blocks[m.group(1)] = {'title': m.group(2).strip(), 'body': text[m.end():end]}
    for b in blocks.values():
        body = b['body']

        def seg(start_marker, next_marker):
            i = body.find(start_marker)
            if i < 0:
                return ''
            i += len(start_marker)
            j = body.find(next_marker, i) if next_marker else -1
            return body[i:j].strip('\n').strip()

        b['metrics'] = seg('- **命中指标**：', '- **SQL**：')
        b['sql'] = seg('- **SQL**：', '- **答案**：')
        b['answer'] = seg('- **答案**：', None)
    return ov, blocks


# ---------------------------------------------------------------- cube 读取
def cube_rec(qid):
    main = json.load(open(os.path.join(HERE, 'raw', qid + '.json'), encoding='utf-8'))
    mresp = main.get('response') or {}
    rec = {'main': main, 'resp': mresp, 'followup': None, 'recovered': False}
    if mresp.get('type') in ('ask', 'error'):
        fp = os.path.join(HERE, 'raw', qid + '-followup.json')
        if os.path.exists(fp):
            rec['followup'] = json.load(open(fp, encoding='utf-8'))
        elif os.path.exists(os.path.join(HERE, 'q13-recovered.json')) and qid == 'q13':
            rec['followup'] = json.load(open(os.path.join(HERE, 'q13-recovered.json'), encoding='utf-8'))
            rec['recovered'] = True
    if rec['followup'] is not None:
        fu = rec['followup']
        rec['eff'] = fu['response'] if isinstance(fu.get('response'), dict) else fu
    else:
        rec['eff'] = mresp
    rec['elapsed'] = (rec['followup'] or main).get('elapsed_sec')
    return rec


def cube_status_label(rec):
    t = rec['resp'].get('type')
    if t == 'answer':
        return 'answer'
    if t == 'nomatch':
        return 'nomatch'
    if t == 'ask':
        tag = '（日志恢复）' if rec.get('recovered') else ''
        return 'ask→追问→answer' + tag
    if t == 'error':
        return 'error(502)→日志恢复' if rec['followup'] else 'error'
    return str(t)


def cube_tables_md(eff):
    out = []
    for tb in eff.get('tables') or []:
        rows = tb.get('rows') or []
        out.append('**%s**（%d 行）' % (tb.get('title') or '结果表', len(rows)))
        if rows:
            cols = list(rows[0].keys())
            out.append('| ' + ' | '.join(c.split('.')[-1] for c in cols) + ' |')
            out.append('|' + '---|' * len(cols))
            for r in rows:
                out.append('| ' + ' | '.join('' if r.get(c) is None else str(r.get(c)) for c in cols) + ' |')
        out.append('')
    return '\n'.join(out)


def cube_query_json(eff):
    parts = []
    for i, tb in enumerate(eff.get('tables') or []):
        q = tb.get('query')
        if not q:
            continue
        head = '-- table[%d] %s' % (i, tb.get('title') or '') if len(eff.get('tables') or []) > 1 else ''
        body = json.dumps(q, ensure_ascii=False, indent=2)
        parts.append((head + '\n' + body) if head else body)
    return '\n\n'.join(parts) if parts else '（无 query JSON）'


def cube_sql(qid, rec):
    cand = []
    if rec['followup'] is not None and rec['resp'].get('type') == 'ask':
        cand.append(os.path.join(HERE, 'sql', qid + '-followup.sql'))
    cand.append(os.path.join(HERE, 'sql', qid + '.sql'))
    for p in cand:
        if os.path.exists(p):
            return open(p, encoding='utf-8').read().strip()
    return '（编译 SQL 未留档）'


# ---------------------------------------------------------------- 逐题内容（人工核对后写定）
# D / C：总表与逐题正文的双方核心数字；N：对账注记（客观差异）；R：总表"对照关系"短语
CONTENT = {
    'q01': dict(
        d='金额 18,208,936,572.27 元（≈182.09 亿）、355 笔；fill_date 落 2022 年、SUM(famt)、COUNT(DISTINCT fid) 去重',
        c='金额 18,208,936,572.27 元、334 笔；pay_date 落 2022 年、SUM(amt)、paybook_count（缴款书数）；追问后按收入类别三类口径作答',
        n=[
            '金额分毫不差：均为 18,208,936,572.27 元。',
            '笔数不同：355（datus，COUNT(DISTINCT fid)）vs 334（cube，paybook_count 缴款书数）。',
            '时间轴不同：datus 用 fill_date（填开日），cube 用 pay_date（缴款日）。',
        ],
        r='金额一致；笔数不同（时间轴与去重键均不同）'),
    'q02': dict(
        d='2021-12 ~ 2026-08 月度表；fill_date 轴；2022-04 尖峰 15,985,631,865.00；无数据月环比显示"—"',
        c='2021-12 ~ 2026-09 共 57 个月；pay_date 轴；固化环比成员 amt_mom_diff / amt_mom_rate，上月缺失报 null',
        n=[
            '时间轴不同（fill_date vs pay_date），各月金额随之不同（如 2022-04：datus 15,985,631,865.00）。',
            '覆盖范围不同：datus 至 2026-08，cube 至 2026-09。',
            '环比空值处理不同：datus 显示"—"（含"上月无基数"），cube 返回 null。',
        ],
        r='口径不同（时间轴不同），月度数字不可直接对照'),
    'q03': dict(
        d='fne_paybook_full_high 按 fcleardate 归年 SUM(fimamt)：2021=0、2022=15,986,577,101.87（320 行）；同比 +159.87 亿，增长率因 2021 基数为 0 不可算',
        c='fiscal_allocation_view 按 pay_date 归年：2022 组合下返回 0 行，无法计算；答案提示可换 trans_date / enter_date 轴',
        n=[
            '查询对象不同：datus 查缴款宽表的 fimamt 按 fcleardate 归年；cube 查划拨视图（trans_amt / im_amt）按 pay_date 归年。',
            'datus 得出 2022 年清分 15,986,577,101.87 元；cube 在其查询组合下返回空集。',
            '参照：cube q05 全库 im_amt 合计 16,016,079,467.68 元与 datus 的 2022 清分数字量级接近（约 99.8%），但两者口径不同（全库无时间轴 vs 2022 年 fcleardate）。',
        ],
        r='对象与时间轴不同；一方有数一方空集'),
    'q04': dict(
        d='fne_treasury_transfer_new，fid 去重 76 行，fmsgdate（报文日期）归年 SUM(ftotalamt)：2022=78,449.12/34、2023=80,659.18/10、2024=3,763.30/15、2025 无、2026=29,372,234.54/17；合计 29,535,106.14',
        c='fiscal_treasury_view，build_date（建单日）归年 SUM(amt)：2022=46,053.04、2023=34,178.26、2024=3,463.30、2025=0、2026=29,372,234.54',
        n=[
            '2026 年金额一致：29,372,234.54 元。',
            '2022-2024 三年不一致：datus 78,449.12 / 80,659.18 / 3,763.30 vs cube 46,053.04 / 34,178.26 / 3,463.30。',
            '时间轴不同：datus fmsgdate（报文日期）vs cube build_date（建单日）。',
            '去重口径不同：datus 按 fid 去重（76 行）vs cube 视图缴库明细直查。',
        ],
        r='2026 一致；2022-2024 不一致（时间轴与去重口径不同）'),
    'q05': dict(
        d='同表单查：fimamt=16,016,079,467.68、famt=18,332,207,203.13、清分率 0.8737',
        c='分入 16,016,079,467.68（allocation 视图 im_amt）+ 缴款总额 18,332,207,203.13（collection 视图 amt），相除 0.8737；追问后落地',
        n=[
            '三个数完全一致：分子、分母、比值。',
            '来源不同：datus 同表两列（fimamt / famt）vs cube 跨两视图两成员（im_amt / amt）分查后相除。',
        ],
        r='完全一致'),
    'q06': dict(
        d='2022（fill_date）9 个执收单位（不足 10 如实报），Top1 测试云南测试环境(试用版) 18,208,882,274.85 / 272 笔（fid 去重）',
        c='2022（pay_date）9 个执收单位，Top1 124045（4 个名称变体以 " / " 拼接）18,208,882,274.85 / 253 笔（paybook_count）',
        n=[
            '两边均返回 9 个执收单位。',
            'Top1 金额一致：18,208,882,274.85 元。',
            'Top1 笔数不同：272（fid 去重）vs 253（paybook_count）。',
            '时间轴不同：fill_date vs pay_date；cube 侧同编码多名称变体拼接展示。',
        ],
        r='主体金额一致；笔数不同（时间轴与去重键不同）'),
    'q07': dict(
        d='fab_agen 树（fpidcode 自联结）查省教育厅 44 家下级单位，合计 183.30 亿；直缴口径 160.47 亿；本部自身无缴款',
        c='nomatch——语义层成员面无单位层级成员，无法按"下级单位"作答',
        n=[
            'datus 通过源表 fab_agen.fpidcode 树形自联结实现：44 家下级、183.30 亿。',
            'cube 语义层无单位层级成员，直接报 nomatch。',
        ],
        r='一方有数，一方声明不可答'),
    'q08': dict(
        d='2022（fill_date）9 单位清分对比，Top1 测试云南测试环境 159.8653 亿、清分率 87.80%',
        c='全量（未限年）25 单位，划拨 trans_amt 与分入 im_amt 双口径并列，Top1 124045：划拨 63,371 元、分入 15,986,585,353.85',
        n=[
            '时间范围不同：datus 限 2022 年 vs cube 全量（未加年份过滤）。',
            '金额口径不同：datus 单一清分口径（fimamt）vs cube 划拨 trans_amt 与分入 im_amt 双口径并列。',
            '主单位分入量级一致（159.87 亿级）；分组数不同（9 vs 25，随时间范围不同）。',
        ],
        r='时间范围与金额口径不同，数字不可直接对照'),
    'q09': dict(
        d='无最终答案——多轮 SQL（31 次）后试图写临时文件被权限拒绝，引擎中断',
        c='nomatch——语义层无单位层级成员',
        n=[
            'datus 引擎运行中断（写文件权限拒绝），未产出最终答案。',
            'cube 报 nomatch（无单位层级成员）。',
        ],
        r='双方均未给出答案'),
    'q10': dict(
        d="fstate='1' + feffdate 已过期（相对 2026-10-21），COUNT(DISTINCT fpaycode)=1 笔（124045）",
        c="追问后同口径 state='1' + eff_date 已过期：1 笔（124045）",
        n=[
            '口径相同（有效 + 已过期），结果一致：1 笔，缴款书 124045。',
            '笔数键表述不同：datus COUNT(DISTINCT fpaycode) vs cube paybook_count（缴款书）。',
        ],
        r='一致'),
    'q11': dict(
        d='指出 103=非税收入、10301=政府性基金（层级修正后作答）；fab_subject 叶子（fisleaf）去重；103010201=15,985,889,302.18/99.81%；103 全前缀 23 叶子合计 160.16 亿',
        c="rec_sub_code startsWith '103' 共 20 组：103010201=15,985,889,302.18（99.81%）、1030110=28,938,336.12、1030106=495,345.65、1030115=495,318.31",
        n=[
            '头部分类数字一致：103010201 = 15,985,889,302.18（99.81%）。',
            "叶子判定方法不同：datus 取 fab_subject 的 fisleaf 标志 vs cube 按 '103' 前缀聚合后声明 20 个编码两两无前缀包含。",
            "datus 先做 103→10301 层级修正再作答；cube 直接按 '103' 前缀聚合。",
        ],
        r='头部数字一致；分类树处理方式不同'),
    'q12': dict(
        d='une_paybook_high（实证 fne ⊂ une 全口径）fitemcode=1030110001、feffdate 轴：2024 峰值 2,912.22 万、历年合计约 3,236 万、含 2027-2029 未来年份',
        c='fiscal_collection_view（fne_paybook_full_high）item_code=1030110001、pay_date 轴：2024 峰值 2,896.20 万、历年合计 3,085.09 万',
        n=[
            '数据源表不同：une_paybook_high（全口径）vs fne_paybook_full_high（fne 直缴链）。',
            '时间轴不同：feffdate（生效日）vs pay_date（缴款日）。',
            '合计不同：约 3,236 万 vs 3,085.09 万（差约 151 万）。',
            'datus 覆盖 2027-2029 未来年份（数据噪声），cube 无。',
        ],
        r='数字不同（数据表与时间轴双差）'),
    'q13': dict(
        d='政府性基金 182.85 亿/99.74%、专项 0.31 亿/0.17%、行政事业性收费 0.16 亿/0.09%、罚没 300 元、未分类 600 元；合计 183.22 亿/1,101 笔（fid 去重）',
        c='502 后从日志恢复：政府性基金 18,285,222,472.21/99.7437%、专项 30,951,894.08/0.1688%、行政事业性收费 16,031,930.84/0.0874%、罚没 306、空 600；分母 18,332,207,203.13',
        n=[
            '各分类数字一致：政府性基金、专项、行政事业性收费、罚没、未分类（元级或接近元级）。',
            'datus 答案文本"合计 183.22 亿"与其自身分项之和（≈183.32 亿）不勾稽；cube 分母 18,332,207,203.13 元。',
            'datus 另计 1,101 笔（fid 去重）；cube 未计笔数。',
        ],
        r='主分类数字一致；datus 合计行与其分项之和不勾稽'),
    'q14': dict(
        d='ffundsnaturecode（缴款票面侧）：12=18,316,046,350.64/1,083 行、2=14,867,151.04、11=1,293,101.45、5=600；合计 18,332,214,203.13/1,272 行',
        c='rec_funds_nature_code（收入归属侧）：政府性基金 16,016,379,742.39/589、一般公共预算 1,184,377.16/63、财政专户 39,329/70、空 2,314,603,154.58/544、其他 600/6',
        n=[
            '取的字段不同：缴款票面 ffundsnaturecode vs 收入归属 rec_funds_nature_code。',
            '数字完全不同（最大组 18,316,046,350.64 vs 16,016,379,742.39）。',
            'cube 存在 544 行空编码组（2,314,603,154.58 元）；datus 无空码组。',
        ],
        r='口径不同（票面 vs 归属），数字不可直接对照'),
    'q15': dict(
        d='按 fitemidcode 归并名称变体后 Top5：农网还贷 530020000079（160.45 亿、直缴 99.81%）、煤炭、民航 3,085.08 万、住宿费、保教费；断言 bus_type 1=直缴 / 2=汇缴',
        c='item_code 分组 Top5：农网还贷 103010201001、煤炭 103010201002、民航 1030110001、农网还贷 a 1030102010011、住宿费 103042758；声明 meta 无 bus_type 映射、编码原样展示',
        n=[
            '项目主键体系不同：fitemidcode（530020000xxx）vs item_code（10301xxxxxx），Top5 集合不同（datus 含保教费，cube 含"农网还贷 a"变体编码）。',
            '名称变体处理不同：datus 按 ID 归并 vs cube 按编码分组、变体分列。',
            'bus_type 映射表述不同：datus 断言 1=直缴/2=汇缴；cube 声明元数据无该映射、按编码原样展示。',
            '民航项目金额量级一致：3,085.08 万 vs 3,085.09 万。',
        ],
        r='口径不同（主键体系不同）；主体项目金额量级一致'),
    'q16': dict(
        d='frecrgncode 分组 fimamt：省本级(530000) 16,016,072,677.53/686 行、中央 4,516.12、昆明市本级 1,778.70、五华区 495.33、云龙县 0；另报空编码 544 行 fimamt 全 NULL',
        c='rec_rgn_code 分组 im_amt：530000=16,016,072,677.53/686、000000=4,516.12/31、530100=1,778.70/8、530102=495.33/1、532929=0/2',
        n=[
            '五组金额与行数分毫不差（16,016,072,677.53/686、4,516.12、1,778.70、495.33、0）。',
            '空编码组：datus 报 544 行 fimamt 全 NULL（不进聚合），cube 未单列空组。',
        ],
        r='完全一致（组级）'),
    'q17': dict(
        d='fchgrgnname（执收区划）分组：云南省本级 18,330,965,893.01/1,081、云龙县 1,156,320、五华区 79,406.12、昆明市本级 5,184、官渡区 400；合计 18,332,205,003.13/1,101',
        c='rec_rgn_code（收入区划）分组：省本级 160.16 亿、空 23.15 亿/544、云龙 1,156,320、中央 9,617.68、昆明 2,541、五华 990.66',
        n=[
            '分组字段不同：datus fchgrgn*（执收区划）vs cube rec_rgn*（收入区划）——题目问"执收区划"。',
            '数字完全不同（datus 主组 183.31 亿 vs cube 省本级 160.16 亿 + 空 23.15 亿）。',
            'datus 出现官渡区组；cube 出现中央组与空组。',
        ],
        r='分组字段不同，数字不可直接对照'),
    'q18': dict(
        d="fchgrgnname='五华区'：3 单位 6 笔（fid 去重）79,406.12（77,324.80 / 1,981.32 / 100）；另给对照口径 frecrgnname='五华区' 仅 990.66",
        c="rec_rgn_code='530102'：3 单位 4 笔 79,406.12，最大 77,324.80（97.3%）",
        n=[
            '金额与单位一致：3 家、合计 79,406.12 元、最大 77,324.80。',
            '笔数不同：6（fid 去重）vs 4（paybook_count）。',
            'datus 另给执收/收入两口径对照（收入口径 990.66）；cube 单口径。',
        ],
        r='金额一致；笔数不同'),
    'q19': dict(
        d='trim(frecbankname)、fill_date 2022：6 家银行 355 笔 18,208,936,572.27；建行 226 笔 / 182.08 亿',
        c='rec_bank_code、pay_date 2022：6 家 334 笔；建行 211 笔 / 182.08 亿',
        n=[
            '银行家数一致（6）。',
            '建行金额量级一致（182.08 亿级）。',
            '笔数与分布不同：总笔数 355 vs 334、建行 226 vs 211（时间轴 fill_date vs pay_date、笔数键 fid vs paybook_count）。',
            '分组键不同：datus 银行名称（trim 后）vs cube 银行编码。',
        ],
        r='主体金额接近；笔数分布不同（时间轴与去重键不同）'),
    'q20': dict(
        d="frecrgnname 三档：明确非省本级 1,169,469.34/41 笔、空 23.15 亿/544 笔、含空合计 2,315,772,623.92/585 笔",
        c="rec_rgn_code ≠ '530000'：2,315,772,623.922/504 笔（含空）；剔除空后 1,169,469.34/39 笔",
        n=[
            '金额完全一致：含空 2,315,772,623.92、剔除空 1,169,469.34。',
            '笔数不同：41/585（fid 去重）vs 39/504（paybook_count）。',
            '实现方式不同：datus 按名称列分组后取非省本级档 vs cube 编码不等于过滤（空组自然落入"≠530000"）。',
        ],
        r='金额一致；笔数口径不同'),
    'q21': dict(
        d="fne_funddivide_transfer 按 fcollectid 去重（指出头行+明细行重复携带整批金额的陷阱）：已划拨 21,024.00/34 批、未划拨 38,142.30/87 批、合计 59,166.30/121 批；另 568 行空 fistransfer（对应 fimamt 160.16 亿）不在口径内",
        c='fiscal_allocation_view 全量：is_transfer 实测全空，改用金额差值——已划拨 trans_amt 合计 72,507.62、未划拨 im_amt−trans_amt=16,016,006,960.06',
        n=[
            '主语不同：datus 限有划拨记录的 121 个批次 vs cube 全量清分记录。',
            '金额不同：datus 去重后 59,166.30 vs cube trans_amt 直 SUM 72,507.62（恰为 datus 指出的"未去重虚增"量级）。',
            '状态判据不同：datus 用 fistransfer 字段 vs cube is_transfer 实测全空、改按金额差值推算。',
        ],
        r='主语与去重口径双重不同，数字不可直接对照'),
    'q22': dict(
        d="fid 去重 76 行，fstatus+fincomestatus：已确认入库（9,1）23 笔/11,064.00、待确认（9,0）3 笔/35,240.09；另 50 笔 29,488,802.05 未缴库（fstatus='0'）；指出「415.5 万中间态」系未去重行口径",
        c='fiscal_treasury_view enter_status：已入国库 46,304.09/26、未入库 29,409,625.05/50',
        n=[
            '状态字段不同：datus fstatus + fincomestatus 双字段组合 vs cube enter_status 单字段。',
            '组划分不同：datus 只计已缴库两组、另列未缴库 vs cube 二分全部。',
            '数字不同：已入库 11,064.00 vs 46,304.09；未入库/未缴库 29,488,802.05 vs 29,409,625.05。',
        ],
        r='状态字段与组划分均不同，数字不可直接对照'),
    'q23': dict(
        d='COUNT(DISTINCT fcollectid) 非空 = 428 批次（头行批次 425、仅明细 3）；空串键 178 行不计（若计为 429）',
        c='追问后 collect_flag=1 记录数 = 550；声明 fcollectid 去重口径在模型面无对应成员、无法直接查',
        n=[
            '计数对象不同：datus 按键去重的批次数（428）vs cube collect_flag=1 的记录行数（550）。',
            'datus 同时报出非空键明细 550 行对应 428 个批次——与 cube 的 550 是同一行数口径的不同计数对象。',
            '实现路径不同：datus 直查源表 uniqExact vs cube 视图成员（collect_flag）。',
        ],
        r='行数一致（550）；批次数 vs 记录数口径不同'),
    'q24': dict(
        d="fisclear='0'：515 笔（COUNT(DISTINCT fid)）/ 2,314,588,645.58",
        c='clear_date 为空：439 缴款书 / 2,314,587,534.58',
        n=[
            '金额几乎一致：差 1,111.00 元。',
            '过滤判据不同：datus fisclear 标志位 vs cube clear_date 空判（cube 声明模型无 is_cleared 成员）。',
            '笔数不同：515（fid 去重）vs 439（paybook_count）。',
        ],
        r='金额基本一致；判据与笔数口径不同'),
    'q25': dict(
        d='同表组内比值可算：直缴 99.80%（160.47 亿→160.16 亿）、汇缴 ≈0.0035%、整体 87.37%',
        c='跨视图 join 报错不可查；拍板口径（划转成功笔数÷清分记录数）0.00%；参考表缴款侧直缴 1,063 行/848 票、汇缴 209 行/120 票',
        n=[
            'datus 分子分母同在 fne_paybook_full_high（fimamt/famt 组内比值），给出三个比值；cube 分子分母分属两视图、声明无 join path，改给拍板口径与参考分布。',
            'cube 参考分布的行数与 datus 一致：直缴 1,063 行、汇缴 209 行。',
            'cube 拍板口径比值 0.00% 与 datus 汇缴比值 ≈0.0035% 量级接近，但两者分母定义不同。',
        ],
        r='分布行数一致；比值口径不同'),
}

# 总表专用短答案（只写答案本身；口径/维度细节在逐题对照里）
SHORT = {
    'q01': ('182.09 亿 / 355 笔', '182.09 亿 / 334 笔'),
    'q02': ('53 个月（至 2026-08），2022-04 尖峰 159.86 亿', '57 个月（至 2026-09）'),
    'q03': ('2021=0、2022=159.87 亿；增长率不可算', '返回 0 行，无法计算'),
    'q04': ('2022=78,449.12、2023=80,659.18、2024=3,763.30、2025 无、2026=29,372,234.54',
            '2022=46,053.04、2023=34,178.26、2024=3,463.30、2025=0、2026=29,372,234.54'),
    'q05': ('清分 160.16 亿 / 缴款 183.32 亿 / 清分率 0.8737', '同三数（160.16 亿 / 183.32 亿 / 0.8737）'),
    'q06': ('9 单位，Top1 测试云南测试环境 182.09 亿 / 272 笔', '9 单位，Top1（124045）182.09 亿 / 253 笔'),
    'q07': ('44 家下级合计 183.30 亿（直缴 160.47 亿）', 'nomatch'),
    'q08': ('2022 年 9 单位，Top1 159.87 亿、清分率 87.80%', '全量 25 单位，Top1 划拨 63,371 元 / 分入 159.87 亿'),
    'q09': ('无最终答案（引擎中断）', 'nomatch'),
    'q10': ('1 笔（124045）', '1 笔（124045）'),
    'q11': ('10301 层级：103010201 最多，159.86 亿 / 99.81%', '103 前缀 20 组，103010201 最多（同值 / 99.81%）'),
    'q12': ('2024 峰值 2,912.22 万，历年合计约 3,236 万', '2024 峰值 2,896.20 万，历年合计 3,085.09 万'),
    'q13': ('政府性基金 182.85 亿 / 99.74%、专项 0.31 亿、行政事业性收费 0.16 亿、罚没 300 元',
            '同四类数字（政府性基金 182.85 亿 / 99.74% 等）'),
    'q14': ('12=183.16 亿、2=1,486.7 万、11=129.3 万、5=600 元',
            '政府性基金 160.16 亿、一般公共预算 118.4 万、财政专户 39,329、空 23.15 亿'),
    'q15': ('Top5：农网还贷 160.45 亿、煤炭、民航 3,085.08 万、住宿费、保教费（各按直缴/汇缴拆分）',
            'Top5：农网还贷、煤炭、民航、农网还贷 a、住宿费'),
    'q16': ('省本级 160.16 亿、中央 4,516.12、昆明市本级 1,778.70、五华区 495.33、云龙县 0', '同五组同值'),
    'q17': ('云南省本级 183.31 亿、云龙县 1,156,320、五华区 79,406.12、昆明市本级 5,184、官渡区 400',
            '省本级 160.16 亿、空 23.15 亿、云龙 1,156,320、中央 9,617.68、昆明 2,541、五华 990.66'),
    'q18': ('3 单位 6 笔 79,406.12（最大 77,324.80）', '3 单位 4 笔 79,406.12（最大 77,324.80）'),
    'q19': ('6 家银行 355 笔 182.09 亿，建行 226 笔 / 182.08 亿', '6 家 334 笔，建行 211 笔 / 182.08 亿'),
    'q20': ('非省本级 116.9 万 / 41 笔 + 空 23.15 亿 / 544 笔，合计 23.16 亿', '23.16 亿（504 笔，含空）；剔除空 116.9 万（39 笔）'),
    'q21': ('已划拨 21,024.00 / 未划拨 38,142.30（共 121 批）', '已划拨 72,507.62 / 未划拨 160.16 亿（全量差值）'),
    'q22': ('已确认入库 11,064.00 / 待确认 35,240.09；另未缴库 29,488,802.05', '已入国库 46,304.09 / 未入库 29,409,625.05'),
    'q23': ('428 个批次', '550 条记录'),
    'q24': ('515 笔 / 23.15 亿', '439 缴款书 / 23.15 亿'),
    'q25': ('直缴 99.80% / 汇缴 ≈0.0035% / 整体 87.37%', '比值不可查，拍板口径 0.00%；参考分布直缴 1,063 行 / 汇缴 209 行'),
}

# datus 侧精编答案（只留问题的答案本体）与答案内 SQL；来自 09-datus 各题原文
DANS = {
    'q01': ("""| 指标 | 结果 |
|---|---|
| **非税缴款金额** | **18,208,936,572.27 元 ≈ 182.09 亿元** |
| **非税缴款笔数** | **355 笔** |""",
     """SELECT
  sum(famt)                     AS 非税缴款金额,
  COUNT(DISTINCT fid)           AS 非税缴款笔数
FROM yunnan0508.fne_paybook_full_high
WHERE toDate(ffilldate) >= '2022-01-01'
  AND toDate(ffilldate) <  '2023-01-01'"""),
    'q02': ("""全部 53 个自然月（含 5 个无数据月）已拼齐并交叉验证：

| 月份 | 金额（元） | 环比增长率 |
|---|---:|---:|
| 2021-12 | 833.00 | — |
| 2022-01 | 13,301.00 | +1,496.76% |
| 2022-02 | 40,779.00 | +206.59% |
| 2022-03 | 19,365.00 | −52.51% |
| **2022-04** | **15,985,631,865.00** | +82,548,993.03% |
| 2022-05 | 494.00 | −100.00% |
| 2022-06 | 4,112.90 | +732.57% |
| 2022-07 | 23.00 | −99.44% |
| 2022-08 | 17,417.79 | +75,629.52% |
| 2022-09 | 5,653.68 | −67.54% |
| 2022-10 | 38,188.35 | +575.46% |
| 2022-11 | 236,794.19 | +520.07% |
| **2022-12** | **2,222,928,578.36** | +938,659.76% |
| 2023-01 | 0.00（无数据） | −100.00% |
| 2023-02 | 44,876.00 | —（上月无基数） |
| 2023-03 | 4,086.00 | −90.89% |
| 2023-04 | 5,819.00 | +42.41% |
| 2023-05 | 964.00 | −83.43% |
| 2023-06 | 43,459.45 | +4,408.24% |
| 2023-07 | 1,171,872.00 | +2,596.47% |
| 2023-08 | 24,457.08 | −97.91% |
| 2023-09 | 128,914.88 | +427.11% |
| 2023-10 | 600.00 | −99.53% |
| 2023-11 | 37,408.60 | +6,134.77% |
| 2023-12 | 3,353.30 | −91.04% |
| 2024-01 | 164,244.58 | +4,798.00% |
| **2024-02** | **46,039,171.70** | +27,930.86% |
| 2024-03 | 3,164.62 | −99.99% |
| **2024-04** | **28,982,824.78** | +915,739.02% |
| 2024-05 | 22,063.00 | −99.92% |
| 2024-06 | 5,836.24 | −73.55% |
| 2024-07 | 1,405.28 | −75.92% |
| 2024-08 | 610,281.59 | +43,327.76% |
| 2024-09 | 6,846.64 | −98.88% |
| 2024-10 | 139,444.89 | +1,936.69% |
| 2024-11 | 9,105.86 | −93.47% |
| 2024-12 | 140,047.64 | +1,437.99% |
| **2025-01** | **30,695,653.30** | +21,818.01% |
| 2025-02 | 453.00 | −100.00% |
| 2025-03 | 27,734.88 | +6,022.49% |
| 2025-04 | 15,413.20 | −44.43% |
| 2025-05 | 0.00（无数据） | −100.00% |
| 2025-06 | 5,256.29 | —（上月无基数） |
| 2025-07 | 1,084.00 | −79.38% |
| 2025-08 | 0.00（无数据） | −100.00% |
| 2025-09 | 1,777.33 | —（上月无基数） |
| 2025-10 | 4,492.36 | +152.76% |
| 2025-11 | 1,501.00 | −66.59% |
| 2025-12 | 1,000.02 | −33.38% |
| 2026-01 | 4,632.00 | +363.19% |
| 2026-02 | 0.00（无数据） | −100.00% |
| 2026-03 | 0.00（无数据） | — |
| 2026-04 | 1,982.32 | —（上月无基数） |
| 2026-05 | 7,222.00 | +264.32% |
| **2026-06** | **14,909,895.85** | +206,351.06% |
| 2026-07 | 752.52 | −99.99% |
| 2026-08 | 700.66 | −6.89% |""",
     """WITH monthly AS (
    SELECT toStartOfMonth(toDate(ffilldate)) AS ym, SUM(famt) AS amt
    FROM fne_paybook_full_high
    GROUP BY ym
)
SELECT
    formatDateTime(a.ym, '%Y-%m')                          AS `月份`,
    ROUND(COALESCE(b.amt, 0), 2)                           AS `非税缴款金额_元`,
    lagInFrame(COALESCE(b.amt, 0), 1) OVER (
        ORDER BY a.ym ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    )                                                      AS `上月金额_元`,
    IF(COALESCE(b.amt, 0) = 0
       OR lagInFrame(COALESCE(b.amt, 0), 1) OVER (
              ORDER BY a.ym ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) IN (0, NULL),
       NULL,
       ROUND((COALESCE(b.amt, 0) - lagInFrame(COALESCE(b.amt, 0), 1) OVER (
              ORDER BY a.ym ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW))
             / lagInFrame(COALESCE(b.amt, 0), 1) OVER (
              ORDER BY a.ym ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) * 100, 2)
    )                                                      AS `环比增长率_%`
FROM (
    SELECT toStartOfMonth(addMonths(toDate('2021-12-01'), number)) AS ym
    FROM numbers(57)          -- 2021-12 起共 57 个自然月，补齐无数据月份
) a
LEFT JOIN monthly b USING (ym)
ORDER BY a.ym"""),
    'q03': ("""**结论：2021 年清分金额为 0，同比增长额 +159.87 亿元，增长率无法计算（基数为 0）**

| 年份 | 清分金额（元） | 明细行数 |
|---|---:|---:|
| 2021 | 0（无任何 `fcleardate` 落在 2021 年的记录） | 0 |
| 2022 | **15,986,577,101.87（≈159.87 亿）** | 320 |""",
     """SELECT substring(fcleardate, 1, 4) AS clear_year,
       round(sum(fimamt), 2) AS clear_amount
FROM yunnan0508.fne_paybook_full_high
WHERE substring(fcleardate, 1, 4) IN ('2021', '2022')
GROUP BY clear_year
ORDER BY clear_year"""),
    'q04': ("""| 年份 | 缴库笔数 | 缴库金额（元） |
|------|---------|---------------|
| 2022 | 34 | 78,449.12 |
| 2023 | 10 | 80,659.18 |
| 2024 | 15 | 3,763.30 |
| 2025 | — | **无缴库报文** |
| 2026 | 17 | 29,372,234.54 |
| **合计** | **76** | **29,535,106.14** |""",
     """SELECT
    toYear(toDate(fmsgdate)) AS yr,
    count() AS bill_cnt,
    round(SUM(ftotalamt), 2) AS treasury_amt
FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY fid) AS _rn
    FROM yunnan0508.fne_treasury_transfer_new
)
WHERE _rn = 1
GROUP BY yr
ORDER BY yr"""),
    'q05': ("""| 指标 | 数值 |
|---|---|
| **清分金额**（SUM(fimamt)） | **16,016,079,467.68 元 ≈ 160.16 亿元** |
| **非税缴款金额**（SUM(famt)，分母） | 18,332,207,203.13 元 ≈ 183.32 亿元 |
| **清分率** = 清分 ÷ 缴款 | **0.8737 ≈ 87.37%** |""",
     """SELECT
  COALESCE(SUM(fimamt), 0) AS cleared_amt,
  COALESCE(SUM(famt), 0)   AS pay_amt,
  COALESCE(SUM(fimamt), 0) / COALESCE(SUM(famt), 0) AS clear_rate
FROM fne_paybook_full_high"""),
    'q06': ("""| 排名 | 执收单位编码 | 执收单位名称 | 缴款金额（元） | 缴款明细笔数 |
|---|---|---|---|---|
| 1 | 36299bf1...16cc588 | 测试云南测试环境(试用版) | 18,208,882,274.85（约 182.09 亿） | 272 |
| 2 | 6e4ba023... | 云南测试单位1209 | 24,034.92 | 4 |
| 3 | 5c18ec29... | 测试1125 | 11,763.68 | 20 |
| 4 | 1cc48566... | 云南医疗单位0729 | 6,864.26 | 19 |
| 5 | 62aa3631... | 测试分成测试 | 5,184.00 | 9 |
| 6 | d5058204... | 测试云南通用测试单位0720 | 2,057.68 | 13 |
| 7 | 57661ea5... | 测试云南医疗单位0805 | 1,915.12 | 9 |
| 8 | 67455953... | 测试测试单位0722 | 1,377.76 | 7 |
| 9 | ec8eb0f0... | 测试云南通用Oracle0728 | 1,100.00 | 2 |

实际只有 9 个单位（2022 年内有缴款数据的执收单位不足 10 个）。""",
     """SELECT
    fchgagenidcode AS agen_code,
    groupUniqArray(fchgagenname) AS agen_names,
    round(SUM(famt), 2) AS amt_sum,
    uniqExact(fid) AS detail_cnt
FROM fne_paybook_full_high
WHERE ffilldate >= '2022-01-01' AND ffilldate < '2023-01-01'
GROUP BY fchgagenidcode
ORDER BY amt_sum DESC
LIMIT 10"""),
    'q07': ("""**"测试云南省教育厅1"（单位编码 124）直属下级单位合计缴款金额：18,330,391,762.78 元（约 183.30 亿元）**

| 项目 | 数值 |
|---|---|
| 直属下级单位数 | **44 家**（全部有缴款记录） |
| 缴款笔数 | 693 笔（按 `uniqExact(fid)` 去重口径） |
| **合计缴款金额** | **18,330,391,762.78 元** |
| ├ 直缴（fbustype='1'） | 16,047,143,059.65 元（87.6%） |
| └ 汇缴（fbustype='2'） | 2,283,248,703.13 元（12.4%） |

上级单位本部自身无缴款记录。""",
     """SELECT
    count()                                        AS pay_rows,
    uniqExact(fid)                                 AS pay_cnt,
    round(SUM(famt), 2)                            AS total_amt,
    round(SUMIf(famt, fbustype = '1'), 2)          AS direct_amt,
    round(SUMIf(famt, fbustype = '2'), 2)          AS agg_amt
FROM yunnan0508.fne_paybook_full_high
WHERE fchgagenidcode IN (
    SELECT fagenidcode
    FROM (
        SELECT fagenidcode, fpidcode, fupdatetime,
               ROW_NUMBER() OVER (PARTITION BY fagenidcode ORDER BY fupdatetime DESC) AS _rn
        FROM yunnan0508.fab_agen
    ) t
    WHERE _rn = 1
      AND fpidcode = 'f8e06e9474514da29117a5194bbe503d'  -- 测试云南省教育厅1
)"""),
    'q08': ("""| 排名 | 执收单位 | 笔数 | 清分金额（亿元） | 占比 | 缴款金额（亿元） | 清分率 |
|---|---|---|---|---|---|---|
| 1 | 测试云南测试环境 | 272 | 159.8653 | ≈100% | 182.0888 | 87.80% |
| 2 | 云南测试单位1209 | 4 | 0.0002 | <0.01% | 0.0002 | 100% |
| 3 | 测试云南医疗单位0729 | 19 | 0.0001 | <0.01% | 0.0001 | 100% |
| 3 | 测试1125 | 20 | 0.0001 | <0.01% | 0.0001 | 99.15% |
| 5 | 测试云南医疗单位0805 | 9 | ~0 | — | ~0 | 100% |
| 5 | 测试云南通用测试单位0720 | 13 | ~0 | — | ~0 | 100% |
| 5 | 测试云南通用Oracle0728 | 2 | ~0 | — | ~0 | 100% |
| 5 | 测试分成测试 | 9 | ~0 | — | 0.0001 | 49.02% |
| 5 | 测试测试单位0722 | 7 | ~0 | — | ~0 | 100% |
| **合计** | **9 个单位** | **355** | **≈159.866** | 100% | **≈182.09** | **≈87.8%** |""",
     """WITH
name_cnt AS (
    SELECT fchgagenidcode AS agen_code, trim(fchgagenname) AS agen_name, count() AS cnt
    FROM yunnan0508.fne_paybook_full_high
    WHERE toYear(toDate(ffilldate)) = 2022
    GROUP BY agen_code, agen_name
),
canon AS (
    SELECT agen_code, argMax(agen_name, cnt) AS agen_name
    FROM name_cnt
    GROUP BY agen_code
)
SELECT
    m.fchgagenidcode AS agen_code,
    any(c.agen_name) AS agen_name,
    count() AS rows,
    uniqExact(m.fid) AS bills,
    round(sum(m.fimamt) / 1e8, 4) AS clear_amt_yi,
    round(sum(m.famt) / 1e8, 4) AS pay_amt_yi,
    round(if(sum(m.famt) = 0, NULL, sum(m.fimamt) / sum(m.famt) * 100), 2) AS clear_rate_pct
FROM yunnan0508.fne_paybook_full_high m
INNER JOIN canon c ON m.fchgagenidcode = c.agen_code
WHERE toYear(toDate(m.ffilldate)) = 2022
GROUP BY m.fchgagenidcode
ORDER BY clear_amt_yi DESC"""),
    'q09': ('（无最终答案——多轮 SQL 后试图写临时文件被权限拒绝，会话中断）', '（无）'),
    'q10': ("""| 执收单位编码 | 执收单位名称 | 未到账缴款笔数 | 明细行数 |
|---|---|---|---|
| 124045 | 测试云南测试环境 | **1** | 1 |""",
     """SELECT
    fchgagencode                                        AS agen_code,
    arrayStringConcat(arraySort(groupUniqArray(fchgagenname)), ' / ') AS agen_name,
    uniqExact(fpaycode)                                 AS unpaid_book_cnt,
    count()                                             AS detail_rows
FROM yunnan0508.fne_paybook_full_high
WHERE fstate = '1'
  AND toDateOrNull(feffdate) < '2026-10-21'
GROUP BY fchgagencode
ORDER BY unpaid_book_cnt DESC
LIMIT 100"""),
    'q11': ("""| 排名 | 科目编码 | 科目名称 | 层级 | 清分金额（元） | 占比 | 清分笔数 |
|---|---|---|---|---|---|---|
| 1 | 103010201 | 中央农网还贷资金收入 | 4 | **15,985,889,302.18** | 99.81% | 412 |
| 2 | 1030110 | 民航发展基金收入 | 3 | 28,938,336.12 | 0.18% | 126 |
| 3 | 1030106 | 铁路建设基金收入 | 3 | 495,345.65 | <0.01% | 66 |
| 4 | 1030115 | 港口建设费收入 | 3 | 495,318.31 | <0.01% | 254 |
| 5 | 1030121 | 旅游发展基金收入 | 3 | 154,995.46 | <0.01% | 95 |
| 6 | 1030129 | 国家电影事业发展专项资金收入 | 3 | 36,668.96 | <0.01% | 23 |
| 7 | 1030146 | 国有土地收益基金收入 | 3 | 22,488.00 | <0.01% | 5 |
| 8 | 1030149 | 大中型水库移民后期扶持基金收入 | 3 | 60.00 | ~0 | 1 |
| 9 | 103014899 | 其他土地出让收入 | 4 | 33.00 | ~0 | 2 |

收得最多的是 103010201 中央农网还贷资金收入：159.86 亿元，占该大类 99.81%。""",
     """WITH subject_dim AS (
  SELECT fsubcode, fsubname, flevel, fpcode, fisleaf
  FROM (
    SELECT fsubcode, fsubname, fyear, flevel, fpcode, fisleaf,
           ROW_NUMBER() OVER (PARTITION BY fsubcode ORDER BY fyear DESC) AS _rn
    FROM yunnan0508.fab_subject
  ) WHERE _rn = 1
),
agg AS (
  SELECT fsubcode AS subject_code, SUM(fimamt) AS amt, uniqExact(fid) AS cnt
  FROM yunnan0508.fne_paybook_full_high
  GROUP BY subject_code
)
SELECT
  a.subject_code AS subject_code,
  s.fsubname AS subject_name,
  toString(s.flevel) AS subject_level,
  COALESCE(round(a.amt, 2), 0) AS clear_amount,
  a.cnt AS clear_cnt
FROM agg a
INNER JOIN subject_dim s ON a.subject_code = s.fsubcode
WHERE toString(s.fisleaf) = '1' AND startsWith(a.subject_code, '103') AND NOT startsWith(a.subject_code, '10301')
ORDER BY clear_amount DESC"""),
    'q12': ("""| 年份 | 笔数 | 缴款金额(万元) | 其中实缴(万元) | 趋势 |
|------|-----:|-------------:|-------------:|------|
| 2022 | 4 | 0.05 | — | 起步 |
| 2023 | 84 | 0.78 | 0.29 | 平稳低位 |
| 2024 | 261 | **2,912.22** | 2,898.67 | ⬆ 峰值（实缴率 99.5%） |
| 2025 | 269 | 246.09 | 187.75 | ⬇ 大幅回落（-91.6%） |
| 2026 | 199 | 15.57 | 4.25 | ⬇ 持续走低 |
| 2027 | 234 | 60.71 | 19.36 | ⬆ 回升 |
| 2028 | 17 | 0.83 | 0.23 | ⬇ |
| 2029 | 8 | 0.23 | — | 边缘 |""",
     """SELECT
  toYear(toDate(feffdate)) AS y,
  count() AS rows_cnt,
  round(sum(famt)/10000, 2) AS amt_wan,
  round(sumIf(famt, fstate='3')/10000, 2) AS paid_wan,
  uniqExact(fpaycode) AS pay_cnt
FROM yunnan0508.une_paybook_high
WHERE fitemcode = '1030110001'
GROUP BY y
ORDER BY y"""),
    'q13': ("""| 收入分类 | 缴款金额（亿元） | 金额占比 | 笔数（去重 fid） |
|---|---:|---:|---:|
| **政府性基金收入** | 182.85 | **99.74%** | 857 |
| **专项收入** | 0.31 | 0.17% | 133 |
| **行政事业性收费收入** | 0.16 | 0.09% | 96 |
| **罚没收入** | 0.000003（仅 300 元） | ≈0 | 9 |
| 未分类（fincomesortname 为空） | 0.000006（600 元） | ≈0 | 6 |
| **合计** | **183.22** | 100% | 1,101 |""",
     """SELECT
    if(fincomesortname = '', '未分类', fincomesortname) AS income_category,
    round(SUM(famt) / 10000, 2)        AS amt_wan_yuan,
    round(SUM(famt) * 100 / SUM(SUM(famt)) OVER (), 4) AS amt_pct,
    uniqExact(fid)                     AS pay_cnt_fid
FROM fne_paybook_full_high
GROUP BY income_category
ORDER BY amt_wan_yuan DESC"""),
    'q14': ("""| 资金性质码 | 资金性质 | 缴款金额（元） | 行数 | 金额占比 |
|---|---|---:|---:|---:|
| 12 | 政府性基金预算收入 | 18,316,046,350.64 | 1,083 | ≈99.9% |
| 2 | 财政专户管理资金 | 14,867,151.04 | 86 | ≈0.08% |
| 11 | 一般公共预算收入 | 1,293,101.45 | 97 | ≈0.007% |
| 5 | 其他 | 600.00 | 6 | ≈0.000003% |
| **合计** | | **18,332,214,203.13** | **1,272** | 100% |""",
     """SELECT
    ffundsnaturecode AS funds_nature_code,
    ffundsnaturename AS funds_nature_name,
    count()           AS row_count,
    round(sum(famt), 2) AS pay_amt
FROM yunnan0508.fne_paybook_full_high
GROUP BY ffundsnaturecode, ffundsnaturename
ORDER BY pay_amt DESC"""),
    'q15': ("""| 排名 | 收费项目 | 项目ID | 缴款金额合计(元) | 直缴金额(元) | 直缴占比 | 汇缴金额(元) | 汇缴占比 | 直缴笔数 | 汇缴笔数 |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| 1 | 农网还贷资金收入 | 530020000079 | 16,044,829,547.49 | 16,014,461,111.69 | 99.81% | 30,368,435.80 | 0.19% | 272 | 25 |
| 2 | 国有重点煤炭企业生产用电、核工业铀扩散厂和堆化工厂生产用电农网还贷资金 | 530020000081 | 2,238,164,885.91 | 159,670.01 | 0.01% | 2,238,005,215.90 | 99.99% | 53 | 14 |
| 3 | 民航发展基金收入 | 530020000503 | 30,850,779.08 | 30,758,057.70 | 99.70% | 92,721.38 | 0.30% | 87 | 39 |
| 4 | 高等学校住宿费 | 530020000028 | 14,841,170.00 | 19,271.00 | 0.13% | 14,821,899.00 | 99.87% | 35 | 5 |
| 5 | 公办幼儿园保教费 | 530020000823 | 1,156,320.00 | 0.00(无直缴) | — | 1,156,320.00 | 100% | 0 | 1 |""",
     """WITH
top5 AS (
    SELECT fitemidcode FROM fne_paybook_full_high
    GROUP BY fitemidcode ORDER BY SUM(famt) DESC LIMIT 5
),
names AS (
    SELECT fitemidcode AS item_id,
           argMax(fitemname, ffilldate) AS item_name,
           groupUniqArray(fitemname) AS all_names
    FROM fne_paybook_full_high
    WHERE fitemidcode IN top5
    GROUP BY item_id
),
bus AS (
    SELECT fitemidcode AS item_id, fbustype AS bustype,
           SUM(famt) AS amt, uniqExact(fid) AS cnt_fid
    FROM fne_paybook_full_high
    WHERE fitemidcode IN top5
    GROUP BY item_id, bustype
)
SELECT n.item_id, n.item_name, n.all_names,
       round(SUM(b.amt), 2) AS amt_total,
       round(sumIf(b.amt, b.bustype = '1'), 2) AS amt_direct,
       round(sumIf(b.amt, b.bustype = '2'), 2) AS amt_agg,
       sumIf(b.cnt_fid, b.bustype = '1') AS cnt_direct,
       sumIf(b.cnt_fid, b.bustype = '2') AS cnt_agg
FROM bus b INNER JOIN names n ON b.item_id = n.item_id
GROUP BY n.item_id, n.item_name, n.all_names
ORDER BY amt_total DESC"""),
    'q16': ("""| 归属区划代码 | 区划名称 | 明细行数 | 清分金额（元） |
|---|---|---:|---:|
| 530000 | 云南省本级 | 686 | 16,016,072,677.53 |
| 000000 | 中央 | 31 | 4,516.12 |
| 530100 | 昆明市本级 | 8 | 1,778.70 |
| 530102 | 五华区 | 1 | 495.33 |
| 532929 | 云龙县 | 2 | 0.00 |
| （空） | 未填归属区划 | 544 | 0.00（fimamt 全 NULL） |

合计 1,272 行，清分金额总计 160.16 亿元，几乎全部集中在云南省本级（530000）。""",
     """SELECT
    if(frecrgncode = '', '(未填)', frecrgncode) AS frecrgncode,
    any(frecrgnname)                            AS frecrgnname,
    count()                                     AS rows_cnt,
    COALESCE(sum(fimamt), 0)                    AS clear_amt
FROM yunnan0508.fne_paybook_full_high
GROUP BY frecrgncode
ORDER BY clear_amt DESC"""),
    'q17': ("""| 执收区划名称 | 缴款金额（元） | 缴款笔数（去重 fid） | 笔均金额（元） |
|---|---:|---:|---:|
| 云南省本级 | 18,330,965,893.01 | 1,081 | 16,957,415.26 |
| 云龙县 | 1,156,320.00 | 1 | 1,156,320.00 |
| 五华区 | 79,406.12 | 6 | 13,234.35 |
| 昆明市本级 | 5,184.00 | 9 | 576.00 |
| 官渡区 | 400.00 | 4 | 100.00 |
| **合计** | **18,332,205,003.13** | **1,101** | — |""",
     """SELECT
    fchgrgnname AS collect_region_name,
    ROUND(SUM(famt), 2) AS pay_amt,
    uniqExact(fid) AS pay_cnt,
    ROUND(SUM(famt) / uniqExact(fid), 2) AS avg_amt
FROM yunnan0508.fne_paybook_full_high
GROUP BY fchgrgnname
ORDER BY pay_amt DESC"""),
    'q18': ("""| 执收单位 | 缴款笔数 | 缴款金额（元） |
|---|---:|---:|
| 智能核销五华区测试单位开票点 | 4 | 77,324.80 |
| 李思维 | 1 | 1,981.32 |
| 开票点001 | 1 | 100.00 |
| **合计** | **6** | **79,406.12** |

对照口径：按资金归属五华区（frecrgnname）统计仅李思维 1 笔 / 990.66 元。""",
     """SELECT
    fchgrgnname AS agen_rgn,
    count() AS row_cnt,
    uniqExact(fid) AS bill_cnt,
    round(sum(famt), 2) AS amt
FROM fne_paybook_full_high
GROUP BY fchgrgnname
ORDER BY amt DESC"""),
    'q19': ("""| 收款银行 | 笔数 | 金额（元） | 金额（亿元） |
|---|---:|---:|---:|
| 中国建设银行 | 226 | 18,208,121,939.04 | ≈182.08 |
| 中国银行 | 107 | 800,419.02 | ≈80.04 万 |
| 中国邮政储蓄银行 | 7 | 7,778.00 | 0.78 万 |
| 中国工商银行 | 11 | 5,426.21 | 0.54 万 |
| 中国农业银行 | 3 | 510.00 | 510 元 |
| 中国光大银行 | 1 | 500.00 | 500 元 |
| **合计** | **355** | **18,208,936,572.27** | **≈182.09 亿** |""",
     """SELECT
    trim(frecbankname) AS bank_name,
    uniqExact(fid)             AS bill_cnt,
    round(sum(famt), 2)        AS total_amt
FROM fne_paybook_full_high
WHERE toYear(toDate(ffilldate)) = 2022
GROUP BY bank_name
ORDER BY total_amt DESC"""),
    'q20': ("""| 口径 | 金额（元） | 笔数 |
|---|---|---|
| **省本级以外（区划有明确值）** | **1,169,469.34（约 116.9 万）** | 41 笔 |
| 归属区划为空（未落值） | 2,314,603,154.58（约 23.15 亿） | 544 笔 |
| 合计（含空串宽口径） | 2,315,772,623.92（约 23.16 亿） | 585 笔 |

明确非省本级的 41 笔构成：云龙县 1,156,320.00/1、中央 9,617.68/31、昆明市本级 2,541.00/8、五华区 990.66/1；对比云南省本级 16,016,434,579.21 元（554 笔）。""",
     """SELECT
    round(sumIf(famt, frecrgnname = '云南省本级'), 2)                        AS prov_amt,
    round(sumIf(famt, frecrgnname != '云南省本级'), 2)                       AS non_prov_amt_incl_blank,
    uniqExactIf(fid, frecrgnname != '云南省本级')                            AS non_prov_bill_cnt,
    round(sumIf(famt, frecrgnname != '云南省本级' AND frecrgnname != ''), 2) AS non_prov_amt_named,
    round(sumIf(famt, frecrgnname = ''), 2)                                  AS blank_amt
FROM fne_paybook_full_high"""),
    'q21': ("""**已划拨 21,024.00 元（34 个批次），未划拨 38,142.30 元（87 个批次）**，合计 59,166.30 元。

| 划拨状态 | 批次数 | 划拨金额（元） |
|---|---:|---:|
| 已划拨（fistransfer='1'） | 34 | 21,024.00 |
| 未划拨（fistransfer='0'） | 87 | 38,142.30 |
| **合计** | **121** | **59,166.30** |""",
     """SELECT
  multiIf(istransfer_grp = '1', '已划拨', '未划拨') AS status,
  uniqExact(fcollectid) AS batches,
  round(sum(batch_amt), 2) AS amount
FROM (
  SELECT
    fcollectid,
    max(fistransfer) AS istransfer_grp,
    max(ftransamt) AS batch_amt
  FROM fne_funddivide_transfer
  WHERE fistransfer IN ('0', '1') AND ftransamt IS NOT NULL
  GROUP BY fcollectid
)
GROUP BY istransfer_grp
ORDER BY istransfer_grp"""),
    'q22': ("""| 缴库状态 | 入库确认状态 | 笔数（fid） | 金额（元） |
|---|---|---:|---:|
| **已缴库 + 已确认入库** | `fstatus='9'` & `fincomestatus='1'` | **23** | **11,064.00** |
| **已缴库 + 待国库确认** | `fstatus='9'` & `fincomestatus='0'` | **3** | **35,240.09** |

其余 50 笔（29,488,802.05 元）为 `fstatus='0'` 的未缴库报文，未计入。""",
     """SELECT
    fstatus AS jiaoku_status,
    toString(fincomestatus) AS income_status,
    uniqExact(fid) AS fid_cnt,
    round(SUM(ftotalamt), 2) AS total_amt
FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY fid) AS _rn
    FROM yunnan0508.fne_treasury_transfer_new
)
WHERE _rn = 1
GROUP BY fstatus, income_status
ORDER BY jiaoku_status, income_status"""),
    'q23': ("""| 口径 | 数量 |
|---|---|
| **有效汇总批次（`fcollectid != ''` 去重）** | **428 个** |
| 其中：有批次头行的批次（`fid = fcollectid`） | 425 个 |
| 其中：仅有明细行、无头行的批次 | 3 个 |
| 未汇总入批次的清分明细行（`fcollectid = ''`，共 178 行） | 不计为批次 |
| 若把空串也算一个"值" | 429（无效口径，不建议） |""",
     """SELECT
  count()                                        AS total_rows,
  uniqExactIf(fcollectid, fcollectid != '')      AS batches_nonempty,
  countIf(fcollectid = '')                       AS rows_empty_key,
  countIf(fcollectid != '' AND fid = fcollectid) AS header_rows
FROM yunnan0508.fne_funddivide_transfer"""),
    'q24': ("""| 指标 | 数值 |
|---|---|
| **未清分缴款笔数** | **515 笔**（按 `fid` 去重口径） |
| **未清分缴款金额** | **2,314,588,645.58 元**（约 **23.15 亿元**） |""",
     """SELECT
    COUNT(DISTINCT fid) AS cnt_uncleared,
    ROUND(SUM(famt), 2) AS amt_uncleared
FROM yunnan0508.fne_paybook_full_high
WHERE fisclear = '0'"""),
    'q25': ("""| 业务类型 | 明细行数 | 缴款笔数 | 非税缴款金额（元） | 清分金额（元） | 清分率 |
|---|---|---|---|---|---|
| **直缴**（fbustype='1'） | 1,063 | 848 | 160.47 亿 | 160.16 亿 | **99.80%** |
| **汇缴**（fbustype='2'） | 209 | 120 | 22.85 亿 | 8.02 万 | **≈0.00%**（实际 0.0035%） |
| 整体（全类型，对照） | 1,272 | 968 | 183.32 亿 | 160.16 亿 | 87.37% |""",
     """SELECT
    multiIf(fbustype = '1', '直缴', fbustype = '2', '汇缴', concat('其他:', fbustype)) AS bustype_name,
    count() AS detail_rows,
    uniqExact(fpaycode) AS pay_count,
    round(SUM(famt), 2) AS non_tax_amt,
    round(SUM(fimamt), 2) AS clear_amt,
    round(SUM(fimamt) / SUM(famt) * 100, 2) AS clear_rate_pct
FROM yunnan0508.fne_paybook_full_high
GROUP BY fbustype
ORDER BY fbustype"""),
}

APPX = {
    'q26': '近似作答：「下级区划/下级单位」无层级成员，按划入方区划（rec_rgn_code）× 划入方单位编码（rec_agency_code，无名称列）替代并已声明，结果含全部区划层级。',
    'q27': '可答（超出 08 文件「答不了」预期）：预算管理样式 bgt_style 可分档作答。',
    'q28': '空集：付款人名称 payer_name 已建模但库内为脱敏空值，返回 0 行。',
    'q29': '追问后可答：bus_type=2（汇缴）明细可查。',
    'q30': 'nomatch：退付相关成员（refund 等）在模型面全空，无法作答。',
}


def plan_lines(plan):
    out = []

    def walk(p, depth):
        if isinstance(p, list):
            for x in p:
                walk(x, depth)
        else:
            out.append(('- ' if depth == 0 else '  - ') + str(p))

    for p in plan:
        if isinstance(p, list):
            walk(p, 1)
        else:
            walk(p, 0)
    return out


def details(summary, inner, lang=None):
    if not inner or not inner.strip():
        inner = '（无内容）'
    if lang:
        inner = '```%s\n%s\n```' % (lang, inner)
    return '<details>\n<summary>%s</summary>\n\n%s\n\n</details>' % (summary, inner)


def main():
    ov, dblocks = parse_datus()
    questions = {x['id']: x['q'] for x in json.load(open(os.path.join(HERE, 'questions.json'), encoding='utf-8'))}
    L = []
    L.append('# 票据链路问数对账（datus vs cube）')
    L.append('')
    L.append('> 生成：2026-10-21。来源：[09-datus-票据链路问数实测记录](09-datus-票据链路问数实测记录.md)（q01-q25）'
             '与 [09-cube-票据链路问数实测记录](09-cube-票据链路问数实测记录.md)（q01-q30，其中 q01-q25 同题）。两份记录编号已统一为 q01-q25。')
    L.append('> 两条链路同数据源（yunnan0508，ClickHouse 23.3）、同日（2026-10-21）独立实测。')
    L.append('> **本文档用途**：汇总两个问数智能体（datus、cube）对同一批问题的答案与生成 SQL，供审核人员集中评审——')
    L.append('> 判断哪些答案是对的、正确的 SQL 应该是什么样、哪个智能体的答案更好。')
    L.append('> 各题「对账注记」只列出双方数字与口径的客观差异（字段、时间轴、去重键等），供评审参考，不预判对错。')
    L.append('')
    L.append('## 一、对账总表')
    L.append('')
    L.append('| 编号 | 问题 | datus 结果 | cube 结果 | 对照关系 |')
    L.append('|---|---|---|---|---|')
    for qid in PAIRS:
        c = CONTENT[qid]
        ds, cs = SHORT[qid]
        q = dblocks[qid]['title'] if qid in dblocks else questions.get(qid, '')
        L.append('| %s | %s | %s | %s | %s |' % (qid, q, ds, cs, c['r']))
    L.append('')
    L.append('## 二、逐题对照')
    L.append('')
    for qid in PAIRS:
        c = CONTENT[qid]
        d = dblocks[qid]
        rec = cube_rec(qid)
        eff = rec['eff']
        st = cube_status_label(rec)
        el = rec.get('elapsed') or '?'
        dans, dsql = DANS[qid]
        L.append('### %s　%s' % (qid, d['title']))
        L.append('')
        L.append('**datus**（%s，%ss）' % (ov.get(qid, {}).get('status', '?'), ov.get(qid, {}).get('secs', '?')))
        L.append('')
        L.append(dans)
        L.append('')
        L.append('**datus 生成 SQL**')
        L.append('')
        if dsql.startswith('（'):
            L.append(dsql)
        else:
            L.append('```sql\n%s\n```' % dsql)
        L.append('')
        tables = cube_tables_md(eff).strip()
        if tables:
            L.append('**cube**（%s，%ss）' % (st, el))
            L.append('')
            L.append(tables)
            csql = cube_sql(qid, rec)
            if not csql.startswith('（'):
                L.append('')
                L.append('**cube 生成 SQL**')
                L.append('')
                L.append('```sql\n%s\n```' % csql)
        else:
            L.append('**cube**（%s，%ss）：%s' % (st, el, c['c']))
        L.append('')
        L.append('**对账注记（客观差异）**')
        L.append('')
        for line in c['n']:
            L.append('- ' + line)
        L.append('')
    L.append('## 三、cube 独有验证题（q26-q30）')
    L.append('')
    L.append('> q26-q30 来自 08 文件"还答不了的"nomatch 验证题，datus 链路未测；列于此供完整性核对。')
    L.append('')
    for qid in ['q26', 'q27', 'q28', 'q29', 'q30']:
        rec = cube_rec(qid)
        eff = rec['eff']
        st = cube_status_label(rec)
        el = rec.get('elapsed') or '?'
        L.append('### %s　%s' % (qid, questions.get(qid, '')))
        L.append('')
        L.append('- 判定：%s（%ss）' % (st, el))
        L.append('- 摘要：%s' % APPX[qid])
        L.append('')
        tables = cube_tables_md(eff).strip()
        if tables:
            L.append(tables)
            L.append('')
            csql = cube_sql(qid, rec)
            if not csql.startswith('（'):
                L.append('**cube 生成 SQL**')
                L.append('')
                L.append('```sql\n%s\n```' % csql)
                L.append('')
    with open(OUT_MD, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(L) + '\n')
    print('written:', OUT_MD, len(L), 'lines')


if __name__ == '__main__':
    main()
