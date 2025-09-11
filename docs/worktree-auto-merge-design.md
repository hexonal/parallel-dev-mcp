# Worktree 自动合并流程设计

## 核心设计原则

基于参考项目分析，结合您的需求，设计一个安全、智能的 worktree 自动合并系统：

### 借鉴 Tmux-Orchestrator 的安全策略
- 每30分钟自动提交，确保工作不丢失
- 合并前创建备份分支
- 分步验证和回滚机制

### 借鉴 SplitMind 的智能协调
- 基于状态同步的合并时机判断
- 冲突预防和解决机制
- 实时进度追踪

## 自动合并流程架构

### 阶段1: 合并准备和验证

```python
class WorktreeMergeManager:
    """Worktree 自动合并管理器"""
    
    def __init__(self):
        self.lock_manager = DistributedLockManager()
        self.conflict_resolver = IntelligentConflictResolver()
        self.backup_manager = BackupManager()
    
    async def prepare_for_merge(self, task_id: str) -> MergePreparation:
        """合并前准备和验证"""
        
        # 1. 获取分布式锁，确保同一时间只有一个合并操作
        async with self.lock_manager.acquire(f"merge-{task_id}"):
            
            # 2. 验证任务完成状态
            task_status = await self.verify_task_completion(task_id)
            if not task_status.is_ready_for_merge:
                raise NotReadyForMergeError(f"任务 {task_id} 未准备好合并")
            
            # 3. 检查代码质量
            quality_check = await self.run_quality_checks(task_id)
            if not quality_check.passed:
                raise QualityCheckFailedError(f"质量检查失败: {quality_check.issues}")
            
            # 4. 创建备份分支
            backup_branch = await self.backup_manager.create_backup(task_id)
            
            # 5. 分析潜在冲突
            conflict_analysis = await self.analyze_potential_conflicts(task_id)
            
            return MergePreparation(
                task_id=task_id,
                backup_branch=backup_branch,
                conflict_analysis=conflict_analysis,
                quality_report=quality_check
            )
```

### 阶段2: 智能冲突检测和解决

```python
class IntelligentConflictResolver:
    """智能冲突解决器"""
    
    async def analyze_potential_conflicts(self, task_id: str) -> ConflictAnalysis:
        """分析潜在冲突"""
        
        worktree_path = f"worktrees/task-{task_id}"
        main_branch = "main"
        
        # 1. 获取文件变更差异
        file_changes = await self.get_file_changes(worktree_path)
        
        # 2. 检查主分支的最新变更
        main_changes = await self.get_main_branch_changes_since(
            self.get_branch_point(task_id)
        )
        
        # 3. 识别重叠文件
        overlapping_files = set(file_changes.keys()) & set(main_changes.keys())
        
        # 4. 分析冲突类型和严重程度
        conflicts = []
        for file_path in overlapping_files:
            conflict_type = await self.analyze_file_conflict(
                file_path, file_changes[file_path], main_changes[file_path]
            )
            conflicts.append(conflict_type)
        
        return ConflictAnalysis(
            overlapping_files=overlapping_files,
            conflicts=conflicts,
            auto_resolvable=self.count_auto_resolvable(conflicts),
            requires_manual_intervention=self.count_manual_required(conflicts)
        )
    
    async def resolve_conflicts_automatically(self, conflicts: List[Conflict]) -> ResolutionResult:
        """自动解决可解决的冲突"""
        
        resolved = []
        failed = []
        
        for conflict in conflicts:
            if conflict.is_auto_resolvable():
                try:
                    resolution = await self.apply_auto_resolution(conflict)
                    resolved.append(resolution)
                except Exception as e:
                    failed.append(ConflictResolutionFailure(conflict, str(e)))
            else:
                failed.append(ConflictResolutionFailure(
                    conflict, "需要人工干预"
                ))
        
        return ResolutionResult(
            resolved=resolved,
            failed=failed,
            success_rate=len(resolved) / len(conflicts) if conflicts else 1.0
        )
```

### 阶段3: 分步式安全合并

```python
class StepwiseMergeExecutor:
    """分步式合并执行器"""
    
    async def execute_merge(self, preparation: MergePreparation) -> MergeResult:
        """执行分步式合并"""
        
        task_id = preparation.task_id
        
        try:
            # 步骤1: 更新主分支到最新
            await self.update_main_branch()
            
            # 步骤2: 在worktree中合并最新的主分支
            merge_status = await self.merge_main_into_worktree(task_id)
            if not merge_status.success:
                return await self.handle_merge_failure(task_id, merge_status)
            
            # 步骤3: 重新运行测试确保兼容性
            test_result = await self.run_comprehensive_tests(task_id)
            if not test_result.passed:
                return await self.handle_test_failure(task_id, test_result)
            
            # 步骤4: 执行实际合并到主分支
            final_merge = await self.merge_worktree_to_main(task_id)
            if not final_merge.success:
                return await self.handle_final_merge_failure(task_id, final_merge)
            
            # 步骤5: 清理worktree
            await self.cleanup_worktree(task_id)
            
            # 步骤6: 更新任务状态
            await self.update_task_status_completed(task_id)
            
            return MergeResult(
                success=True,
                task_id=task_id,
                merge_commit=final_merge.commit_hash,
                cleanup_completed=True
            )
            
        except Exception as e:
            # 任何错误都回滚到备份分支
            await self.rollback_to_backup(preparation.backup_branch)
            return MergeResult(
                success=False,
                task_id=task_id,
                error=str(e),
                rollback_completed=True
            )
```

### 阶段4: 主会话协调和监控

```python
class MasterSessionCoordinator:
    """主会话协调器 - 负责整体合并流程的协调"""
    
    def __init__(self):
        self.merge_manager = WorktreeMergeManager()
        self.session_monitor = SessionMonitor()
        self.taskmaster_sync = TaskMasterSync()
    
    async def coordinate_auto_merge(self, session_name: str):
        """协调自动合并流程"""
        
        # 1. 检查会话状态
        session_status = await self.session_monitor.get_session_status(session_name)
        if session_status.status != SessionStatus.READY_FOR_MERGE:
            return
        
        task_id = session_status.task_id
        
        # 2. 向TaskMaster-AI确认任务完成
        taskmaster_confirmation = await self.taskmaster_sync.confirm_task_completion(task_id)
        if not taskmaster_confirmation.confirmed:
            await self.handle_taskmaster_mismatch(task_id, taskmaster_confirmation)
            return
        
        # 3. 执行合并流程
        merge_result = await self.merge_manager.execute_full_merge(task_id)
        
        # 4. 同步结果到所有系统
        await self.sync_merge_result(task_id, merge_result)
        
        # 5. 通知相关会话
        await self.notify_merge_completion(session_name, merge_result)
    
    async def sync_merge_result(self, task_id: str, merge_result: MergeResult):
        """同步合并结果到所有相关系统"""
        
        # 同步到TaskMaster-AI
        await self.taskmaster_sync.update_task_merged(task_id, merge_result)
        
        # 更新监控仪表板
        await self.update_dashboard(task_id, merge_result)
        
        # 触发后续任务（如果有依赖）
        dependent_tasks = await self.taskmaster_sync.get_dependent_tasks(task_id)
        for dep_task in dependent_tasks:
            await self.initiate_dependent_task(dep_task)
```

## 高级特性和优化

### 智能合并策略

```python
class IntelligentMergeStrategy:
    """智能合并策略"""
    
    def select_merge_strategy(self, conflict_analysis: ConflictAnalysis) -> MergeStrategy:
        """根据冲突分析选择最佳合并策略"""
        
        if conflict_analysis.requires_manual_intervention == 0:
            # 无冲突或所有冲突可自动解决
            return MergeStrategy.FAST_FORWARD_AUTO
        
        if conflict_analysis.auto_resolvable_percentage > 0.8:
            # 大部分冲突可自动解决
            return MergeStrategy.SEMI_AUTO_WITH_REVIEW
        
        if conflict_analysis.critical_files_affected:
            # 关键文件受影响，需要仔细处理
            return MergeStrategy.MANUAL_REVIEW_REQUIRED
        
        return MergeStrategy.STAGED_MERGE
```

### 性能优化和批量处理

```python
class BatchMergeProcessor:
    """批量合并处理器"""
    
    async def process_multiple_ready_tasks(self) -> BatchMergeResult:
        """处理多个准备好的任务"""
        
        ready_tasks = await self.get_ready_for_merge_tasks()
        
        # 按依赖关系排序
        ordered_tasks = self.sort_by_dependencies(ready_tasks)
        
        # 并行处理无依赖的任务
        independent_groups = self.group_independent_tasks(ordered_tasks)
        
        results = []
        for group in independent_groups:
            # 每组内并行处理
            group_results = await asyncio.gather(*[
                self.merge_manager.execute_full_merge(task.task_id)
                for task in group
            ])
            results.extend(group_results)
        
        return BatchMergeResult(
            processed_count=len(ready_tasks),
            successful_merges=[r for r in results if r.success],
            failed_merges=[r for r in results if not r.success]
        )
```

### 安全回滚和恢复机制

```python
class SafetyAndRecovery:
    """安全和恢复机制"""
    
    async def create_system_checkpoint(self) -> SystemCheckpoint:
        """创建系统检查点"""
        
        return SystemCheckpoint(
            timestamp=datetime.now(),
            main_branch_commit=await self.get_main_branch_head(),
            active_worktrees=await self.list_active_worktrees(),
            session_states=await self.capture_all_session_states(),
            taskmaster_state=await self.capture_taskmaster_state()
        )
    
    async def rollback_to_checkpoint(self, checkpoint: SystemCheckpoint):
        """回滚到指定检查点"""
        
        # 1. 停止所有活动会话
        await self.pause_all_sessions()
        
        # 2. 重置主分支
        await self.reset_main_branch(checkpoint.main_branch_commit)
        
        # 3. 恢复worktree状态
        await self.restore_worktrees(checkpoint.active_worktrees)
        
        # 4. 恢复会话状态
        await self.restore_session_states(checkpoint.session_states)
        
        # 5. 同步TaskMaster-AI状态
        await self.restore_taskmaster_state(checkpoint.taskmaster_state)
        
        # 6. 重新启动会话
        await self.resume_all_sessions()
    
    async def automated_health_check(self) -> HealthCheckResult:
        """自动健康检查"""
        
        checks = []
        
        # 检查Git仓库完整性
        checks.append(await self.check_git_integrity())
        
        # 检查worktree一致性
        checks.append(await self.check_worktree_consistency())
        
        # 检查会话状态一致性
        checks.append(await self.check_session_consistency())
        
        # 检查TaskMaster-AI同步状态
        checks.append(await self.check_taskmaster_sync())
        
        return HealthCheckResult(
            overall_health=all(check.passed for check in checks),
            individual_checks=checks,
            recommendations=self.generate_health_recommendations(checks)
        )
```

## 集成测试和验证

```python
class IntegrationValidator:
    """集成验证器"""
    
    async def validate_full_workflow(self) -> ValidationResult:
        """验证完整的工作流程"""
        
        # 1. 创建测试任务
        test_task = await self.create_test_task()
        
        # 2. 验证任务分解
        decomposition = await self.validate_task_decomposition(test_task)
        
        # 3. 验证worktree创建
        worktree_creation = await self.validate_worktree_creation(test_task)
        
        # 4. 验证会话监控
        session_monitoring = await self.validate_session_monitoring(test_task)
        
        # 5. 验证自动合并
        auto_merge = await self.validate_auto_merge(test_task)
        
        # 6. 清理测试数据
        await self.cleanup_test_data(test_task)
        
        return ValidationResult(
            workflow_steps=[
                decomposition, worktree_creation, 
                session_monitoring, auto_merge
            ],
            overall_success=all(step.passed for step in [
                decomposition, worktree_creation, 
                session_monitoring, auto_merge
            ])
        )
```

这个设计提供了一个完整、安全、智能的 worktree 自动合并系统，解决了您提出的所有关键需求，并融合了两个参考项目的最佳实践。