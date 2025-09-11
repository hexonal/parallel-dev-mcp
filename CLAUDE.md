# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based parallel development system that integrates three core components:

1. **Task Management**: Built on [claude-task-master](https://github.com/eyaltoledano/claude-task-master) for intelligent task decomposition and orchestration
2. **Branch Management**: Powered by [FastMCP 2.0](https://gofastmcp.com/servers/server) for automated Git branch creation and management  
3. **Session Management**: Uses [tmuxp](https://tmuxp.git-pull.com/) for multi-session terminal management and parallel workflow execution

## Common Development Commands

### Environment Setup
```bash
# 创建并激活虚拟环境
python3.11 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# 安装依赖（当 requirements.txt 存在时）
pip install -r requirements.txt

# 安装开发依赖
pip install -e .
```

### FastMCP 2.0 Integration
```bash
# 启动 FastMCP 服务器
fastmcp start

# 检查 FastMCP 服务器状态
fastmcp status

# 创建功能分支
fastmcp branch create feature/your-feature-name

# 自动化分支清理
fastmcp branch cleanup
```

### tmuxp Session Management
```bash
# 启动开发会话
tmuxp load .tmuxp/development.yaml

# 启动测试会话
tmuxp load .tmuxp/testing.yaml

# 列出所有可用会话模板
tmuxp ls

# 停止所有会话
tmux kill-server
```

### Task Master Integration
```bash
# 启动任务分解流程
python -m task_master.cli decompose "复杂功能描述"

# 查看任务状态
python -m task_master.cli status

# 执行并行任务
python -m task_master.cli execute --parallel
```

## Development Environment

- **Python Version**: 3.11
- **IDE Configuration**: PyCharm project with Black code formatting
- **Source Directory**: `src/` (configured as source folder)
- **Virtual Environment**: `.venv/` (excluded from VCS)

## Architecture Design

The system follows a three-layer architecture designed for parallel development workflows:

### Layer 1: Task Orchestration (claude-task-master)
- **智能任务分解**: 将复杂功能分解为可并行执行的子任务
- **依赖关系管理**: 自动识别任务间的依赖关系，优化执行顺序
- **进度追踪**: 实时监控任务执行状态和完成进度
- **并行执行规划**: 基于依赖图生成最优的并行执行计划

### Layer 2: Git Workflow Automation (FastMCP 2.0)
- **分支生命周期管理**: 自动创建、切换、合并和清理功能分支
- **智能冲突解决**: 自动检测并解决简单的合并冲突
- **PR 工作流集成**: 与 GitHub/GitLab 的 Pull Request 流程深度集成
- **分支命名规范**: 强制执行 `feature/`、`bugfix/`、`hotfix/` 命名约定

### Layer 3: Session Management (tmuxp)
- **多会话协调**: 为不同类型的开发任务创建专门的终端会话
- **会话持久化**: 保存和恢复开发环境状态，支持跨重启工作
- **并行任务执行**: 在不同会话中同时运行测试、构建、监控等任务
- **实时监控**: 集成日志查看和实时状态监控

## Core Integration Patterns

### 任务到分支的映射
- 每个主要任务自动创建对应的功能分支
- 子任务在独立的 tmux 会话中并行执行
- 任务完成后自动触发分支合并流程

### 会话间通信机制
- 使用共享配置文件在会话间传递状态信息
- 实时同步任务执行进度到所有相关会话
- 统一的日志聚合和错误报告系统

### 状态同步与恢复
- 系统状态持久化到 `config/state.json`
- 支持从任意断点恢复开发工作
- 自动检测和修复不一致状态

## Key Integration Points

### FastMCP Server Integration
- Expects FastMCP 2.0 server running for Git operations
- Branch naming follows conventional patterns: `feature/`, `bugfix/`, `hotfix/`
- Automated branch cleanup and merge conflict resolution

### tmuxp Session Configuration
- Session templates should be defined in `.tmuxp/` directory
- Support for development, testing, and deployment sessions
- Integration with watch modes and live reload capabilities

### Task Master Workflow
- Task decomposition follows hierarchical structure
- Support for parallel task execution where dependencies allow
- Progress tracking and status reporting

## Development Workflow

### 标准开发流程
1. **任务分析**: 使用 claude-task-master 分解复杂功能需求
   ```bash
   python -m task_master.cli analyze "实现用户认证系统"
   ```

2. **环境准备**: FastMCP 自动创建功能分支和开发环境
   ```bash
   fastmcp workflow start --task-id=AUTH_001
   ```

3. **并行开发**: tmuxp 启动多会话开发环境
   ```bash
   tmuxp load .tmuxp/feature-development.yaml
   ```

4. **持续集成**: 实时监控代码质量和测试结果
   ```bash
   # 在专门的 tmux 会话中运行
   python -m task_master.monitor --continuous
   ```

5. **自动化合并**: 任务完成后触发分支合并流程
   ```bash
   fastmcp workflow complete --task-id=AUTH_001
   ```

### 并行开发模式
- **Session 1 (开发)**: 主要代码编写和调试
- **Session 2 (测试)**: 持续运行测试套件
- **Session 3 (监控)**: 实时监控系统状态和性能
- **Session 4 (文档)**: 同步更新技术文档

## Project Structure Expectations

```
parallel-dev-mcp/
├── src/                    # Main source code
├── .venv/                  # Virtual environment (excluded)
├── .tmuxp/                 # tmuxp session configurations
├── config/                 # Configuration files for integrations
└── scripts/                # Automation and utility scripts
```

## MCP Server Dependencies

This project is designed to work with multiple MCP servers:
- FastMCP 2.0 for Git operations
- Task management MCP for orchestration
- Potential future integrations with other development tools

## Critical Integration Dependencies

### MCP 服务器状态检查
```bash
# 在开始任何开发工作前运行
./scripts/check-services.sh
# 应该返回: FastMCP ✓, TaskMaster ✓, tmux ✓
```

### 系统健康监控
```bash
# 实时监控所有服务状态
python -m monitoring.health_check --live
```

### 故障恢复流程
```bash
# 自动恢复中断的开发会话
./scripts/recover-session.sh --last-checkpoint

# 手动恢复特定任务状态
python -m task_master.recovery --task-id=<TASK_ID>
```

## 开发环境要求

### 必需的系统依赖
- Python 3.11+
- tmux 3.0+
- Git 2.30+
- FastMCP 2.0 服务器运行中

### 推荐的 IDE 设置
- PyCharm Professional (已配置 Black 格式化)
- 启用 tmux 集成插件
- Git 工具窗口配置为显示分支图

### 性能优化建议
- 使用 SSD 存储以提高 tmux 会话切换速度
- 配置至少 8GB 内存用于并行会话
- 启用 Git 大文件支持（如需要）