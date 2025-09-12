#!/bin/bash
# ═══════════════════════════════════════════════════════════
#      ████████╗███╗   ███╗██╗   ██╗██╗  ██╗
#      ╚══██╔══╝████╗ ████║██║   ██║╚██╗██╔╝
#         ██║   ██╔████╔██║██║   ██║ ╚███╔╝ 
#         ██║   ██║╚██╔╝██║██║   ██║ ██╔██╗ 
#         ██║   ██║ ╚═╝ ██║╚██████╔╝██╔╝ ██╗
#         ╚═╝   ╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═╝
#              ELITE HACKER TMUX INSTALLER
#              超级黑客专属·逼格满满·安全无比
# ═══════════════════════════════════════════════════════════

set -e

# 超炫颜色定义
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly WHITE='\033[1;37m'
readonly BOLD='\033[1m'
readonly NC='\033[0m'

# 炫酷图标
readonly ROCKET="🚀"
readonly FIRE="🔥"
readonly LIGHTNING="⚡"
readonly DIAMOND="💎"
readonly SKULL="💀"
readonly MATRIX="🔴"
readonly HACKER="👨‍💻"
readonly GEAR="⚙️"
readonly LOCK="🔒"
readonly WARNING="⚠️"

# 打印超炫横幅
print_banner() {
    clear
    echo -e "${PURPLE}${BOLD}"
    cat << 'EOF'
  ███████╗██╗     ██╗████████╗███████╗    ████████╗███╗   ███╗██╗   ██╗██╗  ██╗
  ██╔════╝██║     ██║╚══██╔══╝██╔════╝    ╚══██╔══╝████╗ ████║██║   ██║╚██╗██╔╝
  █████╗  ██║     ██║   ██║   █████╗         ██║   ██╔████╔██║██║   ██║ ╚███╔╝ 
  ██╔══╝  ██║     ██║   ██║   ██╔══╝         ██║   ██║╚██╔╝██║██║   ██║ ██╔██╗ 
  ███████╗███████╗██║   ██║   ███████╗       ██║   ██║ ╚═╝ ██║╚██████╔╝██╔╝ ██╗
  ╚══════╝╚══════╝╚═╝   ╚═╝   ╚══════╝       ╚═╝   ╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═╝
                                                                               
EOF
    echo -e "${NC}"
    echo -e "${CYAN}${BOLD}                 逼格满满 · 极客专属 · 安全无比${NC}"
    echo -e "${WHITE}                   ════════════════════════════════${NC}"
    echo ""
}

# 炫酷日志函数
log_info() {
    echo -e "${BLUE}${LIGHTNING}${BOLD} [INFO] ${NC}$1"
}

log_success() {
    echo -e "${GREEN}${FIRE}${BOLD} [SUCCESS] ${NC}$1"
}

log_warning() {
    echo -e "${YELLOW}${WARNING}${BOLD} [WARNING] ${NC}$1"
}

log_error() {
    echo -e "${RED}${SKULL}${BOLD} [ERROR] ${NC}$1"
}

log_hacker() {
    echo -e "${PURPLE}${HACKER}${BOLD} [HACKER] ${NC}$1"
}

log_secure() {
    echo -e "${GREEN}${LOCK}${BOLD} [SECURE] ${NC}$1"
}

# 检测系统信息
detect_system() {
    log_info "正在检测系统环境..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        if command -v lsb_release &> /dev/null; then
            DISTRO=$(lsb_release -si)
        elif [[ -f /etc/os-release ]]; then
            DISTRO=$(grep ^NAME /etc/os-release | cut -d'"' -f2 | cut -d' ' -f1)
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        DISTRO="macOS $(sw_vers -productVersion)"
    else
        log_error "不支持的操作系统: $OSTYPE"
        exit 1
    fi
    
    log_success "系统检测完成: $DISTRO"
}

# 检查并安装依赖
install_dependencies() {
    log_info "正在安装必要依赖..."
    
    # 安装tmux
    if ! command -v tmux &> /dev/null; then
        log_warning "tmux未安装，正在安装..."
        if [[ "$OS" == "macos" ]]; then
            if command -v brew &> /dev/null; then
                brew install tmux
            else
                log_error "请先安装Homebrew: https://brew.sh"
                exit 1
            fi
        elif [[ "$OS" == "linux" ]]; then
            if command -v apt &> /dev/null; then
                sudo apt update && sudo apt install -y tmux git curl
            elif command -v yum &> /dev/null; then
                sudo yum install -y tmux git curl
            elif command -v pacman &> /dev/null; then
                sudo pacman -S tmux git curl
            fi
        fi
    else
        local version=$(tmux -V)
        log_success "tmux已安装: $version"
    fi
    
    # 检查Nerd Font (可选)
    log_info "检查Nerd Font字体支持..."
    if [[ "$OS" == "macos" ]]; then
        # 检查多个可能的字体路径
        FONT_FOUND=false
        
        # 检查用户字体目录
        if ls ~/Library/Fonts/*Nerd* 2>/dev/null | head -1 >/dev/null; then
            FONT_FOUND=true
        fi
        
        # 检查系统字体目录
        if ls /System/Library/Fonts/*Nerd* 2>/dev/null | head -1 >/dev/null; then
            FONT_FOUND=true
        fi
        
        # 检查 Homebrew 安装的字体
        if ls /opt/homebrew/Caskroom/font-*nerd* 2>/dev/null | head -1 >/dev/null; then
            FONT_FOUND=true
        fi
        
        # 检查旧版 Homebrew 路径
        if ls /usr/local/Caskroom/font-*nerd* 2>/dev/null | head -1 >/dev/null; then
            FONT_FOUND=true
        fi
        
        # 使用 fc-list 命令检查（如果可用）
        if command -v fc-list &> /dev/null; then
            if fc-list | grep -i "nerd\|mono" >/dev/null 2>&1; then
                FONT_FOUND=true
            fi
        fi
        
        # 检查常见的 Nerd Font 字体名
        for font in "JetBrainsMono" "FiraCode" "Hack" "SourceCodePro" "Inconsolata" "DroidSansMono"; do
            if ls ~/Library/Fonts/*${font}*Nerd* 2>/dev/null | head -1 >/dev/null; then
                FONT_FOUND=true
                break
            fi
        done
        
        if [[ "$FONT_FOUND" == "false" ]]; then
            log_warning "建议安装Nerd Font字体以获得最佳图标显示效果"
            echo "推荐字体: JetBrains Mono Nerd Font, Fira Code Nerd Font"
            read -p "是否安装 JetBrains Mono Nerd Font? (y/n): " install_font
            if [[ "$install_font" == "y" || "$install_font" == "Y" ]]; then
                if command -v brew &> /dev/null; then
                    log_info "正在安装字体..."
                    brew install --cask font-jetbrains-mono-nerd-font 2>/dev/null || true
                    log_success "字体安装完成！重启终端后生效"
                else
                    log_warning "请手动安装 JetBrains Mono Nerd Font"
                    echo "下载地址: https://github.com/ryanoasis/nerd-fonts/releases"
                fi
            fi
        else
            log_success "检测到Nerd Font字体，图标显示将正常工作"
        fi
    fi
}

# 主题选择菜单
choose_theme() {
    echo ""
    echo -e "${BOLD}${DIAMOND} 选择您的极客主题 ${DIAMOND}${NC}"
    echo -e "${PURPLE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${CYAN}1)${NC} ${FIRE} Elite Hacker    ${YELLOW}(Catppuccin黑客风·真正的极客美学)${NC}"
    echo -e "${CYAN}2)${NC} ${LIGHTNING} Cyberpunk 2077 ${YELLOW}(霓虹夜城·赛博朋克·未来已来)${NC}"
    echo -e "${CYAN}3)${NC} ${MATRIX} Matrix Digital  ${YELLOW}(数字雨瀑布·Neo的选择·觉醒时刻)${NC}"
    echo -e "${CYAN}4)${NC} ${DIAMOND} Crystal Blue   ${YELLOW}(水晶蓝调·优雅渐变·沉静致远)${NC}"
    echo -e "${CYAN}5)${NC} ${LOCK} Safe Mode      ${YELLOW}(极简安全·IDE完美兼容·企业友好)${NC}"
    echo ""
    echo -e "${WHITE}💡 所有主题都包含：完全配置重置、会话隔离、IDE友好特性、完整复制粘贴功能${NC}"
    echo -e "${GREEN}🔥 新增特性：Vi风格复制、鼠标选择、系统剪贴板集成、搜索翻页等${NC}"
    echo ""
    
    while true; do
        read -p "$(echo -e ${BOLD}"请选择您的专属主题 (1-5): "${NC})" theme_choice
        case $theme_choice in
            1) THEME="elite"; log_hacker "已选择 Elite Hacker - 真正的黑客美学！"; break;;
            2) THEME="cyberpunk"; log_hacker "已选择 Cyberpunk 2077 - 欢迎来到夜之城！"; break;;
            3) THEME="matrix"; log_hacker "已选择 Matrix Digital - Neo，欢迎来到真实世界！"; break;;
            4) THEME="crystal"; log_hacker "已选择 Crystal Blue - 如水晶般纯净优雅！"; break;;
            5) THEME="safe"; log_secure "已选择 Safe Mode - 企业级安全与兼容！"; break;;
            *) log_error "请选择 1-5 之间的数字";;
        esac
    done
}

# 备份现有配置
backup_config() {
    if [[ -f ~/.tmux.conf ]]; then
        local backup_file=~/.tmux.conf.backup.$(date +%Y%m%d_%H%M%S)
        cp ~/.tmux.conf "$backup_file"
        log_warning "已备份现有配置到: $backup_file"
    fi
    
    # 清理可能的问题配置
    for shell_config in ~/.zshrc ~/.bashrc ~/.bash_profile; do
        if [[ -f "$shell_config" ]] && grep -q "ELITE TMUX" "$shell_config" 2>/dev/null; then
            local backup_shell="${shell_config}.backup.$(date +%Y%m%d_%H%M%S)"
            cp "$shell_config" "$backup_shell"
            log_warning "已备份shell配置: $backup_shell"
        fi
    done
}

# 安装配置文件
install_config() {
    log_info "正在安装安全的tmux配置..."
    
    case $THEME in
        "elite")
            create_elite_config
            ;;
        "cyberpunk")
            create_cyberpunk_config
            ;;
        "matrix")
            create_matrix_config
            ;;
        "crystal") 
            create_crystal_config
            ;;
        "safe")
            create_safe_config
            ;;
    esac
    
    log_success "安全配置已安装！"
}

# 创建Elite Hacker主题配置 - 真正的极客风格
create_elite_config() {
    cat > ~/.tmux.conf << 'EOF'
# ═══════════════════════════════════════════════════════════
#      ████████╗███╗   ███╗██╗   ██╗██╗  ██╗
#      ╚══██╔══╝████╗ ████║██║   ██║╚██╗██╔╝
#         ██║   ██╔████╔██║██║   ██║ ╚███╔╝ 
#         ██║   ██║╚██╔╝██║██║   ██║ ██╔██╗ 
#         ██║   ██║ ╚═╝ ██║╚██████╔╝██╔╝ ██╗
#         ╚═╝   ╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═╝
#              ELITE HACKER CONFIGURATION
#              逼格满满·极客专属·安全无比
# ═══════════════════════════════════════════════════════════

# ── 完全重置所有默认设置 ──────────────────────────────────────
# 清除所有快捷键绑定
unbind-key -a

# 重置所有选项到安全默认值
set-option -g prefix C-space
set-option -g prefix2 None
set-option -g status on
set-option -g status-interval 15

# ── 核心性能设置 ──────────────────────────────────────
set-option -g default-terminal "tmux-256color"
set-option -ga terminal-overrides ",*256col*:Tc"
set-option -ga terminal-overrides '*:Ss=\E[%p1%d q:Se=\E[ q'
set-environment -g COLORTERM "truecolor"

set-option -s escape-time 0
set-option -g repeat-time 1000
set-option -g history-limit 100000
set-option -g buffer-limit 20
set-option -g display-time 2000
set-option -g remain-on-exit off

# ── 会话安全和IDE友好设置 ──────────────────────────────────────
# 确保每个会话独立，不共享 - 重要安全设置！
# 注意: default-path 在新版tmux中已废弃，使用其他方式确保会话隔离
set-option -g default-command ""
# IDE友好：禁止tmux控制终端标题
set-option -g set-titles off
set-option -g allow-rename off

# ── 索引和窗口设置 ──────────────────────────────────────
set-option -g base-index 1
set-window-option -g pane-base-index 1
set-option -g renumber-windows on
set-option -g automatic-rename on
set-option -g automatic-rename-format '#{?#{==:#{pane_current_command},zsh},#{b:pane_current_path},#{pane_current_command}}'

# ── 极客鼠标设置 ──────────────────────────────────────
set-option -g mouse on

# ── 极客前缀键 ──────────────────────────────────────
bind-key C-space send-prefix

# ── 超级快捷键绑定 ──────────────────────────────────────
# 配置重载（带炫酷提示）
bind-key r source-file ~/.tmux.conf \; display-message "⚡ ELITE CONFIG RELOADED! ⚡"

# 窗口和面板操作
bind-key c new-window -c "#{pane_current_path}"
bind-key | split-window -h -c "#{pane_current_path}"
bind-key - split-window -v -c "#{pane_current_path}"
bind-key x kill-pane
bind-key & kill-window

# Vim风格面板导航（黑客必备）
bind-key h select-pane -L
bind-key j select-pane -D  
bind-key k select-pane -U
bind-key l select-pane -R

# 面板大小调整（精确控制）
bind-key -r H resize-pane -L 5
bind-key -r J resize-pane -D 5
bind-key -r K resize-pane -U 5
bind-key -r L resize-pane -R 5

# 快速面板切换
bind-key Tab last-pane
bind-key Space next-layout

# 窗口切换
bind-key -r p previous-window
bind-key -r n next-window
bind-key -r [ swap-window -t -1\; select-window -t -1
bind-key -r ] swap-window -t +1\; select-window -t +1

# 面板缩放切换
bind-key z resize-pane -Z

# ── 复制模式（极客级别）──────────────────────────────────────
set-window-option -g mode-keys vi

# 复制模式快捷键
bind-key Enter copy-mode
bind-key [ copy-mode
bind-key Escape copy-mode

# Vi风格选择和复制
bind-key -T copy-mode-vi v send-keys -X begin-selection
bind-key -T copy-mode-vi V send-keys -X select-line
bind-key -T copy-mode-vi C-v send-keys -X rectangle-toggle
bind-key -T copy-mode-vi y send-keys -X copy-pipe-and-cancel "pbcopy"
bind-key -T copy-mode-vi Y send-keys -X copy-end-of-line
bind-key -T copy-mode-vi Escape send-keys -X cancel
bind-key -T copy-mode-vi q send-keys -X cancel

# 移动快捷键
bind-key -T copy-mode-vi h send-keys -X cursor-left
bind-key -T copy-mode-vi j send-keys -X cursor-down
bind-key -T copy-mode-vi k send-keys -X cursor-up
bind-key -T copy-mode-vi l send-keys -X cursor-right
bind-key -T copy-mode-vi H send-keys -X start-of-line
bind-key -T copy-mode-vi L send-keys -X end-of-line
bind-key -T copy-mode-vi 0 send-keys -X start-of-line
bind-key -T copy-mode-vi $ send-keys -X end-of-line
bind-key -T copy-mode-vi w send-keys -X next-word
bind-key -T copy-mode-vi e send-keys -X next-word-end
bind-key -T copy-mode-vi b send-keys -X previous-word
bind-key -T copy-mode-vi g send-keys -X history-top
bind-key -T copy-mode-vi G send-keys -X history-bottom
bind-key -T copy-mode-vi / send-keys -X search-forward
bind-key -T copy-mode-vi ? send-keys -X search-backward
bind-key -T copy-mode-vi n send-keys -X search-again
bind-key -T copy-mode-vi N send-keys -X search-reverse

# 翻页快捷键
bind-key -T copy-mode-vi C-u send-keys -X halfpage-up
bind-key -T copy-mode-vi C-d send-keys -X halfpage-down
bind-key -T copy-mode-vi C-b send-keys -X page-up
bind-key -T copy-mode-vi C-f send-keys -X page-down

# 鼠标支持（完整复制选择功能）
bind-key -T copy-mode-vi MouseDragEnd1Pane send-keys -X copy-pipe-and-cancel "pbcopy"
bind-key -T copy-mode MouseDragEnd1Pane send-keys -X copy-pipe-and-cancel "pbcopy"
bind-key -T copy-mode-vi DoubleClick1Pane select-pane \; send-keys -X select-word \; send-keys -X copy-pipe-and-cancel "pbcopy"
bind-key -T copy-mode-vi TripleClick1Pane select-pane \; send-keys -X select-line \; send-keys -X copy-pipe-and-cancel "pbcopy"

# 粘贴快捷键
bind-key p paste-buffer
bind-key P choose-buffer

# ── ELITE HACKER 颜色主题 ──────────────────────────────────────
# 基于 Catppuccin Mocha 配色，专为黑客定制

# 状态栏主题
set-option -g status-style "fg=#cdd6f4,bg=#11111b"
set-option -g status-left-length 100
set-option -g status-right-length 100

# 左侧状态 - 会话信息
set-option -g status-left "#[fg=#11111b,bg=#89b4fa,bold] 󱂬 #S #[fg=#89b4fa,bg=#313244]#[fg=#cdd6f4,bg=#313244] 󰇘 #I/#P #[fg=#313244,bg=#11111b]"

# 右侧状态 - 系统信息
set-option -g status-right "#[fg=#313244,bg=#11111b]#[fg=#cdd6f4,bg=#313244] 󱑋 #{?client_prefix,󰠠 ,}#[fg=#f9e2af,bg=#313244]󰥔 %H:%M #[fg=#89b4fa,bg=#313244]#[fg=#11111b,bg=#89b4fa,bold] 󰸗 %a %m/%d "

# 窗口状态 - 未激活
set-option -g window-status-format "#[fg=#11111b,bg=#313244]#[fg=#cdd6f4,bg=#313244] #I #[fg=#6c7086,bg=#313244]󰖲 #W#[fg=#cdd6f4]#{?window_zoomed_flag, 󰍉,} #[fg=#313244,bg=#11111b]"

# 窗口状态 - 激活（炫酷高亮）
set-option -g window-status-current-format "#[fg=#11111b,bg=#89b4fa]#[fg=#11111b,bg=#89b4fa,bold] #I #[fg=#11111b,bg=#89b4fa]󰖯 #W#[fg=#11111b]#{?window_zoomed_flag, 󰍉,} #[fg=#89b4fa,bg=#11111b]"

# 窗口状态 - 特殊状态
set-option -g window-status-activity-style "fg=#f38ba8,bg=#313244"
set-option -g window-status-bell-style "fg=#fab387,bg=#313244"

# ── 面板边框主题 ──────────────────────────────────────
set-option -g pane-border-style "fg=#45475a"
set-option -g pane-active-border-style "fg=#89b4fa"

# ── 消息和输入主题 ──────────────────────────────────────
set-option -g message-style "fg=#cdd6f4,bg=#45475a,bold"
set-option -g message-command-style "fg=#cdd6f4,bg=#45475a,bold"
# 复制模式选中效果 - 统一使用绿色高对比度（类似Safe Mode）
set-option -g mode-style "fg=#000000,bg=#00ff00,bold"

# ── 极客启动消息 ──────────────────────────────────────
run-shell 'tmux display-message "🚀 ELITE HACKER TMUX LOADED! Welcome to the Matrix! 💀"'
EOF
}

# 创建Cyberpunk 2077主题配置 - 赛博朋克未来风
create_cyberpunk_config() {
    cat > ~/.tmux.conf << 'EOF'
# ═══════════════════════════════════════════════════════════
#      ▄████▄▓██   ██▓ ▄▄▄▄   ▓█████  ██▀███  
#     ▒██▀ ▀█ ▒██  ██▒▓█████▄ ▓█   ▀ ▓██ ▒ ██▒
#     ▒▓█    ▄ ▒██ ██░▒██▒ ▄██▒███   ▓██ ░▄█ ▒
#     ▒▓▓▄ ▄██▒░ ▐██▓░▒██░█▀  ▒▓█  ▄ ▒██▀▀█▄  
#     ▒ ▓███▀ ░░ ██▒▓░░▓█  ▀█▓░▒████▒░██▓ ▒██▒
#     ░ ░▒ ▒  ░ ██▒▒▒ ░▒▓███▀▒░░ ▒░ ░░ ▒▓ ░▒▓░
#              CYBERPUNK 2077 TERMINAL
#              未来世界·赛博朋克·霓虹夜城
# ═══════════════════════════════════════════════════════════

# ── 完全重置所有默认设置 ──────────────────────────────────────
unbind-key -a
set-option -g prefix C-space
set-option -g prefix2 None

# ── 核心性能设置 ──────────────────────────────────────
set-option -g default-terminal "tmux-256color"
set-option -ga terminal-overrides ",*256col*:Tc"
set-option -s escape-time 0
set-option -g repeat-time 1000
set-option -g history-limit 100000

# ── 会话安全和IDE友好设置 ──────────────────────────────────────
# set-option -g default-path ""  # 已废弃选项，在新版tmux中不再需要
set-option -g default-command ""
set-option -g set-titles off
set-option -g allow-rename off

# ── 索引和窗口设置 ──────────────────────────────────────
set-option -g base-index 1
set-window-option -g pane-base-index 1
set-option -g renumber-windows on
set-option -g automatic-rename on
set-option -g automatic-rename-format '#{?#{==:#{pane_current_command},zsh},[#{b:pane_current_path}],#{pane_current_command}}'

# ── 霓虹鼠标设置 ──────────────────────────────────────
set-option -g mouse on

# ── 赛博朋克前缀键 ──────────────────────────────────────
bind-key C-space send-prefix

# ── 未来快捷键绑定 ──────────────────────────────────────
bind-key r source-file ~/.tmux.conf \; display-message "🔮 CYBERPUNK RELOADED! WELCOME TO THE FUTURE! 🔮"
bind-key c new-window -c "#{pane_current_path}"
bind-key | split-window -h -c "#{pane_current_path}"
bind-key - split-window -v -c "#{pane_current_path}"
bind-key x kill-pane
bind-key & kill-window

# 赛博空间导航
bind-key h select-pane -L
bind-key j select-pane -D  
bind-key k select-pane -U
bind-key l select-pane -R
bind-key -r H resize-pane -L 5
bind-key -r J resize-pane -D 5
bind-key -r K resize-pane -U 5
bind-key -r L resize-pane -R 5
bind-key Tab last-pane
bind-key Space next-layout
bind-key z resize-pane -Z

# ── 神经链接复制模式 ──────────────────────────────────────
set-window-option -g mode-keys vi

# 复制模式快捷键
bind-key Enter copy-mode
bind-key [ copy-mode
bind-key Escape copy-mode

# Vi风格选择和复制
bind-key -T copy-mode-vi v send-keys -X begin-selection
bind-key -T copy-mode-vi V send-keys -X select-line
bind-key -T copy-mode-vi C-v send-keys -X rectangle-toggle
bind-key -T copy-mode-vi y send-keys -X copy-pipe-and-cancel "pbcopy"
bind-key -T copy-mode-vi Y send-keys -X copy-end-of-line
bind-key -T copy-mode-vi Escape send-keys -X cancel
bind-key -T copy-mode-vi q send-keys -X cancel

# 移动快捷键
bind-key -T copy-mode-vi h send-keys -X cursor-left
bind-key -T copy-mode-vi j send-keys -X cursor-down
bind-key -T copy-mode-vi k send-keys -X cursor-up
bind-key -T copy-mode-vi l send-keys -X cursor-right
bind-key -T copy-mode-vi H send-keys -X start-of-line
bind-key -T copy-mode-vi L send-keys -X end-of-line
bind-key -T copy-mode-vi 0 send-keys -X start-of-line
bind-key -T copy-mode-vi $ send-keys -X end-of-line
bind-key -T copy-mode-vi w send-keys -X next-word
bind-key -T copy-mode-vi e send-keys -X next-word-end
bind-key -T copy-mode-vi b send-keys -X previous-word
bind-key -T copy-mode-vi g send-keys -X history-top
bind-key -T copy-mode-vi G send-keys -X history-bottom
bind-key -T copy-mode-vi / send-keys -X search-forward
bind-key -T copy-mode-vi ? send-keys -X search-backward
bind-key -T copy-mode-vi n send-keys -X search-again
bind-key -T copy-mode-vi N send-keys -X search-reverse

# 翻页快捷键
bind-key -T copy-mode-vi C-u send-keys -X halfpage-up
bind-key -T copy-mode-vi C-d send-keys -X halfpage-down
bind-key -T copy-mode-vi C-b send-keys -X page-up
bind-key -T copy-mode-vi C-f send-keys -X page-down

# 鼠标支持（完整复制选择功能）
bind-key -T copy-mode-vi MouseDragEnd1Pane send-keys -X copy-pipe-and-cancel "pbcopy"
bind-key -T copy-mode MouseDragEnd1Pane send-keys -X copy-pipe-and-cancel "pbcopy"
bind-key -T copy-mode-vi DoubleClick1Pane select-pane \; send-keys -X select-word \; send-keys -X copy-pipe-and-cancel "pbcopy"
bind-key -T copy-mode-vi TripleClick1Pane select-pane \; send-keys -X select-line \; send-keys -X copy-pipe-and-cancel "pbcopy"

# 粘贴快捷键
bind-key p paste-buffer
bind-key P choose-buffer

# ── CYBERPUNK 霓虹主题 ──────────────────────────────────────
# 霓虹夜城配色：洋红霓虹 + 青色数据流 + 深空背景

# 状态栏主题
set-option -g status-style "fg=#00ffff,bg=#0d1117"
set-option -g status-left-length 100
set-option -g status-right-length 100

# 左侧状态 - 系统信息（霓虹洋红）
set-option -g status-left "#[fg=#0d1117,bg=#ff00ff,bold] 🔮 #S #[fg=#ff00ff,bg=#161b22]#[fg=#00ffff,bg=#161b22] 󰊠 #I/#P #[fg=#161b22,bg=#0d1117]"

# 右侧状态 - 时间信息（青色数据流）
set-option -g status-right "#[fg=#161b22,bg=#0d1117]#[fg=#ff00ff,bg=#161b22] 󱑋 #{?client_prefix,⚡ ,}#[fg=#00ffff,bg=#161b22]🕐 %H:%M #[fg=#ff00ff,bg=#161b22]#[fg=#0d1117,bg=#ff00ff,bold] 📅 %a %m/%d "

# 窗口状态 - 未激活（数据流青色）
set-option -g window-status-format "#[fg=#0d1117,bg=#161b22]#[fg=#00ffff,bg=#161b22] #I #[fg=#7c3aed,bg=#161b22]🔗 #W#[fg=#00ffff]#{?window_zoomed_flag, 🔍,} #[fg=#161b22,bg=#0d1117]"

# 窗口状态 - 激活（霓虹洋红高亮）
set-option -g window-status-current-format "#[fg=#0d1117,bg=#ff00ff]#[fg=#0d1117,bg=#ff00ff,bold] #I #[fg=#0d1117,bg=#ff00ff]🚀 #W#[fg=#0d1117]#{?window_zoomed_flag, 🔍,} #[fg=#ff00ff,bg=#0d1117]"

# 窗口状态 - 特殊状态
set-option -g window-status-activity-style "fg=#ff6b6b,bg=#161b22"
set-option -g window-status-bell-style "fg=#ffd93d,bg=#161b22"

# ── 霓虹边框主题 ──────────────────────────────────────
set-option -g pane-border-style "fg=#30363d"
set-option -g pane-active-border-style "fg=#ff00ff"

# ── 消息和输入主题 ──────────────────────────────────────
set-option -g message-style "fg=#00ffff,bg=#161b22,bold"
set-option -g message-command-style "fg=#ff00ff,bg=#161b22,bold"
# 复制模式选中效果 - 统一使用绿色高对比度（类似Safe Mode）
set-option -g mode-style "fg=#000000,bg=#00ff00,bold"

# ── 赛博朋克启动消息 ──────────────────────────────────────
run-shell 'tmux display-message "🔮 WELCOME TO NIGHT CITY! CYBERPUNK 2077 ACTIVATED! 🌃"'
EOF
}

create_matrix_config() {
    cat > ~/.tmux.conf << 'EOF'
# ═══════════════════════════════════════════════════════════
#      ███╗   ███╗ █████╗ ████████╗██████╗ ██╗██╗  ██╗
#      ████╗ ████║██╔══██╗╚══██╔══╝██╔══██╗██║╚██╗██╔╝
#      ██╔████╔██║███████║   ██║   ██████╔╝██║ ╚███╔╝ 
#      ██║╚██╔╝██║██╔══██║   ██║   ██╔══██╗██║ ██╔██╗ 
#      ██║ ╚═╝ ██║██║  ██║   ██║   ██║  ██║██║██╔╝ ██╗
#      ╚═╝     ╚═╝╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝
#                THE MATRIX HAS YOU...
#              数字雨·矩阵代码·觉醒时刻
# ═══════════════════════════════════════════════════════════

# ── 完全重置所有默认设置 ──────────────────────────────────────
unbind-key -a
set-option -g prefix C-space
set-option -g prefix2 None

# ── 核心性能设置 ──────────────────────────────────────
set-option -g default-terminal "tmux-256color"
set-option -ga terminal-overrides ",*256col*:Tc"
set-option -s escape-time 0
set-option -g repeat-time 1000
set-option -g history-limit 100000

# ── 会话安全和IDE友好设置 ──────────────────────────────────────
# set-option -g default-path ""  # 已废弃选项，在新版tmux中不再需要
set-option -g default-command ""
set-option -g set-titles off
set-option -g allow-rename off

# ── 索引和窗口设置 ──────────────────────────────────────
set-option -g base-index 1
set-window-option -g pane-base-index 1
set-option -g renumber-windows on
set-option -g automatic-rename on
set-option -g automatic-rename-format '#{?#{==:#{pane_current_command},zsh},[#{b:pane_current_path}],#{pane_current_command}}'

# ── Matrix鼠标设置 ──────────────────────────────────────
set-option -g mouse on

# ── Matrix前缀键 ──────────────────────────────────────
bind-key C-space send-prefix

# ── 数字雨快捷键绑定 ──────────────────────────────────────
bind-key r source-file ~/.tmux.conf \; display-message "💊 THE MATRIX RELOADED! FOLLOW THE WHITE RABBIT... 💊"
bind-key c new-window -c "#{pane_current_path}"
bind-key | split-window -h -c "#{pane_current_path}"
bind-key - split-window -v -c "#{pane_current_path}"
bind-key x kill-pane
bind-key & kill-window

# Matrix导航 - 红药丸或蓝药丸？
bind-key h select-pane -L
bind-key j select-pane -D  
bind-key k select-pane -U
bind-key l select-pane -R
bind-key -r H resize-pane -L 5
bind-key -r J resize-pane -D 5
bind-key -r K resize-pane -U 5
bind-key -r L resize-pane -R 5
bind-key Tab last-pane
bind-key Space next-layout
bind-key z resize-pane -Z

# ── Neo的选择 - 复制模式 ──────────────────────────────────────
set-window-option -g mode-keys vi

# 复制模式快捷键
bind-key Enter copy-mode
bind-key [ copy-mode
bind-key Escape copy-mode

# Vi风格选择和复制
bind-key -T copy-mode-vi v send-keys -X begin-selection
bind-key -T copy-mode-vi V send-keys -X select-line
bind-key -T copy-mode-vi C-v send-keys -X rectangle-toggle
bind-key -T copy-mode-vi y send-keys -X copy-pipe-and-cancel "pbcopy"
bind-key -T copy-mode-vi Y send-keys -X copy-end-of-line
bind-key -T copy-mode-vi Escape send-keys -X cancel
bind-key -T copy-mode-vi q send-keys -X cancel

# 移动快捷键
bind-key -T copy-mode-vi h send-keys -X cursor-left
bind-key -T copy-mode-vi j send-keys -X cursor-down
bind-key -T copy-mode-vi k send-keys -X cursor-up
bind-key -T copy-mode-vi l send-keys -X cursor-right
bind-key -T copy-mode-vi H send-keys -X start-of-line
bind-key -T copy-mode-vi L send-keys -X end-of-line
bind-key -T copy-mode-vi 0 send-keys -X start-of-line
bind-key -T copy-mode-vi $ send-keys -X end-of-line
bind-key -T copy-mode-vi w send-keys -X next-word
bind-key -T copy-mode-vi e send-keys -X next-word-end
bind-key -T copy-mode-vi b send-keys -X previous-word
bind-key -T copy-mode-vi g send-keys -X history-top
bind-key -T copy-mode-vi G send-keys -X history-bottom
bind-key -T copy-mode-vi / send-keys -X search-forward
bind-key -T copy-mode-vi ? send-keys -X search-backward
bind-key -T copy-mode-vi n send-keys -X search-again
bind-key -T copy-mode-vi N send-keys -X search-reverse

# 翻页快捷键
bind-key -T copy-mode-vi C-u send-keys -X halfpage-up
bind-key -T copy-mode-vi C-d send-keys -X halfpage-down
bind-key -T copy-mode-vi C-b send-keys -X page-up
bind-key -T copy-mode-vi C-f send-keys -X page-down

# 鼠标支持（完整复制选择功能）
bind-key -T copy-mode-vi MouseDragEnd1Pane send-keys -X copy-pipe-and-cancel "pbcopy"
bind-key -T copy-mode MouseDragEnd1Pane send-keys -X copy-pipe-and-cancel "pbcopy"
bind-key -T copy-mode-vi DoubleClick1Pane select-pane \; send-keys -X select-word \; send-keys -X copy-pipe-and-cancel "pbcopy"
bind-key -T copy-mode-vi TripleClick1Pane select-pane \; send-keys -X select-line \; send-keys -X copy-pipe-and-cancel "pbcopy"

# 粘贴快捷键
bind-key p paste-buffer
bind-key P choose-buffer

# ── MATRIX 数字雨主题 ──────────────────────────────────────
# 纯绿色Matrix代码风格：数字雨 + 黑客帝国 + 代码瀑布

# 状态栏主题
set-option -g status-style "fg=#00ff00,bg=#000000"
set-option -g status-left-length 100
set-option -g status-right-length 100

# 左侧状态 - Matrix系统（代码绿）
set-option -g status-left "#[fg=#000000,bg=#00ff00,bold] 💊 #S #[fg=#00ff00,bg=#001100]#[fg=#00ff00,bg=#001100] ▣ #I/#P #[fg=#001100,bg=#000000]"

# 右侧状态 - 时间码（数字雨风格）
set-option -g status-right "#[fg=#001100,bg=#000000]#[fg=#00ff00,bg=#001100] ⌘ #{?client_prefix,▣ ,}#[fg=#00aa00,bg=#001100]▢ %H:%M #[fg=#00ff00,bg=#001100]#[fg=#000000,bg=#00ff00,bold] ▧ %a %m/%d "

# 窗口状态 - 未激活（暗绿代码流）
set-option -g window-status-format "#[fg=#000000,bg=#001100]#[fg=#00aa00,bg=#001100] #I #[fg=#006600,bg=#001100]▤ #W#[fg=#00aa00]#{?window_zoomed_flag, ▣,} #[fg=#001100,bg=#000000]"

# 窗口状态 - 激活（亮绿Matrix高亮）
set-option -g window-status-current-format "#[fg=#000000,bg=#00ff00]#[fg=#000000,bg=#00ff00,bold] #I #[fg=#000000,bg=#00ff00]▦ #W#[fg=#000000]#{?window_zoomed_flag, ▣,} #[fg=#00ff00,bg=#000000]"

# 窗口状态 - 特殊状态（Matrix警告）
set-option -g window-status-activity-style "fg=#ff0000,bg=#001100"
set-option -g window-status-bell-style "fg=#ffff00,bg=#001100"

# ── Matrix边框主题 ──────────────────────────────────────
set-option -g pane-border-style "fg=#004400"
set-option -g pane-active-border-style "fg=#00ff00"

# ── Matrix消息主题 ──────────────────────────────────────
set-option -g message-style "fg=#00ff00,bg=#001100,bold"
set-option -g message-command-style "fg=#00ff00,bg=#001100,bold"
# 复制模式选中效果 - 统一使用绿色高对比度（类似Safe Mode）
set-option -g mode-style "fg=#000000,bg=#00ff00,bold"

# ── Matrix觉醒消息 ──────────────────────────────────────
run-shell 'tmux display-message "💊 WELCOME TO THE REAL WORLD, NEO! THE MATRIX HAS YOU... ▦▧▣"'
EOF
}

create_crystal_config() {
    cat > ~/.tmux.conf << 'EOF'
# ═══════════════════════════════════════════════════════════
#       ▄████▄   ██▀███ ▓██   ██▓  ██████ ▄▄▄█████▓ ▄▄▄      
#      ▒██▀ ▀█  ▓██ ▒ ██▒▒██  ██▒▒██    ▒ ▓  ██▒ ▓▒▒████▄    
#      ▒▓█    ▄ ▓██ ░▄█ ▒ ▒██ ██░░ ▓██▄   ▒ ▓██░ ▒░▒██  ▀█▄  
#      ▒▓▓▄ ▄██▒▒██▀▀█▄   ░ ▐██▓░  ▒   ██▒░ ▓██▓ ░ ░██▄▄▄▄██ 
#      ▒ ▓███▀ ░░██▓ ▒██▒ ░ ██▒▓░▒██████▒▒  ▒██▒ ░  ▓█   ▓██▒
#      ░ ░▒ ▒  ░░ ▒▓ ░▒▓░  ██▒▒▒ ▒ ▒▓▒ ▒ ░  ▒ ░░    ▒▒   ▓▒█░
#              CRYSTAL BLUE ELEGANCE
#              水晶蓝调·简约优雅·沉静致远
# ═══════════════════════════════════════════════════════════

# ── 完全重置所有默认设置 ──────────────────────────────────────
unbind-key -a
set-option -g prefix C-space
set-option -g prefix2 None

# ── 核心性能设置 ──────────────────────────────────────
set-option -g default-terminal "tmux-256color"
set-option -ga terminal-overrides ",*256col*:Tc"
set-option -s escape-time 0
set-option -g repeat-time 1000
set-option -g history-limit 100000

# ── 会话安全和IDE友好设置 ──────────────────────────────────────
# set-option -g default-path ""  # 已废弃选项，在新版tmux中不再需要
set-option -g default-command ""
set-option -g set-titles off
set-option -g allow-rename off

# ── 索引和窗口设置 ──────────────────────────────────────
set-option -g base-index 1
set-window-option -g pane-base-index 1
set-option -g renumber-windows on
set-option -g automatic-rename on
set-option -g automatic-rename-format '#{?#{==:#{pane_current_command},zsh},[#{b:pane_current_path}],#{pane_current_command}}'

# ── 水晶鼠标设置 ──────────────────────────────────────
set-option -g mouse on

# ── 水晶前缀键 ──────────────────────────────────────
bind-key C-space send-prefix

# ── 优雅快捷键绑定 ──────────────────────────────────────
bind-key r source-file ~/.tmux.conf \; display-message "💎 CRYSTAL CLARITY RESTORED! ELEGANCE RELOADED! 💎"
bind-key c new-window -c "#{pane_current_path}"
bind-key | split-window -h -c "#{pane_current_path}"
bind-key - split-window -v -c "#{pane_current_path}"
bind-key x kill-pane
bind-key & kill-window

# 水晶导航 - 流畅如水
bind-key h select-pane -L
bind-key j select-pane -D  
bind-key k select-pane -U
bind-key l select-pane -R
bind-key -r H resize-pane -L 5
bind-key -r J resize-pane -D 5
bind-key -r K resize-pane -U 5
bind-key -r L resize-pane -R 5
bind-key Tab last-pane
bind-key Space next-layout
bind-key z resize-pane -Z

# ── 优雅复制模式 ──────────────────────────────────────
set-window-option -g mode-keys vi

# 复制模式快捷键
bind-key Enter copy-mode
bind-key [ copy-mode
bind-key Escape copy-mode

# Vi风格选择和复制
bind-key -T copy-mode-vi v send-keys -X begin-selection
bind-key -T copy-mode-vi V send-keys -X select-line
bind-key -T copy-mode-vi C-v send-keys -X rectangle-toggle
bind-key -T copy-mode-vi y send-keys -X copy-pipe-and-cancel "pbcopy"
bind-key -T copy-mode-vi Y send-keys -X copy-end-of-line
bind-key -T copy-mode-vi Escape send-keys -X cancel
bind-key -T copy-mode-vi q send-keys -X cancel

# 移动快捷键
bind-key -T copy-mode-vi h send-keys -X cursor-left
bind-key -T copy-mode-vi j send-keys -X cursor-down
bind-key -T copy-mode-vi k send-keys -X cursor-up
bind-key -T copy-mode-vi l send-keys -X cursor-right
bind-key -T copy-mode-vi H send-keys -X start-of-line
bind-key -T copy-mode-vi L send-keys -X end-of-line
bind-key -T copy-mode-vi 0 send-keys -X start-of-line
bind-key -T copy-mode-vi $ send-keys -X end-of-line
bind-key -T copy-mode-vi w send-keys -X next-word
bind-key -T copy-mode-vi e send-keys -X next-word-end
bind-key -T copy-mode-vi b send-keys -X previous-word
bind-key -T copy-mode-vi g send-keys -X history-top
bind-key -T copy-mode-vi G send-keys -X history-bottom
bind-key -T copy-mode-vi / send-keys -X search-forward
bind-key -T copy-mode-vi ? send-keys -X search-backward
bind-key -T copy-mode-vi n send-keys -X search-again
bind-key -T copy-mode-vi N send-keys -X search-reverse

# 翻页快捷键
bind-key -T copy-mode-vi C-u send-keys -X halfpage-up
bind-key -T copy-mode-vi C-d send-keys -X halfpage-down
bind-key -T copy-mode-vi C-b send-keys -X page-up
bind-key -T copy-mode-vi C-f send-keys -X page-down

# 鼠标支持（完整复制选择功能）
bind-key -T copy-mode-vi MouseDragEnd1Pane send-keys -X copy-pipe-and-cancel "pbcopy"
bind-key -T copy-mode MouseDragEnd1Pane send-keys -X copy-pipe-and-cancel "pbcopy"
bind-key -T copy-mode-vi DoubleClick1Pane select-pane \; send-keys -X select-word \; send-keys -X copy-pipe-and-cancel "pbcopy"
bind-key -T copy-mode-vi TripleClick1Pane select-pane \; send-keys -X select-line \; send-keys -X copy-pipe-and-cancel "pbcopy"

# 粘贴快捷键
bind-key p paste-buffer
bind-key P choose-buffer

# ── CRYSTAL BLUE 水晶主题 ──────────────────────────────────────
# 水晶蓝调配色：深海蓝 + 天空蓝 + 冰晶白 + 优雅渐变

# 状态栏主题
set-option -g status-style "fg=#e3f2fd,bg=#0d47a1"
set-option -g status-left-length 100
set-option -g status-right-length 100

# 左侧状态 - 系统信息（深海蓝渐变）
set-option -g status-left "#[fg=#ffffff,bg=#1976d2,bold] 💎 #S #[fg=#1976d2,bg=#1565c0]#[fg=#e3f2fd,bg=#1565c0] 🔹 #I/#P #[fg=#1565c0,bg=#0d47a1]"

# 右侧状态 - 时间信息（天空蓝渐变）
set-option -g status-right "#[fg=#1565c0,bg=#0d47a1]#[fg=#e3f2fd,bg=#1565c0] 🔸 #{?client_prefix,✧ ,}#[fg=#bbdefb,bg=#1565c0]⏱ %H:%M #[fg=#1976d2,bg=#1565c0]#[fg=#ffffff,bg=#1976d2,bold] 📅 %a %m/%d "

# 窗口状态 - 未激活（柔和蓝调）
set-option -g window-status-format "#[fg=#0d47a1,bg=#1565c0]#[fg=#bbdefb,bg=#1565c0] #I #[fg=#64b5f6,bg=#1565c0]◆ #W#[fg=#e3f2fd]#{?window_zoomed_flag, 🔍,} #[fg=#1565c0,bg=#0d47a1]"

# 窗口状态 - 激活（亮蓝水晶高亮）
set-option -g window-status-current-format "#[fg=#0d47a1,bg=#42a5f5]#[fg=#ffffff,bg=#42a5f5,bold] #I #[fg=#ffffff,bg=#42a5f5]◇ #W#[fg=#ffffff]#{?window_zoomed_flag, 🔍,} #[fg=#42a5f5,bg=#0d47a1]"

# 窗口状态 - 特殊状态
set-option -g window-status-activity-style "fg=#ff7043,bg=#1565c0"
set-option -g window-status-bell-style "fg=#ffca28,bg=#1565c0"

# ── 水晶边框主题 ──────────────────────────────────────
set-option -g pane-border-style "fg=#1976d2"
set-option -g pane-active-border-style "fg=#42a5f5"

# ── 消息和输入主题 ──────────────────────────────────────
set-option -g message-style "fg=#ffffff,bg=#1976d2,bold"
set-option -g message-command-style "fg=#e3f2fd,bg=#1565c0,bold"
# 复制模式选中效果 - 统一使用绿色高对比度（类似Safe Mode）
set-option -g mode-style "fg=#000000,bg=#00ff00,bold"

# ── 水晶启动消息 ──────────────────────────────────────
run-shell 'tmux display-message "💎 CRYSTAL BLUE ELEGANCE ACTIVATED! FLOW LIKE WATER, SHINE LIKE CRYSTAL! ✧"'
EOF
}

create_safe_config() {
    cat > ~/.tmux.conf << 'EOF'
# SAFE MODE TMUX 配置 - IDE友好，极简安全

# 基础设置
set -g default-terminal "screen-256color"
set -s escape-time 0
set -g base-index 1
set -g pane-base-index 1
set -g renumber-windows on

# 简单前缀键
unbind C-b
set -g prefix C-a
bind C-a send-prefix

# 基本操作
bind r source-file ~/.tmux.conf \; display "配置已重载"
bind | split-window -h -c "#{pane_current_path}"
bind - split-window -v -c "#{pane_current_path}"
bind c new-window -c "#{pane_current_path}"

# Vim导航
bind h select-pane -L
bind j select-pane -D
bind k select-pane -U
bind l select-pane -R

# 鼠标支持
set -g mouse on

# 复制模式（完整功能）
set-window-option -g mode-keys vi

# 复制模式快捷键
bind-key Enter copy-mode
bind-key [ copy-mode
bind-key Escape copy-mode

# Vi风格选择和复制
bind-key -T copy-mode-vi v send-keys -X begin-selection
bind-key -T copy-mode-vi V send-keys -X select-line
bind-key -T copy-mode-vi C-v send-keys -X rectangle-toggle
bind-key -T copy-mode-vi y send-keys -X copy-pipe-and-cancel "pbcopy"
bind-key -T copy-mode-vi Y send-keys -X copy-end-of-line
bind-key -T copy-mode-vi Escape send-keys -X cancel
bind-key -T copy-mode-vi q send-keys -X cancel

# 移动快捷键
bind-key -T copy-mode-vi h send-keys -X cursor-left
bind-key -T copy-mode-vi j send-keys -X cursor-down
bind-key -T copy-mode-vi k send-keys -X cursor-up
bind-key -T copy-mode-vi l send-keys -X cursor-right
bind-key -T copy-mode-vi H send-keys -X start-of-line
bind-key -T copy-mode-vi L send-keys -X end-of-line
bind-key -T copy-mode-vi 0 send-keys -X start-of-line
bind-key -T copy-mode-vi $ send-keys -X end-of-line
bind-key -T copy-mode-vi w send-keys -X next-word
bind-key -T copy-mode-vi e send-keys -X next-word-end
bind-key -T copy-mode-vi b send-keys -X previous-word
bind-key -T copy-mode-vi g send-keys -X history-top
bind-key -T copy-mode-vi G send-keys -X history-bottom
bind-key -T copy-mode-vi / send-keys -X search-forward
bind-key -T copy-mode-vi ? send-keys -X search-backward
bind-key -T copy-mode-vi n send-keys -X search-again
bind-key -T copy-mode-vi N send-keys -X search-reverse

# 翻页快捷键
bind-key -T copy-mode-vi C-u send-keys -X halfpage-up
bind-key -T copy-mode-vi C-d send-keys -X halfpage-down
bind-key -T copy-mode-vi C-b send-keys -X page-up
bind-key -T copy-mode-vi C-f send-keys -X page-down

# 鼠标支持（完整复制选择功能）
bind-key -T copy-mode-vi MouseDragEnd1Pane send-keys -X copy-pipe-and-cancel "pbcopy"
bind-key -T copy-mode MouseDragEnd1Pane send-keys -X copy-pipe-and-cancel "pbcopy"
bind-key -T copy-mode-vi DoubleClick1Pane select-pane \; send-keys -X select-word \; send-keys -X copy-pipe-and-cancel "pbcopy"
bind-key -T copy-mode-vi TripleClick1Pane select-pane \; send-keys -X select-line \; send-keys -X copy-pipe-and-cancel "pbcopy"

# 粘贴快捷键
bind-key p paste-buffer
bind-key P choose-buffer

# 简洁主题
set -g status-style "fg=white,bg=black"
set -g status-left '#[fg=green,bold][#S] '
set -g status-right '#[fg=yellow]%H:%M %m-%d'
set -g window-status-current-style "fg=black,bg=green,bold"
set -g pane-active-border-style "fg=green"

# 消息和复制模式主题
set -g message-style "fg=white,bg=blue,bold"
set -g message-command-style "fg=white,bg=blue,bold"
# 复制模式选中效果 - 高对比度绿色背景
set -g mode-style "fg=black,bg=green,bold"

# 确保会话独立性
# set -g default-path ""  # 已废弃选项，在新版tmux中不再需要
EOF
}

# 安装TPM插件管理器（可选）
install_tpm() {
    read -p "是否安装TPM插件管理器? (y/n): " install_plugins
    if [[ "$install_plugins" == "y" || "$install_plugins" == "Y" ]]; then
        log_info "正在安装TPM插件管理器..."
        
        local tpm_dir=~/.tmux/plugins/tpm
        
        if [[ -d "$tpm_dir" ]]; then
            log_info "更新TPM..."
            cd "$tmp_dir" && git pull
        else
            git clone https://github.com/tmux-plugins/tpm "$tpm_dir"
        fi
        
        # 启用插件支持
        echo "" >> ~/.tmux.conf
        echo "# TPM插件管理器" >> ~/.tmux.conf
        echo "set -g @plugin 'tmux-plugins/tpm'" >> ~/.tmux.conf
        echo "set -g @plugin 'tmux-plugins/tmux-sensible'" >> ~/.tmux.conf
        echo "run '~/.tmux/plugins/tpm/tpm'" >> ~/.tmux.conf
        
        log_success "TPM安装完成，使用 Ctrl-Space + I 安装插件"
    else
        log_info "跳过插件安装"
    fi
}

# 创建安全启动脚本（不自动启动）
create_safe_launchers() {
    log_info "创建安全启动脚本..."
    
    # 安全手动启动脚本
    cat > ~/tmux-elite.sh << 'EOF'
#!/bin/bash
# ELITE TMUX 安全启动脚本

# 生成唯一会话名，避免冲突
SESSION_NAME="elite-$(date +%s)-$$"

echo "🚀 启动 ELITE TMUX 会话: $SESSION_NAME"
tmux new-session -s "$SESSION_NAME" -c "$PWD"
EOF
    
    chmod +x ~/tmux-elite.sh
    
    # 项目开发脚本
    cat > ~/tmux-project.sh << 'EOF'
#!/bin/bash
# 项目开发环境启动脚本

PROJECT_NAME="${1:-$(basename $PWD)}"
SESSION_NAME="project-${PROJECT_NAME}-$(date +%s)"

echo "🔧 启动项目开发环境: $SESSION_NAME"

# 创建主会话
tmux new-session -d -s "$SESSION_NAME" -c "$PWD"

# 窗口1: 编辑器
tmux rename-window -t "$SESSION_NAME:1" "editor"

# 窗口2: 终端
tmux new-window -t "$SESSION_NAME" -n "terminal" -c "$PWD"

# 窗口3: 服务器（如果需要）
tmux new-window -t "$SESSION_NAME" -n "server" -c "$PWD"

# 返回第一个窗口
tmux select-window -t "$SESSION_NAME:1"

# 连接会话
tmux attach-session -t "$SESSION_NAME"
EOF
    
    chmod +x ~/tmux-project.sh
    
    log_success "安全启动脚本已创建："
    echo "  ~/tmux-elite.sh   - 启动Elite主题会话"  
    echo "  ~/tmux-project.sh - 启动项目开发环境"
}

# 清理自动启动配置
cleanup_auto_start() {
    log_secure "清理可能的自动启动配置..."
    
    for shell_config in ~/.zshrc ~/.bashrc ~/.bash_profile ~/.profile; do
        if [[ -f "$shell_config" ]] && grep -q "tmux\|TMUX\|ELITE" "$shell_config" 2>/dev/null; then
            log_info "清理 $shell_config 中的自动启动配置"
            
            # 移除所有tmux相关的自动启动
            sed -i.tmp '/# 🚀 ELITE TMUX/,/^fi$/d' "$shell_config" 2>/dev/null || true
            sed -i.tmp '/exec tmux/d' "$shell_config" 2>/dev/null || true
            sed -i.tmp '/tmux.*elite/d' "$shell_config" 2>/dev/null || true
            sed -i.tmp '/start_elite_tmux/d' "$shell_config" 2>/dev/null || true
            
            rm -f "${shell_config}.tmp" 2>/dev/null || true
        fi
    done
    
    log_secure "自动启动配置已清理，确保手动控制"
}

# 显示使用说明
show_elite_guide() {
    log_success "🎉 ELITE TMUX 安全安装完成！"
    echo ""
    
    cat << EOF
$(echo -e "${PURPLE}${BOLD}")
    ███████╗██╗     ██╗████████╗███████╗    ████████╗███╗   ███╗██╗   ██╗██╗  ██╗
    ██╔════╝██║     ██║╚══██╔══╝██╔════╝    ╚══██╔══╝████╗ ████║██║   ██║╚██╗██╔╝
    █████╗  ██║     ██║   ██║   █████╗         ██║   ██╔████╔██║██║   ██║ ╚███╔╝ 
    ██╔══╝  ██║     ██║   ██║   ██╔══╝         ██║   ██║╚██╔╝██║██║   ██║ ██╔██╗ 
    ███████╗███████╗██║   ██║   ███████╗       ██║   ██║ ╚═╝ ██║╚██████╔╝██╔╝ ██╗
    ╚══════╝╚══════╝╚═╝   ╚═╝   ╚══════╝       ╚═╝   ╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═╝
$(echo -e "${NC}")

$(echo -e "${BOLD}${WHITE}════════════════════ 🔒 SECURE ELITE GUIDE 🔒 ════════════════════${NC}")

$(echo -e "${LOCK}${BOLD} 安全特性:${NC}")
$(echo -e "${GREEN}  ✅ 无会话共享 - 每个会话完全独立${NC}")
$(echo -e "${GREEN}  ✅ 无自动启动 - 完全手动控制${NC}")
$(echo -e "${GREEN}  ✅ IDE友好 - 不会干扰IDEA等IDE${NC}")
$(echo -e "${GREEN}  ✅ 配置备份 - 所有原配置已备份${NC}")

$(echo -e "${FIRE}${BOLD} 基础操作:${NC}")
$(echo -e "${CYAN}  Ctrl-Space |      ${WHITE}垂直分割面板${NC}")
$(echo -e "${CYAN}  Ctrl-Space -      ${WHITE}水平分割面板${NC}")
$(echo -e "${CYAN}  Ctrl-Space h/j/k/l ${WHITE}Vim风格面板切换${NC}")
$(echo -e "${CYAN}  Ctrl-Space c      ${WHITE}新建窗口${NC}")
$(echo -e "${CYAN}  Ctrl-Space r      ${WHITE}重载配置${NC}")

$(echo -e "${LIGHTNING}${BOLD} 复制粘贴操作:${NC}")
$(echo -e "${YELLOW}  Ctrl-Space [      ${WHITE}进入复制模式${NC}")
$(echo -e "${YELLOW}  v                 ${WHITE}开始选择${NC}")
$(echo -e "${YELLOW}  V                 ${WHITE}选择整行${NC}")
$(echo -e "${YELLOW}  Ctrl-v            ${WHITE}矩形选择${NC}")
$(echo -e "${YELLOW}  y                 ${WHITE}复制到系统剪贴板${NC}")
$(echo -e "${YELLOW}  Ctrl-Space p      ${WHITE}粘贴${NC}")
$(echo -e "${YELLOW}  鼠标拖拽           ${WHITE}自动复制${NC}")
$(echo -e "${YELLOW}  双击单词           ${WHITE}选择单词${NC}")
$(echo -e "${YELLOW}  三击行             ${WHITE}选择整行${NC}")

$(echo -e "${ROCKET}${BOLD} 安全启动方式:${NC}")
$(echo -e "${YELLOW}  tmux              ${WHITE}基础启动${NC}")
$(echo -e "${YELLOW}  ~/tmux-elite.sh   ${WHITE}启动Elite主题${NC}")
$(echo -e "${YELLOW}  ~/tmux-project.sh ${WHITE}启动项目环境${NC}")
$(echo -e "${YELLOW}  tmux new -s name  ${WHITE}创建命名会话${NC}")

$(echo -e "${DIAMOND}${BOLD} 会话管理:${NC}")
$(echo -e "${BLUE}  tmux ls           ${WHITE}列出所有会话${NC}")
$(echo -e "${BLUE}  tmux a -t name    ${WHITE}连接指定会话${NC}")
$(echo -e "${BLUE}  tmux kill -t name ${WHITE}关闭指定会话${NC}")

$(echo -e "${BOLD}${WHITE}════════════════════════════════════════════════════════════════════${NC}")
$(echo -e "${GREEN}${BOLD}              🔒 安全至上，逼格不减！现在完全受您控制！${NC}")
$(echo -e "${BOLD}${WHITE}════════════════════════════════════════════════════════════════════${NC}")
EOF

    echo ""
    log_secure "配置完成！不会自动启动，完全手动控制"
    log_info "紧急修复工具已保留: ./emergency_fix.sh"
}

# 主函数
main() {
    print_banner
    
    # 检查配置文件
    if [[ ! -f .tmux.conf.elite ]]; then
        log_error "找不到 .tmux.conf.elite 文件，请确保在正确目录运行"
        exit 1
    fi
    
    detect_system
    install_dependencies
    choose_theme
    backup_config
    cleanup_auto_start  # 重要：先清理自动启动
    install_config
    install_tpm
    create_safe_launchers
    show_elite_guide
}

# 错误处理
trap 'log_error "安装过程中发生错误，请检查日志"; exit 1' ERR

# 启动安装程序
main "$@"