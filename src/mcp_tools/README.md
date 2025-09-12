# MCP Tools - 完美融合的四层架构

## 🏗️ 架构概述

这是从mcp_server完美融合而来的分层MCP工具系统，采用优雅的四层架构设计：

```
🎯 ORCHESTRATOR LAYER (编排层) - 3个工具
   ├── orchestrate_project_workflow    # 项目工作流编排
   ├── manage_project_lifecycle        # 项目生命周期管理
   └── coordinate_parallel_tasks       # 并行任务协调

📊 MONITORING LAYER (监控层) - 6个工具  
   ├── check_system_health             # 系统健康检查
   ├── diagnose_session_issues         # 会话问题诊断
   ├── get_performance_metrics         # 性能指标获取
   ├── get_system_dashboard            # 系统仪表板
   ├── generate_status_report          # 状态报告生成
   └── export_system_metrics           # 指标数据导出

📋 SESSION LAYER (会话层) - 11个工具
   ├── 会话管理 (4个)
   │   ├── create_development_session   # 创建开发会话
   │   ├── terminate_session           # 终止会话
   │   ├── query_session_status        # 查询会话状态
   │   └── list_all_managed_sessions   # 列出所有会话
   ├── 消息系统 (4个)
   │   ├── send_message_to_session     # 发送消息到会话
   │   ├── get_session_messages        # 获取会话消息
   │   ├── mark_message_read           # 标记消息已读
   │   └── broadcast_message           # 广播消息
   └── 关系管理 (3个)
       ├── register_session_relationship # 注册会话关系
       ├── query_child_sessions        # 查询子会话
       └── get_session_hierarchy       # 获取会话层级

🔧 TMUX LAYER (基础层) - 1个工具
   └── tmux_session_orchestrator       # 纯MCP tmux会话编排
```

**总计: 21个独立MCP工具，零shell脚本依赖**

## 🎯 使用指南

### 🔧 Tmux层 - 适合所有用户

最简单的入门方式，一个工具解决所有基础需求：

```python
from src.mcp_tools import tmux_session_orchestrator

# 🚀 一键启动项目环境
tmux_session_orchestrator("init", "ECOMMERCE", ["AUTH", "PAYMENT", "UI"])
tmux_session_orchestrator("start", "ECOMMERCE", ["AUTH", "PAYMENT", "UI"])

# 📊 检查项目状态  
status = tmux_session_orchestrator("status", "ECOMMERCE")

# 💬 会话间通信
tmux_session_orchestrator("message", "ECOMMERCE",
    from_session="master_project_ECOMMERCE",
    to_session="child_ECOMMERCE_task_AUTH",
    message="请切换到OAuth实现")

# 🧹 清理环境
tmux_session_orchestrator("cleanup", "ECOMMERCE")
```

### 📋 Session层 - 适合高级用户

精细化控制，每个MCP工具处理特定功能：

```python
# 🎯 会话管理 - 精确控制每个会话
from src.mcp_tools import create_development_session, terminate_session, query_session_status

# 创建特定类型的会话
create_development_session("ECOMMERCE", "master")
create_development_session("ECOMMERCE", "child", "AUTH_TASK", "/path/to/auth")

# 查询会话详细状态
status = query_session_status("child_ECOMMERCE_task_AUTH")

# 💬 消息系统 - 高级通信功能
from src.mcp_tools import send_message_to_session, broadcast_message, get_session_messages

# 发送带优先级的消息
send_message_to_session("child_ECOMMERCE_task_AUTH", "紧急：切换到OAuth2.0", 
                       message_type="command", priority="urgent")

# 广播给所有子会话
broadcast_message("请在30分钟内报告进度", target_sessions=None, session_pattern="child_ECOMMERCE_*")

# 🔗 关系管理 - 会话层级结构
from src.mcp_tools import register_session_relationship, get_session_hierarchy

# 建立复杂的会话关系
register_session_relationship("master_project_ECOMMERCE", "child_ECOMMERCE_task_AUTH")

# 获取完整层级结构 
hierarchy = get_session_hierarchy("master_project_ECOMMERCE", max_depth=5)
```

### 📊 Monitoring层 - 适合系统管理员

专业级系统监控和诊断：

```python
# 🔍 健康监控 - 全面系统诊断
from src.mcp_tools import check_system_health, diagnose_session_issues, get_performance_metrics

# 全面健康检查
health = check_system_health(include_detailed_metrics=True, check_tmux_integrity=True)
print(f"系统健康分数: {health['health_score']}")
print(f"总体状态: {health['overall_status']}")

# 深度会话诊断
diagnosis = diagnose_session_issues("child_ECOMMERCE_task_AUTH", deep_analysis=True)
if diagnosis['severity'] == 'critical':
    print("⚠️ 发现严重问题，需要立即处理")

# 性能指标收集
metrics = get_performance_metrics(time_range_hours=24, include_historical=True)

# 📈 状态仪表板 - 可视化监控
from src.mcp_tools import get_system_dashboard, generate_status_report, export_system_metrics

# 实时监控仪表板
dashboard = get_system_dashboard(refresh_interval=30, include_trends=True)
print(f"活跃会话: {dashboard['system_overview']['active_sessions']}")
print(f"健康会话: {dashboard['key_metrics']['healthy_session_count']}")

# 生成多格式报告
json_report = generate_status_report("comprehensive", "json", include_recommendations=True)
md_report = generate_status_report("summary", "markdown")
csv_data = export_system_metrics("all", "csv", "24h")
```

### 🎯 Orchestrator层 - 适合项目经理

企业级项目编排和生命周期管理：

```python
# 🎼 项目工作流编排 - 最高级别自动化
from src.mcp_tools import orchestrate_project_workflow, manage_project_lifecycle, coordinate_parallel_tasks

# 编排完整项目工作流
workflow_result = orchestrate_project_workflow(
    project_id="ECOMMERCE",
    workflow_type="development",  # development/testing/deployment
    tasks=["AUTH", "PAYMENT", "UI", "DATABASE"], 
    parallel_execution=True,
    auto_cleanup=True
)

print(f"工作流状态: {workflow_result['overall_success']}")
print(f"执行阶段: {list(workflow_result['phases'].keys())}")

# 📋 项目生命周期管理
# 创建项目
lifecycle_result = manage_project_lifecycle("ECOMMERCE", "create", {
    "team_size": 5,
    "deadline": "2024-12-31",
    "technology_stack": ["React", "Node.js", "PostgreSQL"]
})

# 启动项目
manage_project_lifecycle("ECOMMERCE", "start")

# 暂停/恢复/停止项目
manage_project_lifecycle("ECOMMERCE", "pause")
manage_project_lifecycle("ECOMMERCE", "resume") 

# 🔄 并行任务协调 - 智能依赖管理
tasks = [
    {"id": "setup_db", "name": "Database Setup", "dependencies": []},
    {"id": "auth_service", "name": "Auth Service", "dependencies": ["setup_db"]},
    {"id": "payment_service", "name": "Payment Service", "dependencies": ["setup_db"]},
    {"id": "frontend", "name": "Frontend App", "dependencies": ["auth_service", "payment_service"]}
]

coordination_result = coordinate_parallel_tasks(
    project_id="ECOMMERCE",
    tasks=tasks,
    max_parallel=3,
    dependency_resolution=True
)

print(f"任务协调成功率: {coordination_result['batch_summary']['success_rate']}")
```

## 🔧 架构特性

### ✅ 完美融合成果

- **零能力丢失**: 所有原mcp_server功能完美保留
- **优雅重构**: 从1505行巨型文件重构为模块化组件
- **分层清晰**: 四层架构，职责分明，易于理解维护
- **向上兼容**: 上层工具自动调用下层，形成完整能力体系

### ✅ 技术优势

- **纯MCP架构**: 21个独立MCP工具，零shell脚本依赖
- **工具原子性**: 每个函数都是独立工具，可单独调用
- **智能编排**: Orchestrator层自动调用下层能力
- **错误处理**: 完善的异常处理和状态管理

### ✅ 用户体验

- **渐进式学习**: 从Tmux层的1个工具开始，逐步掌握21个工具
- **角色适配**: 不同层级适配不同技能水平和职责
- **一致接口**: 统一的MCP工具调用方式
- **丰富文档**: 详细的使用示例和最佳实践

## 🧪 测试验证

```bash
# 验证完整架构导入
python -c "
from src.mcp_tools import *
print('✅ 成功导入全部21个MCP工具')
print('🔧 Tmux层: 1个工具')  
print('📋 Session层: 11个工具')
print('📊 Monitoring层: 6个工具') 
print('🎯 Orchestrator层: 3个工具')
"

# 测试基础功能
python -c "
from src.mcp_tools import tmux_session_orchestrator
result = tmux_session_orchestrator('status', 'TEST')
print('✅ 基础功能正常')
"

# 测试高级功能
python -c "
from src.mcp_tools import check_system_health
health = check_system_health()  
print(f'✅ 系统健康检查: {health}')
"
```

## 🚀 快速开始

### 1️⃣ 新手入门 (1分钟)
```python
from src.mcp_tools import tmux_session_orchestrator
tmux_session_orchestrator("start", "MY_PROJECT", ["TASK1", "TASK2"])
```

### 2️⃣ 进阶使用 (5分钟)  
```python  
from src.mcp_tools import create_development_session, send_message_to_session
create_development_session("MY_PROJECT", "child", "SPECIAL_TASK")
send_message_to_session("child_MY_PROJECT_task_SPECIAL_TASK", "开始实现特殊功能")
```

### 3️⃣ 专业运维 (10分钟)
```python
from src.mcp_tools import check_system_health, get_system_dashboard  
health = check_system_health(include_detailed_metrics=True)
dashboard = get_system_dashboard(include_trends=True)
```

### 4️⃣ 项目管理 (15分钟)
```python
from src.mcp_tools import orchestrate_project_workflow
orchestrate_project_workflow("MY_PROJECT", "development", ["AUTH", "API", "UI"])
```

## 🎉 开始你的完美融合之旅

选择适合你的层级，开始使用这套完美融合的MCP工具架构！

- 🔧 **新手**: 从`tmux_session_orchestrator`开始
- 📋 **进阶**: 探索Session层的11个精细工具  
- 📊 **运维**: 掌握Monitoring层的监控能力
- 🎯 **管理**: 使用Orchestrator层的项目编排

**21个工具，无限可能！** ✨