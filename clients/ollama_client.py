import requests
import time
import logging

logger = logging.getLogger(__name__)

class OllamaClient:
    def __init__(self, config, timeout=300, max_retries=2):
        self.url = config.get("url")
        self.model = config.get("model")
        self.temperature = config.get("temperature", 0)
        self.is_chat_api = '/chat' in self.url
        self.timeout = timeout
        self.max_retries = max_retries

    def _post_with_retry(self, url, payload):
        for attempt in range(self.max_retries + 1):
            try:
                response = requests.post(url, json=payload, timeout=self.timeout)
                response.raise_for_status()
                return response
            except (requests.Timeout, requests.ConnectionError) as e:
                logger.warning(f"请求失败，第 {attempt+1} 次重试: {e}")
                if attempt == self.max_retries:
                    raise
                time.sleep(1)
            except Exception as e:
                logger.error(f"不可重试异常: {e}")
                raise

    def chat(self, messages):
        if self.is_chat_api:
            return self._call_chat_api(messages)
        else:
            return self._call_generate_api(messages)

    def chat_with_tools(self, messages, tools):
        return self._call_chat_api(messages, tools)

    def _call_chat_api(self, messages, tools=None):
        url = self.url.replace("/generate", '/chat')
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "temperature": self.temperature
        }
        if tools:
            payload["tools"] = tools

        response = self._post_with_retry(url, payload)
        result = response.json()
        return {
            "message": result.get("message", {}),
            "content": result.get("message", {}).get("content", ""),
            "done": result.get("done", True)
        }

    def _call_generate_api(self, messages):
        prompt = self._messages_to_prompt(messages)
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "temperature": self.temperature
        }
        response = self._post_with_retry(self.url, payload)
        result = response.json()
        return {
            "message": {"role": "assistant", "content": result.get("response", "")},
            "content": result.get("response", ""),
            "done": result.get("done", True)
        }

    def _messages_to_prompt(self, messages):
        lines = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == 'user':
                lines.append(f'user: {content}')
            elif role == 'assistant':
                lines.append(f'assistant: {content}')
            else:
                lines.append(content)
        return "\n".join(lines)


if __name__ == "__main__":
    test_config = {
        "url": "http://localhost:11434/api/generate",
        "model": "qwen2:latest",
        "temperature": 0
    }
    client = OllamaClient(test_config)
    result = client.chat([{"role": "user", "content": "你好，请说一句话"}])
    print(f"回答: {result['content']}")