# 使用示例集合

本文档提供了 Parallel Development MCP 项目的详细使用示例，涵盖各种应用场景。

## 📋 目录

1. [新用户快速上手](#新用户快速上手)
2. [电商项目开发示例](#电商项目开发示例)
3. [Web应用开发示例](#Web应用开发示例)
4. [移动应用开发示例](#移动应用开发示例)
5. [团队协作开发示例](#团队协作开发示例)
6. [CI/CD集成示例](#CICD集成示例)
7. [故障排除实战示例](#故障排除实战示例)

## 🚀 新用户快速上手

### 第一次使用 - 基础检查

```python
# 步骤1: 系统健康检查
print("🔍 检查系统健康状况...")
health_report = system_health_check()

if health_report['overall_status'] == 'healthy':
    print("✅ 系统健康，可以开始使用")
else:
    print("⚠️ 系统存在问题，需要解决:")
    for detail in health_report['details']:
        if detail['status'] in ['warning', 'critical']:
            print(f"- {detail['message']}")

# 步骤2: 环境变量检查
print("\n🌍 检查环境变量...")
env_status = check_critical_env_vars()
if env_status['missing_variables']:
    print(f"❌ 缺失关键环境变量: {', '.join(env_status['missing_variables'])}")
else:
    print("✅ 环境变量配置正常")

# 步骤3: 依赖检查
print("\n📦 检查项目依赖...")
deps = check_project_dependencies()
if deps['missing_critical']:
    print(f"❌ 缺失关键依赖: {', '.join(deps['missing_critical'])}")
    print("请运行: pip install " + " ".join(deps['missing_critical']))
else:
    print("✅ 依赖完整")

print("\n🎉 系统检查完成，可以开始使用MCP工具！")
```

### 创建第一个项目

```python
# 使用Tmux层创建简单项目
project_id = "MY_FIRST_PROJECT"
tasks = ["FRONTEND", "BACKEND", "DATABASE"]

print(f"🚀 创建项目: {project_id}")

# 初始化项目环境
result = tmux_session_orchestrator("init", project_id, tasks)
if result:
    print("✅ 项目环境初始化成功")
    print(f"创建的会话:")
    print(f"- 主会话: parallel_{project_id}_task_master")
    for task in tasks:
        print(f"- 子会话: parallel_{project_id}_task_child_{task}")

# 启动所有会话
tmux_session_orchestrator("start", project_id, tasks)
print("✅ 所有会话已启动")
```

## 🛒 电商项目开发示例

### 完整电商系统开发

```python
# 电商项目配置
ECOMMERCE_PROJECT = {
    "project_id": "ECOMMERCE",
    "tasks": [
        "USER_AUTH",      # 用户认证系统
        "PRODUCT_CATALOG", # 商品目录
        "SHOPPING_CART",   # 购物车
        "PAYMENT",         # 支付系统
        "ORDER_MGMT",      # 订单管理
        "ADMIN_PANEL"      # 管理面板
    ]
}

# 第1步: 系统准备和验证
print("🛒 电商项目开发准备...")
def prepare_ecommerce_project():
    # 检查系统健康
    health = system_health_check()
    if health['overall_status'] != 'healthy':
        print("❌ 系统健康检查失败，请先解决系统问题")
        return False

    # 检查必要依赖
    deps = check_project_dependencies()
    if deps['missing_critical']:
        print(f"❌ 缺失关键依赖: {deps['missing_critical']}")
        return False

    # 检查环境变量
    env_vars = environment_variables_test()
    if env_vars['overall_status'] != 'passed':
        print("⚠️ 环境变量存在问题，但可以继续")

    print("✅ 电商项目准备完成")
    return True

# 第2步: 项目初始化
if prepare_ecommerce_project():
    print("\n🏗️ 初始化电商项目...")

    # 使用Orchestrator层进行项目级管理
    workflow_result = orchestrate_project_workflow(
        project_id=ECOMMERCE_PROJECT["project_id"],
        workflow_type="development",
        tasks=ECOMMERCE_PROJECT["tasks"],
        parallel_execution=True
    )

    if workflow_result:
        print("✅ 电商项目工作流编排成功")

# 第3步: 任务依赖协调
print("\n🔗 配置任务依赖关系...")
dependencies = {
    "SHOPPING_CART": ["USER_AUTH", "PRODUCT_CATALOG"],
    "PAYMENT": ["USER_AUTH", "SHOPPING_CART"],
    "ORDER_MGMT": ["USER_AUTH", "PAYMENT"],
    "ADMIN_PANEL": ["USER_AUTH", "PRODUCT_CATALOG", "ORDER_MGMT"]
}

coordinate_result = coordinate_parallel_tasks(
    project_id=ECOMMERCE_PROJECT["project_id"],
    task_dependencies=dependencies
)

if coordinate_result:
    print("✅ 任务依赖协调完成")

# 第4步: 监控项目状态
print("\n📊 监控项目状态...")
dashboard = get_system_dashboard(include_trends=True)
print(f"系统负载: CPU {dashboard.get('cpu_percent', 0)}%, 内存 {dashboard.get('memory_percent', 0)}%")
```

### 电商项目特定任务管理

```python
# 用户认证任务的详细管理
def manage_user_auth_task():
    session_name = "parallel_ECOMMERCE_task_child_USER_AUTH"

    # 创建专门的认证开发会话
    auth_session = create_development_session(
        project_id="ECOMMERCE",
        session_type="child",
        task_id="USER_AUTH"
    )

    # 发送开发指导消息
    messages = [
        "开始用户认证系统开发",
        "实现JWT token生成和验证",
        "添加密码加密和验证",
        "创建用户注册和登录接口",
        "实现权限控制中间件"
    ]

    for msg in messages:
        send_message_to_session(session_name, msg)
        print(f"📝 已发送: {msg}")

    # 查询任务进度
    status = query_session_status(session_name)
    print(f"认证任务状态: {status}")

# 商品目录任务管理
def manage_product_catalog_task():
    session_name = "parallel_ECOMMERCE_task_child_PRODUCT_CATALOG"

    # 发送产品开发指导
    catalog_tasks = [
        "设计商品数据模型",
        "实现商品CRUD接口",
        "添加商品搜索功能",
        "实现商品分类管理",
        "添加商品图片上传功能"
    ]

    for task in catalog_tasks:
        send_message_to_session(session_name, f"TODO: {task}")

    print("📦 商品目录任务已分配")

# 执行电商任务管理
manage_user_auth_task()
manage_product_catalog_task()
```

## 🌐 Web应用开发示例

### 现代Web应用开发流程

```python
# Web应用项目配置
WEB_APP_PROJECT = {
    "project_id": "WEBAPP",
    "tasks": [
        "FRONTEND_REACT",   # React前端
        "BACKEND_NODE",     # Node.js后端
        "DATABASE_MONGO",   # MongoDB数据库
        "API_GATEWAY",      # API网关
        "AUTH_SERVICE",     # 认证服务
        "TESTING"           # 测试套件
    ]
}

def setup_web_application():
    print("🌐 Web应用开发设置...")

    # 第1步: 环境验证
    print("验证开发环境...")
    env_test = environment_variables_test()

    # 检查Node.js和相关工具
    required_tools = ['node', 'npm', 'git']
    missing_tools = []

    import shutil
    for tool in required_tools:
        if not shutil.which(tool):
            missing_tools.append(tool)

    if missing_tools:
        print(f"❌ 缺失开发工具: {', '.join(missing_tools)}")
        return False

    print("✅ 开发环境验证通过")

    # 第2步: 项目生命周期管理
    lifecycle_result = manage_project_lifecycle(
        project_id=WEB_APP_PROJECT["project_id"],
        lifecycle_stage="setup",
        tasks=WEB_APP_PROJECT["tasks"]
    )

    if lifecycle_result:
        print("✅ 项目生命周期初始化完成")

    # 第3步: 设置开发会话
    for task in WEB_APP_PROJECT["tasks"]:
        session_result = create_development_session(
            project_id=WEB_APP_PROJECT["project_id"],
            session_type="child",
            task_id=task
        )
        print(f"✅ 创建会话: {task}")

    print("🎉 Web应用开发环境设置完成")
    return True

# 前端开发任务管理
def manage_frontend_development():
    session_name = "parallel_WEBAPP_task_child_FRONTEND_REACT"

    frontend_steps = [
        "创建React应用框架",
        "设置路由系统(React Router)",
        "实现组件库和样式系统",
        "集成状态管理(Redux/Context)",
        "实现API调用和数据处理",
        "添加响应式设计",
        "实现用户界面组件"
    ]

    print("⚛️ 开始前端开发流程...")
    for step in frontend_steps:
        send_message_to_session(session_name, f"FRONTEND: {step}")
        print(f"📝 前端任务: {step}")

# 后端开发任务管理
def manage_backend_development():
    session_name = "parallel_WEBAPP_task_child_BACKEND_NODE"

    backend_steps = [
        "设置Express.js服务器",
        "实现RESTful API接口",
        "集成MongoDB数据库连接",
        "实现用户认证中间件",
        "添加API文档(Swagger)",
        "实现错误处理和日志",
        "添加API限流和安全措施"
    ]

    print("🔧 开始后端开发流程...")
    for step in backend_steps:
        send_message_to_session(session_name, f"BACKEND: {step}")
        print(f"📝 后端任务: {step}")

# 执行Web应用开发
if setup_web_application():
    manage_frontend_development()
    manage_backend_development()
```

## 📱 移动应用开发示例

### React Native应用开发

```python
# 移动应用项目配置
MOBILE_APP_PROJECT = {
    "project_id": "MOBILEAPP",
    "tasks": [
        "RN_SETUP",         # React Native环境设置
        "UI_COMPONENTS",    # UI组件开发
        "NAVIGATION",       # 导航系统
        "STATE_MGMT",       # 状态管理
        "API_INTEGRATION",  # API集成
        "PLATFORM_SPECIFIC", # 平台特定功能
        "TESTING_E2E"       # 端到端测试
    ]
}

def setup_mobile_development():
    print("📱 移动应用开发设置...")

    # 检查移动开发环境
    mobile_deps = check_project_dependencies()

    # 检查React Native工具链
    rn_tools = ['npx', 'pod', 'adb']  # iOS/Android工具
    available_tools = []

    import shutil
    for tool in rn_tools:
        if shutil.which(tool):
            available_tools.append(tool)

    print(f"可用开发工具: {', '.join(available_tools)}")

    # 项目工作流编排
    workflow_result = orchestrate_project_workflow(
        project_id=MOBILE_APP_PROJECT["project_id"],
        workflow_type="mobile_development",
        tasks=MOBILE_APP_PROJECT["tasks"],
        parallel_execution=True
    )

    if workflow_result:
        print("✅ 移动应用工作流编排完成")

    return True

def manage_mobile_ui_development():
    session_name = "parallel_MOBILEAPP_task_child_UI_COMPONENTS"

    ui_tasks = [
        "设计通用UI组件库",
        "实现自定义Button组件",
        "创建Input和Form组件",
        "实现Navigation组件",
        "添加Loading和Modal组件",
        "实现主题系统(Dark/Light)",
        "优化移动端交互体验"
    ]

    print("🎨 开始移动UI开发...")
    for task in ui_tasks:
        send_message_to_session(session_name, f"UI: {task}")
        print(f"📱 UI任务: {task}")

# 执行移动应用开发
setup_mobile_development()
manage_mobile_ui_development()
```

## 👥 团队协作开发示例

### 多人协作项目管理

```python
# 团队项目配置
TEAM_PROJECT = {
    "project_id": "TEAMPROJECT",
    "teams": {
        "FRONTEND_TEAM": ["REACT_APP", "MOBILE_APP", "UI_DESIGN"],
        "BACKEND_TEAM": ["API_SERVER", "DATABASE", "AUTH_SERVICE"],
        "DEVOPS_TEAM": ["CI_CD", "DEPLOYMENT", "MONITORING"],
        "QA_TEAM": ["UNIT_TESTS", "INTEGRATION_TESTS", "E2E_TESTS"]
    }
}

def setup_team_collaboration():
    print("👥 设置团队协作环境...")

    # 为每个团队创建主会话
    for team_name, tasks in TEAM_PROJECT["teams"].items():
        team_session = f"parallel_{TEAM_PROJECT['project_id']}_team_{team_name}"

        # 创建团队主会话
        team_master = create_development_session(
            project_id=TEAM_PROJECT["project_id"],
            session_type="master",
            task_id=team_name
        )

        print(f"✅ 创建团队会话: {team_name}")

        # 为团队任务创建子会话
        for task in tasks:
            task_session = create_development_session(
                project_id=TEAM_PROJECT["project_id"],
                session_type="child",
                task_id=f"{team_name}_{task}"
            )
            print(f"  📝 任务会话: {task}")

def coordinate_team_work():
    print("\n🔗 协调团队工作...")

    # 设置团队间依赖关系
    team_dependencies = {
        "FRONTEND_TEAM": ["BACKEND_TEAM"],  # 前端依赖后端API
        "QA_TEAM": ["FRONTEND_TEAM", "BACKEND_TEAM"],  # QA依赖前后端完成
        "DEVOPS_TEAM": ["BACKEND_TEAM"]  # DevOps依赖后端服务
    }

    # 协调团队并行工作
    coordination_result = coordinate_parallel_tasks(
        project_id=TEAM_PROJECT["project_id"],
        task_dependencies=team_dependencies
    )

    if coordination_result:
        print("✅ 团队工作协调完成")

def monitor_team_progress():
    print("\n📊 监控团队进度...")

    # 获取所有团队会话状态
    all_sessions = list_all_managed_sessions()
    team_sessions = [s for s in all_sessions if TEAM_PROJECT["project_id"] in s.get('name', '')]

    print(f"活跃团队会话数: {len(team_sessions)}")

    # 生成团队状态报告
    team_report = generate_status_report(
        project_filter=TEAM_PROJECT["project_id"],
        include_team_metrics=True
    )

    print("📋 团队状态报告已生成")

# 执行团队协作设置
setup_team_collaboration()
coordinate_team_work()
monitor_team_progress()
```

## 🔄 CI/CD集成示例

### 自动化构建和部署

```python
# CI/CD项目配置
CICD_PROJECT = {
    "project_id": "CICD_PIPELINE",
    "stages": [
        "SOURCE_CONTROL",   # 源码管理
        "BUILD",           # 构建阶段
        "TEST",            # 测试阶段
        "QUALITY_CHECK",   # 质量检查
        "STAGING_DEPLOY",  # 预发布部署
        "PROD_DEPLOY"      # 生产部署
    ]
}

def setup_cicd_pipeline():
    print("🔄 设置CI/CD流水线...")

    # 检查CI/CD环境
    cicd_health = diagnose_common_issues()
    if cicd_health['overall_status'] != 'healthy':
        print("⚠️ CI/CD环境存在问题:")
        for issue in cicd_health['issues_found']:
            print(f"- {issue}")

    # 设置流水线生命周期
    pipeline_result = manage_project_lifecycle(
        project_id=CICD_PROJECT["project_id"],
        lifecycle_stage="pipeline_setup",
        tasks=CICD_PROJECT["stages"]
    )

    if pipeline_result:
        print("✅ CI/CD流水线设置完成")

def execute_build_stage():
    session_name = "parallel_CICD_PIPELINE_task_child_BUILD"

    build_steps = [
        "检出源代码",
        "安装项目依赖",
        "执行代码编译",
        "生成构建产物",
        "创建Docker镜像",
        "推送到镜像仓库"
    ]

    print("🔨 执行构建阶段...")
    for step in build_steps:
        send_message_to_session(session_name, f"BUILD: {step}")
        print(f"⚙️ 构建步骤: {step}")

def execute_test_stage():
    session_name = "parallel_CICD_PIPELINE_task_child_TEST"

    test_steps = [
        "运行单元测试",
        "执行集成测试",
        "运行端到端测试",
        "生成测试报告",
        "检查测试覆盖率",
        "上传测试结果"
    ]

    print("🧪 执行测试阶段...")
    for step in test_steps:
        send_message_to_session(session_name, f"TEST: {step}")
        print(f"✅ 测试步骤: {step}")

def monitor_pipeline_health():
    print("\n📊 监控流水线健康状态...")

    # 获取系统性能指标
    performance = get_performance_metrics()

    # 检查CI/CD资源使用
    if performance.get('cpu_percent', 0) > 90:
        print("⚠️ CPU使用率过高，可能影响构建性能")

    if performance.get('memory_percent', 0) > 90:
        print("⚠️ 内存使用率过高，考虑增加构建机器资源")

    # 生成流水线报告
    pipeline_report = generate_status_report(
        project_filter=CICD_PROJECT["project_id"],
        include_performance_metrics=True
    )

    print("📋 流水线健康报告已生成")

# 执行CI/CD流水线
setup_cicd_pipeline()
execute_build_stage()
execute_test_stage()
monitor_pipeline_health()
```

## 🚨 故障排除实战示例

### 常见问题诊断和解决

```python
def comprehensive_troubleshooting():
    """综合故障排除流程"""

    print("🚨 开始故障排除...")

    # 第1步: 系统整体健康检查
    print("1️⃣ 系统健康检查...")
    health_report = system_health_check()

    if health_report['overall_status'] != 'healthy':
        print("❌ 系统健康检查失败")

        # 显示问题详情
        for detail in health_report['details']:
            if detail['status'] in ['critical', 'warning']:
                print(f"  - {detail['check_name']}: {detail['message']}")

        # 显示建议
        if health_report.get('recommendations'):
            print("🔧 建议解决方案:")
            for rec in health_report['recommendations']:
                print(f"  - {rec}")
    else:
        print("✅ 系统健康检查通过")

    # 第2步: 环境变量诊断
    print("\n2️⃣ 环境变量诊断...")
    env_issues = environment_variables_test()

    failed_tests = [t for t in env_issues['test_results'] if t['status'] in ['failed', 'error']]
    if failed_tests:
        print("❌ 环境变量测试失败:")
        for test in failed_tests:
            print(f"  - {test['test_name']}: {test['message']}")
    else:
        print("✅ 环境变量测试通过")

    # 第3步: 依赖问题诊断
    print("\n3️⃣ 依赖问题诊断...")
    dep_status = check_project_dependencies()

    if dep_status['missing_critical'] or dep_status['missing_important']:
        print("❌ 发现依赖问题:")
        if dep_status['missing_critical']:
            print(f"  关键依赖缺失: {', '.join(dep_status['missing_critical'])}")
        if dep_status['missing_important']:
            print(f"  重要依赖缺失: {', '.join(dep_status['missing_important'])}")
    else:
        print("✅ 依赖检查通过")

    # 第4步: Hooks兼容性检查
    print("\n4️⃣ Hooks兼容性检查...")
    hooks_status = hooks_compatibility_check()

    if hooks_status['overall_compatibility'] != 'compatible':
        print(f"⚠️ Hooks兼容性: {hooks_status['overall_compatibility']}")

        # 显示兼容性问题
        for result in hooks_status['check_results']:
            if result['status'] in ['incompatible', 'missing', 'warning']:
                print(f"  - {result['check_name']}: {result['message']}")
    else:
        print("✅ Hooks兼容性检查通过")

    # 第5步: 自动问题诊断
    print("\n5️⃣ 自动问题诊断...")
    diagnosis = diagnose_common_issues()

    if diagnosis['issues_found']:
        print("🔍 发现的问题:")
        for issue in diagnosis['issues_found']:
            print(f"  - {issue}")

        print("🔧 建议的解决方案:")
        for solution in diagnosis['solutions']:
            print(f"  - {solution}")
    else:
        print("✅ 未发现常见问题")

    print("\n🎯 故障排除完成")

def specific_session_troubleshooting(project_id: str, task_id: str = None):
    """特定会话故障排除"""

    print(f"🔍 诊断项目 {project_id} 的会话问题...")

    # 检查主会话
    master_session = f"parallel_{project_id}_task_master"
    try:
        master_status = query_session_status(master_session)
        print(f"✅ 主会话状态: {master_status}")
    except Exception as e:
        print(f"❌ 主会话问题: {str(e)}")

    if task_id:
        # 检查特定子会话
        child_session = f"parallel_{project_id}_task_child_{task_id}"
        try:
            child_status = query_session_status(child_session)
            print(f"✅ 子会话 {task_id} 状态: {child_status}")

            # 检查会话消息
            messages = get_session_messages(child_session, limit=3)
            print(f"📝 最近消息数: {len(messages)}")

        except Exception as e:
            print(f"❌ 子会话 {task_id} 问题: {str(e)}")

    # 列出所有相关会话
    try:
        all_sessions = list_all_managed_sessions()
        project_sessions = [s for s in all_sessions if project_id in s.get('name', '')]
        print(f"📊 项目会话总数: {len(project_sessions)}")

        for session in project_sessions:
            print(f"  - {session.get('name', 'unknown')}")

    except Exception as e:
        print(f"❌ 获取会话列表失败: {str(e)}")

def performance_troubleshooting():
    """性能问题诊断"""

    print("⚡ 性能问题诊断...")

    # 获取性能指标
    performance = get_performance_metrics()

    # CPU使用率检查
    cpu_percent = performance.get('cpu_percent', 0)
    if cpu_percent > 90:
        print(f"🔥 CPU使用率过高: {cpu_percent}%")
        print("  建议: 减少并行任务数量或优化计算密集型操作")
    elif cpu_percent > 70:
        print(f"⚠️ CPU使用率较高: {cpu_percent}%")
    else:
        print(f"✅ CPU使用率正常: {cpu_percent}%")

    # 内存使用率检查
    memory_percent = performance.get('memory_percent', 0)
    if memory_percent > 90:
        print(f"🔥 内存使用率过高: {memory_percent}%")
        print("  建议: 检查内存泄漏或增加系统内存")
    elif memory_percent > 80:
        print(f"⚠️ 内存使用率较高: {memory_percent}%")
    else:
        print(f"✅ 内存使用率正常: {memory_percent}%")

    # 磁盘使用率检查
    disk_percent = performance.get('disk_percent', 0)
    if disk_percent > 95:
        print(f"🔥 磁盘空间不足: {disk_percent}%")
        print("  建议: 清理临时文件或扩展磁盘空间")
    elif disk_percent > 85:
        print(f"⚠️ 磁盘空间较少: {disk_percent}%")
    else:
        print(f"✅ 磁盘空间充足: {disk_percent}%")

# 故障排除示例执行
print("🚨 执行综合故障排除...")
comprehensive_troubleshooting()

print("\n🔍 特定会话诊断...")
specific_session_troubleshooting("ECOMMERCE", "AUTH")

print("\n⚡ 性能问题诊断...")
performance_troubleshooting()
```

## 📝 总结

这些使用示例展示了如何在不同场景下有效使用 Parallel Development MCP 工具：

1. **新用户**: 从基础健康检查开始，逐步学习系统功能
2. **项目开发**: 根据项目类型选择合适的工具和流程
3. **团队协作**: 利用会话管理和消息系统协调团队工作
4. **CI/CD集成**: 将工具集成到自动化流水线中
5. **故障排除**: 系统化的问题诊断和解决流程

建议根据你的具体需求和技能水平，选择相应的示例作为起点，然后根据项目需要进行调整和扩展。