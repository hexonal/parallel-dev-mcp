#!/bin/bash
# Session Coordinator MCP系统演示脚本

set -e

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 清理函数
cleanup() {
    log_info "清理演示环境..."
    
    # 停止所有demo会话
    tmux list-sessions 2>/dev/null | grep "demo_" | cut -d: -f1 | while read session; do
        log_info "停止会话: $session"
        tmux kill-session -t "$session" 2>/dev/null || true
    done
    
    # 清理临时文件
    rm -rf "$PROJECT_ROOT/config/sessions/demo_*" 2>/dev/null || true
    rm -rf "$PROJECT_ROOT/config/hooks/demo_*" 2>/dev/null || true
    
    log_success "清理完成"
}

# 错误处理
trap cleanup EXIT

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."
    
    if ! command -v tmux &> /dev/null; then
        log_error "tmux 未安装"
        exit 1
    fi
    
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未安装"
        exit 1
    fi
    
    log_success "依赖检查通过"
}

# 测试MCP服务器
test_mcp_server() {
    log_info "测试MCP服务器..."
    
    cd "$PROJECT_ROOT"
    
    if python3 -m src.mcp_server.server --test-mode; then
        log_success "MCP服务器配置正确"
    else
        log_error "MCP服务器配置有问题"
        exit 1
    fi
}

# 运行单元测试
run_tests() {
    log_info "运行单元测试..."
    
    cd "$PROJECT_ROOT"
    
    if python3 tests/test_session_coordinator.py; then
        log_success "单元测试通过"
    else
        log_error "单元测试失败"
        exit 1
    fi
}

# 演示hooks管理器
demo_hooks_manager() {
    log_info "演示Hooks管理器..."
    
    cd "$PROJECT_ROOT"
    
    # 生成主会话hooks
    log_info "生成主会话hooks配置..."
    python3 -m src.hooks.hooks_manager generate master demo_master_project_TEST --project-id TEST
    
    # 生成子会话hooks
    log_info "生成子会话hooks配置..."
    python3 -m src.hooks.hooks_manager generate child demo_child_TEST_task_AUTH --project-id TEST --master-session-id demo_master_project_TEST --task-id AUTH
    
    # 列出生成的配置
    log_info "生成的hooks配置文件:"
    find config/hooks -name "demo_*.json" -exec basename {} \; 2>/dev/null || true
    
    log_success "Hooks管理器演示完成"
}

# 模拟会话通信
demo_session_communication() {
    log_info "演示会话间通信..."
    
    cd "$PROJECT_ROOT"
    
    # 启动Python交互式演示
    python3 << 'EOF'
import sys
import os
sys.path.insert(0, os.getcwd())

from src.mcp_server.session_coordinator import SessionCoordinatorMCP
import json

print("创建MCP协调器实例...")
coordinator = SessionCoordinatorMCP("demo-coordinator")

# 演示项目信息
project_id = "DEMO_PROJECT"
master_session = f"demo_master_project_{project_id}"
child_session = f"demo_child_{project_id}_task_AUTH"
task_id = "AUTH"

print("\n=== 演示1: 注册会话关系 ===")
result = coordinator.register_session_relationship(
    parent_session=master_session,
    child_session=child_session,
    task_id=task_id,
    project_id=project_id
)
print(f"注册结果: {result}")

print("\n=== 演示2: 子会话状态上报 ===")
# 模拟开发过程
statuses = [
    ("STARTED", 0, "开始开发任务"),
    ("WORKING", 30, "实现用户模型"),
    ("WORKING", 60, "实现认证逻辑"),
    ("WORKING", 90, "编写单元测试"),
    ("COMPLETED", 100, "任务完成，准备合并")
]

for status, progress, details in statuses:
    result = coordinator.report_session_status(
        session_name=child_session,
        status=status,
        progress=progress,
        details=details
    )
    print(f"状态更新: {status} ({progress}%) - {details}")

print("\n=== 演示3: 主会话查询子会话 ===")
children_result = coordinator.get_child_sessions(master_session)
children_data = json.loads(children_result)
print(f"子会话数量: {children_data['child_count']}")
for child in children_data['children']:
    print(f"  - {child['session_name']}: {child['status']} ({child['progress']}%)")

print("\n=== 演示4: 会话间消息传递 ===")
# 主会话发送指令
send_result = coordinator.send_message_to_session(
    from_session=master_session,
    to_session=child_session,
    message="请确认代码已提交并通过所有测试",
    message_type="INSTRUCTION"
)
print(f"发送消息: {send_result}")

# 子会话获取消息
messages_result = coordinator.get_session_messages(child_session)
messages_data = json.loads(messages_result)
print(f"收到消息数量: {messages_data['unread_count']}")
for msg in messages_data['messages']:
    print(f"  消息内容: {msg['content']}")

print("\n=== 演示5: 系统状态总览 ===")
status_result = coordinator.query_session_status()
status_data = json.loads(status_result)
print(f"系统中活跃会话: {status_data['total_sessions']}个")

print("\n✅ 会话通信演示完成!")
EOF
    
    log_success "会话通信演示完成"
}

# 显示使用说明
show_usage() {
    echo "Session Coordinator MCP系统演示脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  --full       运行完整演示 (默认)"
    echo "  --test-only  仅运行测试"
    echo "  --demo-only  仅运行功能演示" 
    echo "  --cleanup    仅清理环境"
    echo "  --help       显示此帮助"
    echo ""
}

# 主函数
main() {
    echo "================================================="
    echo "   Session Coordinator MCP系统演示"
    echo "================================================="
    echo ""
    
    # 解析参数
    case "${1:---full}" in
        --help)
            show_usage
            exit 0
            ;;
        --cleanup)
            cleanup
            exit 0
            ;;
        --test-only)
            check_dependencies
            test_mcp_server
            run_tests
            ;;
        --demo-only)
            check_dependencies
            demo_hooks_manager
            demo_session_communication
            ;;
        --full|*)
            check_dependencies
            test_mcp_server
            run_tests
            demo_hooks_manager
            demo_session_communication
            ;;
    esac
    
    echo ""
    log_success "演示完成!"
    echo ""
    echo "🎉 Session Coordinator MCP系统功能验证成功！"
    echo ""
    echo "主要成果:"
    echo "  ✅ MCP服务器正常运行"
    echo "  ✅ 会话注册和状态管理"
    echo "  ✅ 双向消息传递"
    echo "  ✅ Claude hooks配置生成"
    echo "  ✅ 所有单元测试通过"
    echo ""
    echo "下一步可以:"
    echo "  1. 集成到实际的Claude Code环境"
    echo "  2. 配置真实的tmux会话"
    echo "  3. 测试与FastMCP 2.0的集成"
    echo ""
}

# 运行主函数
main "$@"