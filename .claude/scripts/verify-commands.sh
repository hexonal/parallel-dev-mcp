#!/bin/bash
# 验证斜杠命令文件格式正确性

COMMANDS_DIR="$(dirname "$0")/../commands"
ERRORS=0

echo "🔍 验证斜杠命令文件..."
echo ""

for file in "$COMMANDS_DIR"/*.md; do
    [ -f "$file" ] || continue
    filename=$(basename "$file")

    # 跳过 README
    [ "$filename" = "README.md" ] && continue

    echo "检查: $filename"

    # 检查是否有祈使句
    if ! grep -qE "^请执行|^运行|^读取|^执行" "$file"; then
        echo "  ❌ 缺少祈使句指令（请执行/运行/读取）"
        ERRORS=$((ERRORS + 1))
    else
        echo "  ✅ 包含执行指令"
    fi

    # 检查是否有代码块
    if ! grep -q '```bash' "$file"; then
        echo "  ❌ 缺少 bash 代码块"
        ERRORS=$((ERRORS + 1))
    else
        echo "  ✅ 包含 bash 代码块"
    fi

    # 检查是否有描述性标题（不好的模式）
    if grep -qE "^# /.*- " "$file"; then
        echo "  ⚠️  包含描述性标题，建议移除"
    fi

    echo ""
done

echo "================================"
if [ $ERRORS -eq 0 ]; then
    echo "✅ 所有命令文件格式正确"
    exit 0
else
    echo "❌ 发现 $ERRORS 个问题"
    exit 1
fi
