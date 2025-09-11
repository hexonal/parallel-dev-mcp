# 并行 Worktree 开发系统 (Parallel Dev MCP)

> 基于 TaskMaster-AI、Tmux-Orchestrator 和 SplitMind 最佳实践构建的智能并行开发系统

## 🎯 项目愿景

创建一个革命性的并行开发系统，通过智能任务分解、并行 worktree 开发和自动化协调，将开发效率提升 3-5 倍，同时保证代码质量和团队协作的无缝体验。

## ✨ 核心特性

### 🤖 智能主会话协调器
- **PM 级别的智能协调**: 主会话作为项目经理，负责任务规划、分发和监控
- **TaskMaster-AI 深度集成**: 自动任务分解和依赖关系管理
- **5分钟定时监控**: 实时跟踪所有子会话的开发进度

### 🌳 并行 Worktree 开发
- **一任务一 Worktree**: 每个子任务获得独立的 Git worktree 和开发环境
- **真正的并行开发**: 多个任务同时进行，互不干扰
- **智能分支管理**: 自动创建、管理和清理功能分支

### 🔍 多层状态检测
- **心跳检测**: 子会话健康状态实时监控
- **状态文件监控**: 详细的任务进度和完成状态跟踪
- **Git 活动分析**: 基于提交活动智能判断开发状态
- **进程活动检测**: 监控开发工具使用情况

### 🛡️ 安全自动合并
- **分步式合并流程**: 准备 → 验证 → 执行 → 清理的安全流程
- **智能冲突解决**: 自动识别和解决常见代码冲突
- **备份和回滚**: 每次操作前自动备份，支持一键回滚

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    主会话协调器机器人                         │
│           ┌─────────────┬─────────────┬─────────────┐       │
│           │TaskMaster-AI│   监控系统   │  合并引擎    │       │
│           │    集成     │   (5min)    │             │       │
└───────────┴─────────────┴─────────────┴─────────────┴───────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
    ┌─────────┐    ┌─────────┐    ┌─────────┐
    │Task-1   │    │Task-2   │    │Task-N   │
    │Session  │    │Session  │    │Session  │
    │Worktree │    │Worktree │    │Worktree │
    └─────────┘    └─────────┘    └─────────┘
```

## 🚀 快速开始

### 环境要求
- Python 3.11+
- tmux 3.0+
- Git 2.30+
- TaskMaster-AI 访问权限
- FastMCP 2.0 服务器

### 安装
```bash
# 克隆项目
git clone <repository-url>
cd parallel-dev-mcp

# 创建虚拟环境
python3.11 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 初始化配置
python setup.py
```

### 基础使用
```bash
# 启动主会话协调器
tmux new-session -s parallel-dev
python -m src.coordinator.main

# 提交开发需求
./scripts/submit-task.sh "实现用户认证系统"

# 监控开发进度
./scripts/monitor-progress.sh
```

## 📋 核心解决的问题

### ✅ 会话状态监控
**问题**: 如何准确判断子会话的开发状态？
**解决**: 四层检测机制，95%+ 准确率的状态判断

### ✅ 嵌套会话防护  
**问题**: 如何防止子会话创建嵌套会话？
**解决**: 环境变量控制 + 权限分级 + 创建拦截器

### ✅ 自动合并安全
**问题**: 如何安全地自动合并 worktree 分支？
**解决**: 分布式锁 + 分步验证 + 智能冲突处理 + 自动回滚

### ✅ TaskMaster-AI 集成
**问题**: 如何与 TaskMaster-AI 无缝协作？
**解决**: RESTful API 深度集成 + 实时状态同步

## 📁 项目结构

```
parallel-dev-mcp/
├── src/                           # 主要源代码
│   ├── coordinator/               # 主会话协调器
│   ├── session/                   # 会话管理
│   ├── worktree/                  # Worktree 管理
│   ├── monitoring/                # 监控系统
│   └── integration/               # 外部集成
├── config/                        # 配置文件
├── scripts/                       # 自动化脚本
├── tests/                         # 测试代码
├── .tmuxp/                        # tmux 会话模板
├── docs/                          # 项目文档
│   ├── user-story-master-session-coordinator.md
│   ├── session-monitoring-design.md
│   ├── worktree-auto-merge-design.md
│   └── project-summary-and-roadmap.md
└── CLAUDE.md                      # Claude Code 指导文档
```

## 🛠️ 开发指南

### 常用命令
```bash
# 环境设置
source .venv/bin/activate
python -m pytest tests/

# TaskMaster-AI 集成
python -m src.integration.taskmaster analyze "复杂功能需求"

# 会话管理
./scripts/create-task-session.sh task-123 "实现登录功能"
./scripts/monitor-sessions.sh

# Worktree 操作
./scripts/create-worktree.sh task-123
./scripts/merge-worktree.sh task-123

# 系统监控
python -m src.monitoring.health_check --live
```

### 开发工作流
1. **任务分析**: 使用 TaskMaster-AI 分解复杂需求
2. **环境准备**: 自动创建 worktree 和开发会话
3. **并行开发**: 多个子任务同时进行
4. **持续监控**: 5分钟间隔的状态检查
5. **自动合并**: 任务完成后自动合并到主分支

## 📊 成功指标

- **会话状态检测准确率**: ≥ 95%
- **自动合并成功率**: ≥ 90%
- **开发效率提升**: 3-5倍
- **错误率降低**: ≥ 90%
- **系统响应时间**: ≤ 2秒

## 🗺️ 实施路线图

### 阶段一: 核心基础设施 (第1-2周)
- 基础 tmux 会话管理
- 状态监控系统
- 权限控制机制

### 阶段二: TaskMaster-AI集成 (第3-4周)
- API 集成和状态同步
- 任务分解和分发
- 依赖关系管理

### 阶段三: Worktree并行开发 (第5-6周)
- Git worktree 自动管理
- 并行会话协调
- 实时状态同步

### 阶段四: 自动合并系统 (第7-8周)
- 智能合并流程
- 冲突检测和解决
- 备份和回滚机制

### 阶段五: 监控和优化 (第9-10周)
- 实时监控仪表板
- 性能优化
- 用户体验改进

### 阶段六: 高级特性和测试 (第11-12周)
- 高级特性开发
- 全面集成测试
- 生产环境准备

## 🔧 参考项目

- **[Tmux-Orchestrator](https://github.com/user/Tmux-Orchestrator)**: 三层架构和自动调度机制
- **[SplitMind](https://github.com/user/splitmind)**: 多代理协调和实时监控
- **[TaskMaster-AI](https://github.com/eyaltoledano/claude-task-master)**: 智能任务分解

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 📄 许可证

MIT License - 自由使用，但请明智使用。

---

**"未来的开发工具将能够自己编程"** - 让我们今天就构建这个未来。