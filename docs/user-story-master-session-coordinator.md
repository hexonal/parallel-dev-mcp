# 主会话机器人协调器 - Brownfield 用户故事

## Story Title
主会话机器人协调器 - 并行 Worktree 开发系统核心组件

## User Story

作为一个并行开发团队的技术负责人，
我希望有一个智能的主会话协调器机器人，
以便能够自动管理多个并行的worktree开发任务，实现任务拆分、会话监控、进度跟踪和自动合并的完整工作流。

## Story Context

**现有系统集成:**

- 集成组件: Tmux-Orchestrator (会话管理) + SplitMind (多代理协调) + TaskMaster-AI (任务拆分)
- 技术栈: Python 3.11, tmux 3.0+, Git worktree, FastMCP 2.0
- 遵循模式: 三层架构模式 (协调器 → 项目管理器 → 开发会话)
- 接触点: Git worktree API, tmux 会话管理, TaskMaster-AI REST API

## Acceptance Criteria

### 功能需求

1. **智能任务拆分与分发**
   - 接收复杂开发需求，自动调用 TaskMaster-AI 进行任务分解
   - 为每个子任务自动创建独立的 Git worktree
   - 将子任务分配到不同的 tmux 子会话进行并行开发

2. **实时会话监控与状态追踪**
   - 每5分钟自动检查所有子会话的开发状态
   - 监控子会话的响应性，区分"正在开发"和"开发完成"状态
   - 提供实时的任务进度汇总和可视化报告

3. **智能合并与同步机制**
   - 检测到子会话完成后，自动将 worktree 分支合并到主分支
   - 在主会话中自动 pull 最新代码，保持代码库同步
   - 处理合并冲突，必要时暂停自动合并等待人工干预

### 集成需求

4. **与现有 TaskMaster-AI 系统保持完全兼容**
   - 继承现有的任务跟踪和进度管理功能
   - 支持 TaskMaster-AI 的智能任务依赖分析

5. **继承 Tmux-Orchestrator 的会话管理模式**
   - 使用相同的三层架构：协调器 → 项目管理器 → 工程师会话
   - 支持自动调度和检查机制

6. **集成 SplitMind 的多代理协调能力**
   - 实现类似 A2AMCP 的会话间通信协议
   - 支持实时状态同步和冲突预防机制

### 质量需求

7. **会话状态检测的准确性达到 95% 以上**
   - 能够准确识别子会话是否在活跃开发中
   - 避免误判导致的不当合并或任务重复分配

8. **防止嵌套会话问题**
   - 子会话只能管理当前项目，不能创建新的嵌套子会话
   - 实施严格的权限控制和会话边界管理

9. **自动恢复和容错机制**
   - 系统重启后能够恢复所有会话状态
   - 处理网络中断、进程崩溃等异常情况

## Technical Notes

### 集成方法

**TaskMaster-AI 集成方式:**
```python
# 任务分解接口
task_breakdown = await taskmaster_ai.decompose_task(
    description="实现用户认证系统",
    project_context=current_project_context
)

# 任务状态同步
await taskmaster_ai.sync_task_status(task_id, status, progress)
```

**会话监控机制:**
```bash
# 基于状态文件的监控
echo "WORKING" > /tmp/session-status/${session_name}.status
# 或使用心跳机制
./scripts/session-heartbeat.sh ${session_name}
```

**Worktree 管理:**
```bash
# 为每个任务创建独立 worktree
git worktree add ../worktrees/task-${task_id} -b feature/task-${task_id}
# 完成后自动合并
git worktree remove ../worktrees/task-${task_id}
git merge feature/task-${task_id}
```

### 现有模式参考

**遵循 Tmux-Orchestrator 的自调度模式:**
```bash
# 自动调度检查
./schedule_with_note.sh 5 "检查所有子会话状态和进度"
```

**借鉴 SplitMind 的状态同步机制:**
```python
# 会话间状态共享
session_state = {
    "task_id": "AUTH_001",
    "status": "IN_PROGRESS", 
    "last_update": timestamp,
    "completion_percentage": 45
}
```

### 关键约束

- **会话隔离**: 子会话不能创建新的子会话，防止无限嵌套
- **资源管理**: 最多同时运行 8 个并行开发会话
- **状态一致性**: 所有会话状态必须与 TaskMaster-AI 保持同步
- **安全合并**: 自动合并前必须通过所有质量检查

## Definition of Done

- [ ] 能够接收复杂需求并自动调用 TaskMaster-AI 进行任务分解
- [ ] 为每个子任务创建独立的 Git worktree 和 tmux 会话
- [ ] 实现5分钟间隔的自动会话状态检查和进度跟踪
- [ ] 能够准确区分"开发中"和"已完成"的会话状态
- [ ] 自动合并完成的 worktree 分支到主分支
- [ ] 防止子会话创建嵌套会话的权限控制机制
- [ ] 与 TaskMaster-AI 的完整集成和状态同步
- [ ] 异常恢复和容错处理机制
- [ ] 完整的测试覆盖和文档

## Risk Assessment & Compatibility Check

### 主要风险

**主要风险:** Git worktree 并发合并可能导致代码冲突和数据丢失
**缓解措施:** 实施分布式锁机制，确保同一时间只有一个合并操作
**回滚方案:** 保留每次合并前的备份分支，支持一键回滚

### 兼容性验证

- [ ] 不破坏现有的 TaskMaster-AI API 接口
- [ ] Git worktree 操作仅为增量操作，不影响主仓库
- [ ] tmux 会话创建遵循现有命名约定和权限模型
- [ ] 性能影响控制在可接受范围内（< 5% CPU 使用率增长）

## Scope Validation

- [ ] 用户故事可以在一个集中的开发周期内完成（预计 2-3 天）
- [ ] 集成方法简单直接，基于现有稳定的API
- [ ] 完全遵循现有的三层架构模式
- [ ] 不需要重大架构设计或新框架引入

## Success Criteria

该用户故事成功实现时将达到:

1. **任务自动化程度提升 80%**: 从手动任务分配到全自动并行开发
2. **开发效率提升 3-5倍**: 通过真正的并行 worktree 开发
3. **错误率降低 90%**: 通过自动化监控和智能合并机制
4. **团队协作体验显著改善**: 实时状态可视化和自动协调
5. **代码质量保持稳定**: 通过强制的质量检查和测试集成

---

**注意**: 这是一个foundational story，为整个并行开发系统奠定核心基础。后续的增强功能（如高级冲突解决、性能优化、监控仪表板等）将作为独立的故事进行开发。