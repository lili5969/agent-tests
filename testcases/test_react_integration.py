
import pytest
from commons.logger import logger
from commons.yaml_util import read_yaml_file
from tool_registry import TOOL_REGISTRY
from commons.react_common import TestHelper
from tools.tool_func import *

# 读取测试数据
case_data = read_yaml_file('testdata/agent_react.yaml')['test_cases']
smoke_cases = [c for c in case_data if c.get("priority") == "P0"]
capability_cases = [c for c in case_data if c.get("capability")]
multi_turns_cases = [c for c in case_data if "turns" in c]
trajectory_cases = [c for c in case_data if c.get("flag") == "trajectory"]
simple_cases = [c for c in case_data if c.get('flag') != "trajectory" and "turns" not in c and not c.get("capability")]

print(f"已注册的工具: {list(TOOL_REGISTRY.keys())}")


def collect_result(metrics, case, passed, score, answer=""):
    """统一收集测试结果"""
    metrics.add_result(
        case_id=case["id"],
        case_type="multi_turn" if "turns" in case else "single",
        priority=case.get("priority", "P1"),
        flags=case.get("flags", []),
        judge_score=score,
        success=passed,
        trajectory_length=getattr(metrics, '_last_traj_len', 0),
        tool_calls_count=getattr(metrics, '_last_tool_cnt', 0)
    )


class TestReActAgent:

    @pytest.mark.smoke
    @pytest.mark.parametrize("case", smoke_cases, ids=lambda x: x["id"])
    def test_smoke(self, agent_deepseek, judge_deepseek, case, metrics_calculator, qualitative_analyzer):

        result = TestHelper.dispatch(agent_deepseek, judge_deepseek, case)

        collect_result(metrics_calculator, case, result["passed"], result.get("score", 0), result.get("answer", ""))

        if not result["passed"]:
            qualitative_analyzer.add_failure(
                case_id=case["id"],
                question=case.get("question", ""),
                expected=str(case.get("expected_keywords", [])),
                actual=result.get("answer", ""),
                judge_score=result.get("score", 0),
                judge_reason=result.get("reason", ""),
                flags=case.get("flags", [])
            )

        assert result["passed"], f"冒烟失败: {result.get('reason', '未知原因')}"

    @pytest.mark.parametrize("case", simple_cases, ids=lambda x: x["id"])
    def test_simple(self, agent_deepseek, judge_deepseek, case, metrics_calculator):
        result = TestHelper.run_simple(agent_deepseek, case)

        # 如果有关键词且 llm_judge，用 Judge 覆盖
        if case.get('llm_judge') and result.get("answer"):
            judge_result = judge_deepseek.judge(
                question=case['question'],
                actual_answer=result["answer"],
                criteria=case.get('judge_criteria')
            )
            result["passed"] = judge_result["score"] >= 6
            result["score"] = judge_result["score"] if result["passed"] else 0

        collect_result(metrics_calculator, case, result["passed"], result.get("score", 0), result.get("answer", ""))
        assert result["passed"], f'测试失败: {result.get("reason", "未知原因")}'

    # ----- 轨迹测试：工具调用验证 -----
    @pytest.mark.parametrize("case", trajectory_cases, ids=lambda x: x["id"])
    def test_trajectory(self, agent_deepseek, judge_deepseek, case, metrics_calculator, qualitative_analyzer):
        # 执行测试前获取轨迹长度
        result = TestHelper.run_trajectory(agent_deepseek, case)

        # 保存指标数据
        if result.get("trajectory"):
            metrics_calculator._last_traj_len = len(result["trajectory"].steps)
            metrics_calculator._last_tool_cnt = len([s for s in result["trajectory"].steps if s.action_name])

        # LLM Judge 可选
        if case.get('llm_judge') and result.get("answer"):
            judge_result = judge_deepseek.judge(
                question=case["question"],
                actual_answer=result["answer"],
                criteria=case.get('judge_criteria')
            )
            logger.info(f"Judge score: {judge_result['score']}, reason: {judge_result['reason']}")
            result["score"] = judge_result["score"]
            result["reason"] = judge_result.get("reason", "")
            result["passed"] = result["passed"] and judge_result["score"] >= 6

        collect_result(metrics_calculator, case, result["passed"], 10 if result["passed"] else 0,
                       result.get("answer", ""))

        if not result["passed"]:
            qualitative_analyzer.add_failure(
                case_id=case["id"],
                question=case["question"],
                expected=str(case.get("expected_action_sequence", [])),
                actual=result.get("answer", "")[:200],
                judge_score=0,
                judge_reason=result.get("reason", ""),
                flags=case.get("flags", [])
            )

        assert result["passed"], f'轨迹测试失败: {result.get("reason", "未知原因")}'
        logger.info(f'✅ 轨迹测试通过 | 答案: {result.get("answer", "")[:50]}')

    # ----- 能力测试：LLM Judge 评分 -----
    @pytest.mark.parametrize("case", capability_cases, ids=lambda x: x["id"])
    def test_capability(self, agent_deepseek, judge_deepseek, case, metrics_calculator, qualitative_analyzer):
        logger.info(f"\n{'=' * 60}")
        logger.info(f" 能力测试: {case['id']} - {case.get('name', case['id'])}")
        logger.info(f"{'=' * 60}")

        result = TestHelper.dispatch(agent_deepseek, judge_deepseek, case)

        # ========== 新增：LLM Judge 逻辑 ==========
        # 如果用例需要 LLM Judge，且 dispatch 返回的结果中没有 judge 分数（即走了 run_trajectory/run_simple）
        if case.get('llm_judge') and result.get("answer"):
            # 构建问题文本（多轮场景取最后一轮）
            if "turns" in case:
                question = case["turns"][-1]["question"]
            else:
                question = case.get("question", "")

            # 调用 Judge
            judge_result = judge_deepseek.judge(
                question=question,
                actual_answer=result["answer"],
                criteria=case.get('judge_criteria')
            )
            logger.info(f"Judge score: {judge_result['score']}, reason: {judge_result['reason']}")

            # 覆盖 score 和 reason
            result["score"] = judge_result["score"]
            result["reason"] = judge_result.get("reason", "")
            result["passed"] = result["passed"] and judge_result["score"] >= 6
        # ========================================

        collect_result(metrics_calculator, case, result["passed"], result.get("score", 0), result.get("answer", ""))

        if not result["passed"]:
            logger.warning(f" 能力测试失败，记录到定性分析")
            qualitative_analyzer.add_failure(
                case["id"],
                case.get("question", case.get("turns", [{}])[-1].get("question", "")),
                str(case.get("expected_final_answer", [""])[0]),
                result.get("answer", ""),
                result.get("score", 0),
                result.get("reason", ""),
                case.get("flags", [])
            )

        min_score = 8 if case.get("priority") == "P0" else 6
        logger.info(f"   最低要求分数: {min_score}")

        assert result["passed"] and result.get("score", 0) >= min_score, \
            f"能力测试失败: {result.get('reason', '未知原因')}"

        logger.info(f" 能力测试通过\n")

    # ----- 多轮记忆测试 -----
    @pytest.mark.timeout(60)
    @pytest.mark.parametrize("case", multi_turns_cases, ids=lambda x: x["id"])
    def test_multiturn(self, agent_deepseek, judge_deepseek, case, metrics_calculator, qualitative_analyzer):
        result = TestHelper.run_multiturn(agent_deepseek, judge_deepseek, case)

        collect_result(metrics_calculator, case, result["passed"], result.get("score", 0), result.get("answer", ""))

        if not result["passed"]:
            qualitative_analyzer.add_failure(
                case["id"],
                case["turns"][-1]["question"],
                str(case.get("expected_keywords", [])),
                result.get("answer", ""),
                result.get("score", 0),
                result.get("reason", ""),
                case.get("flags", [])
            )

        assert result["passed"], f"多轮测试失败: {result.get('reason', '未知原因')}"