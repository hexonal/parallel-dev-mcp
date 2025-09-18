#!/bin/bash
# -*- coding: utf-8 -*-
# 快速修复常见问题脚本

set -e  # 遇到错误时退出

echo "🔧 Parallel Development MCP - 快速修复脚本"
echo "⏰ 修复时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=" * 60

# 获取项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "📁 项目根目录: $PROJECT_ROOT"
cd "$PROJECT_ROOT"

# 1. 设置脚本权限
echo ""
echo "1️⃣ 设置脚本权限..."
if [ -d "scripts" ]; then
    echo "设置scripts目录权限..."
    chmod +x scripts/*.py 2>/dev/null || echo "⚠️ 部分scripts文件权限设置失败"
    echo "✅ scripts目录权限设置完成"
else
    echo "⚠️ scripts目录不存在"
fi

if [ -d "examples/hooks" ]; then
    echo "设置examples/hooks目录权限..."
    chmod +x examples/hooks/*.sh 2>/dev/null || echo "⚠️ 部分hooks文件权限设置失败"
    echo "✅ examples/hooks目录权限设置完成"
else
    echo "⚠️ examples/hooks目录不存在"
fi

# 2. 检查Python环境
echo ""
echo "2️⃣ 检查Python环境..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
    echo "✅ Python版本: $PYTHON_VERSION"

    # 检查Python版本是否满足要求
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 9 ]); then
        echo "❌ Python版本过低，需要3.9+版本"
        echo "请升级Python版本"
        exit 1
    fi
else
    echo "❌ Python3未安装"
    echo "请安装Python 3.9+版本"
    exit 1
fi

# 3. 检查并安装依赖
echo ""
echo "3️⃣ 检查和安装Python依赖..."

# 检查包管理器
if command -v uv &> /dev/null; then
    echo "✅ 检测到uv包管理器"
    echo "同步项目依赖..."
    if uv sync; then
        echo "✅ uv sync 完成"
    else
        echo "⚠️ uv sync 失败，尝试其他方法"
        # 尝试安装核心依赖
        uv add psutil pydantic || echo "⚠️ uv add 失败"
    fi
elif command -v pip &> /dev/null; then
    echo "✅ 检测到pip包管理器"

    # 检查虚拟环境
    if [[ "$VIRTUAL_ENV" != "" ]]; then
        echo "✅ 在虚拟环境中: $VIRTUAL_ENV"
    else
        echo "⚠️ 未在虚拟环境中，建议使用虚拟环境"
    fi

    echo "安装核心依赖..."

    # 安装核心依赖
    CORE_DEPS="psutil pydantic"
    for dep in $CORE_DEPS; do
        echo "安装 $dep..."
        if pip install "$dep"; then
            echo "✅ $dep 安装成功"
        else
            echo "❌ $dep 安装失败"
        fi
    done

    # 安装可选依赖
    OPTIONAL_DEPS="requests flask"
    for dep in $OPTIONAL_DEPS; do
        echo "安装可选依赖 $dep..."
        if pip install "$dep"; then
            echo "✅ $dep 安装成功"
        else
            echo "⚠️ $dep 安装失败（可选依赖）"
        fi
    done
else
    echo "❌ 未找到包管理器（uv或pip）"
    echo "请安装pip: python -m ensurepip --upgrade"
    exit 1
fi

# 4. 检查tmux
echo ""
echo "4️⃣ 检查tmux..."
if command -v tmux &> /dev/null; then
    TMUX_VERSION=$(tmux -V 2>&1)
    echo "✅ tmux已安装: $TMUX_VERSION"
else
    echo "❌ tmux未安装"
    echo "请安装tmux:"
    echo "  macOS: brew install tmux"
    echo "  Ubuntu/Debian: sudo apt install tmux"
    echo "  CentOS/RHEL: sudo yum install tmux"
    echo ""
    echo "⚠️ 没有tmux将无法使用会话管理功能"
fi

# 5. 检查Git
echo ""
echo "5️⃣ 检查Git..."
if command -v git &> /dev/null; then
    GIT_VERSION=$(git --version 2>&1)
    echo "✅ Git已安装: $GIT_VERSION"
else
    echo "❌ Git未安装"
    echo "请安装Git:"
    echo "  macOS: brew install git"
    echo "  Ubuntu/Debian: sudo apt install git"
    echo "  CentOS/RHEL: sudo yum install git"
fi

# 6. 创建必要目录
echo ""
echo "6️⃣ 创建必要目录..."
REQUIRED_DIRS=("docs" "tests" "logs")

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        echo "创建目录: $dir"
        mkdir -p "$dir"
        echo "✅ 目录 $dir 创建成功"
    else
        echo "✅ 目录 $dir 已存在"
    fi
done

# 7. 验证修复结果
echo ""
echo "7️⃣ 验证修复结果..."
if [ -f "scripts/self_diagnosis.py" ]; then
    echo "运行自助诊断..."
    if python3 scripts/self_diagnosis.py; then
        echo "✅ 自助诊断通过"
    else
        echo "⚠️ 自助诊断发现问题，请查看输出"
    fi
else
    echo "⚠️ 自助诊断脚本不存在，跳过验证"
fi

# 8. 清理临时文件
echo ""
echo "8️⃣ 清理临时文件..."
TEMP_PATTERNS=("*.pyc" "__pycache__" "*.tmp" ".DS_Store")

for pattern in "${TEMP_PATTERNS[@]}"; do
    if find . -name "$pattern" -type f 2>/dev/null | head -1 | grep -q .; then
        echo "清理 $pattern 文件..."
        find . -name "$pattern" -type f -delete 2>/dev/null || echo "⚠️ 清理 $pattern 部分失败"
    fi
done

if find . -name "__pycache__" -type d 2>/dev/null | head -1 | grep -q .; then
    echo "清理 __pycache__ 目录..."
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || echo "⚠️ 清理 __pycache__ 部分失败"
fi

echo "✅ 临时文件清理完成"

# 9. 生成修复报告
echo ""
echo "=" * 60
echo "📋 快速修复报告"
echo "=" * 60
echo "⏰ 修复完成时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "📁 项目路径: $PROJECT_ROOT"

echo ""
echo "✅ 完成的修复项目:"
echo "  - 脚本权限设置"
echo "  - Python依赖安装"
echo "  - 必要目录创建"
echo "  - 临时文件清理"

echo ""
echo "📖 下一步建议:"
echo "  1. 运行健康检查: python3 scripts/health_check.py"
echo "  2. 运行环境测试: python3 scripts/env_test.py"
echo "  3. 查看使用文档: docs/usage-examples.md"
echo "  4. 查看故障排除: docs/troubleshooting-guide.md"

if ! command -v tmux &> /dev/null; then
    echo ""
    echo "⚠️ 重要提醒:"
    echo "  tmux未安装，会话管理功能将不可用"
    echo "  请安装tmux后重新运行此脚本"
fi

echo ""
echo "🎉 快速修复完成！"
echo "现在可以开始使用 Parallel Development MCP"