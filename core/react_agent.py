import pytest
from commons.logger import logger
from clients.ollama_client import OllamaClient
from commons.tool_params_validate import APITest
import json
from dataclasses import dataclass, field
from typing import List, Dict,Any, Optional
from langsmith import traceable

@dataclass
class TrajectoryStep:
    """轨迹中的每一步"""
    step_num: int
    action_name: str
    args: Dict[str, Any]
    result: Any = None
    timestamp: float = None

@dataclass
class Trajectory:
    """完整轨迹"""
    steps: List[TrajectoryStep] = field(default_factory=list)
    end_status: str = None
    final_answer: str = None
    total_steps: int = 0

    def add_step(self, step: TrajectoryStep):
        self.steps.append(step)
        self.total_steps = len(self.steps)

    def get_step_result(self, step_index):
        """获取指定步骤的结果"""
        if step_index < len(self.steps):
            return self.steps[step_index].result
        return None

class ReActAgent:
    def __init__(self, llm_client,tools_schema,tool_registry,tool_deps_config = None):
        self.llm_client = llm_client
        self.tools_schema = tools_schema
        self.tool_registry = tool_registry
        self.tool_deps_config = tool_deps_config or []
        self.system_prompt =self._build_system_prompt()
        self.tool_validator = APITest()
        self.tool_rules = self.tool_validator.validate_tool_validator_from_schema(tools_schema)

        self.tool_result_cache = {}
        self.trajectory = None #轨迹记录
        print(f"✅ 已注册工具: {list(self.tool_registry.keys())}")

    @traceable(name = 'ReAct.run')
    def run(self, question, max_steps=5,record_trajectory = False):

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": question}
        ]
        return self._run_loop(messages, max_steps, record_trajectory)

    def _run_loop(self, messages, max_steps, record_trajectory):
        """ReAct 循环核心，不负责初始化 messages"""
        if record_trajectory:
            self.trajectory = Trajectory()

        self.tool_result_cache.clear()
        step_num = 0

        for step in range(max_steps):
            step_num += 1
            logger.info(f'\n---step {step + 1}---')

            res = self._llm_call(messages)
            message = res['message']
            logger.info(f"LLM 返回: {message}")
            messages.append(message)

            tool_calls = message.get('tool_calls', [])

            if tool_calls:
                for tool_call in message['tool_calls']:
                    tool_name = tool_call['function']['name']
                    tool_args_str = tool_call['function']['arguments']
                    tool_call_id = tool_call.get('id', f'tool_{tool_name}_{id(tool_call)}')
                    logger.info(f'调用工具:{tool_name}({tool_args_str})')

                    # 仅兼容接口格式：str / dict 接口标准差异
                    if isinstance(tool_args_str, dict):
                        tool_args = tool_args_str
                    else:
                        try:
                            tool_args = json.loads(tool_args_str)
                        except Exception as e:
                            logger.error(f'参数解析错误: {str(e)}')
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call_id,
                                "content": f"参数解析失败{str(e)}"
                            })
                            continue

                    # 记录轨迹
                    if record_trajectory:
                        trajectory_step = TrajectoryStep(
                            step_num=step_num,
                            action_name=tool_name,
                            args=tool_args
                        )
                    # 工具参数校验
                    ok, msg = self.tool_validator.check_tool(tool_name, tool_args, self.tool_rules)
                    if not ok:
                        logger.error(f"校验失败：{msg}")
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "content": f'校验失败:{msg}'
                        })
                        continue

                    # 依赖解析 + 执行工具
                    tool_args = self._resolve_dependencies(tool_name, tool_args)
                    if tool_name in self.tool_registry:
                        try:
                            result = self.tool_registry[tool_name](**tool_args)
                            logger.info(f'工具返回：{result}')

                            # 记录结果到轨迹
                            if record_trajectory:
                                trajectory_step.result = result
                                self.trajectory.add_step(trajectory_step)
                                print(f'记录 result: {result}')
                            self._cache_result(tool_name, result)

                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call_id,
                                "content": str(result)
                            })
                        except Exception as e:
                            logger.info(f'工具执行异常:{str(e)}')
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call_id,
                                "content": f'执行失败: {str(e)}'
                            })
                    else:
                        logger.info(f'未知工具:{tool_name}')
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "content": f"错误:未知工具 {tool_name}"
                        })
                continue

            content = message.get('content', '').strip()
            if content:
                logger.info(f'最终答案：{content}')
                if record_trajectory:
                    self.trajectory.end_status = "Final Answer"
                    self.trajectory.final_answer = content
                return content

        final_answer = f'达到最大步数限制({max_steps}), 未完成推理。'
        logger.info(f'最终答案: {final_answer}')
        if record_trajectory:
            self.trajectory.end_status = "Max Steps Reached"
        return final_answer

    def run_with_context(self, messages, max_steps=5, record_trajectory=False):
        """
        多轮对话专用，messages 必须包含 system prompt 和历史对话
        """
        # 不重新初始化 system prompt，直接使用传入的 messages
        return self._run_loop(messages, max_steps, record_trajectory)

    @traceable(name = 'LLM.call')
    def _llm_call(self, messages):
        return self.llm_client.chat_with_tools(messages, self.tools_schema)


    def get_trajectory(self):
        """获取最后一次运行的轨迹"""
        return self.trajectory


    def _resolve_dependencies(self, tool_name, tool_args):
        for dep in self.tool_deps_config:
            if dep.get('to_tool') == tool_name:
                input_key = dep.get('input_key')
                output_key = dep.get('output_key')

                if (input_key and output_key and
                        (tool_args.get(input_key) is None or tool_args.get(input_key) == '') and
                        output_key in self.tool_result_cache):
                    tool_args[input_key] = self.tool_result_cache[output_key]
                    logger.info(f"依赖自动填充: {input_key} = {self.tool_result_cache[output_key]}")

        return tool_args

    def _cache_result(self, tool_name: str, result):
        """缓存工具执行结果，用于依赖传递"""
        if isinstance(result, dict):
            self.tool_result_cache.update(result)
        else:
            self.tool_result_cache[tool_name] = result

    def _build_tools_description(self, tools_schema):
        """从 tools_schema 生成工具列表描述"""
        lines = []
        for tool in tools_schema:
            func = tool.get("function", {})
            name = func.get("name")
            desc = func.get("description")
            lines.append(f"- {name}: {desc}")
        return "\n".join(lines)

    def _build_system_prompt(self):
        tools_desc = self._build_tools_description(self.tools_schema)
        return f"""你是一个严格遵循规则的 ReAct 推理助手，**必须100%遵守以下规则，绝对不能违反**。

    【核心铁律 - 绝对禁止违反】
    1.  **需要调用工具时：只返回 tool_calls，content 必须为空字符串 ""**
    2.  **不需要调用工具时：只返回 content，绝对不能返回 tool_calls**
    3.  **绝对禁止同时返回 content 和 tool_calls**
    4.  **禁止使用自身知识回答，必须通过工具调用获取结果。**
        - 获取结果后，可以基于工具返回的数据组织最终答案。
        - 最终答案可以直接呈现结果，不需要重复工具调用过程。
    5.  **没有可用工具能处理的问题 → 直接回答：对不起，没有可用的工具，无法解决你的问题**
    6.  **参数缺失 → 必须反问用户，明确索要缺失参数**
    7.  **禁止编造工具、禁止编造参数**
    8.  **在多轮对话中，用户明确提供的身份信息（如姓名、住址、偏好、订单号等）必须被记住并在后续轮次使用**
    9.  **绝对禁止在后续轮次反问用户已经提供过的信息**。
    10. **如果多轮信息发生更新或覆盖（如用户把目的地从 A 改成 B），必须使用最新的信息**

    【工作流程】
    严格循环：
    Thought → Action → Observation
    直到可以给出最终答案。

    【可用工具】
    {tools_desc}
    """
