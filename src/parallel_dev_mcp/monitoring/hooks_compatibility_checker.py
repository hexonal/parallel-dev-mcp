# -*- coding: utf-8 -*-
"""
Hooks兼容性检查器

@description 检查examples/hooks/目录中文件的兼容性和功能完整性
"""

import os
import sys
import subprocess
import shutil
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from enum import Enum, unique

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@unique
class CompatibilityStatus(Enum):
    """兼容性状态枚举"""
    COMPATIBLE = "compatible"
    WARNING = "warning"
    INCOMPATIBLE = "incompatible"
    MISSING = "missing"
    ERROR = "error"


class HookCompatibilityResult:
    """Hooks兼容性检查结果"""

    def __init__(self, check_name: str, status: CompatibilityStatus, message: str, details: Dict[str, Any] = None):
        """
        初始化检查结果

        Args:
            check_name: 检查项名称
            status: 兼容性状态
            message: 检查消息
            details: 详细信息
        """
        # 1. 基础信息
        self.check_name = check_name
        self.status = status
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "check_name": self.check_name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }


class HooksCompatibilityChecker:
    """
    Hooks兼容性检查器

    检查examples/hooks/目录的文件兼容性和功能完整性
    """

    def __init__(self, project_root: Optional[Path] = None) -> None:
        """
        初始化Hooks兼容性检查器

        Args:
            project_root: 项目根目录
        """
        # 1. 初始化配置
        self.project_root = project_root or Path.cwd()
        self.hooks_dir = self.project_root / "examples" / "hooks"
        self.check_results: List[HookCompatibilityResult] = []

        # 2. 定义期望的文件
        self.expected_files = {
            "README.md": "文档说明文件",
            "web_message_sender.py": "Web消息发送器",
            "tmux_web_service.py": "Tmux Web服务",
            "stop_hook.sh": "Stop事件Hook脚本",
            "session_start_hook.sh": "SessionStart事件Hook脚本"
        }

        # 3. 定义Python依赖
        self.python_dependencies = [
            "requests",
            "flask",
            "json",
            "subprocess",
            "uuid"
        ]

        # 4. 记录初始化
        logger.info(f"Hooks兼容性检查器初始化完成，Hooks目录: {self.hooks_dir}")

    def run_all_checks(self) -> Dict[str, Any]:
        """
        运行所有兼容性检查

        Returns:
            Dict[str, Any]: 完整的兼容性检查报告
        """
        # 1. 清空之前的结果
        self.check_results.clear()

        # 2. 执行各项检查
        self._check_hooks_directory()
        self._check_required_files()
        self._check_python_dependencies()
        self._check_script_permissions()
        self._check_script_syntax()
        self._check_environment_variables()
        self._check_external_commands()
        self._check_configuration_compatibility()

        # 3. 生成兼容性报告
        return self._generate_compatibility_report()

    def _check_hooks_directory(self) -> None:
        """检查hooks目录存在性"""
        try:
            if not self.hooks_dir.exists():
                result = HookCompatibilityResult(
                    check_name="Hooks目录",
                    status=CompatibilityStatus.MISSING,
                    message=f"examples/hooks/目录不存在: {self.hooks_dir}",
                    details={"expected_path": str(self.hooks_dir)}
                )
            elif not self.hooks_dir.is_dir():
                result = HookCompatibilityResult(
                    check_name="Hooks目录",
                    status=CompatibilityStatus.INCOMPATIBLE,
                    message=f"examples/hooks/路径存在但不是目录: {self.hooks_dir}",
                    details={"path_type": "file"}
                )
            else:
                # 检查目录权限
                readable = os.access(self.hooks_dir, os.R_OK)
                executable = os.access(self.hooks_dir, os.X_OK)

                if readable and executable:
                    result = HookCompatibilityResult(
                        check_name="Hooks目录",
                        status=CompatibilityStatus.COMPATIBLE,
                        message="examples/hooks/目录存在且可访问",
                        details={
                            "path": str(self.hooks_dir),
                            "readable": readable,
                            "executable": executable
                        }
                    )
                else:
                    result = HookCompatibilityResult(
                        check_name="Hooks目录",
                        status=CompatibilityStatus.WARNING,
                        message="examples/hooks/目录权限不足",
                        details={
                            "readable": readable,
                            "executable": executable
                        }
                    )

            self.check_results.append(result)

        except Exception as e:
            result = HookCompatibilityResult(
                check_name="Hooks目录",
                status=CompatibilityStatus.ERROR,
                message=f"检查Hooks目录时发生错误: {str(e)}"
            )
            self.check_results.append(result)

    def _check_required_files(self) -> None:
        """检查必需文件"""
        for filename, description in self.expected_files.items():
            try:
                file_path = self.hooks_dir / filename

                if not file_path.exists():
                    result = HookCompatibilityResult(
                        check_name=f"文件_{filename}",
                        status=CompatibilityStatus.MISSING,
                        message=f"缺少{description}: {filename}",
                        details={"expected_path": str(file_path)}
                    )
                else:
                    # 检查文件属性
                    file_size = file_path.stat().st_size
                    is_executable = os.access(file_path, os.X_OK)
                    is_readable = os.access(file_path, os.R_OK)

                    # 检查脚本文件权限
                    if filename.endswith('.sh'):
                        if not is_executable:
                            result = HookCompatibilityResult(
                                check_name=f"文件_{filename}",
                                status=CompatibilityStatus.WARNING,
                                message=f"{description}存在但不可执行: {filename}",
                                details={
                                    "path": str(file_path),
                                    "size": file_size,
                                    "executable": is_executable,
                                    "suggestion": f"运行 chmod +x {file_path}"
                                }
                            )
                        else:
                            result = HookCompatibilityResult(
                                check_name=f"文件_{filename}",
                                status=CompatibilityStatus.COMPATIBLE,
                                message=f"{description}存在且可执行: {filename}",
                                details={
                                    "path": str(file_path),
                                    "size": file_size,
                                    "executable": is_executable
                                }
                            )
                    else:
                        # 非脚本文件
                        if file_size == 0:
                            result = HookCompatibilityResult(
                                check_name=f"文件_{filename}",
                                status=CompatibilityStatus.WARNING,
                                message=f"{description}存在但为空: {filename}",
                                details={
                                    "path": str(file_path),
                                    "size": file_size
                                }
                            )
                        else:
                            result = HookCompatibilityResult(
                                check_name=f"文件_{filename}",
                                status=CompatibilityStatus.COMPATIBLE,
                                message=f"{description}存在且有内容: {filename}",
                                details={
                                    "path": str(file_path),
                                    "size": file_size,
                                    "readable": is_readable
                                }
                            )

                self.check_results.append(result)

            except Exception as e:
                result = HookCompatibilityResult(
                    check_name=f"文件_{filename}",
                    status=CompatibilityStatus.ERROR,
                    message=f"检查文件{filename}时发生错误: {str(e)}"
                )
                self.check_results.append(result)

    def _check_python_dependencies(self) -> None:
        """检查Python依赖"""
        try:
            missing_deps = []
            available_deps = []

            for dep in self.python_dependencies:
                try:
                    if dep in ['json', 'subprocess', 'uuid']:
                        # 标准库模块
                        __import__(dep)
                        available_deps.append(dep)
                    else:
                        # 第三方库
                        __import__(dep)
                        available_deps.append(dep)
                except ImportError:
                    missing_deps.append(dep)

            if not missing_deps:
                result = HookCompatibilityResult(
                    check_name="Python依赖",
                    status=CompatibilityStatus.COMPATIBLE,
                    message="所有Python依赖都可用",
                    details={
                        "available_dependencies": available_deps,
                        "total_checked": len(self.python_dependencies)
                    }
                )
            elif len(missing_deps) <= 2:
                result = HookCompatibilityResult(
                    check_name="Python依赖",
                    status=CompatibilityStatus.WARNING,
                    message=f"部分Python依赖缺失: {', '.join(missing_deps)}",
                    details={
                        "missing_dependencies": missing_deps,
                        "available_dependencies": available_deps,
                        "install_command": f"pip install {' '.join(missing_deps)}"
                    }
                )
            else:
                result = HookCompatibilityResult(
                    check_name="Python依赖",
                    status=CompatibilityStatus.INCOMPATIBLE,
                    message=f"大量Python依赖缺失: {', '.join(missing_deps)}",
                    details={
                        "missing_dependencies": missing_deps,
                        "available_dependencies": available_deps,
                        "install_command": f"pip install {' '.join(missing_deps)}"
                    }
                )

            self.check_results.append(result)

        except Exception as e:
            result = HookCompatibilityResult(
                check_name="Python依赖",
                status=CompatibilityStatus.ERROR,
                message=f"检查Python依赖时发生错误: {str(e)}"
            )
            self.check_results.append(result)

    def _check_script_permissions(self) -> None:
        """检查脚本权限"""
        try:
            shell_scripts = [f for f in self.expected_files.keys() if f.endswith('.sh')]
            permission_issues = []
            correct_permissions = []

            for script_name in shell_scripts:
                script_path = self.hooks_dir / script_name

                if script_path.exists():
                    is_executable = os.access(script_path, os.X_OK)
                    is_readable = os.access(script_path, os.R_OK)

                    if not is_executable:
                        permission_issues.append({
                            "script": script_name,
                            "issue": "不可执行",
                            "fix": f"chmod +x {script_path}"
                        })
                    elif not is_readable:
                        permission_issues.append({
                            "script": script_name,
                            "issue": "不可读",
                            "fix": f"chmod +r {script_path}"
                        })
                    else:
                        correct_permissions.append(script_name)

            if not permission_issues:
                result = HookCompatibilityResult(
                    check_name="脚本权限",
                    status=CompatibilityStatus.COMPATIBLE,
                    message="所有脚本权限正确",
                    details={
                        "scripts_checked": len(shell_scripts),
                        "correct_permissions": correct_permissions
                    }
                )
            else:
                result = HookCompatibilityResult(
                    check_name="脚本权限",
                    status=CompatibilityStatus.WARNING,
                    message=f"发现{len(permission_issues)}个权限问题",
                    details={
                        "permission_issues": permission_issues,
                        "correct_permissions": correct_permissions,
                        "fix_all_command": f"chmod +x {self.hooks_dir}/*.sh"
                    }
                )

            self.check_results.append(result)

        except Exception as e:
            result = HookCompatibilityResult(
                check_name="脚本权限",
                status=CompatibilityStatus.ERROR,
                message=f"检查脚本权限时发生错误: {str(e)}"
            )
            self.check_results.append(result)

    def _check_script_syntax(self) -> None:
        """检查脚本语法"""
        try:
            syntax_results = []

            # 检查Python脚本语法
            python_scripts = [f for f in self.expected_files.keys() if f.endswith('.py')]
            for script_name in python_scripts:
                script_path = self.hooks_dir / script_name

                if script_path.exists():
                    syntax_ok, error_msg = self._check_python_syntax(script_path)
                    syntax_results.append({
                        "script": script_name,
                        "type": "python",
                        "syntax_ok": syntax_ok,
                        "error": error_msg
                    })

            # 检查Shell脚本语法
            shell_scripts = [f for f in self.expected_files.keys() if f.endswith('.sh')]
            for script_name in shell_scripts:
                script_path = self.hooks_dir / script_name

                if script_path.exists():
                    syntax_ok, error_msg = self._check_shell_syntax(script_path)
                    syntax_results.append({
                        "script": script_name,
                        "type": "shell",
                        "syntax_ok": syntax_ok,
                        "error": error_msg
                    })

            # 评估语法检查结果
            syntax_errors = [r for r in syntax_results if not r["syntax_ok"]]

            if not syntax_errors:
                result = HookCompatibilityResult(
                    check_name="脚本语法",
                    status=CompatibilityStatus.COMPATIBLE,
                    message="所有脚本语法正确",
                    details={
                        "scripts_checked": len(syntax_results),
                        "syntax_results": syntax_results
                    }
                )
            else:
                result = HookCompatibilityResult(
                    check_name="脚本语法",
                    status=CompatibilityStatus.INCOMPATIBLE,
                    message=f"发现{len(syntax_errors)}个语法错误",
                    details={
                        "syntax_errors": syntax_errors,
                        "all_results": syntax_results
                    }
                )

            self.check_results.append(result)

        except Exception as e:
            result = HookCompatibilityResult(
                check_name="脚本语法",
                status=CompatibilityStatus.ERROR,
                message=f"检查脚本语法时发生错误: {str(e)}"
            )
            self.check_results.append(result)

    def _check_environment_variables(self) -> None:
        """检查环境变量配置"""
        try:
            required_vars = {
                "PROJECT_PREFIX": "项目前缀",
                "WEB_PORT": "Web服务端口"
            }

            optional_vars = {
                "CLAUDE_SESSION_ID": "Claude会话ID",
                "TMUX": "Tmux会话信息",
                "WEB_SERVICE_URL": "Web服务URL"
            }

            var_status = {}
            missing_required = []
            missing_optional = []

            # 检查必需变量
            for var_name, description in required_vars.items():
                value = os.environ.get(var_name)
                if value:
                    var_status[var_name] = {"status": "set", "value": value[:50], "description": description}
                else:
                    var_status[var_name] = {"status": "missing", "description": description}
                    missing_required.append(var_name)

            # 检查可选变量
            for var_name, description in optional_vars.items():
                value = os.environ.get(var_name)
                if value:
                    var_status[var_name] = {"status": "set", "value": value[:50], "description": description}
                else:
                    var_status[var_name] = {"status": "not_set", "description": description}
                    missing_optional.append(var_name)

            # 评估环境变量状态
            if not missing_required:
                if len(missing_optional) <= len(optional_vars) // 2:
                    status = CompatibilityStatus.COMPATIBLE
                    message = "环境变量配置完整"
                else:
                    status = CompatibilityStatus.WARNING
                    message = f"部分可选环境变量未设置: {', '.join(missing_optional)}"
            else:
                status = CompatibilityStatus.WARNING
                message = f"缺少必需环境变量: {', '.join(missing_required)}"

            result = HookCompatibilityResult(
                check_name="环境变量",
                status=status,
                message=message,
                details={
                    "variable_status": var_status,
                    "missing_required": missing_required,
                    "missing_optional": missing_optional,
                    "setup_commands": [
                        f"export {var}=value" for var in missing_required
                    ]
                }
            )

            self.check_results.append(result)

        except Exception as e:
            result = HookCompatibilityResult(
                check_name="环境变量",
                status=CompatibilityStatus.ERROR,
                message=f"检查环境变量时发生错误: {str(e)}"
            )
            self.check_results.append(result)

    def _check_external_commands(self) -> None:
        """检查外部命令可用性"""
        try:
            required_commands = {
                "python3": "Python 3解释器",
                "tmux": "终端多路复用器",
                "bash": "Bash Shell"
            }

            optional_commands = {
                "curl": "HTTP客户端",
                "jq": "JSON处理工具",
                "date": "日期时间工具"
            }

            command_status = {}
            missing_required = []
            missing_optional = []

            # 检查必需命令
            for cmd, description in required_commands.items():
                if shutil.which(cmd):
                    # 获取版本信息
                    try:
                        if cmd == "python3":
                            version_result = subprocess.run([cmd, "--version"],
                                                          capture_output=True, text=True, timeout=5)
                        elif cmd == "tmux":
                            version_result = subprocess.run([cmd, "-V"],
                                                          capture_output=True, text=True, timeout=5)
                        else:
                            version_result = subprocess.run([cmd, "--version"],
                                                          capture_output=True, text=True, timeout=5)

                        version = version_result.stdout.strip() if version_result.returncode == 0 else "unknown"
                    except:
                        version = "unknown"

                    command_status[cmd] = {
                        "status": "available",
                        "path": shutil.which(cmd),
                        "version": version[:100],
                        "description": description
                    }
                else:
                    command_status[cmd] = {"status": "missing", "description": description}
                    missing_required.append(cmd)

            # 检查可选命令
            for cmd, description in optional_commands.items():
                if shutil.which(cmd):
                    command_status[cmd] = {
                        "status": "available",
                        "path": shutil.which(cmd),
                        "description": description
                    }
                else:
                    command_status[cmd] = {"status": "missing", "description": description}
                    missing_optional.append(cmd)

            # 评估命令可用性
            if not missing_required:
                status = CompatibilityStatus.COMPATIBLE
                message = "所有必需命令都可用"
            else:
                status = CompatibilityStatus.INCOMPATIBLE
                message = f"缺少必需命令: {', '.join(missing_required)}"

            result = HookCompatibilityResult(
                check_name="外部命令",
                status=status,
                message=message,
                details={
                    "command_status": command_status,
                    "missing_required": missing_required,
                    "missing_optional": missing_optional
                }
            )

            self.check_results.append(result)

        except Exception as e:
            result = HookCompatibilityResult(
                check_name="外部命令",
                status=CompatibilityStatus.ERROR,
                message=f"检查外部命令时发生错误: {str(e)}"
            )
            self.check_results.append(result)

    def _check_configuration_compatibility(self) -> None:
        """检查配置兼容性"""
        try:
            # 检查Claude Code配置文件
            claude_settings_path = self.project_root / ".claude" / "settings.json"
            claude_config_compatible = False
            config_details = {}

            if claude_settings_path.exists():
                try:
                    with open(claude_settings_path, 'r', encoding='utf-8') as f:
                        settings = json.load(f)

                    hooks_config = settings.get('hooks', {})
                    has_stop_hook = 'Stop' in hooks_config
                    has_session_start_hook = 'SessionStart' in hooks_config

                    claude_config_compatible = has_stop_hook or has_session_start_hook
                    config_details = {
                        "settings_file_exists": True,
                        "has_hooks_config": bool(hooks_config),
                        "has_stop_hook": has_stop_hook,
                        "has_session_start_hook": has_session_start_hook,
                        "hooks_count": len(hooks_config)
                    }
                except Exception as e:
                    config_details = {
                        "settings_file_exists": True,
                        "parse_error": str(e)
                    }
            else:
                config_details = {"settings_file_exists": False}

            # 评估配置兼容性
            if claude_config_compatible:
                status = CompatibilityStatus.COMPATIBLE
                message = "Claude Code配置兼容"
            elif claude_settings_path.exists():
                status = CompatibilityStatus.WARNING
                message = "Claude Code配置文件存在但未配置Hooks"
            else:
                status = CompatibilityStatus.WARNING
                message = "Claude Code配置文件不存在"

            result = HookCompatibilityResult(
                check_name="配置兼容性",
                status=status,
                message=message,
                details=config_details
            )

            self.check_results.append(result)

        except Exception as e:
            result = HookCompatibilityResult(
                check_name="配置兼容性",
                status=CompatibilityStatus.ERROR,
                message=f"检查配置兼容性时发生错误: {str(e)}"
            )
            self.check_results.append(result)

    def _check_python_syntax(self, script_path: Path) -> Tuple[bool, Optional[str]]:
        """检查Python脚本语法"""
        try:
            result = subprocess.run([
                sys.executable, '-m', 'py_compile', str(script_path)
            ], capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                return True, None
            else:
                return False, result.stderr.strip()

        except subprocess.TimeoutExpired:
            return False, "语法检查超时"
        except Exception as e:
            return False, f"语法检查错误: {str(e)}"

    def _check_shell_syntax(self, script_path: Path) -> Tuple[bool, Optional[str]]:
        """检查Shell脚本语法"""
        try:
            result = subprocess.run([
                'bash', '-n', str(script_path)
            ], capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                return True, None
            else:
                return False, result.stderr.strip()

        except subprocess.TimeoutExpired:
            return False, "语法检查超时"
        except Exception as e:
            return False, f"语法检查错误: {str(e)}"

    def _generate_compatibility_report(self) -> Dict[str, Any]:
        """生成兼容性报告"""
        # 1. 统计兼容性状态
        status_counts = {status.value: 0 for status in CompatibilityStatus}
        for result in self.check_results:
            status_counts[result.status.value] += 1

        # 2. 确定整体兼容性
        if status_counts['incompatible'] > 0 or status_counts['error'] > 0:
            overall_compatibility = "incompatible"
        elif status_counts['missing'] > 0:
            overall_compatibility = "incomplete"
        elif status_counts['warning'] > 0:
            overall_compatibility = "partial"
        else:
            overall_compatibility = "compatible"

        # 3. 生成报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "overall_compatibility": overall_compatibility,
            "hooks_directory": str(self.hooks_dir),
            "summary": {
                "total_checks": len(self.check_results),
                "compatible": status_counts['compatible'],
                "warnings": status_counts['warning'],
                "incompatible": status_counts['incompatible'],
                "missing": status_counts['missing'],
                "errors": status_counts['error']
            },
            "check_results": [result.to_dict() for result in self.check_results],
            "recommendations": self._generate_recommendations()
        }

        return report

    def _generate_recommendations(self) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # 1. 分析检查结果
        for result in self.check_results:
            if result.status in [CompatibilityStatus.INCOMPATIBLE, CompatibilityStatus.MISSING]:
                if "文件" in result.check_name and "missing" in result.message:
                    recommendations.append(f"创建缺失的文件: {result.check_name}")
                elif "Python依赖" in result.check_name:
                    missing_deps = result.details.get('missing_dependencies', [])
                    if missing_deps:
                        recommendations.append(f"安装Python依赖: pip install {' '.join(missing_deps)}")
                elif "外部命令" in result.check_name:
                    missing_cmds = result.details.get('missing_required', [])
                    for cmd in missing_cmds:
                        if cmd == "tmux":
                            recommendations.append("安装tmux: brew install tmux (macOS) 或 apt-get install tmux (Ubuntu)")
                        elif cmd == "python3":
                            recommendations.append("安装Python 3.9+")
                elif "脚本权限" in result.check_name:
                    recommendations.append("设置脚本可执行权限: chmod +x examples/hooks/*.sh")
                elif "环境变量" in result.check_name:
                    missing_vars = result.details.get('missing_required', [])
                    for var in missing_vars:
                        recommendations.append(f"设置环境变量: export {var}=value")

            elif result.status == CompatibilityStatus.WARNING:
                if "配置兼容性" in result.check_name:
                    recommendations.append("在.claude/settings.json中配置Hooks")

        # 2. 去重并返回
        return list(set(recommendations))


def run_hooks_compatibility_check(project_root: Optional[Path] = None) -> Dict[str, Any]:
    """
    运行Hooks兼容性检查

    Args:
        project_root: 项目根目录

    Returns:
        Dict[str, Any]: 兼容性检查报告
    """
    # 1. 创建检查器
    checker = HooksCompatibilityChecker(project_root)

    # 2. 运行检查
    report = checker.run_all_checks()

    # 3. 记录日志
    logger.info(f"Hooks兼容性检查完成，整体兼容性: {report['overall_compatibility']}")

    # 4. 返回报告
    return report


if __name__ == "__main__":
    # 运行Hooks兼容性检查
    report = run_hooks_compatibility_check()
    print(f"Hooks兼容性: {report['overall_compatibility']}")
    print(f"总检查数: {report['summary']['total_checks']}")
    print(f"兼容: {report['summary']['compatible']}")
    print(f"警告: {report['summary']['warnings']}")
    print(f"不兼容: {report['summary']['incompatible']}")
    print(f"缺失: {report['summary']['missing']}")
    print(f"错误: {report['summary']['errors']}")