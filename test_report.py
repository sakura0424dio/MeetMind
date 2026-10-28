# test_report.py
# 项目完整测试脚本：支持录音文件、模拟文本、批量测试

import os
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from src.main import run_analysis_from_transcript
from src.agents.transcription_agent import TranscriptionAgent

# ============================================================
# 配置
# ============================================================

# 7 种会议类型及对应的预期识别结果
MEETING_TYPES = {
    "project_initiation": "project_initiation",
    "retrospective": "retrospective",
    "team_culture": "team_culture",
    "creative_design": "creative_design",
    "progress_sync": "progress_sync",
    "decision_review": "decision_review",
    "operation_marketing": "operation_marketing",
}

# 各类型对应的关键字段（用于验证报告内容）
EXPECTED_FIELDS = {
    "project_initiation": ["risk_assessment", "milestones", "core_goals"],
    "retrospective": ["improvement_sop", "lessons_learned", "what_went_well", "what_went_wrong"],
    "team_culture": ["awards"],
    "creative_design": ["ideas_list", "final_decision"],
    "progress_sync": ["blockers", "next_week_plan"],
    "decision_review": ["final_decision", "action_items"],
    "operation_marketing": ["activity_plan", "key_metrics"],
}

# ============================================================
# 模拟会议文本（用于快速测试）
# ============================================================

MOCK_MEETINGS = {
    "project_initiation": """
    今天我们开个项目启动会，讨论一下新游戏《星际冒险》的立项。
    市场部说现在的Roguelike手游很火，我们团队有技术积累，可以做。
    制作人觉得轻科幻题材比较符合我们团队的风格。
    技术负责人说，实时同步算法是主要难点，但可以引入现有的开源方案来解决。
    美术负责人说，渲染风格需要确认，最好下周出个Demo。
    大家一致决定，目标是Q4上线，首月新增用户50万。
    里程碑的话，7月完成Demo，9月开启内测，10月公测。
    制作人最后说，预算需要增加200万，用于外包部分美术资源，需要老板审批。
    """,

    "retrospective": """
    我们来复盘一下刚刚结束的夏季版本开发迭代。
    先说说做得好的方面，这次新英雄的皮肤设计玩家反馈很不错，好评率超过90%。
    技术侧也进步明显，重构了战斗同步算法，线上运行两周没有出现严重延迟。
    跨部门沟通也比之前顺畅，没有出现反复返工的情况。
    再来谈问题，新手引导太长了，20步的引导流程让很多玩家在第十步左右就退出了。
    美术和程序之间的接口文档更新不够及时，导致两边版本对不上。
    活动预告发得太晚了，距离上线只有两天才发预告。
    改进措施：新手引导精简到8步以内，接口文档代码提交时强制同步更新，活动预告至少提前一周发布。
    """,

    "team_culture": """
    今天开全员大会，主要是季度表彰和战略宣贯。
    经过全员投票，后端开发张伟和原画师陈露当选本季度优秀员工。
    每人奖励现金一万元。
    老板宣布下季度的战略重点是出海，要把游戏推向东南亚市场。
    现场QA环节，大家关心的是出海后海外办公的调休政策。
    人力资源部表示会在下周发邮件详细说明。
    """,

    "creative_design": """
    今天我们讨论新英雄'幽冥猎手'的技能设计方案。
    我准备了三个方案，A是隐身暗杀，B是范围毒雾，C是单体禁锢。
    数值策划强烈反对B方案，说范围毒雾在团战里的伤害数值太难平衡了。
    他推荐A方案，隐身暗杀操作上限高，玩家更喜欢这种秀操作的英雄。
    主策也觉得A方案更符合游戏的竞技调性。
    那就定A方案了，美术这边麻烦把隐身特效做成深紫色的粒子效果。
    技能CD时间先按10秒填表，后续测试再调整。
    """,

    "progress_sync": """
    大家汇报下这周进度。
    客户端这边UI重构基本完成了，但支付SDK的接入遇到了点问题，可能要延迟两天。
    服务器这边，好友系统和排行榜都已经上线了。
    不过压力测试发现，当在线用户超过1万人时，数据库连接池会耗尽，这是个严重的阻塞问题。
    策划这周主要把下个版本的活动文档写完了，目前不阻塞开发。
    当前最大的阻塞点就是服务器那边的连接池问题，优先解决。
    争取周五能出一个集成测试包。
    """,

    "decision_review": """
    讨论下个月版本V3.0要不要上公会战功能。
    玩家呼声很高，但研发这边说如果上公会战，涉及匹配、积分、实时对战，工作量太大了。
    必须砍掉'好友赠送体力'这个轻量功能，不然绝对来不及。
    产品经理觉得赠送体力对留存提升不明显，砍了就砍了。
    公会战是核心社交玩法，必须上。
    最终决定：V3.0上公会战，砍掉赠送体力。
    研发重新排期，周五前给出新的开发排期表。
    """,

    "operation_marketing": """
    下周就是端午节了，策划一场端午龙舟活动。
    玩家每天登录划龙舟，可以获取限定头像框和皮肤碎片。
    活动时间定在6月8号到6月15号。
    美术需要出三款新皮肤作为抽奖大奖。
    活动奖励池大概需要价值15万元的道具。
    玩家社区反馈，最近充值活动太多了，有点反感。
    这次活动就不开充值入口，主要做用户留存和活跃。
    15万预算走市场费用，我来签字。
    """
}


# ============================================================
# 核心测试函数
# ============================================================

def test_with_audio(audio_path: str, expected_type: str = None, verbose: bool = True):
    """
    使用录音文件进行测试
    """
    if not os.path.exists(audio_path):
        print(f"❌ 音频文件不存在: {audio_path}")
        return None

    file_name = os.path.basename(audio_path)
    print(f"\n{'=' * 60}")
    print(f"🎤 测试录音: {file_name}")
    print(f"{'=' * 60}")

    # 1. 转写音频
    print("🔄 正在转写音频 (Whisper)...")
    start_time = time.time()

    try:
        trans_agent = TranscriptionAgent()
        temp_state = {"audio_path": audio_path}
        result = trans_agent.run(temp_state)

        if result.get("error"):
            print(f"❌ 转写失败: {result['error']}")
            return None

        transcript = result.get("transcript", "")
        if not transcript:
            print("❌ 转写结果为空")
            return None

        print(f"✅ 转写完成，耗时 {time.time() - start_time:.1f}s，共 {len(transcript)} 字符")
        print(f"📄 转写预览: {transcript[:150]}...")

    except Exception as e:
        print(f"❌ 转写异常: {e}")
        return None

    # 2. Multi-Agent 分析
    print("🧠 开始 Multi-Agent 分析...")
    start_time = time.time()

    result = run_analysis_from_transcript(transcript)

    if result.get("error"):
        print(f"❌ 分析失败: {result['error']}")
        return None

    print(f"✅ 分析完成，耗时 {time.time() - start_time:.1f}s")

    # 3. 输出结果
    predicted_type = result.get("meeting_type", "未识别")
    print(f"\n🏷️ 识别类型: {predicted_type}")

    if expected_type:
        match = "✅ 匹配" if predicted_type == expected_type else "❌ 不匹配"
        print(f"📌 预期类型: {expected_type} → {match}")

    # 4. 验证关键字段
    if predicted_type in EXPECTED_FIELDS:
        report_json = result.get("report_json", {})
        fields = EXPECTED_FIELDS[predicted_type]
        present = [f for f in fields if report_json.get(f) is not None]
        missing = [f for f in fields if f not in report_json or report_json[f] is None]

        print(f"\n📊 关键字段检查 ({len(present)}/{len(fields)} 存在):")
        if present:
            print(f"  ✅ 存在: {', '.join(present)}")
        if missing:
            print(f"  ❌ 缺失: {', '.join(missing)}")

    # 5. 输出报告摘要
    print(f"\n📋 会议摘要:\n{result.get('summary', '无')[:200]}...")

    print(f"\n📄 报告预览:\n{result.get('report_markdown', '无')[:200]}...")

    return {
        "file": file_name,
        "expected_type": expected_type,
        "predicted_type": predicted_type,
        "match": predicted_type == expected_type if expected_type else None,
        "transcript_length": len(transcript),
        "summary": result.get("summary"),
        "report_json": result.get("report_json"),
        "report_markdown": result.get("report_markdown")
    }


def test_audio_folder(folder_path: str, verbose: bool = True):
    """
    批量测试文件夹中的所有音频文件
    自动根据文件名匹配预期类型
    """
    if not os.path.exists(folder_path):
        print(f"❌ 文件夹不存在: {folder_path}")
        return None

    audio_files = []
    for ext in ['.wav', '.mp3', '.m4a', '.flac', '.webm']:
        audio_files.extend(Path(folder_path).glob(f"*{ext}"))

    if not audio_files:
        print(f"❌ 文件夹中没有音频文件: {folder_path}")
        return None

    print(f"\n{'=' * 60}")
    print(f"📁 批量测试: {folder_path}")
    print(f"📊 找到 {len(audio_files)} 个音频文件")
    print(f"{'=' * 60}")

    results = []
    for audio_file in sorted(audio_files):
        # 从文件名推断预期类型
        file_name = audio_file.stem
        expected_type = None
        for mtype in MEETING_TYPES.keys():
            if mtype in file_name:
                expected_type = mtype
                break

        result = test_with_audio(str(audio_file), expected_type, verbose)
        if result:
            results.append(result)

    # 输出汇总
    print("\n" + "=" * 60)
    print("📊 批量测试结果汇总")
    print("=" * 60)

    total = len(results)
    passed = sum(1 for r in results if r.get("match") is True)
    failed = sum(1 for r in results if r.get("match") is False)
    unknown = sum(1 for r in results if r.get("match") is None)

    print(f"总计: {total} 个文件")
    print(f"✅ 匹配: {passed}")
    print(f"❌ 不匹配: {failed}")
    print(f"❓ 无预期: {unknown}")

    print("\n详细结果:")
    for r in results:
        status = "✅" if r.get("match") else ("❌" if r.get("match") is False else "❓")
        expected = r.get("expected_type") or "无"
        print(f"  {status} {r['file']} → 识别为: {r['predicted_type']} (预期: {expected})")

    return results


def test_with_text(text: str, title: str = "测试会议"):
    """使用纯文本测试"""
    print(f"\n{'=' * 60}")
    print(f"📝 测试会议: {title}")
    print(f"{'=' * 60}")

    result = run_analysis_from_transcript(text)

    if result.get("error"):
        print(f"❌ 测试失败: {result['error']}")
        return None

    print(f"\n✅ 会议类型: {result.get('meeting_type', '未识别')}")
    print(f"\n📋 会议摘要:\n{result.get('summary', '无')[:200]}...")
    print(f"\n📄 报告 Markdown:\n{result.get('report_markdown', '无')[:200]}...")

    return result


def test_with_mock(meeting_type: str):
    """使用模拟文本测试指定类型"""
    if meeting_type not in MOCK_MEETINGS:
        print(f"❌ 未知会议类型: {meeting_type}")
        print(f"可用类型: {list(MOCK_MEETINGS.keys())}")
        return None

    text = MOCK_MEETINGS[meeting_type]
    return test_with_text(text, f"模拟会议 - {meeting_type}")


def test_all_mock():
    """测试所有 7 种模拟会议类型"""
    print("\n" + "=" * 60)
    print("🚀 开始批量测试 7 种会议类型 (模拟文本)")
    print("=" * 60)

    results = {}
    for mtype in MOCK_MEETINGS.keys():
        print(f"\n{'=' * 60}")
        print(f"📝 测试: {mtype}")
        print(f"{'=' * 60}")

        text = MOCK_MEETINGS[mtype]
        result = run_analysis_from_transcript(text)

        if result.get("error"):
            results[mtype] = {"status": "❌ 失败", "error": result["error"]}
            print(f"❌ 错误: {result['error']}")
        else:
            predicted = result.get('meeting_type', '未识别')
            match = predicted == mtype
            results[mtype] = {"status": "✅" if match else "⚠️", "predicted": predicted}
            print(f"✅ 识别类型: {predicted} {'(匹配)' if match else '(不匹配)'}")
            print(f"📋 摘要预览: {result.get('summary', '')[:80]}...")

    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    for mtype, info in results.items():
        status = info.get("status", "未知")
        predicted = info.get("predicted", "N/A")
        print(f"  {status} {mtype} → {predicted}")

    return results


# ============================================================
# 命令行入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="项目完整测试脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 测试单个录音文件
  python test_report.py --audio data/sample_audio/test_retrospective.wav

  # 批量测试文件夹中的所有音频
  python test_report.py --dir data/sample_audio/

  # 测试所有模拟文本（快速验证）
  python test_report.py --all

  # 测试指定类型的模拟文本
  python test_report.py --mock retrospective

  # 自定义文本测试
  python test_report.py --text "会议内容..."
        """
    )

    parser.add_argument("--audio", type=str, help="单个音频文件路径")
    parser.add_argument("--dir", type=str, help="音频文件夹路径（批量测试所有音频）")
    parser.add_argument("--text", type=str, help="直接传入会议文本进行测试")
    parser.add_argument("--mock", type=str, choices=list(MOCK_MEETINGS.keys()),
                        help=f"使用内置模拟文本测试指定类型")
    parser.add_argument("--all", action="store_true", help="测试所有 7 种模拟会议类型")
    parser.add_argument("--verbose", "-v", action="store_true", help="输出详细信息")

    args = parser.parse_args()

    if args.audio:
        test_with_audio(args.audio, verbose=args.verbose)
        return

    if args.dir:
        test_audio_folder(args.dir, verbose=args.verbose)
        return

    if args.all:
        test_all_mock()
        return

    if args.mock:
        test_with_mock(args.mock)
        return

    if args.text:
        test_with_text(args.text)
        return

    # 默认：显示帮助信息
    parser.print_help()


if __name__ == "__main__":
    main()