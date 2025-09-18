#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
独立Hooks兼容性检查脚本

@description 无需MCP依赖的独立Hooks兼容性检查工具
"""

import os
import sys
import json
import subprocess
import shutil
import argparse
from pathlib import Path
from datetime import datetime

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from parallel_dev_mcp.monitoring.hooks_compatibility_checker import run_hooks_compatibility_check
except ImportError as e:
    print(f"导入错误: {e}")
    print("使用简化的兼容性检查...")

    def run_hooks_compatibility_check(project_root=None):
        return run_simplified_hooks_check(project_root)


def run_simplified_hooks_check(project_root=None):
    """简化的Hooks兼容性检查实现"""
    if project_root:
        project_root = Path(project_root)
    else:
        project_root = Path(__file__).parent.parent

    hooks_dir = project_root / "examples" / "hooks"

    # 初始化报告
    report = {
        "timestamp": datetime.now().isoformat(),
        "overall_compatibility": "compatible",
        "hooks_directory": str(hooks_dir),
        "summary": {"total_checks": 0, "compatible": 0, "warnings": 0, "incompatible": 0, "missing": 0, "errors": 0},
        "check_results": [],
        "recommendations": []
    }

    # 检查hooks目录
    if not hooks_dir.exists():
        report["check_results"].append({
            "check_name": "Hooks目录",
            "status": "missing",
            "message": f"examples/hooks/目录不存在: {hooks_dir}",
            "timestamp": datetime.now().isoformat()
        })
        report["recommendations"].append("创建examples/hooks/目录")
        report["overall_compatibility"] = "incomplete"
    else:
        report["check_results"].append({
            "check_name": "Hooks目录",
            "status": "compatible",
            "message": "examples/hooks/目录存在",
            "timestamp": datetime.now().isoformat()
        })

    # 检查必需文件
    expected_files = {
        "README.md": "文档说明文件",
        "web_message_sender.py": "Web消息发送器",
        "tmux_web_service.py": "Tmux Web服务",
        "stop_hook.sh": "Stop事件Hook脚本",
        "session_start_hook.sh": "SessionStart事件Hook脚本"
    }

    for filename, description in expected_files.items():
        file_path = hooks_dir / filename

        if not file_path.exists():
            report["check_results"].append({
                "check_name": f"文件_{filename}",
                "status": "missing",
                "message": f"缺少{description}: {filename}",
                "timestamp": datetime.now().isoformat()
            })
            report["recommendations"].append(f"创建文件: {filename}")
            if report["overall_compatibility"] == "compatible":
                report["overall_compatibility"] = "incomplete"
        else:
            # 检查文件权限
            is_executable = os.access(file_path, os.X_OK)
            file_size = file_path.stat().st_size

            if filename.endswith('.sh') and not is_executable:
                report["check_results"].append({
                    "check_name": f"文件_{filename}",
                    "status": "warning",
                    "message": f"{description}存在但不可执行: {filename}",
                    "timestamp": datetime.now().isoformat()
                })
                report["recommendations"].append(f"设置可执行权限: chmod +x {file_path}")
                if report["overall_compatibility"] == "compatible":
                    report["overall_compatibility"] = "partial"
            elif file_size == 0:
                report["check_results"].append({
                    "check_name": f"文件_{filename}",
                    "status": "warning",
                    "message": f"{description}存在但为空: {filename}",
                    "timestamp": datetime.now().isoformat()
                })
                if report["overall_compatibility"] == "compatible":
                    report["overall_compatibility"] = "partial"
            else:
                report["check_results"].append({
                    "check_name": f"文件_{filename}",
                    "status": "compatible",
                    "message": f"{description}存在且正常: {filename}",
                    "timestamp": datetime.now().isoformat()
                })

    # 检查Python依赖
    python_deps = ["requests", "flask"]
    missing_deps = []

    for dep in python_deps:
        try:
            __import__(dep)
        except ImportError:
            missing_deps.append(dep)

    if missing_deps:
        report["check_results"].append({
            "check_name": "Python依赖",
            "status": "warning",
            "message": f"部分Python依赖缺失: {', '.join(missing_deps)}",
            "timestamp": datetime.now().isoformat()
        })
        report["recommendations"].append(f"安装Python依赖: pip install {' '.join(missing_deps)}")
        if report["overall_compatibility"] == "compatible":
            report["overall_compatibility"] = "partial"
    else:
        report["check_results"].append({
            "check_name": "Python依赖",
            "status": "compatible",
            "message": "Python依赖完整",
            "timestamp": datetime.now().isoformat()
        })

    # 检查外部命令
    required_commands = ["python3", "tmux", "bash"]
    missing_commands = []

    for cmd in required_commands:
        if not shutil.which(cmd):
            missing_commands.append(cmd)

    if missing_commands:
        report["check_results"].append({
            "check_name": "外部命令",
            "status": "incompatible",
            "message": f"缺少必需命令: {', '.join(missing_commands)}",
            "timestamp": datetime.now().isoformat()
        })
        for cmd in missing_commands:
            if cmd == "tmux":
                report["recommendations"].append("安装tmux: brew install tmux (macOS) 或 apt-get install tmux (Ubuntu)")
            elif cmd == "python3":
                report["recommendations"].append("安装Python 3.9+")
        report["overall_compatibility"] = "incompatible"
    else:
        report["check_results"].append({
            "check_name": "外部命令",
            "status": "compatible",
            "message": "所有必需命令都可用",
            "timestamp": datetime.now().isoformat()
        })

    # 统计结果
    status_counts = {"compatible": 0, "warning": 0, "incompatible": 0, "missing": 0, "error": 0}
    for result in report["check_results"]:
        status_counts[result["status"]] += 1

    report["summary"] = {
        "total_checks": len(report["check_results"]),
        "compatible": status_counts["compatible"],
        "warnings": status_counts["warning"],
        "incompatible": status_counts["incompatible"],
        "missing": status_counts["missing"],
        "errors": status_counts["error"]
    }

    return report


def main():
    """主函数"""
    # 1. 解析命令行参数
    parser = argparse.ArgumentParser(description="Hooks兼容性检查工具")
    parser.add_argument("--project-root", "-p", type=str, help="项目根目录")
    parser.add_argument("--output", "-o", type=str, help="输出文件路径")
    parser.add_argument("--format", "-f", choices=["json", "text"], default="text", help="输出格式")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")

    args = parser.parse_args()

    # 2. 确定项目根目录
    if args.project_root:
        project_root = Path(args.project_root)
    else:
        project_root = Path(__file__).parent.parent

    # 3. 运行兼容性检查
    print("正在运行Hooks兼容性检查...")
    try:
        report = run_hooks_compatibility_check(project_root)
    except Exception as e:
        print(f"兼容性检查失败: {e}")
        sys.exit(1)

    # 4. 输出结果
    if args.format == "json":
        output_json(report, args.output)
    else:
        output_text(report, args.output, args.verbose)

    # 5. 设置退出码
    if report["overall_compatibility"] == "incompatible":
        sys.exit(2)
    elif report["overall_compatibility"] in ["incomplete", "partial"]:
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
    lines.append("Hooks兼容性检查报告")
    lines.append("=" * 60)
    lines.append(f"检查时间: {report['timestamp']}")
    lines.append(f"Hooks目录: {report['hooks_directory']}")
    lines.append(f"整体兼容性: {get_compatibility_display(report['overall_compatibility'])}")
    lines.append("")

    # 2. 汇总信息
    summary = report['summary']
    lines.append("检查汇总:")
    lines.append(f"  总检查项: {summary['total_checks']}")
    lines.append(f"  兼容项目: {summary['compatible']} ✅")
    lines.append(f"  警告项目: {summary['warnings']} ⚠️")
    lines.append(f"  不兼容项: {summary['incompatible']} ❌")
    lines.append(f"  缺失项目: {summary['missing']} 📋")
    lines.append("")

    # 3. 详细检查结果
    lines.append("详细检查结果:")
    lines.append("-" * 40)

    for result in report['check_results']:
        status_icon = get_status_icon(result['status'])
        lines.append(f"{status_icon} {result['check_name']}: {result['message']}")

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


def get_compatibility_display(compatibility):
    """获取兼容性显示文本"""
    compatibility_map = {
        "compatible": "完全兼容 ✅",
        "partial": "部分兼容 ⚠️",
        "incomplete": "不完整 📋",
        "incompatible": "不兼容 ❌"
    }
    return compatibility_map.get(compatibility, compatibility)


def get_status_icon(status):
    """获取状态图标"""
    icon_map = {
        "compatible": "✅",
        "warning": "⚠️",
        "incompatible": "❌",
        "missing": "📋",
        "error": "💥"
    }
    return icon_map.get(status, "❓")


if __name__ == "__main__":
    main()