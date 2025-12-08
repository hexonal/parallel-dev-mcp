#!/bin/bash
#
# 加密通信端到端测试
#
# 使用 tmux 启动 Master 和 Worker 进程进行真实测试
#

set -e

SESSION_NAME="parallel-dev-encryption-test"
PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"

echo "=========================================="
echo "  ParallelDev 加密通信 E2E 测试"
echo "=========================================="
echo ""
echo "项目目录: $PROJECT_DIR"
echo "tmux 会话: $SESSION_NAME"
echo ""

# 检查 tmux 是否安装
if ! command -v tmux &> /dev/null; then
    echo "❌ 错误: 未安装 tmux"
    echo "请运行: brew install tmux"
    exit 1
fi

# 杀死已存在的会话
tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true

# 创建临时文件用于传递密钥
KEY_FILE="/tmp/parallel-dev-encryption-key.txt"
rm -f "$KEY_FILE"

echo "📦 创建 tmux 会话..."

# 创建新会话，运行 Master
tmux new-session -d -s "$SESSION_NAME" -c "$PROJECT_DIR" \
    "echo '🚀 启动 Master 服务器...' && npx tsx scripts/test-encryption/master.ts 2>&1 | tee >(grep -o 'Base64.*' | head -1 | cut -d' ' -f2 > $KEY_FILE); bash"

# 等待 Master 启动并输出密钥
echo "⏳ 等待 Master 启动..."
sleep 3

# 检查密钥文件
for i in {1..10}; do
    if [ -s "$KEY_FILE" ]; then
        break
    fi
    sleep 1
done

if [ ! -s "$KEY_FILE" ]; then
    echo "❌ 错误: 无法获取加密密钥"
    echo "请手动查看 tmux 会话: tmux attach -t $SESSION_NAME"
    exit 1
fi

ENCRYPTION_KEY=$(cat "$KEY_FILE")
echo "🔑 获取到加密密钥: ${ENCRYPTION_KEY:0:20}..."

# 创建第二个窗格，运行 Worker
echo "📦 启动 Worker 客户端..."
tmux split-window -h -t "$SESSION_NAME" -c "$PROJECT_DIR" \
    "sleep 2 && echo '🚀 启动 Worker 客户端...' && npx tsx scripts/test-encryption/worker.ts '$ENCRYPTION_KEY'; bash"

# 设置窗格布局
tmux select-layout -t "$SESSION_NAME" even-horizontal

echo ""
echo "=========================================="
echo "  测试环境已启动"
echo "=========================================="
echo ""
echo "📺 查看测试: tmux attach -t $SESSION_NAME"
echo ""
echo "操作说明:"
echo "  - 左侧窗格: Master 服务器"
echo "  - 右侧窗格: Worker 客户端"
echo "  - Ctrl+B 然后 方向键: 切换窗格"
echo "  - Ctrl+B 然后 D: 分离会话"
echo "  - Ctrl+C: 停止进程"
echo ""
echo "关闭测试: tmux kill-session -t $SESSION_NAME"
echo ""

# 自动附加到会话
tmux attach -t "$SESSION_NAME"
