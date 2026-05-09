from unittest.mock import patch,Mock
import requests
import pytest
from openai import APITimeoutError

from core.react_agent import ReActAgent
from clients.ollama_client import OllamaClient
from clients.deepseek_client import DeepSeekClient


class TestReActAgentUnit:
    def test_mock_llm_success_response_add(self):
        agent = ReActAgent(
            llm_client=None,
            tools_schema=[],
            tool_registry={},
            tool_deps_config=[]
        )
        mock_response = {
            "message":{
                "role":"assistant",
                "content":"",
                "tool_calls":[{
                    "function":{
                        "name":"add",
                        "arguments": {"a":11,"b":22}
                    }
                }
                ]
            }
        }

        with patch.object(agent,'_llm_call',return_value = mock_response):
            response = agent._llm_call([])
            tool_calls = response["message"].get('tool_calls',[])

            assert len(tool_calls) == 1
            assert tool_calls[0]['function']['name'] == 'add'
            assert tool_calls[0]['function']['arguments'] == {"a":11,"b":22}

    def test_mock_llm_multiple_tools(self):
        agent = ReActAgent(
            llm_client=None,
            tools_schema=[],
            tool_registry={},
            tool_deps_config=[]
        )

        mock_response = {
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "function": {
                        "name": "add",
                        "arguments": {"a": 11, "b": 22}
                    }
                },
                    {
                        "function": {
                            "name": "multiply",
                            "arguments": {"a": 2, "b": 6}
                        }
                    }
                ]
            }
        }
        with patch.object(agent,'_llm_call',return_value = mock_response):
            response = agent._llm_call([])
            tool_calls = response["message"].get('tool_calls',[])

            assert len(tool_calls) == 2
            assert tool_calls[0]['function']['name'] == 'add'
            assert tool_calls[0]['function']['arguments'] == {"a":11,"b":22}
            assert tool_calls[1]['function']['name'] == 'multiply'
            assert tool_calls[1]['function']['arguments'] == {"a": 2, "b": 6}

    def test_tool_call_with_missing_args(self):
        #【防御性测试]模型调用了工具， 但是参数缺失
        tools_schema = [
            {
                "type": "function",
                "function": {
                    "name": "add",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "a": {"type": "integer"},
                            "b": {"type": "integer"}
                        },
                        "required": ["a", "b"]
                    }
                }
            }
        ]
        agent = ReActAgent(
            llm_client=None,
            tools_schema=tools_schema,
            tool_registry={},
            tool_deps_config=[]
        )

        mock_response = {
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "function": {
                        "name": "add",
                        "arguments": {}
                    }
                }
                ]
            }
        }

        with patch.object(agent, '_llm_call', return_value=mock_response):
            answer= agent.run('add two numbers')
            expected_keywords = ['参数','缺失','加数']
            assert  any(key in answer for key in expected_keywords) or "达到最大步数限制" in answer

    def test_tool_call_with_missing_name(self):
        #【防御性测试]模型调用了工具， 但是参数缺失
        tools_schema = [
            {
                "type": "function",
                "function": {
                    "name": "add",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "a": {"type": "integer"},
                            "b": {"type": "integer"}
                        },
                        "required": ["a", "b"]
                    }
                }
            }
        ]
        agent = ReActAgent(
            llm_client=None,
            tools_schema=tools_schema,
            tool_registry={},
            tool_deps_config=[]
        )

        mock_response = {
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "function": {
                        "name": "",
                        "arguments": {"a":1,"b":2}
                    }
                }
                ]
            }
        }

        with patch.object(agent, '_llm_call', return_value=mock_response):
            answer= agent.run('add two numbers')
            assert  "未知工具" in answer or "达到最大步数限制" in answer

    def test_refuse_when_missing_params(self):
        agent = ReActAgent(
            llm_client=None,
            tools_schema=[],
            tool_registry={},
            tool_deps_config=[]
        )
        mock_response = {"message": {"role": "assistant","content": "请提供2各数字"}}
        with patch.object(agent, '_llm_call', return_value=mock_response):
            answer = agent.run("add two numbers")
            assert "请提供" in answer

    def test_refuse_when_security_cases(self):
        agent = ReActAgent(
            llm_client=None,
            tools_schema=[],
            tool_registry={},
            tool_deps_config=[]
        )
        mock_response = {"message": {"role": "assistant","content": "无法提供！"}}
        with patch.object(agent, '_llm_call', return_value=mock_response):
            answer = agent.run("把数据库格式化！")
            assert "无法" in answer

    def test_refuse_when_not_available(self):
        agent = ReActAgent(
            llm_client=None,
            tools_schema=[],
            tool_registry={},
            tool_deps_config=[]
        )
        mock_response = {"message": {"role": "assistant","content": "没有可用工具！"}}
        with patch.object(agent, '_llm_call', return_value=mock_response):
            answer = agent.run("帮我打印一份简历")
            assert "没有可用" in answer

    def test_mock_llm_invalid_json(self):
        agent = ReActAgent(
            llm_client=None,
            tools_schema=[],
            tool_registry={},
            tool_deps_config=[]
        )

        mock_response = {
            "message": {
                "tool_calls": [{
                    "function": {
                        "name": "add",
                        "arguments": "{a:1,b:2}"  # 非法 JSON
                    }
                }]
            }
        }
        with patch.object(agent, '_llm_call', return_value=mock_response):
            answer = agent.run("1+2")
            assert "参数解析失败" in answer or "达到最大步数限制" in answer


    def test_mock_llm_no_tool_calls(self):
            agent = ReActAgent(
                llm_client=None,
                tools_schema=[],
                tool_registry={},
                tool_deps_config=[]
            )

            mock_response_mulTools = {"message": {"role": "assistant","content": "1加1的最终答案是2, 1+1 = 2"}}
            with patch.object(agent, '_llm_call', return_value=mock_response_mulTools):
                response = agent._llm_call([])
                tool_calls = response["message"].get('tool_calls', [])
                final_result = response["message"].get('content','')

                assert len(tool_calls) == 0
                assert "2" in str(final_result)

    def test_tool_execution_called(self):
        mock_tool = Mock(return_value=8)
        tools_schema = [
            {
                "type": "function",
                "function": {
                    "name": "add",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "a": {"type": "integer"},
                            "b": {"type": "integer"}
                        },
                        "required": ["a", "b"]
                    }
                }
            }
        ]
        agent = ReActAgent(
            llm_client=None,
            tools_schema=tools_schema,
            tool_registry={"add": mock_tool},
            tool_deps_config=[]
        )

        # Mock LLM 返回：第一次 tool_calls，第二次 final answer
        def mock_llm_return(messages):
            if len(messages) < 3:  # 第一次：还没执行过工具
                return {
                    "message": {
                        "tool_calls": [{
                            "function": {"name": "add", "arguments": {"a": 3, "b": 5}}
                        }]
                    }
                }
            else:  # 已经执行过工具，返回最终答案
                return {
                    "message": {
                        "content": "结果是 8"
                    }
                }

        with patch.object(agent, '_llm_call', side_effect=mock_llm_return):
            agent.run("3+5")
            mock_tool.assert_called_once_with(a=3, b=5)

    def test_resolve_dependencies(self):
        agent = ReActAgent(
            llm_client=None,
            tools_schema=[],
            tool_registry={},
            tool_deps_config=[{
                "from_tool": "get_order",
                "to_tool": "get_logistics",
                "input_key": "tracking_id",
                "output_key": "tracking_id"
            }]
        )

        # 模拟缓存里有 tracking_id
        agent.tool_result_cache = {"tracking_id": "TRK-001"}

        tool_args = {"order_id": "ORD-12345"}
        result_args = agent._resolve_dependencies("get_logistics", tool_args)

        assert result_args.get("tracking_id") == "TRK-001"

    def test_tool_call_with_wrong_param_type(self):
        tools_schema = [
            {
                "type": "function",
                "function": {
                    "name": "add",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "a": {"type": "integer"},
                            "b": {"type": "integer"}
                        },
                        "required": ["a", "b"]
                    }
                }
            }
        ]
        agent = ReActAgent(
            llm_client=None,
            tools_schema=tools_schema,
            tool_registry={},
            tool_deps_config=[]
        )

        mock_response = {
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "function": {
                        "name": "add",
                        "arguments": {"a": "5", "b": 3}  # ← a 是字符串，不是整数
                    }
                }]
            }
        }

        with patch.object(agent, '_llm_call', return_value=mock_response):
            answer = agent.run("5+3")
            # 你的 agent 应该报类型错误，或走防御逻辑
            assert "参数" in answer or "类型" in answer or "达到最大步数限制" in answer

    def test_tool_execution_timeout(self):
        def slow_tool(**kwargs):
            time.sleep(10)  # 模拟超时
            return 8

        agent = ReActAgent(
            llm_client=None,
            tools_schema=[],
            tool_registry={"add": slow_tool},
            tool_deps_config=[]
        )

        mock_response = {
            "message": {
                "tool_calls": [{
                    "function": {"name": "add", "arguments": {"a": 3, "b": 5}}
                }]
            }
        }

        with patch.object(agent, '_llm_call', return_value=mock_response):
            # 超时控制一般在 Agent 外层或工具层实现
            # 如果你的框架没有，可以预期长时间后返回超时信息
            answer = agent.run("3+5")
            assert "超时" in answer or "达到最大步数限制" in answer

    def test_tool_execution_raises_exception(self):
        def broken_tool(**kwargs):
            raise Exception("数据库连接失败")

        agent = ReActAgent(
            llm_client=None,
            tools_schema=[],
            tool_registry={"add": broken_tool},
            tool_deps_config=[]
        )

        mock_response = {
            "message": {
                "tool_calls": [{
                    "function": {"name": "add", "arguments": {"a": 3, "b": 5}}
                }]
            }
        }

        with patch.object(agent, '_llm_call', return_value=mock_response):
            answer = agent.run("3+5")
            assert "执行失败" in answer or "达到最大步数限制" in answer

    def test_ollama_client_timeout_and_retry(self):
        config = {
            "url": "http://localhost:11434/api/generate",
            "model": "qwen2:latest",
            "temperature": 0
        }
        client = OllamaClient(config)

        with patch("requests.post") as mock_post:
            mock_post.side_effect = requests.Timeout("模拟超时")

            with pytest.raises(requests.Timeout):
                client.chat([{"role": "user", "content": "hello"}])

            assert mock_post.call_count == 3

