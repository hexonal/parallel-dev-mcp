#!/bin/bash
# Session Coordinator MCP服务器启动脚本

set -e

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# 检查Python环境
check_python() {
    log_info "检查Python环境..."
    
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未安装"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
    log_info "Python版本: $PYTHON_VERSION"
    
    # 检查Python版本是否满足要求 (3.11+)
    if [ "$(echo "$PYTHON_VERSION >= 3.11" | bc 2>/dev/null || echo 0)" -eq 0 ]; then
        log_warning "推荐使用Python 3.11或更高版本"
    fi
}

# 检查虚拟环境
check_venv() {
    log_info "检查虚拟环境..."
    
    VENV_PATH="$PROJECT_ROOT/.venv"
    
    if [ ! -d "$VENV_PATH" ]; then
        log_warning "虚拟环境不存在，正在创建..."
        cd "$PROJECT_ROOT"
        python3 -m venv .venv
        log_success "虚拟环境已创建: $VENV_PATH"
    fi
    
    # 激活虚拟环境
    source "$VENV_PATH/bin/activate"
    log_success "虚拟环境已激活"
}

# 安装依赖
install_dependencies() {
    log_info "检查依赖包..."
    
    # 检查是否有requirements.txt
    if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
        log_info "安装依赖包..."
        pip install -r "$PROJECT_ROOT/requirements.txt"
        log_success "依赖包安装完成"
    else
        log_info "安装基础依赖包..."
        # 安装基本的Python包
        pip install --upgrade pip
        # TODO: 根据实际的FastMCP 2.0包名调整
        # pip install fastmcp
        log_success "基础依赖包安装完成"
    fi
}

# 创建必要目录
create_directories() {
    log_info "创建必要目录..."
    
    mkdir -p "$PROJECT_ROOT/logs"
    mkdir -p "$PROJECT_ROOT/config"
    
    log_success "目录创建完成"
}

# 检查配置文件
check_config() {
    log_info "检查配置文件..."
    
    CONFIG_FILE="$PROJECT_ROOT/config/session_coordinator_config.json"
    
    if [ ! -f "$CONFIG_FILE" ]; then
        log_warning "配置文件不存在，将使用默认配置"
    else
        log_success "配置文件存在: $CONFIG_FILE"
    fi
}

# 测试服务器
test_server() {
    log_info "测试服务器配置..."
    
    cd "$PROJECT_ROOT"
    python3 -m src.mcp_server.server --test-mode
    
    if [ $? -eq 0 ]; then
        log_success "服务器配置测试通过"
    else
        log_error "服务器配置测试失败"
        exit 1
    fi
}

# 启动服务器
start_server() {
    log_info "启动Session Coordinator MCP服务器..."
    
    cd "$PROJECT_ROOT"
    
    # 设置PYTHONPATH
    export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
    
    # 启动服务器
    python3 -m src.mcp_server.server "$@"
}

# 显示帮助
show_help() {
    echo "Session Coordinator MCP服务器启动脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  --test-mode    仅测试配置，不启动服务器"
    echo "  --config FILE  指定配置文件路径"
    echo "  --skip-deps    跳过依赖检查和安装"
    echo "  --help         显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0                           # 正常启动"
    echo "  $0 --test-mode              # 测试模式"
    echo "  $0 --config custom.json     # 使用自定义配置"
    echo ""
}

# 主函数
main() {
    echo "=================================================="
    echo "    Session Coordinator MCP服务器启动脚本"
    echo "=================================================="
    echo ""
    
    # 解析参数
    SKIP_DEPS=false
    TEST_MODE=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help)
                show_help
                exit 0
                ;;
            --test-mode)
                TEST_MODE=true
                shift
                ;;
            --skip-deps)
                SKIP_DEPS=true
                shift
                ;;
            *)
                # 其他参数传递给Python脚本
                break
                ;;
        esac
    done
    
    # 环境检查和准备
    check_python
    check_venv
    
    if [ "$SKIP_DEPS" != true ]; then
        install_dependencies
    fi
    
    create_directories
    check_config
    
    if [ "$TEST_MODE" == true ]; then
        test_server
        exit 0
    fi
    
    # 启动服务器
    echo ""
    log_info "准备启动服务器..."
    echo "按 Ctrl+C 停止服务器"
    echo ""
    
    start_server "$@"
}

# 错误处理
trap 'log_error "脚本执行失败"; exit 1' ERR

# 运行主函数
main "$@"