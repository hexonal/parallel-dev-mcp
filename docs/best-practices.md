# 使用示例和最佳实践指南

本指南提供了 Parallel Development MCP 项目的使用示例和最佳实践，帮助用户充分利用系统的各项功能。

## 📋 目录

1. [系统健康检查最佳实践](#系统健康检查最佳实践)
2. [环境变量管理和测试](#环境变量管理和测试)
3. [项目兼容性验证](#项目兼容性验证)
4. [四层MCP工具使用指南](#四层MCP工具使用指南)
5. [故障排除和诊断流程](#故障排除和诊断流程)
6. [性能优化建议](#性能优化建议)

## 🔧 系统健康检查最佳实践

### 日常健康检查

```python
# 快速系统状态检查（推荐用于频繁监控）
quick_status = quick_system_status()
print(f"系统状态: {quick_status['overall_status']}")

# 全面系统健康检查（推荐用于项目初始化和深度诊断）
health_report = system_health_check()
if health_report['overall_status'] != 'healthy':
    print("需要关注的问题:")
    for detail in health_report['details']:
        if detail['status'] in ['warning', 'critical']:
            print(f"- {detail['check_name']}: {detail['message']}")
```

### 自动问题诊断

```python
# 自动诊断常见问题并获得解决方案
diagnosis = diagnose_common_issues()
if diagnosis['issues_found']:
    print("发现的问题:")
    for issue in diagnosis['issues_found']:
        print(f"- {issue}")

    print("建议的解决方案:")
    for solution in diagnosis['solutions']:
        print(f"- {solution}")
```

### 健康检查最佳时机

- **项目初始化**: 使用 `system_health_check()` 进行全面检查
- **开发过程中**: 使用 `quick_system_status()` 进行快速检查
- **部署前**: 使用 `diagnose_common_issues()` 进行问题诊断
- **故障排除**: 使用所有三个工具的组合诊断

## 🌍 环境变量管理和测试

### 全面环境变量测试

```python
# 完整的环境变量测试
env_report = environment_variables_test()

# 检查测试结果
if env_report['overall_status'] == 'passed':
    print("✅ 环境变量配置正常")
else:
    print(f"⚠️ 环境变量测试状态: {env_report['overall_status']}")

    # 查看失败的测试
    for result in env_report['test_results']:
        if result['status'] in ['failed', 'error']:
            print(f"- {result['test_name']}: {result['message']}")

    # 查看改进建议
    if env_report.get('recommendations'):
        print("\n改进建议:")
        for rec in env_report['recommendations']:
            print(f"- {rec}")
```

### 关键环境变量检查

```python
# 检查关键环境变量（如USER, HOME, PATH等）
critical_vars = check_critical_env_vars()

missing_vars = critical_vars.get('missing_variables', [])
if missing_vars:
    print(f"❌ 缺失关键环境变量: {', '.join(missing_vars)}")
else:
    print("✅ 所有关键环境变量都已设置")
```

### 进程间继承和隔离测试

```python
# 测试环境变量在进程间的继承和隔离
inheritance_test = test_env_inheritance_isolation()

print(f"继承测试: {inheritance_test['inheritance_test']['status']}")
print(f"隔离测试: {inheritance_test['isolation_test']['status']}")

if inheritance_test['overall_status'] != 'passed':
    print("⚠️ 环境变量继承或隔离存在问题，请检查系统配置")
```

## 🔍 项目兼容性验证

### 项目依赖检查

```python
# 检查项目依赖状态
dep_status = check_project_dependencies()

if dep_status['missing_critical']:
    print("❌ 缺少关键依赖:")
    for dep in dep_status['missing_critical']:
        print(f"- {dep}")
    print("请安装缺少的关键依赖")

if dep_status['missing_important']:
    print("⚠️ 缺少重要依赖:")
    for dep in dep_status['missing_important']:
        print(f"- {dep}")
```

### Hooks兼容性验证

```python
# 检查examples/hooks/目录的兼容性
hooks_compat = hooks_compatibility_check()

print(f"Hooks兼容性: {hooks_compat['overall_compatibility']}")

# 查看兼容性问题
for result in hooks_compat['check_results']:
    if result['status'] in ['incompatible', 'missing', 'warning']:
        print(f"- {result['check_name']}: {result['message']}")

# 查看改进建议
if hooks_compat.get('recommendations'):
    print("\n改进建议:")
    for rec in hooks_compat['recommendations']:
        print(f"- {rec}")
```

## 🏗️ 四层MCP工具使用指南

### 🔧 Tmux层 - 基础用户

```python
# 基础会话编排（适合所有用户）
from src.parallel_dev_mcp.tmux.orchestrator import tmux_session_orchestrator

# 初始化项目环境
result = tmux_session_orchestrator("init", "ECOMMERCE", ["AUTH", "PAYMENT", "UI"])
if result:
    print("✅ 项目环境初始化成功")

# 启动所有会话
tmux_session_orchestrator("start", "ECOMMERCE", ["AUTH", "PAYMENT", "UI"])

# 停止所有会话
tmux_session_orchestrator("stop", "ECOMMERCE", ["AUTH", "PAYMENT", "UI"])
```

### 📋 Session层 - 高级用户

```python
# 精细化会话管理
from src.parallel_dev_mcp.session import (
    create_development_session,
    send_message_to_session,
    get_session_messages,
    query_session_status
)

# 创建特定开发会话
session_result = create_development_session(
    project_id="ECOMMERCE",
    session_type="child",
    task_id="AUTH_TASK"
)

# 发送消息到会话
send_message_to_session(
    session_name="parallel_ECOMMERCE_task_child_AUTH",
    message="请报告当前任务进度"
)

# 获取会话消息
messages = get_session_messages("parallel_ECOMMERCE_task_child_AUTH")
for msg in messages:
    print(f"[{msg['timestamp']}] {msg['content']}")

# 查询会话状态
status = query_session_status("parallel_ECOMMERCE_task_child_AUTH")
print(f"会话状态: {status}")
```

### 📊 Monitoring层 - 系统管理员

```python
# 系统监控和诊断
from src.parallel_dev_mcp.monitoring import (
    system_health_check,
    get_system_dashboard,
    generate_status_report
)

# 全面健康检查
health = system_health_check(include_detailed_metrics=True)
print(f"系统健康状态: {health['overall_status']}")

# 获取监控仪表板
dashboard = get_system_dashboard(include_trends=True)
print("系统监控仪表板:")
for metric, value in dashboard.items():
    print(f"- {metric}: {value}")

# 生成状态报告
report = generate_status_report(format="detailed")
print("详细状态报告已生成")
```

### 🎯 Orchestrator层 - 项目经理

```python
# 项目级工作流编排
from src.parallel_dev_mcp.orchestrator import (
    orchestrate_project_workflow,
    manage_project_lifecycle,
    coordinate_parallel_tasks
)

# 编排完整项目工作流
workflow_result = orchestrate_project_workflow(
    project_id="ECOMMERCE",
    workflow_type="development",
    tasks=["AUTH", "PAYMENT", "UI"],
    parallel_execution=True
)

# 管理项目生命周期
lifecycle_result = manage_project_lifecycle(
    project_id="ECOMMERCE",
    lifecycle_stage="development",
    tasks=["AUTH", "PAYMENT", "UI"]
)

# 协调并行任务
coordination_result = coordinate_parallel_tasks(
    project_id="ECOMMERCE",
    task_dependencies={
        "PAYMENT": ["AUTH"],  # PAYMENT依赖AUTH
        "UI": ["AUTH", "PAYMENT"]  # UI依赖AUTH和PAYMENT
    }
)
```

## 🚨 故障排除和诊断流程

### 系统问题诊断流程

```python
def diagnose_system_issues():
    """完整的系统问题诊断流程"""

    print("🔍 开始系统诊断...")

    # 1. 快速状态检查
    quick_status = quick_system_status()
    print(f"快速检查: {quick_status['overall_status']}")

    if quick_status['overall_status'] != 'healthy':
        # 2. 详细健康检查
        health_report = system_health_check()
        print("详细健康检查完成")

        # 3. 自动问题诊断
        diagnosis = diagnose_common_issues()
        print(f"发现 {len(diagnosis['issues_found'])} 个问题")

        # 4. 环境变量检查
        env_status = environment_variables_test()
        print(f"环境变量状态: {env_status['overall_status']}")

        # 5. 依赖检查
        dep_status = check_project_dependencies()
        print(f"依赖状态: {dep_status['overall_status']}")

        # 6. 兼容性检查
        compat_status = hooks_compatibility_check()
        print(f"兼容性: {compat_status['overall_compatibility']}")

        # 汇总建议
        all_recommendations = []
        for result in [health_report, diagnosis, env_status, compat_status]:
            if result.get('recommendations'):
                all_recommendations.extend(result['recommendations'])

        if all_recommendations:
            print("\n🔧 修复建议:")
            for i, rec in enumerate(set(all_recommendations), 1):
                print(f"{i}. {rec}")

    print("✅ 诊断完成")

# 运行完整诊断
diagnose_system_issues()
```

### 会话问题诊断

```python
def diagnose_session_issues(project_id: str, task_id: str = None):
    """会话相关问题诊断"""

    # 检查主会话
    master_session = f"parallel_{project_id}_task_master"
    master_status = query_session_status(master_session)
    print(f"主会话状态: {master_status}")

    if task_id:
        # 检查特定子会话
        child_session = f"parallel_{project_id}_task_child_{task_id}"
        child_status = query_session_status(child_session)
        print(f"子会话状态: {child_status}")

        # 检查会话消息
        messages = get_session_messages(child_session, limit=5)
        print(f"最近消息数: {len(messages)}")

    # 列出所有相关会话
    all_sessions = list_all_managed_sessions()
    project_sessions = [s for s in all_sessions if project_id in s['name']]
    print(f"项目会话数: {len(project_sessions)}")

# 示例使用
diagnose_session_issues("ECOMMERCE", "AUTH")
```

## ⚡ 性能优化建议

### 监控性能指标

```python
# 获取性能指标
performance = get_performance_metrics()

# 分析CPU使用率
if performance.get('cpu_percent', 0) > 80:
    print("⚠️ CPU使用率过高，考虑减少并行任务数量")

# 分析内存使用率
if performance.get('memory_percent', 0) > 85:
    print("⚠️ 内存使用率过高，检查是否有内存泄漏")

# 分析磁盘使用率
if performance.get('disk_percent', 0) > 90:
    print("⚠️ 磁盘空间不足，清理临时文件")
```

### 最佳实践建议

1. **定期健康检查**: 每天开始工作时运行快速状态检查
2. **环境变量验证**: 在项目配置变更后运行环境变量测试
3. **依赖更新检查**: 在添加新依赖后运行依赖状态检查
4. **兼容性验证**: 在更新hooks配置后运行兼容性检查
5. **分层使用**: 根据用户技能水平选择合适的工具层级
6. **故障预防**: 使用自动诊断工具提前发现潜在问题
7. **性能监控**: 定期检查系统性能指标，优化资源使用

### 自动化检查脚本

```bash
#!/bin/bash
# daily_check.sh - 日常系统检查脚本

echo "🔍 执行日常系统检查..."

# 快速状态检查
python -c "
from src.parallel_dev_mcp.monitoring import quick_system_status
status = quick_system_status()
print(f'系统状态: {status[\"overall_status\"]}')
"

# 环境变量检查
python -c "
from src.parallel_dev_mcp.monitoring import check_critical_env_vars
vars_status = check_critical_env_vars()
if vars_status['missing_variables']:
    print(f'⚠️ 缺失关键变量: {vars_status[\"missing_variables\"]}')
else:
    print('✅ 环境变量正常')
"

# 依赖检查
python -c "
from src.parallel_dev_mcp.monitoring import check_project_dependencies
deps = check_project_dependencies()
if deps['missing_critical']:
    print(f'❌ 缺失关键依赖: {deps[\"missing_critical\"]}')
else:
    print('✅ 依赖完整')
"

echo "✅ 日常检查完成"
```

## 📝 总结

通过遵循这些最佳实践，你可以：

1. **提高系统可靠性**: 通过定期健康检查和诊断
2. **减少故障时间**: 通过自动问题诊断和解决方案
3. **优化开发效率**: 通过选择合适的工具层级
4. **确保环境一致性**: 通过环境变量和依赖检查
5. **维护系统性能**: 通过性能监控和优化建议

建议将这些实践集成到你的日常开发工作流中，以获得最佳的开发体验。