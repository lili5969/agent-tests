# from commons.request_util import RequestsUtil
# from commons.yaml_util import read_test_case
# from commons.logger import logger
#
# # ========================
# # 配置路径
# # ========================
# CASE_FILE = "testdata/testAI_FC_original.yaml"
# TEMPLATE_FILE = "testdata/base_templates.yaml"
#
# # ========================
# # 统一读取：只调用工具类
# # ========================
# test_cases = read_test_case(CASE_FILE)  # 读所有用例
#
#
# # ========================
# # 🔥 混合模式核心逻辑
# # ========================
# def run_one_case(case_name, case_data):
#     logger.info(f"\n======================================")
#     logger.info(f"开始执行用例：{case_name}")
#
#     # ------------------------------
#     # 1. 判断：极简模板模式 / 完整用例模式
#     # ------------------------------
#     if "template" in case_data:
#         # 极简模式：用模板
#         from commons.yaml_util import read_agent_template
#         tpl_name = case_data["template"]
#         content = case_data["content"]
#
#         # 读取模板
#         tpl = read_agent_template(TEMPLATE_FILE, tpl_name)
#
#         # 组装请求
#         case_data['request'] = {
#             "url": tpl["url"],
#             "method": tpl["method"],
#             "json": {
#                 "model": tpl["model"],
#                 "stream": tpl["stream"],
#                 "messages": [{"role": "user", "content": content}],
#                 "tools": tpl["tools"]
#             }
#         }
#         case_data['extract'] = tpl["extract"]
#         case_data["need_token"] = False
#
#
#
#     # ------------------------------
#     # 2. 发送请求 + 提取数据
#     # ------------------------------
#     res_util= RequestsUtil()
#     logger.info(f'打印本次请求的测试数据{case_name}')
#     res_util.run_request(case_data)
#
#
# # ========================
# # 执行所有用例
# # ========================
# if __name__ == "__main__":
#     for case_name, case_data in test_cases.items():
#         run_one_case(case_name, case_data)

import pytest


if __name__ == '__main__':
    pytest.main()