# scripts/generate_report_samples.py
"""为 8 种会议类型各准备一个例子，调用项目真实分析管线并保存报告样例。

说明：
- 项目默认模型已在 src/core/llm.py 中调整为 qwen-plus。
- 输出目录：data/outputs/report_samples/
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.llm import LLMClient  # noqa: E402

# 对 429/网络抖动做简单重试，不改变项目源码
_original_chat = LLMClient.chat


def _chat_with_retry(self, messages, temperature=0.7):
    for attempt in range(3):
        result = _original_chat(self, messages, temperature)
        if result is not None:
            return result
        time.sleep(3 * (attempt + 1))
    return None


LLMClient.chat = _chat_with_retry

from src.main import run_analysis_from_transcript  # noqa: E402

OUT_DIR = ROOT / "data" / "outputs" / "report_samples"
OUT_DIR.mkdir(parents=True, exist_ok=True)


SAMPLES = [
    {
        "key": "project_initiation",
        "emoji": "🚀",
        "label": "立项启动",
        "title": "《星海远征》项目立项会",
        "transcript": """张伟：今天开《星海远征》立项会。市场部调研显示，轻科幻 Roguelike 手游仍有空白，我们的技术积累可以复用。
李婷：目标用户是 18 到 30 岁男性，核心差异化是实时舰队协同战斗。
王磊：技术上实时同步是最大难点，概率中等，预案是引入成熟的开源帧同步方案。
陈露：美术风格定为低饱和科幻，预计需要 3 名原画、2 名特效。
张伟：目标定在明年 Q3 上线，首月新增 80 万，月流水 1200 万。
李婷：里程碑是 11 月完成 Demo，明年 2 月内测，5 月公测。
赵岩：预算需要增加 300 万，用于外包场景和音频，需要老板审批。""",
    },
    {
        "key": "creative_design",
        "emoji": "🎨",
        "label": "创意设计",
        "title": "新英雄“幽冥猎手”技能方案评审",
        "transcript": """李婷：今天评审新英雄“幽冥猎手”的技能方案，我准备了三个方向。
陈露：方案 A 是隐身暗杀，操作上限高；方案 B 是范围毒雾，团战强但数值难平衡；方案 C 是单体禁锢，偏控制。
王磊：范围毒雾在多人团战里很难调，容易破坏平衡。
赵岩：从玩家偏好数据看，秀操作的刺客类英雄讨论度更高。
李婷：那就定方案 A。陈露，隐身特效做成深紫色粒子，武器比例缩小一点。
陈露：收到，服饰颜色也改成暗夜蓝。
王磊：技能 CD 先按 10 秒填表，下周测试服验证。""",
    },
    {
        "key": "progress_sync",
        "emoji": "📊",
        "label": "研发进度",
        "title": "项目组第 12 周进度同步会",
        "transcript": """王磊：大家同步下本周进度。客户端 UI 重构完成 90%，支付 SDK 接入遇到签名问题，可能延后两天。
赵岩：服务器好友系统和排行榜已上线，但压测发现同时在线超过 1 万人时数据库连接池耗尽，这是当前最大阻塞。
陈露：美术这周完成了新场景原画，角色皮肤还差两套。
李婷：策划把下个版本活动文档写完了，不阻塞开发。
王磊：连接池问题优先解决，赵岩负责，周三前给出方案。
赵岩：收到，另外需要申请两台测试服务器。
王磊：下周目标：周五出集成测试包，陈露补齐皮肤，李婷完成活动配置。""",
    },
    {
        "key": "decision_review",
        "emoji": "⚖️",
        "label": "决策评审",
        "title": "V3.0 是否上线公会战决策会",
        "transcript": """张伟：今天讨论 V3.0 是否上公会战。玩家呼声很高，但研发说匹配、积分、实时对战工作量太大。
王磊：如果上公会战，必须砍掉“好友赠送体力”，否则排期绝对来不及。
李婷：赠送体力对留存的提升不明显，我同意砍掉。
赵岩：实时对战需要额外服务器资源，预算要加 50 万。
张伟：公会战是核心社交玩法，必须上。最终决定：V3.0 上公会战，砍掉赠送体力。
张伟：研发周五前给出新排期，赵岩同步服务器预算申请。
李婷：新版 UI 的预算还没批，列入待审批事项。""",
    },
    {
        "key": "retrospective",
        "emoji": "🔁",
        "label": "复盘总结",
        "title": "服务器崩溃事故复盘会",
        "transcript": """王磊：复盘昨晚服务器崩溃 2 小时的事故。直接原因是内存泄漏，玩家大量掉线。
赵岩：做得好的地方是监控报警后团队 10 分钟内响应，及时回滚止损。
李婷：做得不好的是告警阈值设置太晚，问题发生 40 分钟才触发。
张伟：根因是上线前没有做长时间压测，流程上缺少强制压测卡点。
王磊：改进措施：建立内存监控看板，告警阈值下调 30%，上线前必须完成 24 小时压测。
赵岩：责任人是我，下周三前完成看板，度量指标是告警平均发现时间小于 5 分钟。
李婷：经验教训写进发布 SOP，所有大版本强制执行。""",
    },
    {
        "key": "operation_marketing",
        "emoji": "📈",
        "label": "运营市场",
        "title": "端午节龙舟活动策划会",
        "transcript": """李婷：下周端午做龙舟活动。当前 DAU 12 万，目标活动期间提升到 15 万，留存从 45% 提到 50%。
赵岩：玩家社区最近反馈充值活动太多，有点反感，这次建议不开充值入口。
陈露：美术出三款限定皮肤作为抽奖大奖，需要额外一周工期。
李婷：活动时间定 6 月 8 日到 6 月 15 日，奖励池预算 15 万，走市场费用。
王磊：服务器需要扩容，预计活动峰值并发翻倍，预算 3 万。
李婷：渠道方面，B 站和抖音各投 5 万，主打“零充值也能拿限定”。
张伟：ROI 预估要做到 1 比 2，低于 1 比 1.5 就启动止损，提前准备公告。""",
    },
    {
        "key": "team_culture",
        "emoji": "🏆",
        "label": "团队文化",
        "title": "季度全员大会暨表彰会",
        "transcript": """张伟：今天开季度全员大会，先进行表彰。经过全员投票，后端张伟和原画师陈露当选本季度优秀员工，每人奖励一万元。
李婷：美术组获得最佳团队奖，共 12 人，表彰他们在新场景上的突破。
张伟：价值观标杆是“玩家第一”和“坦诚协作”，希望大家在跨部门合作中继续坚持。
王磊：下面宣贯下季度战略：重点出海东南亚，先在泰国和越南做小规模测试。
赵岩：员工提问：出海后海外办公的调休政策怎么安排？
李婷：人力资源部下周发邮件详细说明，同时收集大家的签证需求。
张伟：会后请 HR 把问答整理成 FAQ。""",
    },
    {
        "key": "general",
        "emoji": "📝",
        "label": "通用兜底",
        "title": "办公区搬迁与后勤安排沟通会",
        "transcript": """刘洋：今天同步一下办公区搬迁和后勤安排，不涉及业务决策。
赵岩：搬迁时间定在下月 15 日，周末进行，IT 会在周五下班前回收旧工位设备。
陈露：新办公区的工位按部门分配，美术组靠窗，策划组在中间区域。
李婷：班车路线需要调整，行政会发问卷收集大家的通勤需求。
王磊：停车位数量比现在少 10 个，先到先得，后续再协调。
刘洋：食堂供应商也换了，下周一开始试运营三天，欢迎大家反馈口味。
张伟：另外提醒大家本周五前完成消防演练签到。
刘洋：以上都是通知，有问题会后找行政。""",
    },
]


def safe_name(index: int, sample: dict) -> str:
    return f"{index:02d}_{sample['key']}"


def save_sample(index: int, sample: dict, result: dict, elapsed: float) -> dict:
    name = safe_name(index, sample)
    md_path = OUT_DIR / f"{name}.md"
    json_path = OUT_DIR / f"{name}.json"

    report_md = result.get("report_markdown") or ""
    meta = {
        "index": index,
        "expected_type": sample["key"],
        "detected_type": result.get("meeting_type"),
        "title": sample["title"],
        "label": sample["label"],
        "emoji": sample["emoji"],
        "elapsed_seconds": round(elapsed, 2),
        "transcript_chars": len(sample["transcript"]),
        "error": result.get("error"),
        "summary": result.get("summary"),
        "report_json": result.get("report_json"),
        "report_markdown": report_md,
    }

    md_path.write_text(report_md, encoding="utf-8")
    json_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


def build_combined(metas: list[dict]) -> None:
    lines = [
        "# MeetMind 8 类会议报告样例",
        "",
        f"- 生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}",
        "- 生成方式：调用项目真实分析管线 `src.main.run_analysis_from_transcript`",
        "- 使用模型：`qwen-plus`（项目默认模型）",
        "- 每个样例包含：输入转录、识别类型、结构化 JSON、Markdown 报告",
        "",
        "| # | 样例 | 预期类型 | 实际识别 | 耗时 |",
        "|---|---|---|---|---|",
    ]
    for m in metas:
        lines.append(
            f"| {m['index']} | {m['emoji']} {m['label']} | `{m['expected_type']}` | "
            f"`{m['detected_type']}` | {m['elapsed_seconds']}s |"
        )
    lines.append("")

    for m in metas:
        lines.extend([
            "---",
            "",
            f"## {m['index']}. {m['emoji']} {m['label']}：{m['title']}",
            "",
            f"- 预期类型：`{m['expected_type']}`",
            f"- 实际识别：`{m['detected_type']}`",
            f"- 耗时：{m['elapsed_seconds']} 秒；转录长度：{m['transcript_chars']} 字符",
            "",
        ])
        if m.get("error"):
            lines.extend([f"> ⚠️ 错误：{m['error']}", ""])

        lines.extend([
            "<details>",
            "<summary>输入转录</summary>",
            "",
            "~~~text",
            m.get("transcript", ""),
            "~~~",
            "",
            "</details>",
            "",
            "### Markdown 报告",
            "",
            m.get("report_markdown") or "（无）",
            "",
            "<details>",
            "<summary>结构化 JSON</summary>",
            "",
            "~~~json",
            json.dumps(m.get("report_json") or {}, ensure_ascii=False, indent=2),
            "~~~",
            "",
            "</details>",
            "",
        ])

    (OUT_DIR / "ALL_REPORTS.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    force = "--force" in sys.argv
    metas: list[dict] = []

    for index, sample in enumerate(SAMPLES, start=1):
        name = safe_name(index, sample)
        json_path = OUT_DIR / f"{name}.json"

        if json_path.exists() and not force:
            meta = json.loads(json_path.read_text(encoding="utf-8"))
            meta["transcript"] = sample["transcript"]
            metas.append(meta)
            print(f"[{index}/8] SKIP {sample['key']} (已存在)", flush=True)
            continue

        print(f"[{index}/8] START {sample['key']} ...", flush=True)
        started = time.time()
        try:
            result = run_analysis_from_transcript(sample["transcript"])
        except Exception as exc:  # noqa: BLE001
            result = {"error": f"{type(exc).__name__}: {exc}"}
        elapsed = time.time() - started

        meta = save_sample(index, sample, result, elapsed)
        meta["transcript"] = sample["transcript"]
        metas.append(meta)

        print(
            f"[{index}/8] DONE  expected={sample['key']} "
            f"detected={meta['detected_type']} elapsed={elapsed:.1f}s "
            f"report_chars={len(meta['report_markdown'] or '')}",
            flush=True,
        )

    metas.sort(key=lambda item: item["index"])
    build_combined(metas)

    print("\n===== SUMMARY =====", flush=True)
    for meta in metas:
        status = "OK" if meta["detected_type"] == meta["expected_type"] else "MISMATCH"
        print(
            f"{meta['index']}. {meta['expected_type']:22s} -> {meta['detected_type']!s:22s} "
            f"{status:8s} {meta['elapsed_seconds']:6.1f}s",
            flush=True,
        )
    print(f"\n输出目录: {OUT_DIR}", flush=True)


if __name__ == "__main__":
    main()
