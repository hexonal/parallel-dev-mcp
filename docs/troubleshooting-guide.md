# 故障排除指南和常见问题解答

本指南提供了 Parallel Development MCP 项目的完整故障排除方案和常见问题解答。

## 📋 目录

1. [快速诊断工具](#快速诊断工具)
2. [系统安装和配置问题](#系统安装和配置问题)
3. [环境变量相关问题](#环境变量相关问题)
4. [依赖和兼容性问题](#依赖和兼容性问题)
5. [会话管理问题](#会话管理问题)
6. [性能和资源问题](#性能和资源问题)
7. [MCP工具问题](#MCP工具问题)
8. [Hooks配置问题](#Hooks配置问题)
9. [常见错误信息解决](#常见错误信息解决)
10. [自助诊断脚本](#自助诊断脚本)

## 🔧 快速诊断工具

### 一键诊断脚本

在遇到问题时，首先运行这个综合诊断脚本：

```python
def emergency_diagnosis():
    """紧急诊断：快速识别主要问题"""

    print("🚨 紧急系统诊断...")

    issues_found = []

    # 1. 快速系统状态
    try:
        status = quick_system_status()
        if status['overall_status'] != 'healthy':
            issues_found.append(f"系统状态异常: {status['overall_status']}")
    except Exception as e:
        issues_found.append(f"系统状态检查失败: {str(e)}")

    # 2. 关键环境变量
    try:
        env_vars = check_critical_env_vars()
        if env_vars['missing_variables']:
            issues_found.append(f"缺失关键环境变量: {', '.join(env_vars['missing_variables'])}")
    except Exception as e:
        issues_found.append(f"环境变量检查失败: {str(e)}")

    # 3. 基础依赖
    try:
        deps = check_project_dependencies()
        if deps['missing_critical']:
            issues_found.append(f"缺失关键依赖: {', '.join(deps['missing_critical'])}")
    except Exception as e:
        issues_found.append(f"依赖检查失败: {str(e)}")

    # 4. 报告结果
    if not issues_found:
        print("✅ 紧急诊断: 未发现严重问题")
        return True
    else:
        print("❌ 紧急诊断发现问题:")
        for issue in issues_found:
            print(f"  - {issue}")
        return False

# 运行紧急诊断
emergency_diagnosis()
```

### 独立诊断脚本

如果Python环境有问题，可以使用这些独立脚本：

```bash
# 系统健康检查
python scripts/health_check.py

# 环境变量测试
python scripts/env_test.py

# Hooks兼容性检查
python scripts/hooks_compatibility_check.py
```

## 🛠️ 系统安装和配置问题

### Q1: `ModuleNotFoundError: No module named 'fastmcp'`

**问题**: 导入fastmcp模块失败

**原因**:
- fastmcp未安装或版本不兼容
- Python版本过低（需要3.10+）
- 虚拟环境未激活

**解决方案**:
```bash
# 检查Python版本
python --version  # 需要3.10+

# 安装/升级fastmcp
uv add fastmcp>=2.11.3
# 或者
pip install fastmcp>=2.11.3

# 检查安装
python -c "import fastmcp; print(fastmcp.__version__)"
```

**备用方案**: 使用简化版本（见独立脚本）

### Q2: `command not found: uv`

**问题**: uv包管理器未安装

**解决方案**:
```bash
# 安装uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 或使用pip安装
pip install uv

# 验证安装
uv --version
```

### Q3: `command not found: tmux`

**问题**: tmux未安装

**解决方案**:
```bash
# macOS
brew install tmux

# Ubuntu/Debian
sudo apt-get update && sudo apt-get install tmux

# CentOS/RHEL
sudo yum install tmux

# 验证安装
tmux -V
```

### Q4: 权限问题 - Permission denied

**问题**: 脚本执行权限不足

**解决方案**:
```bash
# 为scripts目录下的脚本添加执行权限
chmod +x scripts/*.py
chmod +x examples/hooks/*.sh

# 为特定脚本添加权限
chmod +x scripts/health_check.py
chmod +x examples/hooks/stop_hook.sh
```

## 🌍 环境变量相关问题

### Q5: 环境变量测试失败

**问题**: `environment_variables_test()` 返回失败状态

**诊断步骤**:
```python
# 详细诊断环境变量问题
env_report = environment_variables_test()

print("测试结果:")
for result in env_report['test_results']:
    if result['status'] in ['failed', 'error']:
        print(f"❌ {result['test_name']}: {result['message']}")

print("改进建议:")
for rec in env_report.get('recommendations', []):
    print(f"🔧 {rec}")
```

**常见解决方案**:
```bash
# 设置缺失的环境变量
export USER=$(whoami)
export HOME=$HOME
export PATH=$PATH

# 重新加载shell配置
source ~/.bashrc  # 或 ~/.zshrc

# 验证环境变量
echo $USER $HOME $PATH
```

### Q6: 环境变量继承失败

**问题**: 子进程无法继承父进程的环境变量

**诊断**:
```python
# 测试环境变量继承
inheritance_test = test_env_inheritance_isolation()
print(f"继承测试: {inheritance_test['inheritance_test']['status']}")
print(f"隔离测试: {inheritance_test['isolation_test']['status']}")
```

**解决方案**:
```bash
# 确保环境变量已导出
export MY_VAR="value"  # 而不是 MY_VAR="value"

# 检查shell类型
echo $SHELL

# 重启shell或重新登录
exec $SHELL
```

## 📦 依赖和兼容性问题

### Q7: 项目依赖检查失败

**问题**: `check_project_dependencies()` 显示缺失依赖

**诊断**:
```python
deps = check_project_dependencies()

print("依赖状态:")
print(f"缺失关键依赖: {deps['missing_critical']}")
print(f"缺失重要依赖: {deps['missing_important']}")
print(f"缺失可选依赖: {deps['missing_optional']}")
```

**解决方案**:
```bash
# 安装所有依赖
uv sync

# 安装特定依赖
uv add psutil pydantic requests flask

# 验证安装
python -c "import psutil, pydantic, requests, flask; print('✅ 依赖安装成功')"
```

### Q8: Python版本兼容性问题

**问题**: Python版本过低导致功能不可用

**检查版本**:
```python
import sys
print(f"Python版本: {sys.version_info}")

# 运行兼容性检查
diagnosis = diagnose_common_issues()
python_issues = [issue for issue in diagnosis['issues_found'] if 'Python' in issue]
```

**解决方案**:
```bash
# 升级Python（推荐使用pyenv）
pyenv install 3.12
pyenv global 3.12

# 或使用系统包管理器升级
# macOS: brew install python@3.12
# Ubuntu: sudo apt install python3.12
```

## 📡 会话管理问题

### Q9: 会话创建失败

**问题**: `create_development_session()` 返回错误

**诊断**:
```python
def diagnose_session_creation(project_id, task_id):
    print(f"🔍 诊断会话创建: {project_id}/{task_id}")

    # 检查tmux是否可用
    import shutil
    if not shutil.which('tmux'):
        print("❌ tmux未安装")
        return

    # 检查现有会话
    import subprocess
    result = subprocess.run(['tmux', 'list-sessions'],
                          capture_output=True, text=True)

    print("现有会话:")
    print(result.stdout)

    # 尝试创建会话
    session_name = f"parallel_{project_id}_task_child_{task_id}"
    try:
        session_result = create_development_session(project_id, "child", task_id)
        print(f"✅ 会话创建成功: {session_name}")
    except Exception as e:
        print(f"❌ 会话创建失败: {str(e)}")

# 使用示例
diagnose_session_creation("TESTPROJECT", "TESTTASK")
```

**常见解决方案**:
```bash
# 清理僵尸会话
tmux kill-server

# 手动创建测试会话
tmux new-session -d -s "test_session"
tmux list-sessions

# 检查会话命名规范
# 正确: parallel_PROJECT_task_child_TASK
# 错误: project_task_child (缺少parallel前缀)
```

### Q10: 会话消息发送失败

**问题**: `send_message_to_session()` 无法发送消息

**诊断**:
```python
def diagnose_message_sending(session_name, test_message="test"):
    print(f"🔍 诊断消息发送: {session_name}")

    # 检查会话是否存在
    try:
        status = query_session_status(session_name)
        print(f"会话状态: {status}")
    except Exception as e:
        print(f"❌ 会话不存在或无法访问: {str(e)}")
        return

    # 尝试发送测试消息
    try:
        result = send_message_to_session(session_name, test_message)
        print(f"✅ 消息发送成功: {result}")
    except Exception as e:
        print(f"❌ 消息发送失败: {str(e)}")

    # 检查消息接收
    try:
        messages = get_session_messages(session_name, limit=1)
        print(f"最近消息: {messages}")
    except Exception as e:
        print(f"❌ 消息获取失败: {str(e)}")

# 使用示例
diagnose_message_sending("parallel_TESTPROJECT_task_master")
```

## ⚡ 性能和资源问题

### Q11: 系统性能过低

**问题**: CPU、内存或磁盘使用率过高

**诊断**:
```python
def diagnose_performance_issues():
    print("⚡ 性能问题诊断...")

    # 获取性能指标
    performance = get_performance_metrics()

    # CPU诊断
    cpu_percent = performance.get('cpu_percent', 0)
    if cpu_percent > 90:
        print(f"🔥 CPU使用率危险: {cpu_percent}%")
        print("建议:")
        print("  - 减少并行任务数量")
        print("  - 检查CPU密集型进程")
        print("  - 考虑增加CPU资源")

    # 内存诊断
    memory_percent = performance.get('memory_percent', 0)
    if memory_percent > 90:
        print(f"🔥 内存使用率危险: {memory_percent}%")
        print("建议:")
        print("  - 检查内存泄漏")
        print("  - 重启相关服务")
        print("  - 增加系统内存")

    # 磁盘诊断
    disk_percent = performance.get('disk_percent', 0)
    if disk_percent > 95:
        print(f"🔥 磁盘空间不足: {disk_percent}%")
        print("建议:")
        print("  - 清理临时文件")
        print("  - 删除不必要的日志")
        print("  - 扩展磁盘空间")

diagnose_performance_issues()
```

**解决方案**:
```bash
# 清理系统资源
# 清理临时文件
rm -rf /tmp/*
rm -rf ~/.cache/*

# 清理日志文件
sudo journalctl --vacuum-time=7d

# 查找大文件
find / -size +100M -type f 2>/dev/null

# 重启资源密集型服务
sudo systemctl restart high-cpu-service
```

### Q12: tmux会话占用资源过多

**问题**: 大量tmux会话导致系统负载过高

**诊断**:
```bash
# 检查活跃会话数量
tmux list-sessions | wc -l

# 查看会话详情
tmux list-sessions -F "#{session_name}: #{session_windows} windows, #{session_attached} attached"

# 检查僵尸会话
ps aux | grep tmux
```

**解决方案**:
```bash
# 清理不活跃的会话
tmux list-sessions | grep -v attached | cut -d: -f1 | xargs -I {} tmux kill-session -t {}

# 批量清理项目会话
tmux list-sessions | grep "parallel_OLD_PROJECT" | cut -d: -f1 | xargs -I {} tmux kill-session -t {}

# 重启tmux服务器
tmux kill-server
```

## 🔌 MCP工具问题

### Q13: MCP工具导入失败

**问题**: 无法导入MCP工具函数

**诊断**:
```python
def diagnose_mcp_imports():
    print("🔌 MCP工具导入诊断...")

    # 测试各层工具导入
    layers = {
        "tmux": ["tmux_session_orchestrator"],
        "session": ["create_development_session", "send_message_to_session"],
        "monitoring": ["system_health_check", "environment_variables_test"],
        "orchestrator": ["orchestrate_project_workflow"]
    }

    for layer, tools in layers.items():
        print(f"\n📋 {layer.upper()} 层:")
        for tool in tools:
            try:
                exec(f"from src.parallel_dev_mcp.{layer} import {tool}")
                print(f"  ✅ {tool}")
            except ImportError as e:
                print(f"  ❌ {tool}: {str(e)}")
            except Exception as e:
                print(f"  ⚠️ {tool}: {str(e)}")

diagnose_mcp_imports()
```

**解决方案**:
```bash
# 重新安装项目
uv sync --reinstall

# 检查PYTHONPATH
echo $PYTHONPATH

# 添加项目到PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# 开发模式安装
uv pip install -e .
```

### Q14: MCP服务器连接失败

**问题**: Claude Code无法连接到MCP服务器

**检查MCP配置**:
```json
{
  "mcpServers": {
    "parallel-dev-mcp": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/your-repo/parallel-dev-mcp.git",
        "parallel-dev-mcp"
      ],
      "env": {
        "PROJECT_ID": "YOUR_PROJECT"
      }
    }
  }
}
```

**常见问题和解决方案**:
- **权限问题**: 添加 `"DANGEROUSLY_SKIP_PERMISSIONS": "true"`
- **网络问题**: 检查Git仓库访问权限
- **路径问题**: 使用绝对路径而非相对路径
- **环境变量**: 确保PROJECT_ID设置正确

## 🎣 Hooks配置问题

### Q15: Hooks兼容性检查失败

**问题**: `hooks_compatibility_check()` 显示不兼容

**诊断**:
```python
def diagnose_hooks_compatibility():
    print("🎣 Hooks兼容性诊断...")

    # 运行兼容性检查
    compat_report = hooks_compatibility_check()

    print(f"整体兼容性: {compat_report['overall_compatibility']}")

    # 显示详细问题
    for result in compat_report['check_results']:
        if result['status'] in ['incompatible', 'missing', 'warning']:
            print(f"❌ {result['check_name']}: {result['message']}")

    # 显示修复建议
    if compat_report.get('recommendations'):
        print("\n🔧 修复建议:")
        for rec in compat_report['recommendations']:
            print(f"  - {rec}")

diagnose_hooks_compatibility()
```

**常见解决方案**:
```bash
# 设置脚本权限
chmod +x examples/hooks/*.sh

# 检查文件存在性
ls -la examples/hooks/

# 安装缺失的Python依赖
pip install requests flask

# 修复环境变量
export PROJECT_PREFIX="parallel"
export WEB_PORT="8080"
```

### Q16: 智能会话识别失败

**问题**: hooks无法正确识别会话类型

**检查会话命名**:
```bash
# 正确的命名格式
parallel_PROJECT_task_master      # 主会话
parallel_PROJECT_task_child_TASK  # 子会话

# 错误的命名格式
project_task_master              # 缺少parallel前缀
parallel_project_task_master     # 项目名小写
parallel_PROJECT_master          # 缺少task部分
```

**调试智能识别**:
```python
# 手动测试会话名称解析
def test_session_parsing(session_name):
    import re

    # 主会话模式
    master_pattern = r"parallel_([A-Z_]+)_task_master"
    # 子会话模式
    child_pattern = r"parallel_([A-Z_]+)_task_child_([A-Z_]+)"

    master_match = re.match(master_pattern, session_name)
    child_match = re.match(child_pattern, session_name)

    if master_match:
        project_id = master_match.group(1)
        print(f"✅ 主会话: 项目={project_id}")
    elif child_match:
        project_id = child_match.group(1)
        task_id = child_match.group(2)
        print(f"✅ 子会话: 项目={project_id}, 任务={task_id}")
    else:
        print(f"❌ 无法识别会话类型: {session_name}")

# 测试示例
test_session_parsing("parallel_ECOMMERCE_task_master")
test_session_parsing("parallel_ECOMMERCE_task_child_AUTH")
test_session_parsing("invalid_session_name")
```

## 🚨 常见错误信息解决

### ImportError: No module named 'parallel_dev_mcp'

**解决方案**:
```bash
# 安装项目包
uv pip install -e .

# 或添加到PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

### FileNotFoundError: [Errno 2] No such file or directory: 'tmux'

**解决方案**:
```bash
# 安装tmux
brew install tmux  # macOS
sudo apt install tmux  # Ubuntu
```

### PermissionError: [Errno 13] Permission denied

**解决方案**:
```bash
# 修复文件权限
chmod +x scripts/*.py
chmod +x examples/hooks/*.sh

# 或使用python直接运行
python scripts/health_check.py
```

### TimeoutError: Command timed out

**解决方案**:
```python
# 增加超时时间或检查系统负载
performance = get_performance_metrics()
if performance.get('cpu_percent', 0) > 80:
    print("系统负载过高，请稍后重试")
```

## 🛠️ 自助诊断脚本

### 完整自助诊断脚本

创建 `scripts/self_diagnosis.py`:

```python
#!/usr/bin/env python3
"""
完整自助诊断脚本
"""

import sys
import subprocess
import shutil
from pathlib import Path

def run_comprehensive_diagnosis():
    """运行完整的自助诊断"""

    print("🔍 开始自助诊断...")

    issues = []
    warnings = []

    # 1. Python环境检查
    python_version = sys.version_info
    if python_version < (3, 9):
        issues.append(f"Python版本过低: {python_version.major}.{python_version.minor}")
    elif python_version < (3, 10):
        warnings.append(f"Python版本较低: {python_version.major}.{python_version.minor}")

    # 2. 必要工具检查
    required_tools = ['tmux', 'git']
    for tool in required_tools:
        if not shutil.which(tool):
            issues.append(f"缺少必要工具: {tool}")

    # 3. 项目结构检查
    project_root = Path(__file__).parent.parent
    required_dirs = ['src/parallel_dev_mcp', 'examples/hooks', 'scripts']
    for dir_name in required_dirs:
        if not (project_root / dir_name).exists():
            issues.append(f"缺少目录: {dir_name}")

    # 4. Python包检查
    try:
        import psutil
    except ImportError:
        issues.append("缺少psutil包")

    try:
        import pydantic
    except ImportError:
        issues.append("缺少pydantic包")

    # 5. 环境变量检查
    import os
    critical_vars = ['USER', 'HOME', 'PATH']
    for var in critical_vars:
        if not os.environ.get(var):
            issues.append(f"缺少环境变量: {var}")

    # 6. 生成报告
    print("\n📋 诊断报告:")

    if not issues and not warnings:
        print("✅ 系统健康，未发现问题")
        return True

    if issues:
        print("❌ 发现严重问题:")
        for issue in issues:
            print(f"  - {issue}")

    if warnings:
        print("⚠️ 发现警告:")
        for warning in warnings:
            print(f"  - {warning}")

    # 7. 修复建议
    print("\n🔧 修复建议:")

    if any("Python版本" in issue for issue in issues):
        print("  - 升级Python到3.10+")

    if any("tmux" in issue for issue in issues):
        print("  - 安装tmux: brew install tmux (macOS) 或 apt install tmux (Ubuntu)")

    if any("psutil" in issue or "pydantic" in issue for issue in issues):
        print("  - 安装Python依赖: uv sync 或 pip install psutil pydantic")

    if any("环境变量" in issue for issue in issues):
        print("  - 检查shell配置文件 (~/.bashrc, ~/.zshrc)")

    return len(issues) == 0

if __name__ == "__main__":
    success = run_comprehensive_diagnosis()
    sys.exit(0 if success else 1)
```

### 快速修复脚本

创建 `scripts/quick_fix.sh`:

```bash
#!/bin/bash
# 快速修复常见问题

echo "🔧 快速修复脚本..."

# 设置脚本权限
echo "设置脚本权限..."
chmod +x scripts/*.py
chmod +x examples/hooks/*.sh

# 检查并安装依赖
echo "检查Python依赖..."
if command -v uv &> /dev/null; then
    uv sync
else
    pip install psutil pydantic requests flask
fi

# 检查tmux
if ! command -v tmux &> /dev/null; then
    echo "⚠️ tmux未安装，请手动安装:"
    echo "  macOS: brew install tmux"
    echo "  Ubuntu: sudo apt install tmux"
else
    echo "✅ tmux已安装"
fi

# 验证修复结果
echo "验证修复结果..."
python scripts/self_diagnosis.py

echo "✅ 快速修复完成"
```

## 📞 获取帮助

如果上述解决方案都无法解决你的问题，可以：

1. **运行完整诊断**: `python scripts/self_diagnosis.py`
2. **查看详细日志**: 在出错的函数中添加详细的日志输出
3. **检查系统资源**: 确保CPU、内存、磁盘空间充足
4. **重启相关服务**: 重启tmux、清理缓存等
5. **创建最小化测试**: 创建最简单的测试用例来复现问题

### 问题报告模板

```
## 问题描述
[详细描述遇到的问题]

## 环境信息
- 操作系统: [macOS/Linux/Windows]
- Python版本: [运行 python --version]
- 项目版本: [git commit hash]
- 依赖版本: [运行 pip freeze | grep -E "(fastmcp|psutil|pydantic)"]

## 复现步骤
1. [第一步]
2. [第二步]
3. [第三步]

## 错误信息
```
[粘贴完整的错误信息和堆栈跟踪]
```

## 诊断结果
```
[运行 python scripts/self_diagnosis.py 的输出]
```

## 尝试的解决方案
- [已经尝试的解决方案1]
- [已经尝试的解决方案2]
```

通过这个详细的故障排除指南，你应该能够解决绝大多数使用过程中遇到的问题。记住，最重要的是系统化地诊断问题，而不是随意尝试各种解决方案。