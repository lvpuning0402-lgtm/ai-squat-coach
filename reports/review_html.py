"""Render offline replay results as a self-contained, escaped Chinese report."""
from html import escape
import math

from feedback.capture_quality import assessment_limited
from feedback.insights import SessionInsightBuilder

PHASES = {'descent': '下降', 'bottom': '底部', 'ascent': '起身'}
VIEWS = {'FRONT': '正面', 'SIDE': '侧面'}
CONFIDENCE = {'HIGH': '高', 'MEDIUM': '中（参考）', 'LOW': '低（暂不评分）'}


def text(value):
    return escape(str(value), quote=True)


def score(value, confidence):
    if (confidence not in ('HIGH', 'MEDIUM') or isinstance(value, bool)
            or not isinstance(value, (int, float)) or not math.isfinite(value)):
        return '—'
    return f'约 {value:.0f}' if confidence == 'MEDIUM' else f'{value:.1f}'


def render_review_html(report):
    """Display an OFFLINE_REPLAY result; no camera, scripts or network resources."""
    summary = report.get('summary', {})
    coach = report.get('coach_feedback', {})
    reps = report.get('reps', [])
    sections = []
    for view, phases in summary.get('phase_observations_by_view', {}).items():
        rows = []
        for key, label in PHASES.items():
            phase = phases.get(key, {})
            rows.append('<tr>' + ''.join(f'<td>{text(v)}</td>' for v in (
                label, score(phase.get('score'), phase.get('confidence')),
                CONFIDENCE.get(phase.get('confidence'), '未知'),
                f"{phase.get('evaluated_reps', 0)} / {phase.get('eligible_reps', 0)}",
            )) + '</tr>')
        sections.append(f'<h3>{text(VIEWS.get(view, view))}</h3>'
                        '<table><thead><tr><th>阶段</th><th>参考分</th><th>置信度</th>'
                        '<th>纳入 / 可用动作</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table>')
    detail_rows = []
    for rep in reps:
        valid = rep.get('analysis_valid', True) and rep.get('set_valid', True)
        confidence = rep.get('detail_confidence')
        standard = '已排除' if not valid else ('通过' if rep.get('standard_met') else '需复核')
        if not valid:
            detail = '本次未纳入评价。'
        elif confidence not in ('HIGH', 'MEDIUM'):
            detail = '评价指标有限，不能据此判断动作不合格。' if assessment_limited(rep) else '证据不足，请先复核采集与对齐情况。'
        else:
            checks = rep.get('detail_checks', {})
            deductions = {d['name']: d.get('lost_points', 0) for d in rep.get('detail_deductions', [])}
            warnings = sorted(rep.get('detail_warnings', []), key=lambda name: (
                checks.get(name, {}).get('state') == 'REVIEW', deductions.get(name, 0)), reverse=True)
            detail = '；'.join(SessionInsightBuilder.DETAIL_TEXT_ZH.get(w, w) for w in warnings) or '暂无细节提示'
        evidence = rep.get('confidence_breakdown', {})
        phase_available = valid and all(evidence.get(k) in ('HIGH', 'MEDIUM')
                                        for k in ('pose_quality', 'view_quality'))
        phase_values = [score(rep.get('phase_scores', {}).get(p, {}).get('score'),
                              rep.get('phase_scores', {}).get(p, {}).get('confidence')) if phase_available and rep.get('phase_scores', {}).get(p, {}).get('samples', 0) >= 2 else '—'
                        for p in PHASES]
        values = (rep.get('rep', '—'), VIEWS.get(rep.get('view'), '未知'), standard,
                  score(rep.get('detail_score'), confidence) if valid else '—',
                  CONFIDENCE.get(confidence, '未知'), *phase_values, detail)
        detail_rows.append('<tr>' + ''.join(f'<td>{text(v)}</td>' for v in values) + '</tr>')
    feedback = ''.join(f'<p>{text(coach[k])}</p>' for k in ('headline', 'overview', 'focus', 'next_action') if coach.get(k))
    return '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>深蹲训练 · 离线复核</title><style>
*{box-sizing:border-box}body{margin:0;background:#f2f5f7;color:#182c37;font:16px/1.7 system-ui,sans-serif}
main{max-width:1100px;margin:40px auto;padding:0 24px}h1{margin:8px 0}h2{font-size:22px}h3{font-size:18px}
section{background:white;border:1px solid #dce4e8;border-radius:14px;padding:24px;margin:20px 0}
.tag{color:#126657;font-weight:700}.muted{color:#536571}table{border-collapse:collapse;width:100%;font-size:14px}
th,td{text-align:left;padding:12px;border-bottom:1px solid #e3e9ed;vertical-align:top}th{background:#edf5f3;white-space:nowrap}
.scroll{overflow-x:auto}.scroll td:not(:last-child){white-space:nowrap}
.scroll td:last-child{min-width:240px;overflow-wrap:anywhere}code{overflow-wrap:anywhere;font-size:12px}details{margin:18px 0}summary{cursor:pointer}
@media(max-width:600px){main{margin:20px auto;padding:0 12px}section{padding:16px}h1{font-size:26px}}
@media print{body{background:white}main{max-width:none;margin:0}section{break-inside:avoid}.scroll{overflow:visible}}
</style></head><body><main><div class="tag">AI SPORT COACH · 离线复核</div>
<h1>深蹲训练报告</h1><p class="muted">使用当前代码重新计算历史报告，不代表一次新训练；未写入训练数据库。</p>
''' + f'<p>来源训练：{text(report.get("source_session_id", "未知"))} · 类型：{text(report.get("session_type", "未知"))} · 动作记录：{len(reps)} 次</p>' + \
        '<section><h2>教练反馈</h2>' + (feedback or '<p>暂无可用反馈。</p>') + '</section>' + \
        '<section><h2>分阶段观察</h2><p class="muted">正面与侧面分开统计。各阶段可能来自不同动作子集，不能直接据此比较最弱阶段。约数为中等置信度参考值。</p>' + \
        (''.join(sections) or '<p>暂无可用阶段数据。</p>') + '</section>' + \
        '<section><h2>逐次结果</h2><p class="muted">整体细节分和阶段分使用不同汇总口径；标准通过不等于所有细节都完美。</p><div class="scroll"><table><thead><tr>' + \
        ''.join(f'<th>{label}</th>' for label in ('次数', '视角', '标准', '细节分', '置信度', '下降', '底部', '起身', '细节提示')) + \
        '</tr></thead><tbody>' + ''.join(detail_rows) + '</tbody></table></div></section>' + \
        '<details><summary>数据来源与回放状态</summary><p>原报告 SHA256：<code>' + text(report.get('source_sha256', '未提供')) + \
        '</code></p><ul>' + ''.join(f'<li>第 {text(n.get("rep"))} 次：{text(n.get("status"))}</li>' for n in report.get('replay_notes', [])) + \
        '</ul><p>ALIGNED：逐帧重新对齐；LEGACY_AGGREGATES_ONLY：仅复算旧聚合指标；UNAVAILABLE：对齐不可用。对齐成功仍是工程近似，不等于真人准确性验证。</p></details>' + \
        '<p class="muted">仅供训练观察，不是医学诊断或比赛裁判结果。TEST 数据不用于正式训练趋势。</p></main></body></html>'
