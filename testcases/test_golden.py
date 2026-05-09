import pytest
from commons.logger import logger
from commons.yaml_util import read_yaml_file
from commons.react_common import TestHelper
from tools.tool_func import *

# 读取测试数据
case_data = read_yaml_file('testdata/agent_react.yaml')['test_cases']

# 黄金集用例列表
GOLDEN_IDS = [
    "TC-002", "TC-003", "TC-006", "TC-007", "TC-011",
    "TC-014", "TC-015", "TC-021", "TC-022", "TC-027",
    "TC-028", "TC-031", "TC-040", "TC-041", "TC-043"
]

# 筛选黄金用例
golden_cases = [c for c in case_data if c["id"] in GOLDEN_IDS]

print(f"黄金集: {len(golden_cases)} 个用例")
for c in golden_cases:
    print(f"   - {c['id']}: {c.get('name', c['id'])}")


class TestGoldenSet:
    """黄金集回归测试"""

    @pytest.mark.parametrize("case", golden_cases, ids=lambda x: x["id"])
    def test_golden(self, agent_deepseek, judge_deepseek, case):
        """黄金用例 - 必须通过"""
        logger.info(f"\n{'=' * 50}")
        logger.info(f"黄金测试: {case['id']} - {case.get('name', case['id'])}")
        logger.info(f"{'=' * 50}")

        # 使用公共方法执行
        result = TestHelper.dispatch(agent_deepseek, judge_deepseek, case)

        # 断言结果
        assert result["passed"], f"黄金用例失败: {result.get('reason', '未知原因')}"

        logger.info(f"黄金用例 {case['id']} 通过")