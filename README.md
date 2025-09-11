# Session Coordinator MCP - 并行开发系统

Claude Code的多会话管理和通信系统，支持并行开发工作流。

## 🚀 快速开始

### 一键配置

```bash
# 克隆项目
git clone https://github.com/yourname/parallel-dev-mcp.git
cd parallel-dev-mcp

# 自动配置到Claude Code
bash scripts/setup_claude_code.sh --project-id YOUR_PROJECT
```

### 启动并行开发

```bash
# 1. 启动主会话（项目协调）
bash scripts/start_master_YOUR_PROJECT.sh

# 2. 启动子会话（具体任务）
bash scripts/start_child_YOUR_PROJECT.sh AUTH
bash scripts/start_child_YOUR_PROJECT.sh PAYMENT
bash scripts/start_child_YOUR_PROJECT.sh UI

# 3. 查看项目状态
bash scripts/status_YOUR_PROJECT.sh
```

## 🎯 核心功能

### MCP工具

| 工具 | 功能 | 使用者 |
|------|------|--------|
| `register_session_relationship` | 注册主子会话关系 | 主会话 |
| `report_session_status` | 上报工作状态 | 子会话 |
| `get_child_sessions` | 获取子会话列表 | 主会话 |
| `send_message_to_session` | 发送指令/消息 | 主会话 |
| `get_session_messages` | 获取未读消息 | 子会话 |
| `query_session_status` | 查询会话状态 | 任意会话 |

### 自动化Hooks

- **子会话**: 自动注册、状态上报、消息检查、完成通知
- **主会话**: 定期监控、完成处理、指令发送

### 会话命名约定

- **主会话**: `master_project_{PROJECT_ID}`
- **子会话**: `child_{PROJECT_ID}_task_{TASK_ID}`

## 📋 使用场景

### 电商项目示例

```bash
# 主会话（项目协调）
master_project_ECOMMERCE

# 子会话（并行任务）
child_ECOMMERCE_task_AUTH      # 用户认证系统
child_ECOMMERCE_task_PAYMENT   # 支付处理系统  
child_ECOMMERCE_task_CART      # 购物车功能
child_ECOMMERCE_task_UI        # 前端界面
```

### 工作流程

1. **启动阶段**: 主会话创建，子会话按需启动
2. **开发阶段**: 子会话并行开发，自动上报进度
3. **协调阶段**: 主会话监控进度，发送指令
4. **完成阶段**: 子会话完成通知，主会话整合

## 🔧 配置方式

### 方式1：自动配置（推荐）

```bash
bash scripts/setup_claude_code.sh --project-id MYPROJECT
```

### 方式2：手动配置

1. **配置MCP服务器**到 `~/.claude/config.json`
2. **生成hooks配置**
3. **创建tmux会话**
4. **启动Claude Code**

详见：[Claude Code集成指南](docs/claude-code-integration.md)

## 📁 项目结构

```
parallel-dev-mcp/
├── src/
│   ├── mcp_server/          # MCP服务器核心
│   └── hooks/               # Hooks管理系统
├── docs/                    # 详细文档
├── scripts/                 # 自动化脚本
├── config/                  # 配置文件
└── tests/                   # 测试套件
```

## 📚 文档

- [Claude Code集成指南](docs/claude-code-integration.md) - 完整配置步骤
- [使用指南](docs/usage-guide.md) - 详细使用方法
- [MCP工具演示](docs/mcp-tools-demo.py) - 工具调用示例

## 🧪 测试验证

```bash
# 系统验证（17项测试）
python3 scripts/validate_mcp_system.py

# 功能演示
python3 docs/mcp-tools-demo.py

# 完整演示
bash scripts/demo_workflow.sh
```

## 🛠️ 管理命令

```bash
# 查看项目状态
bash scripts/status_MYPROJECT.sh

# 清理所有会话
bash scripts/cleanup_MYPROJECT.sh

# 列出活跃会话
python3 -m src.hooks.hooks_manager list-sessions
```

## ⚡ 核心优势

### 🔄 并行开发
- 多个子会话同时处理不同任务
- 主会话统一协调和监控

### 🤖 自动化
- Claude Hooks自动处理状态同步
- 无需手动管理会话通信

### 🔗 实时通信
- 主子会话间双向消息传递
- 实时进度跟踪和状态同步

### 🎯 智能路由
- 基于命名约定的自动路由
- 无需配置复杂的路由规则

### 📊 监控可视化
- 实时查看所有子任务状态
- 项目整体进度一目了然

## 🔍 故障排除

### 常见问题

1. **MCP服务器连接失败**
   ```bash
   # 检查服务器状态
   python3 -m src.mcp_server.server
   ```

2. **Hooks不执行**
   ```bash
   # 检查配置文件
   ls -la ~/.claude/config.json
   ```

3. **会话通信失败**
   ```bash
   # 验证会话名称格式
   python3 -c "from src.mcp_server.session_utils import validate_session_name; print(validate_session_name('master_project_TEST'))"
   ```

### 调试工具

```bash
# 完整系统验证
python3 scripts/validate_mcp_system.py

# 查看MCP工具状态
python3 docs/mcp-tools-demo.py

# 清理配置重新开始
python3 -m src.hooks.hooks_manager cleanup
```

## 🏗️ 架构设计

### 三层架构

1. **MCP协议层**: 标准MCP工具接口
2. **会话管理层**: 状态同步和消息路由
3. **Hooks集成层**: Claude Code自动化

### 通信机制

```
主会话 ←→ MCP服务器 ←→ 子会话
   ↓                      ↓
 监控仪表板              任务执行
```

### 数据流

1. **注册**: 子会话启动时注册到主会话
2. **状态**: 子会话定期上报工作进度
3. **指令**: 主会话发送指令到子会话
4. **完成**: 子会话完成后通知主会话

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License

## 🎉 致谢

感谢Claude Code团队提供的MCP协议支持，使得这个并行开发系统成为可能。

---

**开始你的并行开发之旅！** 🚀

```bash
bash scripts/setup_claude_code.sh --project-id YOUR_AMAZING_PROJECT
```