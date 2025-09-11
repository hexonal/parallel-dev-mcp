# Story: MCP会话协调系统 - 智能并行开发核心组件

<!-- Source: 棕地项目综合技术文档 -->
<!-- Context: 并行 Worktree 开发系统的核心通信机制 -->

## Status: Draft

## Story

作为一个并行开发系统的架构师，
我希望有一个基于MCP的会话协调系统，
以便实现主会话和子会话间的智能通信、状态管理和任务协调，为并行 worktree 开发奠定坚实的技术基础。

## Story Context

**现有系统集成:**

- 基础设施: Python 3.11+, tmux 3.0+, Git worktree, FastMCP 2.0
- 核心组件: TaskMaster-AI (任务分解), Claude Code (hooks机制)
- 技术模式: 三层架构 (主协调器 → 项目管理器 → 开发会话)
- 关键约束: 最多8个并行会话, 防止嵌套会话, 95%状态检测准确率

**当前项目状态:**
- 📁 目录结构已创建 (`src/`, `config/`, `scripts/`, `docs/`)
- 📄 设计文档完整 (会话监控设计, worktree合并设计, 用户故事)
- 🚧 实现代码为空 (仅有 `.gitkeep` 占位文件)

## Acceptance Criteria

### 功能需求

1. **MCP Session Coordinator 服务器**
   - 实现会话注册和关系管理功能
   - 支持主子会话的身份识别和路由
   - 提供会话状态跟踪和消息传递机制
   - 集成Claude Code hooks调用接口

2. **智能会话路由系统**
   - 基于会话命名规范自动识别父子关系
   - 子会话状态自动路由到对应主会话
   - 主会话可精确定位和控制特定子会话
   - 支持会话间双向消息传递

3. **Claude Hooks集成**
   - 子会话通过hooks自动上报任务进度
   - 支持任务完成、工具调用、错误状态的自动检测
   - 主会话接收实时状态更新和完成通知
   - 集成定期消息检查机制

### 集成需求

4. **与现有tmux生态完全兼容**
   - 利用tmux会话名称和环境变量机制
   - 支持tmux send-keys和capture-pane操作
   - 遵循现有的三层架构模式

5. **TaskMaster-AI预留接口**
   - 为任务分解和分发预留MCP接口
   - 支持任务依赖关系管理
   - 保持与未来TaskMaster-AI集成的兼容性

### 质量需求

6. **高可靠性通信机制**
   - MCP工具调用成功率 ≥ 98%
   - 会话状态同步延迟 ≤ 5秒
   - 支持网络中断和服务重启恢复

7. **安全的会话边界控制**
   - 严格的会话命名规范验证
   - 防止非授权会话注册和消息访问
   - 会话生命周期完整跟踪和清理

## Dev Technical Guidance

### 系统架构设计

**MCP服务器核心组件:**
```python
# src/mcp_server/session_coordinator.py
class SessionCoordinatorMCP:
    # 会话关系管理
    session_relationships: Dict[str, SessionRelationship]
    # 活跃会话状态  
    active_sessions: Dict[str, SessionStatus]
    # 会话间消息队列
    session_messages: Dict[str, List[Message]]
    
    # 核心MCP工具
    @mcp.tool("register_session_relationship")
    @mcp.tool("report_session_status") 
    @mcp.tool("get_child_sessions")
    @mcp.tool("send_message_to_session")
    @mcp.tool("get_session_messages")
```

**会话命名规范:**
- 主会话: `master_project_<project_id>`
- 子会话: `child_<project_id>_task_<task_id>`
- 自动解析: `parse_session_relationship(session_name)`

**Claude Hooks配置模板:**
```json
// 子会话 .claude/hooks.json
{
  "session-start": ["mcp://session-coordinator/report_session_status?..."],
  "after-tool-call": ["mcp://session-coordinator/report_session_status?..."],
  "task-completion": ["mcp://session-coordinator/report_session_status?..."],
  "periodic-message-check": ["mcp://session-coordinator/get_session_messages?..."]
}
```

### 技术实现要点

**1. 会话身份识别机制**
- 环境变量传递: `MASTER_SESSION_ID`, `TASK_ID`, `SESSION_ROLE`
- tmux会话名称解析: 自动提取项目ID和任务ID
- 注册时验证: 防止重复注册和非法命名

**2. 状态同步策略**
- hooks触发: 实时状态上报 (立即响应)
- 定期扫描: 5分钟兜底检查 (防遗漏)
- 消息路由: 基于父子关系自动分发

**3. 错误处理和恢复**
- MCP调用失败重试机制
- 会话异常断开检测和清理
- 状态不一致自动修复

### 关键文件结构

```
src/
├── mcp_server/
│   ├── session_coordinator.py      # MCP服务器主体
│   ├── session_models.py           # 数据模型定义
│   └── session_utils.py            # 工具函数
├── coordinator/
│   ├── master_session.py           # 主会话管理器
│   └── child_session.py            # 子会话管理器
├── hooks/
│   ├── hooks_templates/            # Claude hooks模板
│   └── hooks_manager.py            # hooks配置管理
└── utils/
    ├── session_naming.py           # 会话命名工具
    └── tmux_helpers.py            # tmux操作封装
```

### 现有集成点参考

**从项目文档中提取的模式:**
- 心跳检测机制: `docs/session-monitoring-design.md:49-80`
- 权限控制设计: `docs/session-monitoring-design.md:84-141`
- 自动调度模式: `docs/user-story-master-session-coordinator.md:103-107`

## Tasks / Subtasks

### 阶段1: MCP服务器基础框架 (1-2天)

- [ ] **Task 1.1: 创建MCP服务器骨架**
  - [ ] 设置FastMCP 2.0项目结构
  - [ ] 实现基础的MCP工具接口定义
  - [ ] 创建会话数据模型 (`SessionRelationship`, `SessionStatus`)
  - [ ] 配置服务器启动脚本和配置文件

- [ ] **Task 1.2: 实现会话注册功能**
  - [ ] `register_session_relationship` 工具实现
  - [ ] 会话命名规范验证逻辑
  - [ ] 父子关系存储和查询机制
  - [ ] 单元测试: 注册功能和数据完整性

### 阶段2: 状态管理和消息路由 (2-3天)

- [ ] **Task 2.1: 会话状态跟踪系统**
  - [ ] `report_session_status` 工具实现
  - [ ] 状态自动路由到父会话逻辑
  - [ ] 状态历史记录和持久化
  - [ ] 集成测试: 状态上报和路由准确性

- [ ] **Task 2.2: 会话间消息传递**
  - [ ] `send_message_to_session` 工具实现
  - [ ] `get_session_messages` 工具实现
  - [ ] 消息队列管理和过期清理
  - [ ] 集成测试: 双向消息传递功能

### 阶段3: Claude Hooks集成 (2天)

- [ ] **Task 3.1: Hooks模板和配置管理**
  - [ ] 创建子会话hooks.json模板
  - [ ] 实现hooks配置自动生成脚本
  - [ ] 环境变量动态注入机制
  - [ ] 验证hooks调用MCP工具的完整流程

- [ ] **Task 3.2: 主会话监控机制**
  - [ ] `get_child_sessions` 工具实现
  - [ ] 主会话定期状态检查脚本
  - [ ] 任务完成通知处理逻辑
  - [ ] 集成测试: 端到端通信流程

### 阶段4: 会话生命周期管理 (1-2天)

- [ ] **Task 4.1: 会话创建和销毁**
  - [ ] 主会话创建子会话脚本实现
  - [ ] 环境变量和tmux配置传递
  - [ ] 会话终止时的清理机制
  - [ ] 异常会话检测和恢复

- [ ] **Task 4.2: 错误处理和容错机制**
  - [ ] MCP调用失败重试逻辑
  - [ ] 会话断开检测和状态修复
  - [ ] 日志记录和错误报告系统
  - [ ] 压力测试: 多会话并发场景

### 阶段5: 集成验证和生产准备 (1天)

- [ ] **Task 5.1: 端到端集成测试**
  - [ ] 创建完整的测试场景脚本
  - [ ] 验证8个并行会话的性能表现
  - [ ] 测试会话异常恢复能力
  - [ ] 性能基准测试和优化

- [ ] **Task 5.2: 生产部署准备**
  - [ ] 编写MCP服务器部署指南
  - [ ] 创建会话使用示例和最佳实践
  - [ ] 配置自动启动脚本和监控
  - [ ] 完成用户手册和故障排除指南

## Risk Assessment

### 主要风险

**主要风险:** MCP服务器单点故障可能导致整个会话协调系统失效
**缓解措施:** 
- 实现MCP服务器自动重启机制
- 设计状态持久化避免数据丢失
- 提供降级模式支持基本的tmux操作
**验证方法:** 故意终止MCP服务器，验证重启后状态恢复

### 兼容性验证

- [ ] MCP工具调用不干扰Claude Code正常功能
- [ ] hooks配置不影响现有Claude Code使用方式
- [ ] tmux会话操作兼容现有开发工作流
- [ ] 性能影响控制在可接受范围 (< 10% CPU增长)

### 安全考虑

- [ ] 会话命名规范防止恶意注册
- [ ] 消息访问权限验证机制
- [ ] 敏感信息不在MCP消息中传输
- [ ] 会话数据定期清理避免泄露

## Rollback Plan

**简单回滚步骤:**
1. 停止MCP Session Coordinator服务器
2. 恢复原始的.claude/hooks.json配置
3. 清理临时创建的会话和配置文件
4. 验证标准Claude Code功能正常

**状态恢复:**
- MCP服务器数据存储在 `config/session_state.json`
- 自动备份每小时创建，保留24小时
- 支持从任意备份点恢复会话状态

## Success Criteria

该MCP会话协调系统成功实现时将达到:

1. **技术指标达成:**
   - MCP工具调用响应时间 < 2秒
   - 会话状态同步准确率 ≥ 98%
   - 支持8个并发会话稳定运行
   - 系统资源占用 < 100MB内存

2. **功能完整性验证:**
   - 子会话状态能够实时上报到主会话
   - 主会话可以精确控制特定子会话
   - Claude hooks无缝集成MCP调用
   - 会话异常自动检测和恢复

3. **生产就绪状态:**
   - MCP服务器稳定运行并可自动重启
   - 完整的用户手册和部署指南
   - 故障排除文档和最佳实践指南
   - 为用户提供开箱即用的并行会话协调能力

## Implementation Notes

**关键决策记录:**
- 选择基于MCP而非文件系统通信，提供标准化接口
- 使用会话命名规范自动识别父子关系，简化配置
- Claude hooks作为状态上报触发器，实现零配置监控
- 预留TaskMaster-AI接口，支持未来智能任务分解集成

**范围控制:**
- 专注于MCP会话协调系统的完整实现
- 暂不包含TaskMaster-AI集成 (预留接口)
- 暂不包含Git worktree自动管理 (独立故事)
- 暂不包含UI监控界面 (命令行优先)

**质量优先:**
- 确保MCP通信机制的稳定性和可靠性
- 完善错误处理和异常恢复机制
- 提供完整的测试覆盖和文档

---

**注意**: 这是一个自包含的完整功能故事。实现后将为用户提供稳定可用的并行会话协调系统，无需依赖其他未完成组件。