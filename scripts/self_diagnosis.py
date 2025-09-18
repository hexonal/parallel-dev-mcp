#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整自助诊断脚本

@description 无需MCP依赖的独立自助诊断工具
"""

import sys
import os
import subprocess
import shutil
import json
from pathlib import Path
from datetime import datetime

def run_comprehensive_diagnosis():
    """运行完整的自助诊断"""

    print("🔍 开始自助诊断...")
    print("=" * 60)

    issues = []
    warnings = []
    recommendations = []

    # 1. Python环境检查
    print("1️⃣ Python环境检查...")
    python_version = sys.version_info
    if python_version < (3, 9):
        issues.append(f"Python版本过低: {python_version.major}.{python_version.minor}.{python_version.micro}")
        recommendations.append("升级Python到3.9+版本")
    elif python_version < (3, 10):
        warnings.append(f"Python版本较低: {python_version.major}.{python_version.minor}.{python_version.micro}")
        recommendations.append("建议升级Python到3.10+以支持完整功能")
    else:
        print(f"✅ Python版本正常: {python_version.major}.{python_version.minor}.{python_version.micro}")

    # 2. 必要工具检查
    print("\n2️⃣ 必要工具检查...")
    required_tools = {
        'tmux': 'tmux终端多路复用器',
        'git': 'Git版本控制工具',
        'python3': 'Python 3解释器'
    }

    missing_tools = []
    for tool, description in required_tools.items():
        if shutil.which(tool):
            # 尝试获取版本信息
            try:
                if tool == 'tmux':
                    result = subprocess.run([tool, '-V'], capture_output=True, text=True, timeout=5)
                elif tool == 'python3':
                    result = subprocess.run([tool, '--version'], capture_output=True, text=True, timeout=5)
                elif tool == 'git':
                    result = subprocess.run([tool, '--version'], capture_output=True, text=True, timeout=5)

                version = result.stdout.strip() if result.returncode == 0 else "版本未知"
                print(f"✅ {description}: {version}")
            except:
                print(f"✅ {description}: 已安装")
        else:
            missing_tools.append(tool)
            issues.append(f"缺少必要工具: {tool} ({description})")

    # 3. 项目结构检查
    print("\n3️⃣ 项目结构检查...")
    project_root = Path(__file__).parent.parent
    required_dirs = {
        'src/parallel_dev_mcp': '主要源代码目录',
        'examples/hooks': 'Hooks示例目录',
        'scripts': '工具脚本目录',
        'docs': '文档目录'
    }

    missing_dirs = []
    for dir_name, description in required_dirs.items():
        dir_path = project_root / dir_name
        if dir_path.exists():
            print(f"✅ {description}: {dir_path}")
        else:
            missing_dirs.append(dir_name)
            issues.append(f"缺少目录: {dir_name} ({description})")

    # 4. Python包检查
    print("\n4️⃣ Python包检查...")
    required_packages = {
        'psutil': '系统信息获取',
        'pydantic': '数据验证',
        'requests': 'HTTP请求（可选）',
        'flask': 'Web框架（可选）'
    }

    missing_packages = []
    for package, description in required_packages.items():
        try:
            __import__(package)
            print(f"✅ {description}: {package}")
        except ImportError:
            if package in ['psutil', 'pydantic']:
                missing_packages.append(package)
                issues.append(f"缺少关键Python包: {package} ({description})")
            else:
                warnings.append(f"缺少可选Python包: {package} ({description})")

    # 5. 环境变量检查
    print("\n5️⃣ 环境变量检查...")
    critical_vars = {
        'USER': '当前用户名',
        'HOME': '用户主目录',
        'PATH': '可执行文件搜索路径',
        'SHELL': '默认Shell'
    }

    missing_vars = []
    empty_vars = []
    for var_name, description in critical_vars.items():
        value = os.environ.get(var_name)
        if value is None:
            missing_vars.append(var_name)
            issues.append(f"缺少环境变量: {var_name} ({description})")
        elif not value.strip():
            empty_vars.append(var_name)
            warnings.append(f"环境变量为空: {var_name} ({description})")
        else:
            # 显示值的前50个字符
            display_value = value[:50] + "..." if len(value) > 50 else value
            print(f"✅ {description}: {display_value}")

    # 6. 文件权限检查
    print("\n6️⃣ 文件权限检查...")
    script_files = list((project_root / "scripts").glob("*.py")) if (project_root / "scripts").exists() else []
    hook_files = list((project_root / "examples/hooks").glob("*.sh")) if (project_root / "examples/hooks").exists() else []

    permission_issues = []
    for script_file in script_files:
        if not os.access(script_file, os.X_OK):
            permission_issues.append(str(script_file))

    for hook_file in hook_files:
        if not os.access(hook_file, os.X_OK):
            permission_issues.append(str(hook_file))

    if permission_issues:
        warnings.append(f"部分脚本缺少执行权限: {len(permission_issues)}个文件")
        recommendations.append("设置脚本可执行权限: chmod +x scripts/*.py examples/hooks/*.sh")
    else:
        print("✅ 脚本权限正常")

    # 7. 磁盘空间检查
    print("\n7️⃣ 磁盘空间检查...")
    try:
        if shutil.which('df'):
            result = subprocess.run(['df', '-h', '.'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) >= 2:
                    disk_info = lines[1].split()
                    if len(disk_info) >= 5:
                        used_percent = disk_info[4].rstrip('%')
                        try:
                            used_pct = int(used_percent)
                            if used_pct > 95:
                                issues.append(f"磁盘空间严重不足: {used_percent}%")
                            elif used_pct > 85:
                                warnings.append(f"磁盘空间较少: {used_percent}%")
                            else:
                                print(f"✅ 磁盘空间充足: 已使用 {used_percent}%")
                        except ValueError:
                            print("⚠️ 无法解析磁盘使用率")
    except:
        print("⚠️ 无法检查磁盘空间")

    # 8. 生成报告
    print("\n" + "=" * 60)
    print("📋 诊断报告:")
    print("=" * 60)

    if not issues and not warnings:
        print("🎉 系统健康，未发现问题")
        print("✅ 所有检查项目都通过")
        return True

    if issues:
        print(f"❌ 发现 {len(issues)} 个严重问题:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")

    if warnings:
        print(f"\n⚠️ 发现 {len(warnings)} 个警告:")
        for i, warning in enumerate(warnings, 1):
            print(f"  {i}. {warning}")

    # 9. 修复建议
    if recommendations or missing_tools or missing_packages:
        print(f"\n🔧 修复建议:")

        if missing_tools:
            print("  安装缺少的工具:")
            for tool in missing_tools:
                if tool == 'tmux':
                    print("    - tmux: brew install tmux (macOS) 或 apt install tmux (Ubuntu)")
                elif tool == 'git':
                    print("    - git: brew install git (macOS) 或 apt install git (Ubuntu)")

        if missing_packages:
            print("  安装缺少的Python包:")
            print(f"    uv sync 或 pip install {' '.join(missing_packages)}")

        for rec in recommendations:
            print(f"  - {rec}")

    # 10. 下一步建议
    print(f"\n📖 下一步建议:")
    if issues:
        print("  1. 先解决上述严重问题")
        print("  2. 重新运行诊断: python scripts/self_diagnosis.py")
        print("  3. 如果问题持续，请查看故障排除指南: docs/troubleshooting-guide.md")
    else:
        print("  1. 可以开始使用系统功能")
        print("  2. 运行健康检查: python scripts/health_check.py")
        print("  3. 查看使用示例: docs/usage-examples.md")

    return len(issues) == 0


def generate_diagnosis_report():
    """生成详细的诊断报告"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "diagnosis_type": "self_diagnosis",
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "platform": sys.platform,
        "working_directory": str(Path.cwd()),
        "project_root": str(Path(__file__).parent.parent),
        "checks_performed": [],
        "issues_found": [],
        "warnings": [],
        "recommendations": []
    }

    # 这里可以添加更详细的报告生成逻辑
    return report


def main():
    """主函数"""
    print("🏥 Parallel Development MCP - 自助诊断工具")
    print(f"⏰ 诊断时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        success = run_comprehensive_diagnosis()

        print(f"\n{'='*60}")
        if success:
            print("🎉 诊断完成 - 系统健康")
            print("现在可以安全使用 Parallel Development MCP 的所有功能")
            sys.exit(0)
        else:
            print("⚠️ 诊断完成 - 发现问题")
            print("请根据上述建议解决问题后重新运行诊断")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ 诊断过程中发生错误: {str(e)}")
        print("请检查Python环境和项目结构")
        sys.exit(2)


if __name__ == "__main__":
    main()