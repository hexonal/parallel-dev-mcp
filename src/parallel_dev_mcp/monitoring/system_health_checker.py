# -*- coding: utf-8 -*-
"""
系统健康检查工具

@description 提供全面的系统健康检查和诊断功能
"""

import os
import sys
import shutil
import subprocess
import platform
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum, unique

# 尝试导入psutil和pydantic，如果失败则使用基本功能
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    from pydantic import BaseModel, Field
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    # 如果pydantic不可用，创建一个简单的替代
    class BaseModel:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

        def model_dump(self):
            return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

    def Field(**kwargs):
        return None

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@unique
class HealthStatus(Enum):
    """健康状态枚举"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class HealthCheckResult(BaseModel):
    """健康检查结果数据模型"""

    check_name: str = Field(..., description="检查项名称")
    status: HealthStatus = Field(..., description="检查状态")
    message: str = Field(..., description="检查消息")
    details: Dict[str, Any] = Field(default_factory=dict, description="详细信息")
    timestamp: datetime = Field(default_factory=datetime.now, description="检查时间")


class SystemHealthChecker:
    """
    系统健康检查器

    提供全面的系统健康检查和诊断功能
    """

    def __init__(self, project_root: Optional[Path] = None) -> None:
        """
        初始化系统健康检查器

        Args:
            project_root: 项目根目录
        """
        # 1. 初始化配置
        self.project_root = project_root or Path.cwd()

        # 2. 初始化检查结果存储
        self.results: List[HealthCheckResult] = []

        # 3. 记录初始化
        logger.info(f"系统健康检查器初始化完成，项目根目录: {self.project_root}")

    def run_all_checks(self) -> Dict[str, Any]:
        """
        运行所有健康检查

        Returns:
            Dict[str, Any]: 完整的健康检查报告
        """
        # 1. 清空之前的结果
        self.results.clear()

        # 2. 执行各项检查
        self._check_system_resources()
        self._check_python_environment()
        self._check_tmux_availability()
        self._check_project_structure()
        self._check_dependencies()
        self._check_file_permissions()

        # 3. 生成汇总报告
        return self._generate_summary_report()

    def _check_system_resources(self) -> None:
        """检查系统资源"""
        if not PSUTIL_AVAILABLE:
            # 1. psutil不可用时的处理
            self.results.append(HealthCheckResult(
                check_name="系统资源",
                status=HealthStatus.WARNING,
                message="psutil未安装，无法检查系统资源详情"
            ))
            return

        try:
            # 2. CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)

            # 3. 内存使用情况
            memory = psutil.virtual_memory()

            # 4. 磁盘使用情况
            disk = psutil.disk_usage('/')

            # 5. 评估资源状态
            status = HealthStatus.HEALTHY
            issues = []

            if cpu_percent > 80:
                status = HealthStatus.WARNING
                issues.append(f"CPU使用率过高: {cpu_percent}%")

            if memory.percent > 85:
                status = HealthStatus.WARNING
                issues.append(f"内存使用率过高: {memory.percent}%")

            if disk.percent > 90:
                status = HealthStatus.CRITICAL
                issues.append(f"磁盘使用率过高: {disk.percent}%")

            # 6. 创建检查结果
            message = "系统资源正常" if status == HealthStatus.HEALTHY else f"发现问题: {', '.join(issues)}"

            result = HealthCheckResult(
                check_name="系统资源",
                status=status,
                message=message,
                details={
                    "cpu_percent": cpu_percent,
                    "memory_total_gb": round(memory.total / (1024**3), 2),
                    "memory_used_percent": memory.percent,
                    "disk_total_gb": round(disk.total / (1024**3), 2),
                    "disk_used_percent": disk.percent,
                    "issues": issues,
                    "psutil_available": True
                }
            )

            self.results.append(result)

        except Exception as e:
            # 7. 异常处理
            self.results.append(HealthCheckResult(
                check_name="系统资源",
                status=HealthStatus.CRITICAL,
                message=f"系统资源检查失败: {str(e)}"
            ))

    def _check_python_environment(self) -> None:
        """检查Python环境"""
        try:
            # 1. Python版本信息
            python_version = sys.version_info
            python_version_str = f"{python_version.major}.{python_version.minor}.{python_version.micro}"

            # 2. 检查Python版本兼容性
            status = HealthStatus.HEALTHY
            issues = []

            if python_version < (3, 9):
                status = HealthStatus.CRITICAL
                issues.append(f"Python版本过低: {python_version_str} (需要 >= 3.9)")
            elif python_version < (3, 10):
                status = HealthStatus.WARNING
                issues.append(f"Python版本较低: {python_version_str} (推荐 >= 3.10 用于fastmcp)")

            # 3. 检查虚拟环境
            in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
            if not in_venv:
                status = HealthStatus.WARNING
                issues.append("未使用虚拟环境")

            # 4. 创建检查结果
            message = "Python环境正常" if status == HealthStatus.HEALTHY else f"发现问题: {', '.join(issues)}"

            result = HealthCheckResult(
                check_name="Python环境",
                status=status,
                message=message,
                details={
                    "python_version": python_version_str,
                    "python_executable": sys.executable,
                    "platform": platform.platform(),
                    "in_virtual_env": in_venv,
                    "issues": issues
                }
            )

            self.results.append(result)

        except Exception as e:
            # 5. 异常处理
            self.results.append(HealthCheckResult(
                check_name="Python环境",
                status=HealthStatus.CRITICAL,
                message=f"Python环境检查失败: {str(e)}"
            ))

    def _check_tmux_availability(self) -> None:
        """检查tmux可用性"""
        try:
            # 1. 检查tmux是否安装
            tmux_path = shutil.which('tmux')

            if not tmux_path:
                result = HealthCheckResult(
                    check_name="tmux可用性",
                    status=HealthStatus.CRITICAL,
                    message="tmux未安装或不在PATH中"
                )
                self.results.append(result)
                return

            # 2. 检查tmux版本
            version_result = subprocess.run(
                ['tmux', '-V'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if version_result.returncode != 0:
                result = HealthCheckResult(
                    check_name="tmux可用性",
                    status=HealthStatus.CRITICAL,
                    message="tmux版本检查失败"
                )
                self.results.append(result)
                return

            # 3. 测试tmux基本功能
            test_session_name = "health_check_test"

            # 创建测试会话
            create_result = subprocess.run(
                ['tmux', 'new-session', '-d', '-s', test_session_name, 'echo "test"'],
                capture_output=True,
                timeout=10
            )

            if create_result.returncode == 0:
                # 清理测试会话
                subprocess.run(['tmux', 'kill-session', '-t', test_session_name],
                             capture_output=True, timeout=5)

                status = HealthStatus.HEALTHY
                message = "tmux功能正常"
            else:
                status = HealthStatus.WARNING
                message = "tmux基本功能测试失败"

            # 4. 创建检查结果
            result = HealthCheckResult(
                check_name="tmux可用性",
                status=status,
                message=message,
                details={
                    "tmux_path": tmux_path,
                    "tmux_version": version_result.stdout.strip(),
                    "basic_test_passed": create_result.returncode == 0
                }
            )

            self.results.append(result)

        except subprocess.TimeoutExpired:
            # 5. 超时处理
            self.results.append(HealthCheckResult(
                check_name="tmux可用性",
                status=HealthStatus.WARNING,
                message="tmux检查超时"
            ))
        except Exception as e:
            # 6. 异常处理
            self.results.append(HealthCheckResult(
                check_name="tmux可用性",
                status=HealthStatus.CRITICAL,
                message=f"tmux检查失败: {str(e)}"
            ))

    def _check_project_structure(self) -> None:
        """检查项目结构"""
        try:
            # 1. 必需的目录和文件
            required_paths = [
                "src/parallel_dev_mcp",
                "src/parallel_dev_mcp/session",
                "src/parallel_dev_mcp/prompts",
                "src/parallel_dev_mcp/tmux",
                "pyproject.toml"
            ]

            # 2. 检查路径存在性
            missing_paths = []
            existing_paths = []

            for path_str in required_paths:
                path = self.project_root / path_str
                if path.exists():
                    existing_paths.append(path_str)
                else:
                    missing_paths.append(path_str)

            # 3. 评估项目结构状态
            if not missing_paths:
                status = HealthStatus.HEALTHY
                message = "项目结构完整"
            elif len(missing_paths) <= 2:
                status = HealthStatus.WARNING
                message = f"部分路径缺失: {', '.join(missing_paths)}"
            else:
                status = HealthStatus.CRITICAL
                message = f"关键路径缺失: {', '.join(missing_paths)}"

            # 4. 创建检查结果
            result = HealthCheckResult(
                check_name="项目结构",
                status=status,
                message=message,
                details={
                    "project_root": str(self.project_root),
                    "existing_paths": existing_paths,
                    "missing_paths": missing_paths,
                    "total_required": len(required_paths),
                    "total_existing": len(existing_paths)
                }
            )

            self.results.append(result)

        except Exception as e:
            # 5. 异常处理
            self.results.append(HealthCheckResult(
                check_name="项目结构",
                status=HealthStatus.CRITICAL,
                message=f"项目结构检查失败: {str(e)}"
            ))

    def _check_dependencies(self) -> None:
        """检查依赖包"""
        try:
            # 1. 关键依赖列表
            critical_deps = ['psutil', 'pydantic']
            optional_deps = ['fastmcp', 'flask', 'requests']

            # 2. 检查依赖导入
            available_deps = []
            missing_critical = []
            missing_optional = []

            for dep in critical_deps:
                try:
                    __import__(dep)
                    available_deps.append(dep)
                except ImportError:
                    missing_critical.append(dep)

            for dep in optional_deps:
                try:
                    __import__(dep)
                    available_deps.append(dep)
                except ImportError:
                    missing_optional.append(dep)

            # 3. 评估依赖状态
            if not missing_critical:
                if not missing_optional:
                    status = HealthStatus.HEALTHY
                    message = "所有依赖可用"
                else:
                    status = HealthStatus.WARNING
                    message = f"可选依赖缺失: {', '.join(missing_optional)}"
            else:
                status = HealthStatus.CRITICAL
                message = f"关键依赖缺失: {', '.join(missing_critical)}"

            # 4. 创建检查结果
            result = HealthCheckResult(
                check_name="依赖包",
                status=status,
                message=message,
                details={
                    "available_dependencies": available_deps,
                    "missing_critical": missing_critical,
                    "missing_optional": missing_optional,
                    "total_checked": len(critical_deps) + len(optional_deps)
                }
            )

            self.results.append(result)

        except Exception as e:
            # 5. 异常处理
            self.results.append(HealthCheckResult(
                check_name="依赖包",
                status=HealthStatus.CRITICAL,
                message=f"依赖检查失败: {str(e)}"
            ))

    def _check_file_permissions(self) -> None:
        """检查文件权限"""
        try:
            # 1. 检查关键目录的权限
            directories_to_check = [
                self.project_root / "src",
                self.project_root / "tests",
                Path.home() / ".local" if (Path.home() / ".local").exists() else None
            ]

            # 2. 过滤掉不存在的目录
            directories_to_check = [d for d in directories_to_check if d and d.exists()]

            # 3. 检查权限
            permission_issues = []
            readable_dirs = []
            writable_dirs = []

            for dir_path in directories_to_check:
                if os.access(dir_path, os.R_OK):
                    readable_dirs.append(str(dir_path))
                else:
                    permission_issues.append(f"无读权限: {dir_path}")

                if os.access(dir_path, os.W_OK):
                    writable_dirs.append(str(dir_path))
                else:
                    permission_issues.append(f"无写权限: {dir_path}")

            # 4. 评估权限状态
            if not permission_issues:
                status = HealthStatus.HEALTHY
                message = "文件权限正常"
            else:
                status = HealthStatus.WARNING
                message = f"权限问题: {', '.join(permission_issues)}"

            # 5. 创建检查结果
            result = HealthCheckResult(
                check_name="文件权限",
                status=status,
                message=message,
                details={
                    "readable_directories": readable_dirs,
                    "writable_directories": writable_dirs,
                    "permission_issues": permission_issues,
                    "checked_directories": [str(d) for d in directories_to_check]
                }
            )

            self.results.append(result)

        except Exception as e:
            # 6. 异常处理
            self.results.append(HealthCheckResult(
                check_name="文件权限",
                status=HealthStatus.CRITICAL,
                message=f"文件权限检查失败: {str(e)}"
            ))

    def _generate_summary_report(self) -> Dict[str, Any]:
        """生成汇总报告"""
        # 1. 统计各状态数量
        status_counts = {status.value: 0 for status in HealthStatus}
        for result in self.results:
            status_counts[result.status.value] += 1

        # 2. 确定整体状态
        if status_counts['critical'] > 0:
            overall_status = HealthStatus.CRITICAL
        elif status_counts['warning'] > 0:
            overall_status = HealthStatus.WARNING
        else:
            overall_status = HealthStatus.HEALTHY

        # 3. 生成报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall_status.value,
            "summary": {
                "total_checks": len(self.results),
                "healthy": status_counts['healthy'],
                "warnings": status_counts['warning'],
                "critical": status_counts['critical'],
                "unknown": status_counts['unknown']
            },
            "details": [result.model_dump() for result in self.results],
            "recommendations": self._generate_recommendations()
        }

        return report

    def _generate_recommendations(self) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # 1. 遍历检查结果生成建议
        for result in self.results:
            if result.status == HealthStatus.CRITICAL:
                if "Python版本过低" in result.message:
                    recommendations.append("升级Python到3.10+以支持fastmcp")
                elif "tmux未安装" in result.message:
                    recommendations.append("安装tmux: brew install tmux (macOS) 或 apt-get install tmux (Ubuntu)")
                elif "关键依赖缺失" in result.message:
                    recommendations.append("安装缺失的依赖: uv sync 或 pip install -r requirements.txt")
                elif "磁盘使用率过高" in result.message:
                    recommendations.append("清理磁盘空间，删除不必要的文件")

            elif result.status == HealthStatus.WARNING:
                if "可选依赖缺失" in result.message:
                    recommendations.append("考虑安装可选依赖以获得完整功能")
                elif "未使用虚拟环境" in result.message:
                    recommendations.append("使用虚拟环境隔离项目依赖")
                elif "CPU使用率过高" in result.message:
                    recommendations.append("检查并关闭不必要的进程")

        # 2. 去重并返回
        return list(set(recommendations))


def run_health_check(project_root: Optional[Path] = None) -> Dict[str, Any]:
    """
    运行系统健康检查

    Args:
        project_root: 项目根目录

    Returns:
        Dict[str, Any]: 健康检查报告
    """
    # 1. 创建健康检查器
    checker = SystemHealthChecker(project_root)

    # 2. 运行检查
    report = checker.run_all_checks()

    # 3. 记录日志
    logger.info(f"系统健康检查完成，整体状态: {report['overall_status']}")

    # 4. 返回报告
    return report


if __name__ == "__main__":
    # 运行健康检查
    report = run_health_check()
    print(f"系统健康状态: {report['overall_status']}")
    print(f"检查项目数: {report['summary']['total_checks']}")
    print(f"健康项目: {report['summary']['healthy']}")
    print(f"警告项目: {report['summary']['warnings']}")
    print(f"严重项目: {report['summary']['critical']}")