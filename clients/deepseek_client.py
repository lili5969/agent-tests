from openai import OpenAI, APITimeoutError, APIError
import logging

logger = logging.getLogger(__name__)

class DeepSeekClient:
    def __init__(self, config, timeout=30, max_retries=2):
        self.client = OpenAI(
            api_key=config['api_key'],
            base_url=config.get('base_url', 'https://api.deepseek.com'),
            timeout=timeout,
            max_retries=max_retries
        )
        self.model = config.get('model', 'deepseek-chat')
        self.temperature = config.get('temperature', 0)

    def chat(self, messages):
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature
            )
            content = response.choices[0].message.content
            return {
                "message": {"role": "assistant", "content": content},
                "content": content,
                "done": True
            }
        except (APITimeoutError, APIError) as e:
            logger.error(f"大模型调用失败: {e}")
            return {
                "message": {"role": "assistant", "content": "调用失败，请稍后重试"},
                "content": "调用失败，请稍后重试",
                "done": True,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"未知异常: {e}")
            return {
                "message": {"role": "assistant", "content": "系统异常"},
                "content": "系统异常",
                "done": True,
                "error": str(e)
            }

    def chat_with_tools(self, messages, tools):
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                temperature=self.temperature
            )
            message = response.choices[0].message
            result = {
                "message": {
                    "role": message.role,
                    "content": message.content or ""
                }
            }
            if message.tool_calls:
                tool_calls_list = []
                for tc in message.tool_calls:
                    tool_calls_list.append({
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    })
                result['message']["tool_calls"] = tool_calls_list
            return result
        except (APITimeoutError, APIError) as e:
            logger.error(f"大模型调用失败: {e}")
            return {
                "message": {"role": "assistant", "content": "调用失败，请稍后重试"},
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"未知异常: {e}")
            return {
                "message": {"role": "assistant", "content": "系统异常"},
                "error": str(e)
            }


if __name__ == "__main__":
    import os

    api_key = os.environ.get("DEEPSEEK_API_KEY", "")

    if not api_key:
        print("请先设置环境变量: export DEEPSEEK_API_KEY=你的key")
    else:
        test_config = {
            "api_key": api_key,
            "base_url": "https://api.deepseek.com",
            "model": "deepseek-chat",
            "temperature": 0
        }

        client = DeepSeekClient(test_config)
        result = client.chat([{"role": "user", "content": "你好，请说一句话"}])
        print(f"回答: {result['content']}")
