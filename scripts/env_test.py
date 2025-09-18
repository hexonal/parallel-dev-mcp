#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境变量测试脚本

@description 独立的环境变量测试工具
"""

import os
import sys
import json
import argparse
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from parallel_dev_mcp.monitoring.env_variable_tester import run_env_tests, TestStatus
except ImportError as e:
    print(f"导入错误: {e}")
    print("使用简化的环境变量测试...")

    # 使用简化的环境变量测试
    def run_env_tests(project_root=None):
        return run_simplified_env_tests(project_root)

    class TestStatus:
        PASSED = "passed"
        FAILED = "failed"
        SKIPPED = "skipped"
        ERROR = "error"


def run_simplified_env_tests(project_root=None):
    """简化的环境变量测试实现"""
    from datetime import datetime
    import subprocess

    if project_root:
        project_root = Path(project_root)
    else:
        project_root = Path(__file__).parent.parent

    # 初始化报告
    report = {
        "timestamp": datetime.now().isoformat(),
        "overall_status": "passed",
        "summary": {"total_tests": 0, "passed": 0, "failed": 0, "skipped": 0, "errors": 0},
        "test_results": [],
        "recommendations": []
    }

    # 检查关键环境变量
    critical_vars = {
        "USER": "当前用户名",
        "HOME": "用户主目录",
        "PATH": "可执行文件搜索路径"
    }

    for var_name, description in critical_vars.items():
        value = os.environ.get(var_name)

        if value is None:
            status = "failed"
            message = f"关键环境变量 {var_name} 未设置"
            report["recommendations"].append(f"设置环境变量 {var_name}")
        elif not value.strip():
            status = "failed"
            message = f"关键环境变量 {var_name} 为空"
            report["recommendations"].append(f"检查环境变量 {var_name} 的值")
        else:
            status = "passed"
            message = f"关键环境变量 {var_name} 正常"

        report["test_results"].append({
            "test_name": f"关键环境变量_{var_name}",
            "status": status,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "details": {"variable": var_name, "description": description}
        })

    # 检查PATH
    path_value = os.environ.get('PATH', '')
    if not path_value:
        status = "failed"
        message = "PATH环境变量为空"
        report["recommendations"].append("检查并设置PATH环境变量")
    else:
        path_dirs = path_value.split(os.pathsep)
        existing_dirs = sum(1 for d in path_dirs if d and Path(d).exists())

        if existing_dirs == 0:
            status = "failed"
            message = "PATH中没有有效目录"
        elif existing_dirs < len(path_dirs) / 2:
            status = "failed"
            message = f"PATH中大部分目录不存在: {existing_dirs}/{len(path_dirs)}"
        else:
            status = "passed"
            message = f"PATH配置正常: {existing_dirs}/{len(path_dirs)} 目录有效"

    report["test_results"].append({
        "test_name": "PATH环境变量",
        "status": status,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "details": {"total_dirs": len(path_dirs) if path_value else 0, "valid_dirs": existing_dirs if path_value else 0}
    })

    # 测试环境变量继承
    test_var = "SIMPLIFIED_ENV_TEST"
    test_value = "test_inheritance"
    os.environ[test_var] = test_value

    try:
        cmd = [sys.executable, '-c', f'import os; print(os.environ.get("{test_var}", "NOT_FOUND"))']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

        if result.returncode == 0 and test_value in result.stdout:
            status = "passed"
            message = "环境变量继承正常"
        else:
            status = "failed"
            message = "环境变量继承失败"
            report["recommendations"].append("检查进程间环境变量继承")

        report["test_results"].append({
            "test_name": "环境变量继承",
            "status": status,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "details": {"child_output": result.stdout.strip() if result.stdout else ""}
        })
    except Exception as e:
        report["test_results"].append({
            "test_name": "环境变量继承",
            "status": "error",
            "message": f"测试失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        })
    finally:
        os.environ.pop(test_var, None)

    # 统计结果
    status_counts = {"passed": 0, "failed": 0, "skipped": 0, "error": 0}
    for result in report["test_results"]:
        status_counts[result["status"]] += 1

    report["summary"] = {
        "total_tests": len(report["test_results"]),
        "passed": status_counts["passed"],
        "failed": status_counts["failed"],
        "skipped": status_counts["skipped"],
        "errors": status_counts["error"]
    }

    # 确定整体状态
    if status_counts["failed"] > 0 or status_counts["error"] > 0:
        report["overall_status"] = "failed"
    else:
        report["overall_status"] = "passed"

    return report


def main():
    """主函数"""
    # 1. 解析命令行参数
    parser = argparse.ArgumentParser(description="环境变量测试工具")
    parser.add_argument("--project-root", "-p", type=str, help="项目根目录")
    parser.add_argument("--output", "-o", type=str, help="输出文件路径")
    parser.add_argument("--format", "-f", choices=["json", "text"], default="text", help="输出格式")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.add_argument("--filter", "-t", choices=["all", "failed", "passed", "critical"],
                       default="all", help="过滤测试结果")

    args = parser.parse_args()

    # 2. 确定项目根目录
    if args.project_root:
        project_root = Path(args.project_root)
    else:
        project_root = Path(__file__).parent.parent

    # 3. 运行环境变量测试
    print("正在运行环境变量测试...")
    try:
        report = run_env_tests(project_root)
    except Exception as e:
        print(f"环境变量测试失败: {e}")
        sys.exit(1)

    # 4. 过滤结果
    if args.filter != "all":
        filtered_results = filter_test_results(report['test_results'], args.filter)
        report['test_results'] = filtered_results
        report['summary']['displayed'] = len(filtered_results)

    # 5. 输出结果
    if args.format == "json":
        output_json(report, args.output)
    else:
        output_text(report, args.output, args.verbose)

    # 6. 设置退出码
    if report["overall_status"] == "failed":
        sys.exit(1)
    else:
        sys.exit(0)


def filter_test_results(test_results, filter_type):
    """过滤测试结果"""
    if filter_type == "failed":
        return [r for r in test_results if r['status'] in ['failed', 'error']]
    elif filter_type == "passed":
        return [r for r in test_results if r['status'] == 'passed']
    elif filter_type == "critical":
        return [r for r in test_results if r['status'] in ['failed', 'error'] and '关键' in r['test_name']]
    else:
        return test_results


def output_json(report, output_file=None):
    """输出JSON格式结果"""
    json_str = json.dumps(report, indent=2, ensure_ascii=False)

    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(json_str)
        print(f"结果已保存到: {output_file}")
    else:
        print(json_str)


def output_text(report, output_file=None, verbose=False):
    """输出文本格式结果"""
    lines = []

    # 1. 标题和整体状态
    lines.append("=" * 60)
    lines.append("环境变量测试报告")
    lines.append("=" * 60)
    lines.append(f"测试时间: {report['timestamp']}")
    lines.append(f"整体状态: {get_status_display(report['overall_status'])}")
    lines.append("")

    # 2. 汇总信息
    summary = report['summary']
    lines.append("测试汇总:")
    lines.append(f"  总测试数: {summary['total_tests']}")
    lines.append(f"  通过测试: {summary['passed']} ✅")
    lines.append(f"  失败测试: {summary['failed']} ❌")
    lines.append(f"  跳过测试: {summary['skipped']} ⏭️")
    lines.append(f"  错误测试: {summary['errors']} ⚠️")

    if 'displayed' in summary:
        lines.append(f"  显示测试: {summary['displayed']} (已过滤)")

    lines.append("")

    # 3. 详细测试结果
    lines.append("详细测试结果:")
    lines.append("-" * 40)

    for result in report['test_results']:
        status_icon = get_status_icon(result['status'])
        lines.append(f"{status_icon} {result['test_name']}: {result['message']}")

        if verbose and result.get('details'):
            for key, value in result['details'].items():
                if isinstance(value, (list, dict)):
                    value = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
                lines.append(f"    {key}: {value}")
            lines.append("")

    # 4. 改进建议
    if report.get('recommendations'):
        lines.append("")
        lines.append("改进建议:")
        lines.append("-" * 40)
        for i, rec in enumerate(report['recommendations'], 1):
            lines.append(f"{i}. {rec}")

    # 5. 输出
    output_text = "\n".join(lines)

    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(output_text)
        print(f"结果已保存到: {output_file}")
    else:
        print(output_text)


def get_status_display(status):
    """获取状态显示文本"""
    status_map = {
        "passed": "通过 ✅",
        "failed": "失败 ❌",
        "unknown": "未知 ❓"
    }
    return status_map.get(status, status)


def get_status_icon(status):
    """获取状态图标"""
    icon_map = {
        "passed": "✅",
        "failed": "❌",
        "skipped": "⏭️",
        "error": "⚠️"
    }
    return icon_map.get(status, "❓")


if __name__ == "__main__":
    main()