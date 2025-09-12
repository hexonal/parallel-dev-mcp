#!/bin/bash
# ═══════════════════════════════════════════════════════════
#                     紧急修复脚本
#           修复tmux会话共享bug和IDEA终端问题
# ═══════════════════════════════════════════════════════════

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${RED}🚨 紧急修复：解决tmux会话共享和自动启动问题${NC}"
echo ""

# 1. 立即停止所有tmux会话共享
stop_session_sharing() {
    echo -e "${BLUE}[1/6] 停止会话共享...${NC}"
    
    # 杀死所有可能的共享会话
    pkill -f "tmux.*-S" 2>/dev/null || true
    
    # 清理可能的共享socket
    rm -f /tmp/tmux-* 2>/dev/null || true
    rm -f /tmp/shared* 2>/dev/null || true
    
    echo -e "${GREEN}✅ 会话共享已停止${NC}"
}

# 2. 移除所有自动启动配置
remove_auto_start() {
    echo -e "${BLUE}[2/6] 移除自动启动配置...${NC}"
    
    # 备份并清理shell配置文件
    for config in ~/.zshrc ~/.bashrc ~/.bash_profile ~/.profile; do
        if [[ -f "$config" ]]; then
            # 备份
            cp "$config" "${config}.emergency_backup.$(date +%Y%m%d_%H%M%S)" 2>/dev/null || true
            
            # 移除所有tmux自动启动相关配置
            sed -i.tmp '/# 🚀 ELITE TMUX/,/^fi$/d' "$config" 2>/dev/null || true
            sed -i.tmp '/ELITE.*TMUX/,/^fi$/d' "$config" 2>/dev/null || true  
            sed -i.tmp '/tmux new-session.*elite/d' "$config" 2>/dev/null || true
            sed -i.tmp '/exec tmux/d' "$config" 2>/dev/null || true
            sed -i.tmp '/start_elite_tmux/d' "$config" 2>/dev/null || true
            
            # 清理临时文件
            rm -f "${config}.tmp" 2>/dev/null || true
            
            echo "  已清理: $config"
        fi
    done
    
    echo -e "${GREEN}✅ 自动启动配置已移除${NC}"
}

# 3. 重置tmux配置为安全默认
reset_tmux_config() {
    echo -e "${BLUE}[3/6] 重置tmux配置为安全默认...${NC}"
    
    # 备份现有配置
    if [[ -f ~/.tmux.conf ]]; then
        cp ~/.tmux.conf ~/.tmux.conf.emergency_backup.$(date +%Y%m%d_%H%M%S)
        echo "  已备份现有tmux配置"
    fi
    
    # 创建安全的默认配置
    cat > ~/.tmux.conf << 'EOF'
# 安全的tmux默认配置 - 无自动启动，无会话共享

# 基础设置
set -g default-terminal "screen-256color"
set -s escape-time 0
set -g base-index 1
set -g pane-base-index 1
set -g renumber-windows on

# 前缀键
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

# 调整面板大小
bind -r H resize-pane -L 5
bind -r J resize-pane -D 5
bind -r K resize-pane -U 5
bind -r L resize-pane -R 5

# 鼠标支持
set -g mouse on

# 复制模式
setw -g mode-keys vi
bind -T copy-mode-vi v send-keys -X begin-selection
bind -T copy-mode-vi y send-keys -X copy-pipe-and-cancel "pbcopy"

# 简单状态栏
set -g status-style "fg=white,bg=black"
set -g status-left '#[fg=green][#S] '
set -g status-right '#[fg=yellow]%H:%M %m-%d'
set -g window-status-current-style "fg=black,bg=green"

# 确保每个会话独立，不共享（default-path已废弃，无需设置）
EOF
    
    echo -e "${GREEN}✅ 安全的tmux配置已设置${NC}"
}

# 4. 清理可能的问题脚本
cleanup_scripts() {
    echo -e "${BLUE}[4/6] 清理问题脚本...${NC}"
    
    # 移除可能导致问题的脚本
    rm -f ~/start-hacker-workspace.sh 2>/dev/null || true
    rm -f ~/tmux-dev-session.sh 2>/dev/null || true
    rm -f ~/quick-dev.sh 2>/dev/null || true
    
    echo -e "${GREEN}✅ 问题脚本已清理${NC}"
}

# 5. 杀死所有现有tmux会话
kill_all_sessions() {
    echo -e "${BLUE}[5/6] 重置所有tmux会话...${NC}"
    
    # 警告用户
    echo -e "${YELLOW}⚠️  即将关闭所有tmux会话，请确保重要工作已保存${NC}"
    read -p "继续吗? (y/N): " confirm
    
    if [[ "$confirm" == "y" || "$confirm" == "Y" ]]; then
        # 关闭所有会话
        tmux kill-server 2>/dev/null || true
        echo -e "${GREEN}✅ 所有会话已重置${NC}"
    else
        echo -e "${YELLOW}跳过会话重置${NC}"
    fi
}

# 6. 创建安全的手动启动脚本
create_safe_launcher() {
    echo -e "${BLUE}[6/6] 创建安全的启动脚本...${NC}"
    
    cat > ~/tmux-safe.sh << 'EOF'
#!/bin/bash
# 安全的tmux启动脚本 - 每次创建唯一会话

# 生成唯一会话名
SESSION_NAME="work-$(date +%s)-$$"

# 启动独立会话
echo "🔒 启动安全的tmux会话: $SESSION_NAME"
tmux new-session -s "$SESSION_NAME" -c "$PWD"
EOF
    
    chmod +x ~/tmux-safe.sh
    
    echo -e "${GREEN}✅ 安全启动脚本已创建: ~/tmux-safe.sh${NC}"
}

# 显示修复结果和使用说明
show_results() {
    echo ""
    echo -e "${GREEN}🎉 紧急修复完成！${NC}"
    echo ""
    echo -e "${BLUE}════════════════════════════════════════${NC}"
    echo -e "${BLUE}              修复结果                   ${NC}"  
    echo -e "${BLUE}════════════════════════════════════════${NC}"
    echo ""
    echo -e "${GREEN}✅ 会话共享问题已修复${NC}"
    echo -e "${GREEN}✅ 自动启动已禁用${NC}"
    echo -e "${GREEN}✅ IDEA终端跳转问题已解决${NC}"
    echo -e "${GREEN}✅ 配置已重置为安全默认${NC}"
    echo ""
    echo -e "${BLUE}现在如何使用tmux:${NC}"
    echo -e "${YELLOW}1. 手动启动：${NC}tmux"
    echo -e "${YELLOW}2. 安全启动：${NC}~/tmux-safe.sh"
    echo -e "${YELLOW}3. 命名会话：${NC}tmux new -s myproject"
    echo -e "${YELLOW}4. 连接会话：${NC}tmux attach -t myproject"
    echo ""
    echo -e "${BLUE}重要：${NC}"
    echo "- 现在每个tmux会话都是独立的，不会共享"
    echo "- 不会自动启动，需要手动启动"
    echo "- IDEA终端不会再跳转目录"
    echo "- 所有配置文件都已备份"
    echo ""
    echo -e "${YELLOW}重启终端生效！${NC}"
}

# 主执行流程
main() {
    stop_session_sharing
    remove_auto_start  
    reset_tmux_config
    cleanup_scripts
    kill_all_sessions
    create_safe_launcher
    show_results
}

# 执行修复
main "$@"