import json
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Any
from pathlib import Path


class MetricsCalculator:
    """评测指标计算器 - 纯 Python 实现"""

    def __init__(self, test_run_id=None):
        self.test_run_id = test_run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results = []
        self.start_time = datetime.now()
        self.report_dir = Path("reports")
        self.report_dir.mkdir(exist_ok=True)

    def add_result(self, case_id: str, case_type: str, priority: str,
                   flags: List[str], judge_score: int,
                   trajectory_length: int = 0, tool_calls_count: int = 0,
                   success: bool = None, expected_steps: int = None,
                   execution_time: float = None):
        if success is None:
            success = judge_score >= 6

        self.results.append({
            "case_id": case_id,
            "case_type": case_type,
            "priority": priority,
            "flags": flags,
            "judge_score": judge_score,
            "trajectory_length": trajectory_length,
            "tool_calls_count": tool_calls_count,
            "expected_steps": expected_steps,
            "success": success,
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        })

    def _mean(self, numbers):
        """计算平均值"""
        if not numbers:
            return 0
        return sum(numbers) / len(numbers)

    def _median(self, numbers):
        """计算中位数"""
        if not numbers:
            return 0
        sorted_nums = sorted(numbers)
        n = len(sorted_nums)
        mid = n // 2
        if n % 2 == 0:
            return (sorted_nums[mid - 1] + sorted_nums[mid]) / 2
        return sorted_nums[mid]

    def _std(self, numbers):
        """计算标准差"""
        if len(numbers) <= 1:
            return 0
        mean = self._mean(numbers)
        variance = sum((x - mean) ** 2 for x in numbers) / (len(numbers) - 1)
        return variance ** 0.5

    def calculate_metrics(self) -> Dict[str, Any]:
        if not self.results:
            return {"error": "No results"}

        total = len(self.results)
        passed = sum(1 for r in self.results if r["success"])
        scores = [r["judge_score"] for r in self.results]

        return {
            "test_run_id": self.test_run_id,
            "total_cases": total,
            "passed_cases": passed,
            "failed_cases": total - passed,
            "pass_rate": passed / total if total > 0 else 0,
            "average_score": self._mean(scores),
            "median_score": self._median(scores),
            "std_score": self._std(scores),
            "score_distribution": {
                "excellent": len([s for s in scores if s >= 9]),
                "good": len([s for s in scores if 7 <= s <= 8]),
                "fair": len([s for s in scores if 4 <= s <= 6]),
                "poor": len([s for s in scores if s <= 3])
            },
            "by_priority": self._group_by("priority"),
            "by_capability": self._group_by_capability(),
            "by_case_type": self._group_by("case_type"),
            "efficiency": self._calculate_efficiency(),
            "execution_time": (datetime.now() - self.start_time).total_seconds()
        }

    def _group_by(self, key: str) -> Dict[str, Dict]:
        groups = defaultdict(list)
        for r in self.results:
            groups[r[key]].append(r)

        result = {}
        for name, group in groups.items():
            scores = [r["judge_score"] for r in group]
            passed = sum(1 for r in group if r["success"])
            result[name] = {
                "count": len(group),
                "pass_rate": passed / len(group),
                "avg_score": self._mean(scores)
            }
        return result

    def _group_by_capability(self) -> Dict[str, Dict]:
        capabilities = ["tool_calling", "task_planning", "feedback_loop",
                        "error_fallback", "state_memory", "safety", "ood"]
        result = {}
        for cap in capabilities:
            cap_results = [r for r in self.results if cap in r["flags"]]
            if cap_results:
                scores = [r["judge_score"] for r in cap_results]
                passed = sum(1 for r in cap_results if r["success"])
                result[cap] = {
                    "count": len(cap_results),
                    "pass_rate": passed / len(cap_results),
                    "avg_score": self._mean(scores)
                }
        return result

    def _calculate_efficiency(self) -> Dict[str, float]:
        efficiency = {}
        step_lengths = [r["trajectory_length"] for r in self.results if r["trajectory_length"] > 0]
        if step_lengths:
            efficiency["avg_trajectory_length"] = self._mean(step_lengths)

        tool_calls = [r["tool_calls_count"] for r in self.results if r["tool_calls_count"] > 0]
        if tool_calls:
            efficiency["avg_tool_calls"] = self._mean(tool_calls)

        return efficiency

    def print_summary(self):
        m = self.calculate_metrics()
        if "error" in m:
            print("无测试数据")
            return

        print(f"\n{'=' * 70}")
        print(f"📊 测试报告 - {self.test_run_id}")
        print(f"{'=' * 70}")
        print(f"\n📈 总体统计:")
        print(f"  总用例数: {m['total_cases']}")
        print(f"  通过: {m['passed_cases']} | 失败: {m['failed_cases']}")
        print(f"  通过率: {m['pass_rate']:.1%}")
        print(f"  平均分: {m['average_score']:.2f} (中位数: {m['median_score']:.2f})")

        print(f"\n📊 分数分布:")
        d = m['score_distribution']
        print(f"  优秀(9-10): {d['excellent']} 个")
        print(f"  良好(7-8):  {d['good']} 个")
        print(f"  及格(4-6):  {d['fair']} 个")
        print(f"  较差(0-3):  {d['poor']} 个")

        print(f"\n🎯 能力维度:")
        for cap, stats in m['by_capability'].items():
            bar = "█" * int(stats['pass_rate'] * 20)
            print(
                f"  {cap:15} | {stats['count']:3}个 | 通过率: {stats['pass_rate']:5.1%} | 均分: {stats['avg_score']:.1f} {bar}")

        if m['efficiency']:
            print(f"\n⚡ 效率:")
            if 'avg_trajectory_length' in m['efficiency']:
                print(f"  平均轨迹长度: {m['efficiency']['avg_trajectory_length']:.1f} 步")
            if 'avg_tool_calls' in m['efficiency']:
                print(f"  平均工具调用: {m['efficiency']['avg_tool_calls']:.1f} 次")

        print(f"\n⏱️  执行时间: {m['execution_time']:.1f} 秒")
        print(f"{'=' * 70}\n")

    def save_report(self):
        metrics = self.calculate_metrics()
        report_path = self.report_dir / f"metrics_{self.test_run_id}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)
        return str(report_path)