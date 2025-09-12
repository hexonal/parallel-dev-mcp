#!/bin/bash

echo "🧪 开始测试 Claude hooks 集成..."

# 设置测试环境
export HOOKS_CONFIG="/Users/flink/parallel-dev-mcp/config/hooks/mcp_test_hooks.json"
export PROJECT_ROOT="/Users/flink/parallel-dev-mcp"

echo "🔧 测试环境设置:"
echo "  HOOKS_CONFIG: $HOOKS_CONFIG"
echo "  PROJECT_ROOT: $PROJECT_ROOT"

# 验证 hooks 配置文件存在
if [ -f "$HOOKS_CONFIG" ]; then
    echo "✅ Hooks 配置文件存在"
else
    echo "❌ Hooks 配置文件不存在: $HOOKS_CONFIG"
    exit 1
fi

echo -e "\n🎯 测试方案:"
echo "1. 复制当前的 hooks 配置作为备份"
echo "2. 使用 MCP 生成的 hooks 配置替换现有配置"  
echo "3. 启动新的 Claude 会话进行测试"
echo "4. 恢复原始配置"

# 备份当前 hooks 配置
BACKUP_HOOKS="/Users/flink/.claude/hooks/config.json.backup"
if [ -f "/Users/flink/.claude/hooks/config.json" ]; then
    cp "/Users/flink/.claude/hooks/config.json" "$BACKUP_HOOKS"
    echo "✅ 已备份原始 hooks 配置"
fi

# 使用 MCP 生成的配置
cp "$HOOKS_CONFIG" "/Users/flink/.claude/hooks/config.json"
echo "✅ 已应用 MCP 生成的 hooks 配置"

echo -e "\n📋 当前 hooks 配置内容:"
cat "/Users/flink/.claude/hooks/config.json" | python3 -m json.tool

echo -e "\n⚡ 现在需要手动验证:"
echo "1. 在新终端中运行: claude --mcp-config mcp.json --dangerously-skip-permissions"
echo "2. 发送任意消息，观察是否出现: '🎯 MCP生成的Hooks生效: 用户提示已提交'"
echo "3. 验证完成后运行此脚本恢复配置"

read -p "按回车键恢复原始配置..."

# 恢复原始配置
if [ -f "$BACKUP_HOOKS" ]; then
    cp "$BACKUP_HOOKS" "/Users/flink/.claude/hooks/config.json"
    rm "$BACKUP_HOOKS"
    echo "✅ 已恢复原始 hooks 配置"
else
    echo "⚠️  未找到备份，请手动恢复 hooks 配置"
fi

echo "🎉 测试完成"