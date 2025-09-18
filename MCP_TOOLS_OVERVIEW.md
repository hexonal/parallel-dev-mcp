# 并行开发MCP系统 - 工具概览

## 📊 工具总览

**当前状态**: 13个MCP工具，已精简46%（从24个减少到13个）

### 🏗️ 架构分层

```
🔧 TMUX层 - 基础会话管理      4个工具
📋 SESSION层 - 开发环境管理   4个工具
🎯 PROMPT层 - 模板和提示管理  1个工具（精简5个）
📊 MESSAGE层 - 消息传递       1个工具（精简6个）
⚙️ SERVER层 - 系统管理        3个工具
```

---

## 🔧 TMUX层 - 基础会话管理 (4个工具)

### `list_tmux_sessions`
- **功能**: 列出tmux会话，支持项目前缀过滤
- **用途**: 会话发现和管理基础
- **优先级**: 🔴 核心必需

### `kill_tmux_session`
- **功能**: 删除指定的tmux会话，支持强制删除
- **用途**: 资源清理工具
- **优先级**: 🔴 核心必需

### `send_keys_to_tmux_session`
- **功能**: 向tmux会话发送按键序列，核心交互工具
- **用途**: 远程会话控制，最重要的交互工具
- **优先级**: 🔴 核心必需

### `get_tmux_session_info`
- **功能**: 获取tmux会话详细信息，用于调试监控
- **用途**: 会话状态诊断
- **优先级**: 🟡 可选保留

---

## 📋 SESSION层 - 开发环境管理 (4个工具)

### `create_session`
- **功能**: 创建完整开发环境(worktree + tmux + Claude Code)
- **用途**: 一键环境搭建，核心业务工具
- **优先级**: 🔴 核心必需

### `update_master_resource`
- **功能**: 更新Master项目资源信息和状态
- **用途**: 项目级状态维护
- **优先级**: 🔴 核心必需

### `update_child_resource`
- **功能**: 更新Child任务资源信息和状态
- **用途**: 任务级状态维护
- **优先级**: 🔴 核心必需

### `remove_child_resource`
- **功能**: 移除Child资源，支持清理worktree和tmux
- **用途**: 资源清理和回收，避免资源泄漏
- **优先级**: 🔴 核心必需

---

## 🎯 PROMPT层 - 模板和提示管理 (1个工具，已精简5个) mcp_prompt
# master_prompt
标准对话{task_master_protmt}
# child_prompt
严格限制对话+{task_master_child_protmt}

# 内部流转会话
## master
- 继续
# child
 master 发送给 child 的会话保存起来（前置行为）
继续+ (master 发送给 child 的会话) ->master 发送信号：任务已经完成



### `generate_continue_prompt_tool` ✅
- **功能**: 生成继续执行Prompt，用于限流恢复
- **用途**: 限流恢复
- **优先级**: 🔴 核心必需
- **说明**: 专门处理限流场景，保留为核心功能

### ❌ 已移除的工具 (5个)
- `generate_prompt_tool` - 过度工程化，简单字符串拼接即可
- `list_templates_tool` - 模板数量有限，硬编码即可
- `reload_template_tool` - 生产环境不需要热重载
- `validate_templates_tool` - 可在构建时验证，不需要运行时工具
- `get_template_info_tool` - 调试用途，可简化为日志输出

---

## 📊 MESSAGE层 - 消息传递 (1个工具，已精简6个)

### `send_delayed_message_tool` ✅
- **功能**: 延时发送消息到tmux会话，支持优先级
- **用途**: 异步消息传递
- **优先级**: 🔴 核心必需
- **说明**: 核心延时消息功能，支持优先级队列

### ❌ 已移除的工具 (6个)
- `get_message_status_tool` - 过度设计，使用简单日志即可
- `get_queue_status_tool` - 队列简单时不需要专门工具
- `cancel_message_tool` - 使用场景有限
- `clear_message_queue_tool` - 使用频率极低
- `get_performance_metrics_tool` - 可合并到系统状态工具中
- `get_system_logs_tool` - 直接查看日志文件更简单

---

## ⚙️ SERVER层 - 系统管理 (3个工具)

### `get_system_info`
- **功能**: 获取系统状态、版本、工具数量等信息
- **用途**: 系统状态查询
- **优先级**: 🟡 可选保留
- **说明**: 调试和监控有用

### `initialize_parallel_dev_system`
- **功能**: 初始化并行开发系统资源
- **用途**: 系统初始化
- **优先级**: 🟡 可选保留
- **说明**: 如果初始化复杂，可保留

### `get_parallel_dev_status`
- **功能**: 获取并行开发系统运行状态
- **用途**: 系统状态监控
- **优先级**: 🟡 可选保留
- **说明**: 可与get_system_info合并

---

## 🎯 优化建议

### 🔴 核心必需工具 (10个) - 已确认保留
- `list_tmux_sessions`
- `kill_tmux_session`
- `send_keys_to_tmux_session`
- `create_session`
- `update_master_resource`
- `update_child_resource`
- `remove_child_resource`
- `send_delayed_message_tool`
- `generate_continue_prompt_tool`

### 🟡 系统管理工具 (4个) - 可选保留
- `get_tmux_session_info`
- `get_system_info`
- `initialize_parallel_dev_system`
- `get_parallel_dev_status`

### ✅ 已成功移除工具 (11个) - 过度设计
**MESSAGE层移除 (6个)**:
- `get_message_status_tool`
- `get_queue_status_tool`
- `cancel_message_tool`
- `clear_message_queue_tool`
- `get_performance_metrics_tool`
- `get_system_logs_tool`

**PROMPT层移除 (5个)**:
- `generate_prompt_tool`
- `list_templates_tool`
- `reload_template_tool`
- `validate_templates_tool`
- `get_template_info_tool`

---

## 📈 优化结果总结

### ✅ 已完成的优化 (目标已达成)

1. **PROMPT层精简**: 从6个工具精简为1个核心工具 ✅
   - 保留 `generate_continue_prompt_tool` (限流恢复核心功能)
   - 移除 5个过度设计工具

2. **MESSAGE层精简**: 从7个工具精简为1个核心工具 ✅
   - 保留 `send_delayed_message_tool` (延时消息核心功能)
   - 移除 6个过度设计工具

3. **最终实现架构**:
   ```
   🔧 TMUX层: 4个工具 (保持不变)
   📋 SESSION层: 4个工具 (保持不变)
   🎯 PROMPT层: 1个工具 (精简5个) ✅
   📊 MESSAGE层: 1个工具 (精简6个) ✅
   ⚙️ SERVER层: 3个工具 (保持不变)
   总计: 13个工具 (精简46%)
   ```

---

## 🔄 架构演进历史

- **原始设计**: 16个工具 (4层架构)
- **功能扩展**: 24个工具 (5个模块)
- **首次精简**: 18个工具 (移除6个MESSAGE工具)
- **二次精简**: 13个工具 (移除5个PROMPT工具) ← 当前状态
- **精简效果**: 46%工具减少，保持核心功能完整

---

## 💡 设计原则

1. **保持简洁**: 避免过度工程化
2. **功能聚焦**: 每个工具有明确的单一职责
3. **用户友好**: 工具功能直观易用
4. **维护性**: 减少复杂性，提高代码可维护性
5. **性能优先**: 精简的工具集提供更好的性能