markdown
# Tool Agent 测试框架

> 基于 ReAct 架构，测试 Agent 的工具调用、多轮对话、安全合规等核心能力。支持能力评测、质量门禁、模型对比(**仅本地运行**，依赖 Ollama)。

## 功能

### 业务覆盖（测什么）
- **Tool Agent 专项**：
  - 算术工具：add、multiply
  - 天气工具：get_weather
  - 时间工具：get_time
  - 订单物流：get_order、get_logistics、get_delivery_status
  - 订票工具：book_ticket
  - 验证点：参数依赖、并行调用
- **多轮记忆**：上下文累积、信息更新、否定理解
- **安全合规**：拒绝泄露 API 密钥/系统提示词、拒绝恶意指令
- **异常处理**：缺参数反问、边界输入、OOD 拒绝

### 技术架构（怎么测）
- **分层测试**：冒烟测试、集成测试、黄金集门禁、能力专项
- **多维度断言**：关键词、轨迹验证、参数依赖、LLM-as-Judge
- **模型对比**：Qwen2 vs DeepSeek 能力对比，输出选型报告
- **黄金集管理**：15个核心用例（覆盖5大能力），发版红线
- **指标统计**：定量（通过率/平均分）+ 定性（失败模式分类）

## 快速开始

### 目录结构
```
├── testcases/                        # 测试用例入口
│   ├── test_golden.py                # 发版黄金门禁用例
│   ├── test_react_integration.py     # 全量集成回归
│   └── test_model_comparison.py      # 多模型对比测试
├── core/                             # Agent 基础调度核心
├── tools/                            # 自定义工具函数
├── metrics/                          # 简单指标统计与报告
├── testdata/                         # YAML 结构化测试数据
└── conftest.py                       # pytest 全局配置
```

## 环境准备

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 API Key（创建 .env 文件，不会提交到 Git）
echo DEEPSEEK_API_KEY=你的密钥 > .env
echo LANGSMITH_API_KEY=你的密钥 >> .env

# 3. （可选）模型对比测试需要本地 Ollama
# 参考 https://ollama.com
ollama pull qwen2:7b
```

## 运行测试

按 CI/CD 时间线执行：

```bash
# 1. CI 阶段（每次 MR，< 5min）
pytest testcases/test_react_unit.py -v                # 单元测试 + Mock

# 2. CD 阶段（部署测试环境后，15min）
pytest testcases/test_react_integration.py -v -m smoke  # 冒烟测试（P0 核心用例）
pytest testcases/test_react_integration.py -v            # 全量功能回归

# 3. 预发布阶段（发版前，手动触发，5min）
pytest testcases/test_golden.py -v                      # 黄金集门禁（必须 100%）

# 4. Nightly（每日凌晨，定时触发，30min）
pytest testcases/test_react_integration.py -v --tb=short  # 全量集成 + 能力报告

# 5. 模型升级时（手动触发，1h，**仅本地运行**）
pytest testcases/test_model_comparison.py -v              # Qwen2(需要本地 Ollama) 和 DeepSeek
```

## 测试闭环

集成测试发现问题 → 定性分析自动分类 → 人工确认 → 记录 Bad Case 台账 → 优化后回归验证。

**效果**：问题可追溯、优化有方向、质量可度量。

## 测试结果

- **黄金集**：15/15 通过 ✅  
  覆盖能力：tool_calling、task_planning、state_memory、safety、error_fallback

- **全量集成**：53/64 通过（82.8%）

- **模型对比**：DeepSeek 优于 Qwen2（安全能力 + 工具规范性） > 注：模型对比测试仅本地运行，CI 自动跳过。

## 配置说明

| 变量 | 说明 | 必填 |
|------|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | 必须 |
| `LANGSMITH_API_KEY` | LangSmith 追踪密钥 | 可选 |

## 项目状态

| 项目 | 状态 |
|------|------|
| 黄金集 | 100% |
| 集成测试 | ≥80% |
| 模型对比 | 已完成 |
| 指标报告 | 自动生成 |

