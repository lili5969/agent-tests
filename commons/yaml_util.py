#读取测试用例yaml
import os

import yaml

def read_yaml_file(file_path):
    """
    通用：读取整个 YAML 文件
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"YAML 文件不存在：{file_path}")

    with open(file_path, encoding="utf-8", mode="r") as f:
        return yaml.safe_load(f)


def read_test_case(yaml_path, case_name = None):
    """
    读取测试用例（兼容你原来的用法）
    """
    data = read_yaml_file(yaml_path)
    if case_name:
        return data.get(case_name)
    return data


def read_agent_template(template_path, template_name):
    """
    专门读取 Agent 模板（新功能）
    """
    data = read_yaml_file(template_path)
    return data.get(template_name)