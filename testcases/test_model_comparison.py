"""
模型对比测试：Qwen2 vs DeepSeek

注意：本测试依赖本地 Ollama 环境，CI 中会自动跳过。
手动运行需要先安装 Ollama 并拉取 qwen2:7b 模型。

运行方式：
    pytest testcases/test_model_comparison.py -v
"""




import pytest
from commons.logger import logger
from commons.yaml_util import read_yaml_file
from tool_registry import TOOL_REGISTRY
from tools.tool_func import *
from commons.react_common import TestHelper

# 读取对比测试数据
case_data = read_yaml_file('testdata/agent_react.yaml')['test_cases']
comparison_cases = [c for c in case_data if c.get("capability")]


print(f"📊 模型对比用例数: {len(comparison_cases)}")


class TestModelComparison:
    """模型对比测试"""

    @pytest.mark.model_comparison
    @pytest.mark.parametrize("case", comparison_cases, ids=lambda x: x["id"])
    def test_compare_models(self, case, agent_ollama, agent_deepseek, judge_deepseek):
        """对比 Qwen2 和 DeepSeek 的表现"""

        models = {
            "Qwen2": agent_ollama,
            "DeepSeek": agent_deepseek
        }

        results = {}

        for name, agent in models.items():
            logger.info(f"\n{'=' * 40}")
            logger.info(f"正在测试: {name} - {case['id']}")
            logger.info(f"{'=' * 40}")

            # 使用公共方法执行
            result = TestHelper.dispatch(agent, judge_deepseek, case)
            results[name] = result
            logger.info(f"{name} 结果: passed={result['passed']}, score={result.get('score', 'N/A')}")

        # 对比结论
        self._compare_results(results, case)

    def _compare_results(self, results, case):
        """对比两个模型的结果"""

        qwen = results.get("Qwen2", {})
        deepseek = results.get("DeepSeek", {})

        qwen_passed = qwen.get("passed", False)
        deepseek_passed = deepseek.get("passed", False)
        qwen_score = qwen.get("score", 0)
        deepseek_score = deepseek.get("score", 0)

        logger.info(f"\n{'=' * 50}")
        logger.info(f"📊 对比结果: {case['id']} - {case.get('name', case['id'])}")
        logger.info(f"{'=' * 50}")
        logger.info(f"Qwen2:    passed={qwen_passed}, score={qwen_score}")
        logger.info(f"DeepSeek: passed={deepseek_passed}, score={deepseek_score}")

        diff = deepseek_score - qwen_score
        if diff > 0:
            logger.info(f"✅ DeepSeek 领先 {diff} 分")
        elif diff < 0:
            logger.info(f"⚠️ DeepSeek 落后 {abs(diff)} 分")
        else:
            logger.info(f"🤝 平局")

        # 断言：DeepSeek 不应明显落后于 Qwen2
        if qwen_passed and not deepseek_passed:
            pytest.fail(f"DeepSeek 失败但 Qwen2 通过: {deepseek.get('reason', '未知原因')}")

        if deepseek_score < qwen_score - 2:
            pytest.fail(f"DeepSeek 得分 {deepseek_score} 明显低于 Qwen2 {qwen_score}")