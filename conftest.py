import pytest
import os
from tool_registry import TOOL_REGISTRY, TOOL_DEPS
from clients.ollama_client import OllamaClient
from commons.yaml_util import read_yaml_file
from clients.deepseek_client import DeepSeekClient
import sys
import pytest
from pathlib import Path
from metrics import MetricsCalculator, QualitativeAnalyzer


#这是langsmith需要的  读.env里面内容的, 也供deepseek api key
from dotenv import load_dotenv
load_dotenv()

#这是绝对路径 防止用相对路径找不到文件 比如tool_registry.py, 确保导入不报错
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

# 读取 tools_schema（从 fc_config.yaml）
fc_config = read_yaml_file('schemas/fc_config.yaml')
tools_schema = fc_config.get('tools', [])

@pytest.fixture(scope="session")
def ollama_client():
    config = read_yaml_file('config/qwen2.yaml')
    request_info = config['client_qwen2']['request']
    json_body=request_info['json']

    client_config = {
        'url':request_info['url'],
        'model':json_body['model'],
        'temperature':json_body.get('temperature',0)
    }

    return OllamaClient(client_config)

@pytest.fixture(scope="session")
def deepseek_client():
    config = read_yaml_file('config/config.yaml')
    api_key = config.get('api_key','')
    if api_key.startswith('${') and api_key.endswith('}'):
        env_var = api_key[2:-1]
        api_key = os.environ.get(env_var,'')

    if not api_key:
        pytest.skip('No DEEPSEEK API key provided')

    client_config = {
        'api_key':api_key,
        'base_url':config.get('base_url','https://api.deepseek.com'),
        'model': config.get('model','deepseek-chat'),
        'temperature': config.get('temperature',0)
    }
    return DeepSeekClient(client_config)

@pytest.fixture(scope="session")
def agent_ollama(ollama_client):
    from core.react_agent import ReActAgent
    return ReActAgent(
        llm_client=ollama_client,
        tools_schema=tools_schema,
        tool_registry=TOOL_REGISTRY,
        tool_deps_config=TOOL_DEPS
    )

@pytest.fixture(scope="session")
def agent_deepseek(deepseek_client):
    from core.react_agent import ReActAgent
    return ReActAgent(
        llm_client=deepseek_client,
        tools_schema=tools_schema,
        tool_registry=TOOL_REGISTRY,
        tool_deps_config=TOOL_DEPS
    )


@pytest.fixture
def judge_deepseek(deepseek_client):
    from core.judge import Judge
    return Judge(judge_client=deepseek_client, tools_schema=tools_schema, tool_registry=TOOL_REGISTRY)


# 全局实例
_metrics_calculator = None
_qualitative_analyzer = None


def pytest_configure(config):
    """pytest 启动时初始化"""
    global _metrics_calculator, _qualitative_analyzer
    _metrics_calculator = MetricsCalculator()
    _qualitative_analyzer = QualitativeAnalyzer()

    config._metrics_calculator = _metrics_calculator
    config._qualitative_analyzer = _qualitative_analyzer

    Path("reports").mkdir(exist_ok=True)


def pytest_sessionfinish(session, exitstatus):
    """测试结束后生成报告"""
    if _metrics_calculator and _metrics_calculator.results:
        print("\n" + "🎯" * 35)
        print("最终评测报告")
        print("🎯" * 35)

        _metrics_calculator.print_summary()
        _qualitative_analyzer.print_summary()

        report_path = _metrics_calculator.save_report()
        print(f"\n✅ 详细报告已保存: {report_path}")


@pytest.fixture
def metrics_calculator():
    return _metrics_calculator


@pytest.fixture
def qualitative_analyzer():
    return _qualitative_analyzer