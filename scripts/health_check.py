#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
独立系统健康检查脚本

@description 无需MCP依赖的独立健康检查工具
"""

import os
import sys
import json
import argparse
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# 先检查并避免fastmcp导入问题
try:
    # 测试导入核心依赖
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# 导入健康检查器
try:
    from parallel_dev_mcp.monitoring.system_health_checker import run_health_check, HealthStatus
except ImportError as e:
    print(f"导入错误: {e}")
    print("尝试使用简化的健康检查...")

    # 使用简化的健康检查
    def run_health_check(project_root=None):
        return run_simplified_health_check(project_root)

    class HealthStatus:
        HEALTHY = "healthy"
        WARNING = "warning"
        CRITICAL = "critical"


def run_simplified_health_check(project_root=None):
    """简化的健康检查实现"""
    from datetime import datetime
    import shutil
    import subprocess
    import platform

    if project_root:
        project_root = Path(project_root)
    else:
        project_root = Path(__file__).parent.parent

    # 初始化报告
    report = {
        "timestamp": datetime.now().isoformat(),
        "overall_status": "healthy",
        "summary": {"total_checks": 0, "healthy": 0, "warnings": 0, "critical": 0, "unknown": 0},
        "details": [],
        "recommendations": []
    }

    # 检查Python版本
    python_version = sys.version_info
    if python_version < (3, 9):
        status = "critical"
        message = f"Python版本过低: {python_version.major}.{python_version.minor}.{python_version.micro}"
        report["recommendations"].append("升级Python到3.9+版本")
    elif python_version < (3, 10):
        status = "warning"
        message = f"Python版本较低: {python_version.major}.{python_version.minor}.{python_version.micro} (推荐3.10+)"
        report["recommendations"].append("考虑升级Python到3.10+以支持完整功能")
    else:
        status = "healthy"
        message = f"Python版本正常: {python_version.major}.{python_version.minor}.{python_version.micro}"

    report["details"].append({
        "check_name": "Python版本",
        "status": status,
        "message": message,
        "timestamp": datetime.now().isoformat()
    })

    # 检查tmux
    tmux_available = shutil.which('tmux') is not None
    if tmux_available:
        try:
            result = subprocess.run(['tmux', '-V'], capture_output=True, text=True, timeout=5)
            tmux_status = "healthy"
            tmux_message = f"tmux可用: {result.stdout.strip()}"
        except:
            tmux_status = "warning"
            tmux_message = "tmux已安装但功能测试失败"
    else:
        tmux_status = "critical"
        tmux_message = "tmux未安装"
        report["recommendations"].append("安装tmux")

    report["details"].append({
        "check_name": "tmux可用性",
        "status": tmux_status,
        "message": tmux_message,
        "timestamp": datetime.now().isoformat()
    })

    # 检查项目结构
    required_paths = ["src/parallel_dev_mcp", "pyproject.toml"]
    missing_paths = []
    for path_str in required_paths:
        if not (project_root / path_str).exists():
            missing_paths.append(path_str)

    if not missing_paths:
        structure_status = "healthy"
        structure_message = "项目结构完整"
    else:
        structure_status = "warning"
        structure_message = f"缺少路径: {', '.join(missing_paths)}"

    report["details"].append({
        "check_name": "项目结构",
        "status": structure_status,
        "message": structure_message,
        "timestamp": datetime.now().isoformat()
    })

    # 统计状态
    status_counts = {"healthy": 0, "warning": 0, "critical": 0, "unknown": 0}
    for detail in report["details"]:
        status_counts[detail["status"]] += 1

    report["summary"] = {
        "total_checks": len(report["details"]),
        "healthy": status_counts["healthy"],
        "warnings": status_counts["warning"],
        "critical": status_counts["critical"],
        "unknown": status_counts["unknown"]
    }

    # 确定整体状态
    if status_counts["critical"] > 0:
        report["overall_status"] = "critical"
    elif status_counts["warning"] > 0:
        report["overall_status"] = "warning"
    else:
        report["overall_status"] = "healthy"

    return report


def main():
    """主函数"""
    # 1. 解析命令行参数
    parser = argparse.ArgumentParser(description="系统健康检查工具")
    parser.add_argument("--project-root", "-p", type=str, help="项目根目录")
    parser.add_argument("--output", "-o", type=str, help="输出文件路径")
    parser.add_argument("--format", "-f", choices=["json", "text"], default="text", help="输出格式")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")

    args = parser.parse_args()

    # 2. 确定项目根目录
    if args.project_root:
        project_root = Path(args.project_root)
    else:
        # 从脚本位置推断项目根目录
        project_root = Path(__file__).parent.parent

    # 3. 运行健康检查
    print("正在运行系统健康检查...")
    try:
        report = run_health_check(project_root)
    except Exception as e:
        print(f"健康检查失败: {e}")
        sys.exit(1)

    # 4. 输出结果
    if args.format == "json":
        output_json(report, args.output)
    else:
        output_text(report, args.output, args.verbose)

    # 5. 设置退出码
    if report["overall_status"] == "critical":
        sys.exit(2)
    elif report["overall_status"] == "warning":
        sys.exit(1)
    else:
        sys.exit(0)


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
    lines.append("系统健康检查报告")
    lines.append("=" * 60)
    lines.append(f"检查时间: {report['timestamp']}")
    lines.append(f"整体状态: {get_status_display(report['overall_status'])}")
    lines.append("")

    # 2. 汇总信息
    summary = report['summary']
    lines.append("检查汇总:")
    lines.append(f"  总检查项: {summary['total_checks']}")
    lines.append(f"  健康项目: {summary['healthy']} ✅")
    lines.append(f"  警告项目: {summary['warnings']} ⚠️")
    lines.append(f"  严重项目: {summary['critical']} ❌")
    lines.append("")

    # 3. 详细检查结果
    lines.append("详细检查结果:")
    lines.append("-" * 40)

    for detail in report['details']:
        status_icon = get_status_icon(detail['status'])
        lines.append(f"{status_icon} {detail['check_name']}: {detail['message']}")

        if verbose and detail.get('details'):
            for key, value in detail['details'].items():
                if key != 'issues':  # issues 会在message中显示
                    lines.append(f"    {key}: {value}")

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
        "healthy": "健康 ✅",
        "warning": "警告 ⚠️",
        "critical": "严重 ❌",
        "unknown": "未知 ❓"
    }
    return status_map.get(status, status)


def get_status_icon(status):
    """获取状态图标"""
    icon_map = {
        "healthy": "✅",
        "warning": "⚠️",
        "critical": "❌",
        "unknown": "❓"
    }
    return icon_map.get(status, "❓")


if __name__ == "__main__":
    main()