# 🚀 现代化 Tmux 配置指南

高性能、美观且易用的 tmux 终端复用器配置，专为开发者优化。

## ✨ 特性

### 🎨 视觉体验
- **现代蓝色主题** - 专业且护眼的颜色搭配
- **美观状态栏** - 显示会话、时间和系统信息
- **活跃面板高亮** - 清晰识别当前操作区域
- **256色支持** - 丰富的颜色显示

### ⚡ 性能优化
- **零延迟响应** - `escape-time 0` 消除输入延迟
- **高刷新率** - 5秒状态更新间隔平衡性能和实时性
- **大历史缓冲** - 50000行历史记录
- **智能重排** - 窗口自动重新编号

### 🖱️ 鼠标支持
- **点击切换** - 鼠标点击切换面板和窗口
- **拖拽复制** - 直接拖拽选择文本并复制到剪贴板
- **滚轮支持** - 自然的滚动体验
- **调整大小** - 拖拽边框调整面板大小

### ⌨️ 快捷键优化
- **Ctrl-a 前缀** - 更易按的前缀键（替代 Ctrl-b）
- **Vim 风格导航** - h/j/k/l 切换面板
- **直观分割** - `|` 垂直分割，`-` 水平分割
- **Vi 复制模式** - 熟悉的 Vi 键绑定

## 🛠️ 安装

### 快速安装
```bash
# 1. 克隆或下载配置文件
git clone <repository> tmux-config
cd tmux-config

# 2. 运行自动安装脚本
./install_tmux.sh
```

### 手动安装
```bash
# 1. 安装 tmux
# macOS
brew install tmux

# Ubuntu/Debian
sudo apt install tmux

# CentOS/RHEL
sudo yum install tmux

# 2. 安装配置
cp .tmux.conf ~/.tmux.conf

# 3. 安装插件管理器
git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm

# 4. 重新加载配置
tmux source ~/.tmux.conf

# 5. 安装插件（在 tmux 中按 Ctrl-a + I）
```

## 📖 使用指南

### 基础操作

| 快捷键 | 功能 |
|--------|------|
| `Ctrl-a` | 前缀键（所有操作前需先按此键） |
| `Ctrl-a r` | 重新加载配置文件 |
| `Ctrl-a ?` | 显示所有快捷键 |

### 会话管理

```bash
# 会话操作
tmux                        # 启动新会话
tmux new -s project         # 创建命名会话 "project"
tmux ls                     # 列出所有会话
tmux a                      # 连接最近的会话
tmux a -t project           # 连接指定会话
tmux kill-session -t project # 删除指定会话

# 在会话内
Ctrl-a d                    # 分离会话（会话继续运行）
Ctrl-a s                    # 选择会话
```

### 窗口管理

| 快捷键 | 功能 |
|--------|------|
| `Ctrl-a c` | 创建新窗口 |
| `Ctrl-a ,` | 重命名当前窗口 |
| `Ctrl-a &` | 关闭当前窗口 |
| `Ctrl-a n` | 下一个窗口 |
| `Ctrl-a p` | 上一个窗口 |
| `Ctrl-a 0-9` | 切换到指定编号窗口 |
| `Ctrl-a w` | 窗口选择菜单 |

### 面板管理

| 快捷键 | 功能 |
|--------|------|
| `Ctrl-a \|` | 垂直分割面板 |
| `Ctrl-a -` | 水平分割面板 |
| `Ctrl-a x` | 关闭当前面板 |
| `Ctrl-a h/j/k/l` | Vim 风格切换面板 |
| `Ctrl-a H/J/K/L` | 调整面板大小 |
| `Ctrl-a z` | 最大化/恢复面板 |
| `Ctrl-a {` | 向左交换面板 |
| `Ctrl-a }` | 向右交换面板 |

### 复制粘贴

| 快捷键 | 功能 |
|--------|------|
| `Ctrl-a [` | 进入复制模式 |
| `v` | 开始选择（复制模式中） |
| `V` | 行选择（复制模式中） |
| `Ctrl-v` | 矩形选择（复制模式中） |
| `y` | 复制选中内容到剪贴板 |
| `Ctrl-a ]` | 粘贴 |
| `Escape` | 退出复制模式 |

**鼠标操作：**
- 直接拖拽选择文本
- 双击选择单词
- 三击选择整行
- 选择完成后自动复制到系统剪贴板

## 🔌 插件系统

### 已集成插件

1. **tmux-sensible** - 基础配置改进
2. **tmux-resurrect** - 会话保存/恢复
3. **tmux-continuum** - 自动保存会话
4. **tmux-yank** - 复制增强
5. **tmux-prefix-highlight** - 前缀键状态显示

### 插件管理

| 快捷键 | 功能 |
|--------|------|
| `Ctrl-a I` | 安装插件 |
| `Ctrl-a U` | 更新插件 |
| `Ctrl-a alt-u` | 卸载插件 |

### 会话持久化

插件会自动保存和恢复：
- 窗口布局
- 面板内容
- 工作目录
- 运行的程序

## 🎯 开发工作流

### 项目开发会话

使用提供的示例脚本快速启动开发环境：

```bash
~/tmux-dev-session.sh
```

这将创建包含以下窗口的开发会话：
1. **editor** - 代码编辑
2. **server** - 服务器运行（分为上下两个面板）
3. **terminal** - 命令行操作
4. **monitor** - 系统监控（自动运行 htop）

### 自定义开发环境

```bash
#!/bin/bash
# 自定义项目会话脚本

SESSION="myproject"
PROJECTPATH="$HOME/projects/myproject"

# 创建会话
tmux new-session -d -s $SESSION -c $PROJECTPATH

# 窗口 1: 编辑器
tmux rename-window -t $SESSION:1 'editor'
tmux send-keys -t $SESSION:1 'code .' Enter

# 窗口 2: 服务器
tmux new-window -t $SESSION -n 'server' -c $PROJECTPATH
tmux send-keys -t $SESSION:server 'npm run dev' Enter

# 窗口 3: Git
tmux new-window -t $SESSION -n 'git' -c $PROJECTPATH
tmux send-keys -t $SESSION:git 'git status' Enter

# 连接会话
tmux attach-session -t $SESSION
```

## ⚙️ 自定义配置

### 修改颜色主题

在 `~/.tmux.conf` 中修改颜色设置：

```bash
# 自定义颜色（在配置文件中修改）
set -g status-bg colour235        # 状态栏背景色
set -g status-fg colour136        # 状态栏前景色
set -g pane-active-border-style fg=colour166  # 活跃面板边框
```

### 添加自定义快捷键

```bash
# 在 ~/.tmux.conf 中添加
bind-key C-h send-keys "clear" Enter  # Ctrl-a Ctrl-h 清屏
bind-key S command-prompt "new-session -s '%%'"  # Ctrl-a S 创建命名会话
```

### 状态栏自定义

```bash
# 自定义右侧状态栏
set -g status-right '#[fg=colour244] #(whoami)@#H #[fg=colour166]%Y-%m-%d %H:%M'

# 添加 CPU 使用率（需要安装相关插件）
set -g @plugin 'tmux-plugins/tmux-cpu'
set -g status-right '#{cpu_bg_color} CPU: #{cpu_icon} #{cpu_percentage} #[fg=colour244] %Y-%m-%d %H:%M'
```

## 🐛 故障排除

### 常见问题

**Q: 鼠标滚动不工作**
```bash
# 确保终端支持鼠标，并检查配置
set -g mouse on
```

**Q: 颜色显示异常**
```bash
# 设置正确的终端类型
export TERM=xterm-256color
```

**Q: 复制到系统剪贴板失败**
```bash
# macOS 安装 reattach-to-user-namespace
brew install reattach-to-user-namespace

# Linux 安装 xclip 或 xsel
sudo apt install xclip
```

**Q: 插件无法安装**
```bash
# 确保 git 可用，并检查网络连接
git --version

# 手动安装 TPM
git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm
```

### 性能调优

如果遇到性能问题：

```bash
# 减少状态栏更新频率
set -g status-interval 15

# 减少历史缓冲区大小
set -g history-limit 10000

# 禁用不需要的监控
setw -g monitor-activity off
```

## 🚀 高级技巧

### 批量操作

```bash
# 同时在所有面板执行命令
Ctrl-a :setw synchronize-panes on

# 关闭同步
Ctrl-a :setw synchronize-panes off
```

### 会话共享

```bash
# 创建可共享的会话
tmux -S /tmp/shared new -s shared

# 其他用户连接
tmux -S /tmp/shared attach -t shared
```

### 脚本化管理

```bash
# 检查会话是否存在
tmux has-session -t myproject 2>/dev/null && echo "Session exists"

# 条件创建会话
tmux has-session -t myproject 2>/dev/null || tmux new-session -d -s myproject
```

## 📚 更多资源

- [Tmux 官方文档](https://github.com/tmux/tmux/wiki)
- [Awesome Tmux](https://github.com/rothgar/awesome-tmux) - 精选插件和配置
- [Tmux Cheat Sheet](https://tmuxcheatsheet.com/) - 快捷键参考

---

**享受高效的终端体验！** 🎉