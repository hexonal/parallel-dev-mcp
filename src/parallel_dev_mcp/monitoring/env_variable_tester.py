# -*- coding: utf-8 -*-
"""
环境变量测试工具

@description 测试环境变量组合和边界情况
"""

import os
import sys
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from enum import Enum, unique

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@unique
class TestStatus(Enum):
    """测试状态枚举"""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class EnvTestResult:
    """环境变量测试结果"""

    def __init__(self, test_name: str, status: TestStatus, message: str, details: Dict[str, Any] = None):
        """
        初始化测试结果

        Args:
            test_name: 测试名称
            status: 测试状态
            message: 测试消息
            details: 详细信息
        """
        # 1. 基础信息
        self.test_name = test_name
        self.status = status
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "test_name": self.test_name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }


class EnvironmentVariableTester:
    """
    环境变量测试器

    测试各种环境变量组合和边界情况
    """

    def __init__(self, project_root: Optional[Path] = None) -> None:
        """
        初始化环境变量测试器

        Args:
            project_root: 项目根目录
        """
        # 1. 初始化配置
        self.project_root = project_root or Path.cwd()
        self.test_results: List[EnvTestResult] = []

        # 2. 定义关键环境变量
        self.critical_env_vars = {
            "USER": "当前用户名",
            "HOME": "用户主目录",
            "PATH": "可执行文件搜索路径",
            "PYTHONPATH": "Python模块搜索路径"
        }

        self.optional_env_vars = {
            "PROJECT_PREFIX": "项目前缀",
            "TMUX": "Tmux会话信息",
            "TERM": "终端类型",
            "SHELL": "默认Shell"
        }

        # 3. 记录初始化
        logger.info(f"环境变量测试器初始化完成，项目根目录: {self.project_root}")

    def run_all_tests(self) -> Dict[str, Any]:
        """
        运行所有环境变量测试

        Returns:
            Dict[str, Any]: 完整的测试报告
        """
        # 1. 清空之前的结果
        self.test_results.clear()

        # 2. 执行各项测试
        self._test_critical_env_vars()
        self._test_optional_env_vars()
        self._test_env_var_values()
        self._test_path_variables()
        self._test_python_path()
        self._test_env_inheritance()
        self._test_env_isolation()
        self._test_edge_cases()

        # 3. 生成测试报告
        return self._generate_test_report()

    def _test_critical_env_vars(self) -> None:
        """测试关键环境变量"""
        for var_name, description in self.critical_env_vars.items():
            try:
                # 1. 检查环境变量是否存在
                value = os.environ.get(var_name)

                if value is None:
                    result = EnvTestResult(
                        test_name=f"关键环境变量_{var_name}",
                        status=TestStatus.FAILED,
                        message=f"关键环境变量 {var_name} 未设置",
                        details={"variable": var_name, "description": description}
                    )
                elif not value.strip():
                    result = EnvTestResult(
                        test_name=f"关键环境变量_{var_name}",
                        status=TestStatus.FAILED,
                        message=f"关键环境变量 {var_name} 为空",
                        details={"variable": var_name, "description": description, "value": value}
                    )
                else:
                    result = EnvTestResult(
                        test_name=f"关键环境变量_{var_name}",
                        status=TestStatus.PASSED,
                        message=f"关键环境变量 {var_name} 正常",
                        details={"variable": var_name, "description": description, "value": value[:100]}
                    )

                self.test_results.append(result)

            except Exception as e:
                # 2. 异常处理
                result = EnvTestResult(
                    test_name=f"关键环境变量_{var_name}",
                    status=TestStatus.ERROR,
                    message=f"测试关键环境变量 {var_name} 时发生错误: {str(e)}"
                )
                self.test_results.append(result)

    def _test_optional_env_vars(self) -> None:
        """测试可选环境变量"""
        for var_name, description in self.optional_env_vars.items():
            try:
                # 1. 检查可选环境变量
                value = os.environ.get(var_name)

                if value is None:
                    result = EnvTestResult(
                        test_name=f"可选环境变量_{var_name}",
                        status=TestStatus.SKIPPED,
                        message=f"可选环境变量 {var_name} 未设置",
                        details={"variable": var_name, "description": description}
                    )
                else:
                    result = EnvTestResult(
                        test_name=f"可选环境变量_{var_name}",
                        status=TestStatus.PASSED,
                        message=f"可选环境变量 {var_name} 已设置",
                        details={"variable": var_name, "description": description, "value": value[:100]}
                    )

                self.test_results.append(result)

            except Exception as e:
                # 2. 异常处理
                result = EnvTestResult(
                    test_name=f"可选环境变量_{var_name}",
                    status=TestStatus.ERROR,
                    message=f"测试可选环境变量 {var_name} 时发生错误: {str(e)}"
                )
                self.test_results.append(result)

    def _test_env_var_values(self) -> None:
        """测试环境变量值的有效性"""
        tests = [
            ("HOME", self._validate_home_directory),
            ("PATH", self._validate_path_variable),
            ("USER", self._validate_user_variable),
            ("SHELL", self._validate_shell_variable)
        ]

        for var_name, validator in tests:
            try:
                # 1. 获取环境变量值
                value = os.environ.get(var_name)

                if value is None:
                    result = EnvTestResult(
                        test_name=f"环境变量值_{var_name}",
                        status=TestStatus.SKIPPED,
                        message=f"环境变量 {var_name} 未设置，跳过值验证"
                    )
                else:
                    # 2. 验证值
                    is_valid, message, details = validator(value)

                    result = EnvTestResult(
                        test_name=f"环境变量值_{var_name}",
                        status=TestStatus.PASSED if is_valid else TestStatus.FAILED,
                        message=message,
                        details=details
                    )

                self.test_results.append(result)

            except Exception as e:
                # 3. 异常处理
                result = EnvTestResult(
                    test_name=f"环境变量值_{var_name}",
                    status=TestStatus.ERROR,
                    message=f"验证环境变量 {var_name} 值时发生错误: {str(e)}"
                )
                self.test_results.append(result)

    def _test_path_variables(self) -> None:
        """测试PATH相关环境变量"""
        try:
            # 1. 获取PATH
            path_value = os.environ.get('PATH', '')

            # 2. 分析PATH
            path_dirs = path_value.split(os.pathsep) if path_value else []
            existing_dirs = []
            missing_dirs = []

            for path_dir in path_dirs:
                if path_dir and Path(path_dir).exists():
                    existing_dirs.append(path_dir)
                elif path_dir:
                    missing_dirs.append(path_dir)

            # 3. 检查重要可执行文件
            important_executables = ['python', 'python3', 'pip', 'git', 'tmux']
            available_executables = []
            missing_executables = []

            for executable in important_executables:
                import shutil
                if shutil.which(executable):
                    available_executables.append(executable)
                else:
                    missing_executables.append(executable)

            # 4. 评估结果
            if not path_dirs:
                status = TestStatus.FAILED
                message = "PATH环境变量为空"
            elif len(missing_dirs) > len(existing_dirs):
                status = TestStatus.FAILED
                message = f"PATH中大部分目录不存在: {len(missing_dirs)}/{len(path_dirs)}"
            elif missing_executables:
                status = TestStatus.FAILED if 'python' in missing_executables else TestStatus.PASSED
                message = f"部分重要可执行文件不在PATH中: {', '.join(missing_executables)}"
            else:
                status = TestStatus.PASSED
                message = "PATH环境变量配置正常"

            # 5. 创建测试结果
            result = EnvTestResult(
                test_name="PATH环境变量",
                status=status,
                message=message,
                details={
                    "total_directories": len(path_dirs),
                    "existing_directories": len(existing_dirs),
                    "missing_directories": len(missing_dirs),
                    "available_executables": available_executables,
                    "missing_executables": missing_executables,
                    "path_sample": path_dirs[:5]  # 只显示前5个路径
                }
            )

            self.test_results.append(result)

        except Exception as e:
            # 6. 异常处理
            result = EnvTestResult(
                test_name="PATH环境变量",
                status=TestStatus.ERROR,
                message=f"测试PATH环境变量时发生错误: {str(e)}"
            )
            self.test_results.append(result)

    def _test_python_path(self) -> None:
        """测试PYTHONPATH环境变量"""
        try:
            # 1. 获取PYTHONPATH
            pythonpath = os.environ.get('PYTHONPATH', '')

            # 2. 检查Python模块搜索路径
            import sys
            python_paths = sys.path

            # 3. 分析项目相关路径
            project_in_path = any(str(self.project_root) in path for path in python_paths)
            src_in_path = any('src' in path for path in python_paths)

            # 4. 评估结果
            if not pythonpath and not project_in_path:
                status = TestStatus.FAILED
                message = "PYTHONPATH未设置且项目路径不在Python搜索路径中"
            elif project_in_path or src_in_path:
                status = TestStatus.PASSED
                message = "Python模块搜索路径配置正常"
            else:
                status = TestStatus.PASSED
                message = "PYTHONPATH配置正常"

            # 5. 创建测试结果
            result = EnvTestResult(
                test_name="PYTHONPATH环境变量",
                status=status,
                message=message,
                details={
                    "pythonpath": pythonpath[:200] if pythonpath else None,
                    "project_in_path": project_in_path,
                    "src_in_path": src_in_path,
                    "total_python_paths": len(python_paths),
                    "python_paths_sample": python_paths[:3]
                }
            )

            self.test_results.append(result)

        except Exception as e:
            # 6. 异常处理
            result = EnvTestResult(
                test_name="PYTHONPATH环境变量",
                status=TestStatus.ERROR,
                message=f"测试PYTHONPATH环境变量时发生错误: {str(e)}"
            )
            self.test_results.append(result)

    def _test_env_inheritance(self) -> None:
        """测试环境变量继承"""
        try:
            # 1. 创建测试环境变量
            test_var_name = "PARALLEL_DEV_MCP_TEST"
            test_var_value = "test_inheritance_value"

            # 2. 设置环境变量
            os.environ[test_var_name] = test_var_value

            # 3. 启动子进程验证继承
            cmd = [sys.executable, '-c', f'import os; print(os.environ.get("{test_var_name}", "NOT_FOUND"))']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            # 4. 检查结果
            if result.returncode == 0 and test_var_value in result.stdout:
                status = TestStatus.PASSED
                message = "环境变量继承正常"
                details = {"child_output": result.stdout.strip()}
            else:
                status = TestStatus.FAILED
                message = "环境变量继承失败"
                details = {"child_output": result.stdout.strip(), "child_stderr": result.stderr.strip()}

            # 5. 清理测试环境变量
            os.environ.pop(test_var_name, None)

            # 6. 创建测试结果
            test_result = EnvTestResult(
                test_name="环境变量继承",
                status=status,
                message=message,
                details=details
            )

            self.test_results.append(test_result)

        except subprocess.TimeoutExpired:
            # 7. 超时处理
            result = EnvTestResult(
                test_name="环境变量继承",
                status=TestStatus.FAILED,
                message="环境变量继承测试超时"
            )
            self.test_results.append(result)
        except Exception as e:
            # 8. 异常处理
            result = EnvTestResult(
                test_name="环境变量继承",
                status=TestStatus.ERROR,
                message=f"测试环境变量继承时发生错误: {str(e)}"
            )
            self.test_results.append(result)

    def _test_env_isolation(self) -> None:
        """测试环境变量隔离"""
        try:
            # 1. 创建测试环境变量
            test_var_name = "PARALLEL_DEV_MCP_ISOLATION_TEST"
            original_value = os.environ.get(test_var_name)

            # 2. 在子进程中设置环境变量
            cmd = [
                sys.executable, '-c',
                f'import os; os.environ["{test_var_name}"] = "child_value"; '
                f'print(os.environ.get("{test_var_name}"))'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            # 3. 检查父进程中的环境变量
            current_value = os.environ.get(test_var_name)

            # 4. 评估隔离效果
            if current_value == original_value and "child_value" in result.stdout:
                status = TestStatus.PASSED
                message = "环境变量隔离正常"
                details = {
                    "parent_value": current_value,
                    "child_output": result.stdout.strip(),
                    "isolation_preserved": True
                }
            else:
                status = TestStatus.FAILED
                message = "环境变量隔离失败"
                details = {
                    "parent_value": current_value,
                    "original_value": original_value,
                    "child_output": result.stdout.strip(),
                    "isolation_preserved": False
                }

            # 5. 创建测试结果
            test_result = EnvTestResult(
                test_name="环境变量隔离",
                status=status,
                message=message,
                details=details
            )

            self.test_results.append(test_result)

        except subprocess.TimeoutExpired:
            # 6. 超时处理
            result = EnvTestResult(
                test_name="环境变量隔离",
                status=TestStatus.FAILED,
                message="环境变量隔离测试超时"
            )
            self.test_results.append(result)
        except Exception as e:
            # 7. 异常处理
            result = EnvTestResult(
                test_name="环境变量隔离",
                status=TestStatus.ERROR,
                message=f"测试环境变量隔离时发生错误: {str(e)}"
            )
            self.test_results.append(result)

    def _test_edge_cases(self) -> None:
        """测试边界情况"""
        edge_case_tests = [
            ("空值环境变量", self._test_empty_env_vars),
            ("特殊字符环境变量", self._test_special_char_env_vars),
            ("长值环境变量", self._test_long_env_vars),
            ("Unicode环境变量", self._test_unicode_env_vars)
        ]

        for test_name, test_func in edge_case_tests:
            try:
                # 1. 执行边界测试
                test_func()

            except Exception as e:
                # 2. 异常处理
                result = EnvTestResult(
                    test_name=test_name,
                    status=TestStatus.ERROR,
                    message=f"执行{test_name}测试时发生错误: {str(e)}"
                )
                self.test_results.append(result)

    def _test_empty_env_vars(self) -> None:
        """测试空值环境变量"""
        test_var = "PARALLEL_DEV_MCP_EMPTY_TEST"

        try:
            # 1. 设置空值
            os.environ[test_var] = ""

            # 2. 验证空值处理
            value = os.environ.get(test_var)
            is_empty = value == ""

            # 3. 清理
            os.environ.pop(test_var, None)

            # 4. 创建结果
            result = EnvTestResult(
                test_name="空值环境变量",
                status=TestStatus.PASSED if is_empty else TestStatus.FAILED,
                message="空值环境变量处理正常" if is_empty else "空值环境变量处理异常",
                details={"empty_value_preserved": is_empty}
            )

            self.test_results.append(result)

        except Exception as e:
            result = EnvTestResult(
                test_name="空值环境变量",
                status=TestStatus.ERROR,
                message=f"测试空值环境变量时发生错误: {str(e)}"
            )
            self.test_results.append(result)

    def _test_special_char_env_vars(self) -> None:
        """测试特殊字符环境变量"""
        test_var = "PARALLEL_DEV_MCP_SPECIAL_TEST"
        special_value = "test:value;with/special\\chars$and spaces"

        try:
            # 1. 设置特殊字符值
            os.environ[test_var] = special_value

            # 2. 验证特殊字符处理
            retrieved_value = os.environ.get(test_var)
            preserved = retrieved_value == special_value

            # 3. 清理
            os.environ.pop(test_var, None)

            # 4. 创建结果
            result = EnvTestResult(
                test_name="特殊字符环境变量",
                status=TestStatus.PASSED if preserved else TestStatus.FAILED,
                message="特殊字符处理正常" if preserved else "特殊字符处理异常",
                details={
                    "original_value": special_value,
                    "retrieved_value": retrieved_value,
                    "characters_preserved": preserved
                }
            )

            self.test_results.append(result)

        except Exception as e:
            result = EnvTestResult(
                test_name="特殊字符环境变量",
                status=TestStatus.ERROR,
                message=f"测试特殊字符环境变量时发生错误: {str(e)}"
            )
            self.test_results.append(result)

    def _test_long_env_vars(self) -> None:
        """测试长值环境变量"""
        test_var = "PARALLEL_DEV_MCP_LONG_TEST"
        long_value = "x" * 10000  # 10KB的值

        try:
            # 1. 设置长值
            os.environ[test_var] = long_value

            # 2. 验证长值处理
            retrieved_value = os.environ.get(test_var)
            preserved = retrieved_value == long_value

            # 3. 清理
            os.environ.pop(test_var, None)

            # 4. 创建结果
            result = EnvTestResult(
                test_name="长值环境变量",
                status=TestStatus.PASSED if preserved else TestStatus.FAILED,
                message="长值处理正常" if preserved else "长值处理异常",
                details={
                    "value_length": len(long_value),
                    "retrieved_length": len(retrieved_value) if retrieved_value else 0,
                    "length_preserved": preserved
                }
            )

            self.test_results.append(result)

        except Exception as e:
            result = EnvTestResult(
                test_name="长值环境变量",
                status=TestStatus.ERROR,
                message=f"测试长值环境变量时发生错误: {str(e)}"
            )
            self.test_results.append(result)

    def _test_unicode_env_vars(self) -> None:
        """测试Unicode环境变量"""
        test_var = "PARALLEL_DEV_MCP_UNICODE_TEST"
        unicode_value = "测试Unicode值🚀中文字符"

        try:
            # 1. 设置Unicode值
            os.environ[test_var] = unicode_value

            # 2. 验证Unicode处理
            retrieved_value = os.environ.get(test_var)
            preserved = retrieved_value == unicode_value

            # 3. 清理
            os.environ.pop(test_var, None)

            # 4. 创建结果
            result = EnvTestResult(
                test_name="Unicode环境变量",
                status=TestStatus.PASSED if preserved else TestStatus.FAILED,
                message="Unicode处理正常" if preserved else "Unicode处理异常",
                details={
                    "original_value": unicode_value,
                    "retrieved_value": retrieved_value,
                    "unicode_preserved": preserved
                }
            )

            self.test_results.append(result)

        except Exception as e:
            result = EnvTestResult(
                test_name="Unicode环境变量",
                status=TestStatus.ERROR,
                message=f"测试Unicode环境变量时发生错误: {str(e)}"
            )
            self.test_results.append(result)

    def _validate_home_directory(self, value: str) -> Tuple[bool, str, Dict[str, Any]]:
        """验证HOME目录"""
        home_path = Path(value)
        exists = home_path.exists()
        is_dir = home_path.is_dir() if exists else False
        readable = os.access(value, os.R_OK) if exists else False

        if not exists:
            return False, f"HOME目录不存在: {value}", {"path": value, "exists": False}
        elif not is_dir:
            return False, f"HOME路径不是目录: {value}", {"path": value, "is_directory": False}
        elif not readable:
            return False, f"HOME目录不可读: {value}", {"path": value, "readable": False}
        else:
            return True, f"HOME目录有效: {value}", {"path": value, "valid": True}

    def _validate_path_variable(self, value: str) -> Tuple[bool, str, Dict[str, Any]]:
        """验证PATH变量"""
        if not value:
            return False, "PATH为空", {"empty": True}

        paths = value.split(os.pathsep)
        valid_paths = sum(1 for p in paths if p and Path(p).exists())
        total_paths = len([p for p in paths if p])

        if total_paths == 0:
            return False, "PATH中没有有效路径", {"total_paths": 0}
        elif valid_paths / total_paths < 0.5:
            return False, f"PATH中大部分路径无效: {valid_paths}/{total_paths}",
                   {"valid_paths": valid_paths, "total_paths": total_paths}
        else:
            return True, f"PATH配置正常: {valid_paths}/{total_paths} 路径有效",
                   {"valid_paths": valid_paths, "total_paths": total_paths}

    def _validate_user_variable(self, value: str) -> Tuple[bool, str, Dict[str, Any]]:
        """验证USER变量"""
        if not value or not value.strip():
            return False, "USER变量为空", {"empty": True}
        elif len(value) > 50:
            return False, f"USER变量过长: {len(value)} 字符", {"length": len(value)}
        else:
            return True, f"USER变量正常: {value}", {"user": value, "length": len(value)}

    def _validate_shell_variable(self, value: str) -> Tuple[bool, str, Dict[str, Any]]:
        """验证SHELL变量"""
        if not value:
            return True, "SHELL变量未设置（可选）", {"optional": True}

        shell_path = Path(value)
        if not shell_path.exists():
            return False, f"SHELL路径不存在: {value}", {"path": value, "exists": False}
        elif not os.access(value, os.X_OK):
            return False, f"SHELL文件不可执行: {value}", {"path": value, "executable": False}
        else:
            return True, f"SHELL配置正常: {value}", {"path": value, "valid": True}

    def _generate_test_report(self) -> Dict[str, Any]:
        """生成测试报告"""
        # 1. 统计测试结果
        status_counts = {status.value: 0 for status in TestStatus}
        for result in self.test_results:
            status_counts[result.status.value] += 1

        # 2. 确定整体状态
        if status_counts['error'] > 0 or status_counts['failed'] > 0:
            overall_status = "failed"
        elif status_counts['passed'] > 0:
            overall_status = "passed"
        else:
            overall_status = "unknown"

        # 3. 生成报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall_status,
            "summary": {
                "total_tests": len(self.test_results),
                "passed": status_counts['passed'],
                "failed": status_counts['failed'],
                "skipped": status_counts['skipped'],
                "errors": status_counts['error']
            },
            "test_results": [result.to_dict() for result in self.test_results],
            "recommendations": self._generate_recommendations()
        }

        return report

    def _generate_recommendations(self) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # 1. 分析失败的测试
        failed_tests = [r for r in self.test_results if r.status == TestStatus.FAILED]

        for test in failed_tests:
            if "关键环境变量" in test.test_name:
                var_name = test.details.get('variable', 'unknown')
                recommendations.append(f"设置关键环境变量 {var_name}")
            elif "PATH" in test.test_name:
                recommendations.append("检查并修复PATH环境变量配置")
            elif "HOME" in test.test_name:
                recommendations.append("检查HOME目录权限和存在性")
            elif "继承" in test.test_name:
                recommendations.append("检查环境变量继承机制")

        # 2. 去重并返回
        return list(set(recommendations))


def run_env_tests(project_root: Optional[Path] = None) -> Dict[str, Any]:
    """
    运行环境变量测试

    Args:
        project_root: 项目根目录

    Returns:
        Dict[str, Any]: 测试报告
    """
    # 1. 创建测试器
    tester = EnvironmentVariableTester(project_root)

    # 2. 运行测试
    report = tester.run_all_tests()

    # 3. 记录日志
    logger.info(f"环境变量测试完成，整体状态: {report['overall_status']}")

    # 4. 返回报告
    return report


if __name__ == "__main__":
    # 运行环境变量测试
    report = run_env_tests()
    print(f"环境变量测试状态: {report['overall_status']}")
    print(f"总测试数: {report['summary']['total_tests']}")
    print(f"通过: {report['summary']['passed']}")
    print(f"失败: {report['summary']['failed']}")
    print(f"跳过: {report['summary']['skipped']}")
    print(f"错误: {report['summary']['errors']}")