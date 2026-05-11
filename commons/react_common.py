from collections import Counter
from commons.logger import logger


class TestHelper:
    """测试公共辅助类"""

    # ========== 参数验证辅助方法 ==========

    @staticmethod
    def assert_args_match(expected_args, actual_args, tool_name=None, step_index=None):
        """校验参数，支持 dict 和 list 两种格式"""
        if not expected_args:
            return True
        if isinstance(expected_args, dict):
            for key, value in expected_args.items():
                if actual_args.get(key) != value:
                    raise AssertionError(
                        f"{'步骤' + str(step_index + 1) if step_index is not None else tool_name} "
                        f"参数 {key} 不匹配！期望 {value}，实际 {actual_args.get(key)}"
                    )
        elif isinstance(expected_args, list):
            actual_values = list(actual_args.values())
            if len(actual_values) != len(expected_args):
                raise AssertionError(
                    f"参数数量不匹配！期望 {len(expected_args)} 个，实际 {len(actual_values)} 个"
                )
            for j, (actual_val, expected_val) in enumerate(zip(actual_values, expected_args)):
                if actual_val != expected_val:
                    raise AssertionError(
                        f"第{j + 1}个参数不匹配！期望 {expected_val}，实际 {actual_val}"
                    )
        return True

    @staticmethod
    def validate_parameters(case, trajectory, mode):
        """验证参数 - 支持 strict/order_insensitive/contains 三种模式"""
        if mode == "strict":
            for i, expected in enumerate(case["expected_action_sequence"]):
                actual_args = trajectory.steps[i].args
                TestHelper.assert_args_match(expected.get("args"), actual_args, step_index=i)
        elif mode == "order_insensitive":
            actual_map = {step.action_name: step.args for step in trajectory.steps}
            for expected in case["expected_action_sequence"]:
                tool_name = expected["action"]
                actual_args = actual_map.get(tool_name)
                if actual_args is None:
                    raise AssertionError(f"工具 {tool_name} 未被调用")
                TestHelper.assert_args_match(expected.get("args"), actual_args, tool_name=tool_name)
        elif mode == "contains":
            actual_map = {step.action_name: step.args for step in trajectory.steps}
            for expected in case["expected_action_sequence"]:
                tool_name = expected["action"]
                if tool_name not in actual_map:
                    logger.warning(f"期望调用工具 {tool_name} 但未调用")
                    continue
                actual_args = actual_map[tool_name]
                TestHelper.assert_args_match(expected.get("args"), actual_args, tool_name=tool_name)
        return True

    @staticmethod
    def validate_dependencies(case, trajectory):
        """验证参数依赖关系"""
        if "parameter_dependencies" not in case:
            return True
        mode = case.get("action_match_mode", "strict")
        if mode != "strict":
            return True

        for dep in case["parameter_dependencies"]:
            target_step = dep["target_step"]
            target_param = dep["target_param"]
            source_step = dep["source_step"]
            raw_result = trajectory.steps[source_step].result
            source_field = dep.get("source_field", "result")

            # 获取源值
            if source_field == "result":
                source_value = raw_result
            elif source_field.startswith("result."):
                field_name = source_field.split(".")[1]
                source_value = raw_result.get(field_name) if isinstance(raw_result, dict) else None
            else:
                source_value = trajectory.steps[source_step].args.get(source_field)

            # 获取目标值
            target_value = trajectory.steps[target_step].args.get(target_param)

            logger.info(
                f"依赖验证: 步骤{target_step + 1}的参数 {target_param} = {target_value} "
                f"应该等于步骤{source_step + 1}的{source_field} = {source_value}"
            )

            if source_value != target_value:
                raise AssertionError(
                    f"依赖错误！步骤{target_step + 1}的参数 '{target_param}' "
                    f"应该是步骤{source_step + 1}的{source_field} ({source_value})，实际是 {target_value}"
                )
        return True

    @staticmethod
    def verify_trajectory(case, answer, trajectory):
        """验证轨迹 - 动作序列、参数、依赖等"""
        logger.info(f"\n{'=' * 60}")
        logger.info(f"开始轨迹验证: {case['id']} - {case.get('name', case['id'])}")
        logger.info(f"{'=' * 60}")

        expected_actions = [step["action"] for step in case["expected_action_sequence"]]
        actual_actions = [step.action_name for step in trajectory.steps]
        mode = case.get("action_match_mode", "strict")

        logger.info(f"验证模式: {mode}")
        logger.info(f"期望动作序列: {expected_actions}")
        logger.info(f"实际动作序列: {actual_actions}")

        # 1. 验证动作序列
        logger.info(f"\n 步骤1: 验证动作序列")
        if mode == "order_insensitive":
            if Counter(expected_actions) != Counter(actual_actions):
                logger.error(f" 无序动作验证失败!")
                logger.error(f"   期望: {expected_actions}")
                logger.error(f"   实际: {actual_actions}")
                raise AssertionError(
                    f"无序action验证失败! 期望 {expected_actions}, 实际 {actual_actions}"
                )
            logger.info(f"无序动作验证通过")


        elif mode == 'strict':
            logger.info(f"   模式: strict，期望序列: {expected_actions}，实际序列: {actual_actions}")
            if actual_actions != expected_actions:
                logger.error(f"   严格模式动作序列验证失败!")
                logger.error(f"     期望顺序: {expected_actions}")
                logger.error(f"     实际顺序: {actual_actions}")
                raise AssertionError(
                    f"动作序列不匹配！期望顺序 {expected_actions}，实际 {actual_actions}"
                )
            if not expected_actions:
                logger.info(f" 期望无工具调用 (expected_action_sequence 为空)，实际也无调用")
            else:

                logger.info(f" 严格模式动作序列验证通过")

        elif mode == "contains":
            missing_actions = []
            for action in expected_actions:
                if action not in actual_actions:
                    missing_actions.append(action)
            if missing_actions:
                logger.error(f" 包含模式验证失败! 缺少必要工具: {missing_actions}")
                logger.error(f"   期望包含: {expected_actions}")
                logger.error(f"   实际调用: {actual_actions}")
                raise AssertionError(
                    f"缺少必要工具 {missing_actions}，实际调用 {actual_actions}"
                )
            logger.info(f" 包含模式验证通过，必要工具 {expected_actions} 均已调用")

        # 2. 验证参数
        logger.info(f"\n 步骤2: 验证工具参数")
        try:
            TestHelper.validate_parameters(case, trajectory, mode)
            logger.info(f" 参数验证通过")
        except AssertionError as e:
            logger.error(f" 参数验证失败: {e}")
            raise

        # 3. 验证参数依赖
        if "parameter_dependencies" in case:
            logger.info(f"\n 步骤3: 验证参数依赖")
            logger.info(f"   依赖配置: {case['parameter_dependencies']}")
            try:
                TestHelper.validate_dependencies(case, trajectory)
                logger.info(f" 参数依赖验证通过")
            except AssertionError as e:
                logger.error(f" 参数依赖验证失败: {e}")
                raise
        else:
            logger.info(f"\n 步骤3: 无参数依赖配置，跳过")

        # 4. 验证禁止动作
        if "forbidden_actions" in case:
            logger.info(f"\n 步骤4: 验证禁止动作")
            logger.info(f"   禁止动作: {case['forbidden_actions']}")
            for forbidden in case["forbidden_actions"]:
                if forbidden in actual_actions:
                    logger.error(f" 使用了禁止的工具: {forbidden}")
                    raise AssertionError(f"使用了禁止的工具: {forbidden}")
            logger.info(f" 禁止动作验证通过，未使用禁止工具")
        else:
            logger.info(f"\n 步骤4: 无禁止动作配置，跳过")

        # 5. 验证步数限制
        logger.info(f"\n 步骤5: 验证步数限制")
        max_steps = case.get("max_steps", 5)
        actual_steps = len(trajectory.steps)
        logger.info(f"   最大步数: {max_steps}, 实际步数: {actual_steps}")
        if actual_steps > max_steps:
            logger.error(f" 超过最大步数限制! {actual_steps} > {max_steps}")
            raise AssertionError(
                f"超过最大步数限制 {max_steps}，实际 {actual_steps}"
            )
        logger.info(f" 步数限制验证通过")

        # 6. 验证正常结束
        logger.info(f"\n 步骤6: 验证结束状态")
        logger.info(f"   结束状态: {trajectory.end_status}")
        if trajectory.end_status != "Final Answer":
            logger.error(f" 非正常结束: {trajectory.end_status}")
            raise AssertionError(f"非正常结束: {trajectory.end_status}")
        logger.info(f" 结束状态验证通过")

        # 7. 验证最终答案
        if "expected_final_answer" in case:
            logger.info(f"\n 步骤7: 验证最终答案")
            logger.info(f"   期望关键词: {case['expected_final_answer']}")
            logger.info(f"   实际答案: {answer[:200]}..." if len(answer) > 200 else f"   实际答案: {answer}")
            for keyword in case["expected_final_answer"]:
                if keyword not in answer:
                    logger.error(f" 最终答案中未找到关键词: {keyword}")
                    raise AssertionError(
                        f"最终答案中未找到预期关键词: {keyword}，实际回答: {answer}"
                    )
            logger.info(f" 最终答案验证通过")
        else:
            logger.info(f"\n 步骤7: 无最终答案配置，跳过")

        logger.info(f"\n{'=' * 60}")
        logger.info(f" 轨迹验证全部通过!")
        logger.info(f"{'=' * 60}\n")

        return True

    # ========== 关键词验证辅助方法 ==========

    @staticmethod
    def validate_keywords(answer, case):
        """
        验证关键词
        - expected_keywords: 至少匹配一个（any）
        - expected_not_keywords: 都不能出现
        """
        expected_keywords = case.get("expected_keywords", [])
        if expected_keywords:
            matched = any(kw in answer for kw in expected_keywords)
            if not matched:
                raise AssertionError(f"未找到预期关键词 {expected_keywords}，实际回答: {answer}")

        for kw in case.get("expected_not_keywords", []):
            if kw in answer:
                raise AssertionError(f"出现禁止词: {kw}，实际回答: {answer}")

        return True

    # ========== LLM Judge 统一方法 ==========

    @staticmethod
    def run_llm_judge(agent, judge, case):
        """
        统一的 LLM Judge 打分方法
        适用于所有 llm_judge: true 且无 expected_action_sequence 的用例
        """
        try:
            # 1. 执行 Agent 获取回答和轨迹
            if "turns" in case:
                # 多轮场景
                messages = [{"role": "system", "content": agent.system_prompt}]
                for turn in case["turns"]:
                    messages.append({"role": "user", "content": turn["question"]})
                    agent.run_with_context(messages, record_trajectory=False)
                answer = messages[-1].get("content", "")
                question = case["turns"][-1]["question"]
                trajectory_text = "（多轮对话，中间步骤略）"
                logger.info(f"多轮场景，最后一轮问题: {question}")
            else:
                # 单轮场景：记录完整轨迹
                answer = agent.run(case["question"], record_trajectory=True)
                trajectory = agent.get_trajectory()
                trajectory_text = "\n".join([
                    f"Step {step.step_num}: {step.action_name}({step.args}) -> {step.result}"
                    for step in trajectory.steps
                ]) if trajectory else "无轨迹记录"
                question = case["question"]
                logger.info(f"单轮场景，轨迹步数: {len(trajectory.steps) if trajectory else 0}")

            logger.info(f"问题: {question}")
            logger.info(f"回答: {answer[:200]}..." if len(answer) > 200 else f"回答: {answer}")

            # 2. 构建 Judge 上下文
            context = f"""
系统提示词（System Prompt）：
{agent.system_prompt}

执行轨迹（Trajectory）：
{trajectory_text}

用户问题：{question}

Agent 回答：{answer}

黄金标准（Golden Standard）：
{case.get("golden_standard", "")}
"""

            # 3. 获取 judge_criteria
            judge_criteria = case.get("judge_criteria")

            if judge_criteria:
                final_criteria = f"{context}\n{judge_criteria}"
                logger.info(f"使用自定义 judge_criteria，长度: {len(final_criteria)} 字符")
            else:
                # 默认 judge_criteria
                default_criteria = "评估回答质量，0-10分。请根据回答的准确性、完整性、合理性给出评分。"
                final_criteria = f"{context}\n{default_criteria}"
                logger.info(f"使用默认 judge_criteria")

            # 4. 调用 LLM Judge 打分
            logger.info("调用 LLM Judge 打分...")
            judge_result = judge.judge(
                question=question,
                actual_answer=answer,
                criteria=final_criteria
            )

            score = judge_result["score"]
            reason = judge_result.get("reason", "")

            logger.info(f"Judge 评分: {score}/10")
            logger.info(f"Judge 评语: {reason}")

            # 5. 根据优先级决定阈值
            min_score = 8 if case.get("priority") == "P0" else 6
            passed = score >= min_score

            status = "✅ 通过" if passed else "❌ 失败"
            logger.info(f"最终结果: {status} (阈值: {min_score}分)")

            return {
                "passed": passed,
                "score": score,
                "answer": answer,
                "reason": reason,
                "judge_response": judge_result
            }

        except AssertionError as e:
            logger.error(f"断言失败: {e}")
            return {"passed": False, "score": 0, "reason": str(e), "answer": ""}
        except Exception as e:
            logger.error(f"异常: {e}")
            return {"passed": False, "score": 0, "reason": str(e), "answer": ""}

    # ========== 各类型测试执行方法 ==========

    @staticmethod
    def run_simple(agent, case):
        """执行简单关键词测试"""
        try:
            answer = agent.run(case["question"])
            TestHelper.validate_keywords(answer, case)
            return {"passed": True, "score": 10, "answer": answer}
        except AssertionError as e:
            return {"passed": False, "score": 0, "reason": str(e), "answer": answer}
        except Exception as e:
            return {"passed": False, "score": 0, "reason": str(e), "answer": ""}

    @staticmethod
    def run_trajectory(agent, case):
        """执行轨迹测试（仅轨迹验证，不含 Judge）"""
        logger.info(f"\n{'=' * 70}")
        logger.info(f" [TRAJECTORY_VERIFY] 用例: {case['id']} - {case.get('name', case['id'])}")
        logger.info(f"   expected_action_sequence: {case.get('expected_action_sequence', '未设置')}")
        logger.info(f"{'=' * 70}")

        try:
            answer = agent.run(case["question"], record_trajectory=True)
            traj = agent.get_trajectory()

            actual_actions = [step.action_name for step in traj.steps]
            logger.info(f"   📋 实际工具调用序列: {actual_actions}")

            # 验证轨迹
            TestHelper.verify_trajectory(case, answer, traj)

            # 验证关键词（兜底）
            TestHelper.validate_keywords(answer, case)

            logger.info(f" [TRAJECTORY_VERIFY] 通过: {case['id']}\n")

            return {
                "passed": True,
                "score": 10,
                "answer": answer,
                "trajectory": traj,
                "trajectory_length": len(traj.steps),
                "tool_calls_count": len([s for s in traj.steps if s.action_name])
            }
        except AssertionError as e:
            logger.error(f"❌ [TRAJECTORY_VERIFY] 失败: {case['id']} - {e}\n")
            return {"passed": False, "score": 0, "reason": str(e), "answer": ""}
        except Exception as e:
            logger.error(f"❌ [TRAJECTORY_VERIFY] 异常: {case['id']} - {e}\n")
            return {"passed": False, "score": 0, "reason": str(e), "answer": ""}


    @staticmethod
    def run_multiturn(agent, judge, case):
        """执行多轮测试"""
        try:
            messages = [{"role": "system", "content": agent.system_prompt}]

            for turn in case["turns"]:
                messages.append({"role": "user", "content": turn["question"]})
                agent.run_with_context(messages, record_trajectory=False)

            final_answer = messages[-1].get("content", "")

            # 如果需要 LLM Judge
            if case.get("llm_judge"):
                return TestHelper.run_llm_judge(agent, judge, case)

            # 否则用关键词验证
            TestHelper.validate_keywords(final_answer, case)
            return {"passed": True, "score": 10, "answer": final_answer}

        except AssertionError as e:
            return {"passed": False, "score": 0, "reason": str(e), "answer": ""}
        except Exception as e:
            return {"passed": False, "score": 0, "reason": str(e), "answer": ""}


    @staticmethod
    def dispatch(agent, judge, case):
        # 1. 轨迹验证
        if "expected_action_sequence" in case:
            return TestHelper.run_trajectory(agent, case)

        # 2. 多轮对话
        if "turns" in case:
            return TestHelper.run_multiturn(agent, judge, case)

        # 3. LLM Judge（只有明确写了 llm_judge: true 才走）
        if case.get("llm_judge"):
            return TestHelper.run_llm_judge(agent, judge, case)

        # 4. 其他所有（包括 capability: true 的用例）→ 走简单验证
        return TestHelper.run_simple(agent, case)