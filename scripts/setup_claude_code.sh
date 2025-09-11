#!/bin/bash
# Claude Code 集成配置脚本
# 自动配置Session Coordinator MCP系统到Claude Code

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

# 显示使用说明
show_usage() {
    echo "Claude Code Session Coordinator 配置脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  --project-id ID     项目标识符 (必需)"
    echo "  --claude-config DIR Claude配置目录 (默认: ~/.claude)"
    echo "  --global            配置为全局MCP服务器"
    echo "  --local             配置为项目本地MCP服务器 (默认)"
    echo "  --help              显示此帮助"
    echo ""
    echo "示例:"
    echo "  $0 --project-id ECOMMERCE"
    echo "  $0 --project-id BLOG --global"
    echo ""
}

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."
    
    # 检查Python3
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未安装"
        exit 1
    fi
    
    # 检查tmux
    if ! command -v tmux &> /dev/null; then
        log_error "tmux 未安装"
        exit 1
    fi
    
    # 检查Claude Code (可选)
    if command -v claude &> /dev/null; then
        log_success "Claude Code 已安装"
    else
        log_warning "Claude Code 未检测到，请确保已正确安装"
    fi
    
    log_success "依赖检查通过"
}

# 验证MCP服务器
validate_mcp_server() {
    log_info "验证MCP服务器..."
    
    cd "$PROJECT_ROOT"
    
    if python3 -c "
import sys
sys.path.insert(0, '.')
from src.mcp_server.session_coordinator import SessionCoordinatorMCP
coordinator = SessionCoordinatorMCP('validation')
print('MCP服务器验证通过')
"; then
        log_success "MCP服务器配置正确"
    else
        log_error "MCP服务器配置有问题"
        exit 1
    fi
}

# 配置MCP服务器到Claude Code
configure_mcp_server() {
    local claude_config_dir="$1"
    local is_global="$2"
    
    log_info "配置MCP服务器到Claude Code..."
    
    # 创建Claude配置目录
    mkdir -p "$claude_config_dir"
    
    # MCP服务器配置
    local mcp_config="{
  \"mcpServers\": {
    \"session-coordinator\": {
      \"command\": [\"python3\", \"-m\", \"src.mcp_server.server\"],
      \"args\": [],
      \"cwd\": \"$PROJECT_ROOT\",
      \"timeout\": 30000,
      \"env\": {
        \"PYTHONPATH\": \"$PROJECT_ROOT\"
      }
    }
  }
}"
    
    # 配置文件路径
    local config_file="$claude_config_dir/config.json"
    
    if [ -f "$config_file" ]; then
        log_warning "配置文件已存在: $config_file"
        log_info "创建备份..."
        cp "$config_file" "$config_file.backup.$(date +%Y%m%d_%H%M%S)"
    fi
    
    # 写入配置
    echo "$mcp_config" > "$config_file"
    
    log_success "MCP服务器配置已写入: $config_file"
}

# 生成项目hooks配置
generate_project_hooks() {
    local project_id="$1"
    
    log_info "生成项目hooks配置..."
    
    cd "$PROJECT_ROOT"
    
    # 生成主会话hooks
    local master_session="master_project_$project_id"
    python3 -m src.hooks.hooks_manager generate master "$master_session" \
        --project-id "$project_id" \
        --output "config/hooks/${master_session}_hooks.json"
    
    # 生成示例子会话hooks (AUTH任务)
    local child_session="child_${project_id}_task_AUTH"
    python3 -m src.hooks.hooks_manager generate child "$child_session" \
        --project-id "$project_id" \
        --master-session-id "$master_session" \
        --task-id "AUTH" \
        --output "config/hooks/${child_session}_hooks.json"
    
    log_success "项目hooks配置已生成"
    log_info "主会话配置: config/hooks/${master_session}_hooks.json"
    log_info "子会话配置: config/hooks/${child_session}_hooks.json"
}

# 创建启动脚本
create_startup_scripts() {
    local project_id="$1"
    
    log_info "创建启动脚本..."
    
    local scripts_dir="$PROJECT_ROOT/scripts"
    mkdir -p "$scripts_dir"
    
    # 主会话启动脚本
    local master_script="$scripts_dir/start_master_$project_id.sh"
    cat > "$master_script" << EOF
#!/bin/bash
# 启动主会话: master_project_$project_id

PROJECT_ROOT="$PROJECT_ROOT"
SESSION_NAME="master_project_$project_id"

echo "启动主会话: \$SESSION_NAME"

tmux new-session -s "\$SESSION_NAME" -d \\
  -e "PROJECT_ID=$project_id" \\
  -e "SESSION_ROLE=master" \\
  -e "HOOKS_CONFIG_PATH=\$PROJECT_ROOT/config/hooks/\${SESSION_NAME}_hooks.json" \\
  "claude"

echo "主会话已启动，使用以下命令连接:"
echo "tmux attach-session -t \$SESSION_NAME"
EOF
    
    # 子会话启动脚本模板
    local child_script="$scripts_dir/start_child_$project_id.sh"
    cat > "$child_script" << EOF
#!/bin/bash
# 启动子会话脚本模板

PROJECT_ROOT="$PROJECT_ROOT"
PROJECT_ID="$project_id"
MASTER_SESSION="master_project_$project_id"

# 使用方法: $0 TASK_ID
if [ -z "\$1" ]; then
    echo "用法: \$0 TASK_ID"
    echo "示例: \$0 AUTH"
    exit 1
fi

TASK_ID="\$1"
SESSION_NAME="child_\${PROJECT_ID}_task_\${TASK_ID}"

echo "启动子会话: \$SESSION_NAME (任务: \$TASK_ID)"

tmux new-session -s "\$SESSION_NAME" -d \\
  -e "PROJECT_ID=\$PROJECT_ID" \\
  -e "TASK_ID=\$TASK_ID" \\
  -e "MASTER_SESSION_ID=\$MASTER_SESSION" \\
  -e "SESSION_ROLE=child" \\
  -e "HOOKS_CONFIG_PATH=\$PROJECT_ROOT/config/hooks/\${SESSION_NAME}_hooks.json" \\
  "claude"

echo "子会话已启动，使用以下命令连接:"
echo "tmux attach-session -t \$SESSION_NAME"
EOF
    
    # 设置执行权限
    chmod +x "$master_script"
    chmod +x "$child_script"
    
    log_success "启动脚本已创建"
    log_info "主会话启动: $master_script"
    log_info "子会话启动: $child_script TASK_ID"
}

# 创建管理脚本
create_management_scripts() {
    local project_id="$1"
    
    log_info "创建管理脚本..."
    
    local scripts_dir="$PROJECT_ROOT/scripts"
    
    # 状态查询脚本
    local status_script="$scripts_dir/status_$project_id.sh"
    cat > "$status_script" << EOF
#!/bin/bash
# 查询项目状态: $project_id

PROJECT_ROOT="$PROJECT_ROOT"
PROJECT_ID="$project_id"
MASTER_SESSION="master_project_$project_id"

echo "=== $project_id 项目状态 ==="
echo ""

# 检查tmux会话
echo "活跃会话:"
tmux list-sessions 2>/dev/null | grep "$project_id" || echo "  无相关会话运行"
echo ""

# 查询MCP系统状态
echo "MCP系统状态:"
cd "\$PROJECT_ROOT"
python3 -c "
from src.mcp_server.session_coordinator import SessionCoordinatorMCP
import json
coordinator = SessionCoordinatorMCP('status-check')
result = coordinator.get_child_sessions('\$MASTER_SESSION')
data = json.loads(result)
print(f'  子会话数量: {data[\"child_count\"]}')
if data['children']:
    print('  子会话详情:')
    for child in data['children']:
        print(f'    - {child[\"session_name\"]}: {child[\"status\"]} ({child[\"progress\"]}%)')
else:
    print('  暂无活跃子会话')
"
EOF
    
    # 清理脚本
    local cleanup_script="$scripts_dir/cleanup_$project_id.sh"
    cat > "$cleanup_script" << EOF
#!/bin/bash
# 清理项目会话: $project_id

PROJECT_ID="$project_id"

echo "清理 $project_id 项目的所有会话..."

# 终止所有相关tmux会话
tmux list-sessions 2>/dev/null | grep "$project_id" | cut -d: -f1 | while read session; do
    echo "终止会话: \$session"
    tmux kill-session -t "\$session" 2>/dev/null || true
done

echo "清理完成"
EOF
    
    # 设置执行权限
    chmod +x "$status_script"
    chmod +x "$cleanup_script"
    
    log_success "管理脚本已创建"
    log_info "状态查询: $status_script"
    log_info "清理会话: $cleanup_script"
}

# 运行测试验证
run_tests() {
    log_info "运行集成测试..."
    
    cd "$PROJECT_ROOT"
    
    # 运行验证脚本
    if python3 scripts/validate_mcp_system.py > /dev/null 2>&1; then
        log_success "系统验证通过"
    else
        log_warning "系统验证有部分问题，但可以继续使用"
    fi
    
    # 运行MCP工具演示
    log_info "运行MCP工具演示..."
    if python3 docs/mcp-tools-demo.py > /dev/null 2>&1; then
        log_success "MCP工具演示通过"
    else
        log_warning "MCP工具演示有问题，请检查配置"
    fi
}

# 显示完成信息
show_completion_info() {
    local project_id="$1"
    local claude_config_dir="$2"
    
    echo ""
    log_success "🎉 Claude Code 集成配置完成！"
    echo ""
    echo "📋 配置摘要:"
    echo "  项目ID: $project_id"
    echo "  Claude配置目录: $claude_config_dir"
    echo "  MCP服务器: session-coordinator"
    echo "  项目根目录: $PROJECT_ROOT"
    echo ""
    echo "🚀 下一步操作:"
    echo "  1. 启动主会话: bash scripts/start_master_$project_id.sh"
    echo "  2. 启动子会话: bash scripts/start_child_$project_id.sh AUTH"
    echo "  3. 查看状态: bash scripts/status_$project_id.sh"
    echo "  4. 清理会话: bash scripts/cleanup_$project_id.sh"
    echo ""
    echo "📚 文档参考:"
    echo "  - 详细使用指南: docs/claude-code-integration.md"
    echo "  - 使用手册: docs/usage-guide.md"
    echo "  - MCP工具演示: python3 docs/mcp-tools-demo.py"
    echo ""
    echo "💡 提示:"
    echo "  - 确保Claude Code已正确安装"
    echo "  - 检查MCP服务器配置: $claude_config_dir/config.json"
    echo "  - 在Claude Code中使用MCP工具时，会自动通过hooks系统进行状态同步"
    echo ""
}

# 主函数
main() {
    local project_id=""
    local claude_config_dir="$HOME/.claude"
    local is_global=false
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --project-id)
                project_id="$2"
                shift 2
                ;;
            --claude-config)
                claude_config_dir="$2"
                shift 2
                ;;
            --global)
                is_global=true
                shift
                ;;
            --local)
                is_global=false
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                log_error "未知参数: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # 验证必需参数
    if [ -z "$project_id" ]; then
        log_error "缺少必需参数: --project-id"
        show_usage
        exit 1
    fi
    
    echo "==============================================="
    echo "   Claude Code Session Coordinator 配置"
    echo "==============================================="
    echo ""
    
    # 执行配置步骤
    check_dependencies
    validate_mcp_server
    configure_mcp_server "$claude_config_dir" "$is_global"
    generate_project_hooks "$project_id"
    create_startup_scripts "$project_id"
    create_management_scripts "$project_id"
    run_tests
    
    # 显示完成信息
    show_completion_info "$project_id" "$claude_config_dir"
}

# 运行主函数
main "$@"