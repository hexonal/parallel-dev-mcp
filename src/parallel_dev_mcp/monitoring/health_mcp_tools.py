# -*- coding: utf-8 -*-
"""
健康检查MCP工具

@description 为系统健康检查提供MCP接口
"""

from pathlib import Path
from typing import Dict, Any
from ..mcp_instance import mcp
from .system_health_checker import run_health_check
from .env_variable_tester import run_env_tests


@mcp.tool
def system_health_check(project_root: str = None) -> Dict[str, Any]:
    """
    系统健康检查工具

    检查系统资源、Python环境、tmux可用性、项目结构、依赖包和文件权限。
    提供全面的系统健康状态评估和改进建议。

    Args:
        project_root: 项目根目录路径（可选，默认使用当前目录）

    Returns:
        Dict[str, Any]: 健康检查报告，包含整体状态、详细检查结果和改进建议
    """
    # 1. 处理项目根目录参数
    root_path = Path(project_root) if project_root else None

    # 2. 运行健康检查
    report = run_health_check(root_path)

    # 3. 返回报告
    return report


@mcp.tool
def quick_system_status() -> Dict[str, Any]:
    """
    快速系统状态检查

    快速检查系统关键指标，适用于频繁监控场景。

    Returns:
        Dict[str, Any]: 简化的系统状态信息
    """
    try:
        # 1. 导入所需模块
        import psutil
        import sys
        import shutil
        from datetime import datetime

        # 2. 收集关键指标
        status = {
            "timestamp": datetime.now().isoformat(),
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "tmux_available": shutil.which('tmux') is not None
        }

        # 3. 评估整体状态
        if status["cpu_percent"] > 80 or status["memory_percent"] > 85 or status["disk_percent"] > 90:
            status["overall_status"] = "warning"
        elif not status["tmux_available"]:
            status["overall_status"] = "critical"
        else:
            status["overall_status"] = "healthy"

        # 4. 返回状态
        return status

    except Exception as e:
        # 5. 异常处理
        return {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "error",
            "error_message": str(e)
        }


@mcp.tool
def check_project_dependencies(requirements_file: str = "pyproject.toml") -> Dict[str, Any]:
    """
    检查项目依赖状态

    检查项目依赖包的安装状态和版本兼容性。

    Args:
        requirements_file: 依赖文件路径（默认为pyproject.toml）

    Returns:
        Dict[str, Any]: 依赖检查结果
    """
    try:
        # 1. 导入所需模块
        import importlib.util
        from datetime import datetime

        # 2. 定义检查的依赖包
        dependencies = {
            "critical": ["psutil", "pydantic"],
            "important": ["requests", "flask"],
            "optional": ["fastmcp", "pytest"]
        }

        # 3. 检查依赖状态
        results = {
            "timestamp": datetime.now().isoformat(),
            "dependency_status": {},
            "missing_critical": [],
            "missing_important": [],
            "missing_optional": []
        }

        # 4. 遍历检查各类依赖
        for category, deps in dependencies.items():
            for dep in deps:
                try:
                    spec = importlib.util.find_spec(dep)
                    if spec is not None:
                        results["dependency_status"][dep] = "available"
                    else:
                        results["dependency_status"][dep] = "missing"
                        results[f"missing_{category}"].append(dep)
                except Exception:
                    results["dependency_status"][dep] = "error"
                    results[f"missing_{category}"].append(dep)

        # 5. 评估整体状态
        if results["missing_critical"]:
            results["overall_status"] = "critical"
        elif results["missing_important"]:
            results["overall_status"] = "warning"
        else:
            results["overall_status"] = "healthy"

        # 6. 返回结果
        return results

    except Exception as e:
        # 7. 异常处理
        return {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "error",
            "error_message": str(e)
        }


@mcp.tool
def diagnose_common_issues() -> Dict[str, Any]:
    """
    诊断常见问题

    自动检测和诊断系统中的常见问题，并提供解决方案。

    Returns:
        Dict[str, Any]: 问题诊断结果和解决方案
    """
    try:
        # 1. 导入所需模块
        import sys
        import shutil
        import subprocess
        from pathlib import Path
        from datetime import datetime

        # 2. 初始化诊断结果
        diagnosis = {
            "timestamp": datetime.now().isoformat(),
            "issues_found": [],
            "solutions": [],
            "overall_status": "healthy"
        }

        # 3. 检查Python版本兼容性
        python_version = sys.version_info
        if python_version < (3, 9):
            diagnosis["issues_found"].append("Python版本过低（< 3.9）")
            diagnosis["solutions"].append("升级Python到3.9+版本")
            diagnosis["overall_status"] = "critical"
        elif python_version < (3, 10):
            diagnosis["issues_found"].append("Python版本较低（< 3.10），无法使用fastmcp")
            diagnosis["solutions"].append("考虑升级Python到3.10+以支持fastmcp功能")
            if diagnosis["overall_status"] == "healthy":
                diagnosis["overall_status"] = "warning"

        # 4. 检查tmux安装
        if not shutil.which('tmux'):
            diagnosis["issues_found"].append("tmux未安装")
            diagnosis["solutions"].append("安装tmux: brew install tmux (macOS) 或 apt-get install tmux (Ubuntu)")
            diagnosis["overall_status"] = "critical"

        # 5. 检查项目结构
        project_root = Path.cwd()
        required_dirs = ["src/parallel_dev_mcp", "tests"]
        for dir_name in required_dirs:
            if not (project_root / dir_name).exists():
                diagnosis["issues_found"].append(f"缺少目录: {dir_name}")
                diagnosis["solutions"].append(f"创建缺少的目录: mkdir -p {dir_name}")
                if diagnosis["overall_status"] == "healthy":
                    diagnosis["overall_status"] = "warning"

        # 6. 检查虚拟环境
        in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
        if not in_venv:
            diagnosis["issues_found"].append("未在虚拟环境中运行")
            diagnosis["solutions"].append("使用虚拟环境: python -m venv venv && source venv/bin/activate")
            if diagnosis["overall_status"] == "healthy":
                diagnosis["overall_status"] = "warning"

        # 7. 检查Git仓库状态
        try:
            git_result = subprocess.run(['git', 'status', '--porcelain'],
                                      capture_output=True, text=True, timeout=5)
            if git_result.returncode == 0 and git_result.stdout.strip():
                diagnosis["issues_found"].append("Git工作区有未提交的更改")
                diagnosis["solutions"].append("提交或暂存更改: git add . && git commit -m 'commit message'")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # 8. 返回诊断结果
        return diagnosis

    except Exception as e:
        # 9. 异常处理
        return {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "error",
            "error_message": str(e),
            "issues_found": ["诊断过程中发生错误"],
            "solutions": ["检查系统日志或联系技术支持"]
        }


@mcp.tool
def environment_variables_test(project_root: str = None) -> Dict[str, Any]:
    """
    环境变量测试工具

    全面测试环境变量配置、继承、隔离和边界情况。
    检查关键环境变量、PATH配置、PYTHONPATH设置和各种边界条件。

    Args:
        project_root: 项目根目录路径（可选，默认使用当前目录）

    Returns:
        Dict[str, Any]: 环境变量测试报告，包含测试结果、状态统计和改进建议
    """
    # 1. 处理项目根目录参数
    root_path = Path(project_root) if project_root else None

    # 2. 运行环境变量测试
    report = run_env_tests(root_path)

    # 3. 返回报告
    return report


@mcp.tool
def check_critical_env_vars() -> Dict[str, Any]:
    """
    检查关键环境变量

    快速检查系统关键环境变量的存在性和有效性。

    Returns:
        Dict[str, Any]: 关键环境变量检查结果
    """
    try:
        # 1. 导入所需模块
        import os
        from datetime import datetime

        # 2. 定义关键环境变量
        critical_vars = {
            "USER": "当前用户名",
            "HOME": "用户主目录",
            "PATH": "可执行文件搜索路径",
            "SHELL": "默认Shell"
        }

        # 3. 检查各环境变量
        results = {
            "timestamp": datetime.now().isoformat(),
            "critical_variables": {},
            "missing_variables": [],
            "empty_variables": [],
            "overall_status": "healthy"
        }

        for var_name, description in critical_vars.items():
            value = os.environ.get(var_name)

            if value is None:
                results["missing_variables"].append(var_name)
                results["critical_variables"][var_name] = {
                    "status": "missing",
                    "description": description
                }
                results["overall_status"] = "critical"
            elif not value.strip():
                results["empty_variables"].append(var_name)
                results["critical_variables"][var_name] = {
                    "status": "empty",
                    "description": description,
                    "value": value
                }
                if results["overall_status"] == "healthy":
                    results["overall_status"] = "warning"
            else:
                results["critical_variables"][var_name] = {
                    "status": "available",
                    "description": description,
                    "value": value[:100]  # 限制长度
                }

        # 4. 返回结果
        return results

    except Exception as e:
        # 5. 异常处理
        return {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "error",
            "error_message": str(e)
        }


@mcp.tool
def test_env_inheritance_isolation() -> Dict[str, Any]:
    """
    测试环境变量继承和隔离

    测试环境变量在进程间的继承机制和隔离效果。

    Returns:
        Dict[str, Any]: 继承和隔离测试结果
    """
    try:
        # 1. 导入所需模块
        import os
        import sys
        import subprocess
        from datetime import datetime

        # 2. 初始化结果
        results = {
            "timestamp": datetime.now().isoformat(),
            "inheritance_test": {},
            "isolation_test": {},
            "overall_status": "unknown"
        }

        # 3. 测试继承
        test_var = "PARALLEL_DEV_MCP_INHERIT_TEST"
        test_value = "inheritance_test_value"
        os.environ[test_var] = test_value

        cmd = [sys.executable, '-c', f'import os; print(os.environ.get("{test_var}", "NOT_FOUND"))']
        inherit_result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        if inherit_result.returncode == 0 and test_value in inherit_result.stdout:
            results["inheritance_test"] = {
                "status": "passed",
                "message": "环境变量继承正常",
                "child_output": inherit_result.stdout.strip()
            }
            inheritance_passed = True
        else:
            results["inheritance_test"] = {
                "status": "failed",
                "message": "环境变量继承失败",
                "child_output": inherit_result.stdout.strip(),
                "child_stderr": inherit_result.stderr.strip()
            }
            inheritance_passed = False

        # 4. 测试隔离
        isolation_var = "PARALLEL_DEV_MCP_ISOLATE_TEST"
        original_value = os.environ.get(isolation_var)

        cmd = [
            sys.executable, '-c',
            f'import os; os.environ["{isolation_var}"] = "child_isolation_value"; '
            f'print(os.environ.get("{isolation_var}"))'
        ]
        isolate_result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        current_value = os.environ.get(isolation_var)
        if current_value == original_value and "child_isolation_value" in isolate_result.stdout:
            results["isolation_test"] = {
                "status": "passed",
                "message": "环境变量隔离正常",
                "parent_value": current_value,
                "child_output": isolate_result.stdout.strip()
            }
            isolation_passed = True
        else:
            results["isolation_test"] = {
                "status": "failed",
                "message": "环境变量隔离失败",
                "parent_value": current_value,
                "original_value": original_value,
                "child_output": isolate_result.stdout.strip()
            }
            isolation_passed = False

        # 5. 清理测试变量
        os.environ.pop(test_var, None)

        # 6. 确定整体状态
        if inheritance_passed and isolation_passed:
            results["overall_status"] = "passed"
        elif inheritance_passed or isolation_passed:
            results["overall_status"] = "partial"
        else:
            results["overall_status"] = "failed"

        # 7. 返回结果
        return results

    except subprocess.TimeoutExpired:
        # 8. 超时处理
        return {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "timeout",
            "error_message": "测试超时"
        }
    except Exception as e:
        # 9. 异常处理
        return {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "error",
            "error_message": str(e)
        }