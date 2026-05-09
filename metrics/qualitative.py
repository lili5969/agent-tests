from collections import defaultdict
from typing import List, Dict, Any


class QualitativeAnalyzer:
    """失败模式分析器"""

    def __init__(self):
        self.failures = []

    def add_failure(self, case_id: str, question: str,
                    expected: str, actual: str,
                    judge_score: int, judge_reason: str,
                    flags: List[str], trajectory: List = None):
        """记录失败用例"""
        self.failures.append({
            "case_id": case_id,
            "question": question[:100],
            "expected": expected[:100] if expected else "",
            "actual": actual[:200],
            "judge_score": judge_score,
            "judge_reason": judge_reason,
            "flags": flags,
            "failure_type": self._classify_failure(judge_reason, flags)
        })

    def _classify_failure(self, reason: str, flags: List[str]) -> str:
        """分类失败类型"""
        reason_lower = reason.lower()

        if any(kw in reason_lower for kw in ["工具", "tool", "调用"]):
            if "未调用" in reason_lower:
                return "tool_not_called"
            return "tool_issue"

        if any(kw in reason_lower for kw in ["忘记", "forget", "记忆"]):
            return "memory_loss"

        if any(kw in reason_lower for kw in ["反问", "ask"]):
            return "unnecessary_ask"

        if any(kw in reason_lower for kw in ["步数", "step"]):
            return "step_limit"

        if "语义" in reason_lower or "理解" in reason_lower:
            return "semantic_error"

        return "other"

    def generate_analysis(self) -> Dict[str, Any]:
        """生成分析报告"""
        if not self.failures:
            return {"status": "no_failures"}

        type_stats = defaultdict(int)
        cap_stats = defaultdict(int)

        for f in self.failures:
            type_stats[f["failure_type"]] += 1
            for flag in f["flags"]:
                cap_stats[flag] += 1

        return {
            "total_failures": len(self.failures),
            "failure_by_type": dict(type_stats),
            "failure_by_capability": dict(cap_stats),
            "top_failures": self.failures[:3]
        }

    def print_summary(self):
        """打印摘要"""
        analysis = self.generate_analysis()

        if analysis.get("status") == "no_failures":
            print("\n🎉 太棒了！没有失败用例！")
            return

        print(f"\n{'=' * 70}")
        print("🔍 失败模式分析")
        print(f"{'=' * 70}")
        print(f"\n📊 失败统计: {analysis['total_failures']} 个失败用例")

        print(f"\n🔴 失败类型分布:")
        for ftype, count in sorted(analysis['failure_by_type'].items(), key=lambda x: -x[1]):
            print(f"  {ftype}: {count} 个")

        if analysis['top_failures']:
            print(f"\n📝 典型案例:")
            for f in analysis['top_failures'][:2]:
                print(f"  [{f['case_id']}] {f['question']}")
                print(f"    预期: {f['expected']}")
                print(f"    实际: {f['actual'][:80]}...")

        print(f"{'=' * 70}\n")