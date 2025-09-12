# 智能会话识别系统

Claude Code hooks 的智能会话识别解决方案，提供零配置的自动化会话管理。

## 🧠 核心特性

### 智能会话识别
- **自动类型识别**: 根据 tmux 会话名称自动判断主会话 vs 子会话
- **零环境变量依赖**: 完全基于会话名称模式匹配
- **动态会话发现**: 实时发现和协调相关会话
- **智能消息路由**: 自动建立主子会话通信链路

### 支持的会话命名规范
- **主会话**: `parallel_{PROJECT_ID}_task_master`
- **子会话**: `parallel_{PROJECT_ID}_task_child_{TASK_ID}`

## 📋 smart_session_detector.py

### 识别逻辑
```python
# 主会话识别
if session_name.endswith("_task_master"):
    session_type = "master"
    project_id = extract_project_id(session_name)

# 子会话识别  
elif "_task_child_" in session_name:
    session_type = "child"
    project_id, task_id = extract_project_and_task(session_name)
```

### 支持的事件类型
| 事件 | 描述 | 触发时机 |
|------|------|----------|
| `session-start` | 会话启动 | Claude Code 会话开始时 |
| `user-prompt` | 用户提示 | 用户提交提示时 |
| `stop` | 任务暂停 | 任务执行暂停时（用于进度汇报） |
| `session-end` | 会话结束 | Claude Code 会话结束时 |

### 自动行为

#### 主会话启动时
- 🔍 **发现子会话**: 自动扫描所有相关子会话
- 📊 **状态监控**: 显示发现的子会话数量和状态
- 🎯 **协调准备**: 准备接收来自子会话的消息

#### 子会话启动时  
- 📝 **自动注册**: 向主会话发送注册消息
- 🔗 **建立通信**: 自动建立与主会话的通信链路
- ✅ **确认连接**: 显示注册成功状态

#### 任务进度汇报
- 📈 **定时汇报**: 在任务暂停时向主会话汇报进度
- 📊 **状态同步**: 保持主会话对所有子会话状态的了解

#### 会话完成时
- 🎉 **完成通知**: 子会话向主会话发送完成消息  
- 📋 **状态更新**: 主会话更新项目整体状态

## 🚀 使用方式

### ⚠️ 重要前提：PROJECT_ID 与会话命名一致性

**关键要求**: MCP配置中的 `PROJECT_ID` 环境变量必须与 tmux 会话名称中的 `{PROJECT_ID}` 部分完全一致！

#### 正确的配置关联：
```bash
# MCP 配置中设置：
"env": { "PROJECT_ID": "ECOMMERCE" }

# 对应的会话名称：
parallel_ECOMMERCE_task_master        # 主会话
parallel_ECOMMERCE_task_child_AUTH    # 子会话
```

### 1. 自动使用（推荐）
通过配置生成器自动配置：
```bash
python tools/config_generator.py --project-id MYPROJECT --tasks TASK1 TASK2
```

生成的 `smart_hooks.json` 会自动配置所有必要的hooks。

**重要**: 确保你的MCP服务器配置中的 `PROJECT_ID` 环境变量与生成配置时使用的 `--project-id` 参数值一致！

### 2. 手动测试
```bash
# 测试会话信息获取
python examples/hooks/smart_session_detector.py info -v

# 模拟会话启动
python examples/hooks/smart_session_detector.py session-start -v

# 模拟用户提示
python examples/hooks/smart_session_detector.py user-prompt "测试提示" -v
```

### 3. 调试模式
使用 `-v` 或 `--verbose` 参数查看详细的处理结果：
```bash
python examples/hooks/smart_session_detector.py session-start -v
```

输出示例：
```json
{
  "status": "success",
  "session_type": "child",
  "project_id": "ECOMMERCE",
  "task_id": "AUTH",
  "master_session": "parallel_ECOMMERCE_task_master",
  "registered": true
}
```

## 🔧 配置集成

### Claude Code 配置
将生成的 `smart_hooks.json` 配置到 Claude Code：

```json
{
  "user-prompt-submit-hook": {
    "command": [
      "python", 
      "/path/to/smart_session_detector.py", 
      "user-prompt", 
      "{{prompt}}"
    ]
  },
  "session-start-hook": {
    "command": [
      "python", 
      "/path/to/smart_session_detector.py", 
      "session-start"
    ]
  },
  "stop-hook": {
    "command": [
      "python", 
      "/path/to/smart_session_detector.py", 
      "stop"
    ]
  },
  "session-end-hook": {
    "command": [
      "python", 
      "/path/to/smart_session_detector.py", 
      "session-end"
    ]
  }
}
```

### 关键优势
- **统一配置**: 所有会话类型使用同一个配置文件
- **零维护**: 添加新任务无需更新hooks配置
- **自动适配**: 支持任意项目ID和任务ID组合
- **高可靠**: 基于tmux实际状态，不依赖外部配置

## 🎯 设计理念

### 简化原则
- **配置最小化**: 从N+1个配置文件减少到1个
- **依赖最小化**: 零环境变量依赖，纯会话名称识别
- **维护最小化**: 一次配置，永久使用

### 智能原则  
- **自动发现**: 动态发现和适配会话结构
- **智能路由**: 自动建立正确的通信路径
- **状态感知**: 实时感知和响应会话状态变化

### 可靠性原则
- **基于实际状态**: 依赖tmux实际会话状态而非配置
- **容错处理**: 优雅处理会话不存在等异常情况
- **静默失败**: 避免影响正常工作流程

## 🔧 故障排除指南

### 常见问题和解决方案

| 问题症状 | 可能原因 | 解决方法 |
|----------|----------|----------|
| **hooks无响应** | 会话名称不符合规范 | 检查会话名称是否使用 `parallel_{PROJECT_ID}_task_*` 格式 |
| **"未找到主会话"** | PROJECT_ID不匹配 | 确认MCP配置中的PROJECT_ID与会话名称一致 |
| **子会话无法注册** | 主会话未创建 | 先创建主会话再创建子会话 |
| **智能识别失败** | 会话名称解析错误 | 使用标准命名规范，避免特殊字符 |

### 调试步骤

#### 步骤1: 验证会话命名
```bash
# 检查当前所有会话
tmux list-sessions

# 确认命名格式正确
# ✅ 正确: parallel_ECOMMERCE_task_master
# ❌ 错误: ECOMMERCE_master, parallel-ECOMMERCE-task-master
```

#### 步骤2: 验证MCP配置
```bash
# 检查MCP配置中的PROJECT_ID
# 应该与会话名称中的{PROJECT_ID}部分完全一致
echo $PROJECT_ID  # 在MCP环境中检查
```

#### 步骤3: 手动测试智能识别
```bash
# 在正确命名的会话中测试
python examples/hooks/smart_session_detector.py info -v

# 应该看到正确的会话信息识别
```

#### 步骤4: 测试会话通信
```bash
# 从子会话测试向主会话发送消息
python examples/hooks/smart_session_detector.py session-start -v

# 检查主会话是否收到注册消息
```

### 正确设置检查清单

- [ ] MCP配置中的 `PROJECT_ID` 已设置
- [ ] 会话名称遵循 `parallel_{PROJECT_ID}_task_*` 格式
- [ ] MCP中的 `PROJECT_ID` 与会话名称中的 `{PROJECT_ID}` 一致
- [ ] 主会话在子会话之前创建
- [ ] 智能hooks配置文件路径正确
- [ ] Python脚本具有执行权限

---

**这个智能系统代表了Claude Code hooks配置的重大进步，从复杂的多文件配置转向了简单、智能、可靠的单一配置解决方案。通过正确的PROJECT_ID配置，实现了MCP环境与tmux会话的完美关联。**