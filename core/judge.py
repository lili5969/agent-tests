import commons.logger as logger


class Judge:
    def __init__(self, judge_client,tool_registry,tools_schema = None,default_criteria = None):
        self.judge_client = judge_client
        self.tools_schema = tools_schema or []
        self.tool_registry = tool_registry
        self.default_criteria = default_criteria or '回答是否正确， 完成， 有用'


    def judge(self,question, actual_answer,criteria = None):
        criteria = criteria or self.default_criteria
        prompt =self._build_system_prompt(question, actual_answer,criteria)
        messages = [{"role": "user", "content": prompt}]
        response = self.judge_client.chat(messages)
        return self._parse_response(response)

    def _build_system_prompt(self, question, actual_answer, criteria):
        tools_desc = self._build_tools_description()
        return f"""你是一个严格的质量评估专家。请根据以下标准对 Agent 的回答进行打分（0-10 分）：

    问题：{question}
    Agent 回答：{actual_answer}

    评估标准：
    {criteria}

    可用工具：
    {tools_desc}

    请输出 JSON 格式：
    {{
        "score": 整数分数,
        "reason": "简短理由"
    }}
    """

    def _build_tools_description(self):
        if not self.tools_schema:
            return "（本次评估不涉及工具调用）"
        lines = []
        for tool in self.tools_schema:
            func = tool.get("function", {})
            name = func.get("name")
            desc = func.get("description")
            lines.append(f"- {name}: {desc}")
        return "\n".join(lines)

    def _parse_response(self, response):
        content = response.get('content', '{}')
        try:
            import json
            result = json.loads(content)
            return {
                "score": result.get("score", 0),
                "reason": result.get("reason", ""),
                "raw": content
            }
        except json.JSONDecodeError:
            logger.warning(f"Judge 返回非 JSON: {content}")
            return {
                "score": 0,
                "reason": "解析失败",
                "raw": content
            }