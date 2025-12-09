/**
 * MasterOrchestrator - 主编排控制器
 *
 * Layer 2: 编排层核心组件
 * 负责事件驱动的任务调度和 Worker 协调
 */

import { EventEmitter } from 'events';
import { simpleGit } from 'simple-git';
import {
  Task,
  Worker,
  WorkerEvent,
  ParallelDevConfig,
  SchedulerStats,
} from '../types';
import { TaskManager } from '../task/TaskManager';
import { WorkerPool } from './WorkerPool';
import { StateManager, SystemState } from './StateManager';
import { GitService } from '../git/GitService';
import { TmuxController } from '../tmux/TmuxController';
import { HybridExecutor } from '../worker/HybridExecutor';
import { SessionMonitor } from '../tmux/SessionMonitor';
import { MasterServer } from '../../repl/MasterServer';
import { ConflictResolver } from '../quality/ConflictResolver';
import { SubagentRunner } from '../quality/SubagentRunner';

/**
 * 编排器事件类型
 */
export type OrchestratorEventType =
  | 'started'
  | 'stopped'
  | 'task_assigned'
  | 'task_completed'
  | 'task_failed'
  | 'all_completed'
  | 'error';

/**
 * MasterOrchestrator 类
 *
 * 事件驱动的主控制器，协调任务调度和 Worker 管理
 */
export class MasterOrchestrator extends EventEmitter {
  private config: ParallelDevConfig;
  private projectRoot: string;
  private taskManager: TaskManager;
  private workerPool: WorkerPool;
  private stateManager: StateManager;
  private gitService: GitService;
  private tmuxController: TmuxController;
  private masterServer: MasterServer | null = null;
  private isRunning: boolean = false;
  private conflictResolver: ConflictResolver | null = null;

  // 冲突追踪
  private unresolvedConflicts: Array<{
    taskId: string;
    branchName: string;
    files: string[];
    reason: string;
    timestamp: string;
  }> = [];

  constructor(config: ParallelDevConfig, projectRoot: string) {
    super();
    this.config = config;
    this.projectRoot = projectRoot;

    // 初始化各组件
    this.taskManager = new TaskManager(projectRoot, config);
    this.workerPool = new WorkerPool(config.maxWorkers);
    this.stateManager = new StateManager(projectRoot);
    this.gitService = new GitService(projectRoot, config.worktreeDir);
    // 不传参数，让 TmuxController 自动检测当前 tmux 会话名作为前缀
    this.tmuxController = new TmuxController();

    // 初始化冲突解决器
    this.initConflictResolver();
  }

  /**
   * 初始化冲突解决器
   */
  private initConflictResolver(): void {
    const subagentRunner = new SubagentRunner({
      projectRoot: this.projectRoot,
    });

    this.conflictResolver = new ConflictResolver({
      projectRoot: this.projectRoot,
      subagentRunner,
    });

    // 监听冲突解决事件
    this.conflictResolver.on('resolved', ({ conflict, level }) => {
      console.log(`   ✅ 自动解决: ${conflict.file} (Level ${level})`);
    });

    this.conflictResolver.on('humanReview', ({ file, reason }) => {
      console.log(`   ⚠️ 需要人工介入: ${file}`);
      console.log(`      原因: ${reason}`);
    });

    this.conflictResolver.on('error', (error: string) => {
      console.log(`   ❌ 冲突解决错误: ${error}`);
    });
  }

  /**
   * 启动编排器（事件驱动主循环）
   * @returns 启动的会话信息（fireAndForget 模式下）
   */
  async start(): Promise<{ sessions: string[] } | void> {
    if (this.isRunning) {
      throw new Error('Orchestrator is already running');
    }

    this.isRunning = true;
    this.emit('started', { timestamp: new Date().toISOString() });

    try {
      // 1. 加载任务
      const tasks = await this.taskManager.loadTasks();

      // 2. 启动 MasterServer (Socket.IO 服务)
      this.masterServer = new MasterServer({ port: this.config.socketPort });
      await this.masterServer.start();
      this.setupMasterServerListeners();

      // 3. 初始化 Worker 池
      await this.workerPool.initialize(this.projectRoot, this.config);

      // 5. 更新状态
      this.stateManager.updateState({
        currentPhase: 'running',
        startedAt: new Date().toISOString(),
        tasks,
        workers: this.workerPool.getAllWorkers(),
      });

      // 6. 启动自动保存
      this.stateManager.startAutoSave(30000);

      // 7. 开始分配任务
      await this.tryAssignTasks();

      // 8. fireAndForget 模式：返回会话信息但保持 MasterServer 运行
      if (this.config.fireAndForget) {
        const sessions = this.tmuxController.listSessions();
        await this.stateManager.saveState(this.stateManager.getState());
        // 注意：不要停止 autoSave 和 MasterServer
        // 它们需要继续运行以接收 Worker 的状态回馈
        return { sessions };
      }
    } catch (error) {
      this.isRunning = false;
      this.emit('error', { error, timestamp: new Date().toISOString() });
      throw error;
    }
  }

  /**
   * 停止编排器
   */
  async stop(): Promise<void> {
    if (!this.isRunning) {
      return;
    }

    this.isRunning = false;

    // 停止自动保存
    this.stateManager.stopAutoSave();

    // 停止 MasterServer
    if (this.masterServer) {
      await this.masterServer.stop();
      this.masterServer = null;
    }

    // 清理 Worker 池
    await this.workerPool.cleanup();

    // 保存最终状态
    await this.stateManager.saveState(this.stateManager.getState());

    this.emit('stopped', { timestamp: new Date().toISOString() });
  }

  /**
   * 设置 MasterServer 事件监听器
   * 接收 Worker 通过 Socket.IO 发送的状态更新
   */
  private setupMasterServerListeners(): void {
    if (!this.masterServer) {
      return;
    }

    // Worker 任务完成
    this.masterServer.on('worker:task_completed', ({ workerId, taskId, result }) => {
      this.handleTaskCompleted({
        type: 'task_completed',
        workerId,
        taskId,
        timestamp: new Date().toISOString(),
        payload: { output: result },
      });
    });

    // Worker 任务失败
    this.masterServer.on('worker:task_failed', ({ workerId, taskId, error }) => {
      this.handleTaskFailed({
        type: 'task_failed',
        workerId,
        taskId,
        timestamp: new Date().toISOString(),
        payload: { error },
      });
    });

    // Worker 进度更新
    this.masterServer.on('worker:progress', (update) => {
      this.emit('task_progress', {
        taskId: update.taskId,
        workerId: update.workerId,
        percent: update.percent,
        message: update.message,
        timestamp: new Date().toISOString(),
      });
    });

    // Worker 连接
    this.masterServer.on('worker:connected', ({ workerId }) => {
      this.emit('worker_connected', {
        workerId,
        timestamp: new Date().toISOString(),
      });
    });

    // Worker 断开
    this.masterServer.on('worker:disconnected', ({ workerId }) => {
      this.emit('worker_disconnected', {
        workerId,
        timestamp: new Date().toISOString(),
      });
    });

    // Worker 请求合并
    this.masterServer.on('worker:merge_request', async ({ workerId, taskId, branchName }) => {
      this.emit('merge_request', {
        workerId,
        taskId,
        branchName,
        timestamp: new Date().toISOString(),
      });

      // 执行合并
      await this.handleMergeRequest(workerId, taskId, branchName);
    });
  }

  /**
   * 处理合并请求
   * 在主 worktree 中执行 git merge，并显示 commit 信息
   */
  private async handleMergeRequest(workerId: string, taskId: string, branchName: string): Promise<void> {
    const mainBranch = this.config.mainBranch || 'main';
    const task = this.taskManager.getTask(taskId);
    const taskTitle = task?.title || taskId;
    const git = simpleGit(this.projectRoot);

    try {

      // 1. 确保在主分支
      const currentBranch = await git.branch();
      if (currentBranch.current !== mainBranch) {
        await git.checkout(mainBranch);
      }

      // 2. 拉取最新代码（保持同步）
      try {
        await git.pull('origin', mainBranch);
      } catch {
        // 忽略 pull 错误（如没有远程连接）
      }

      // 3. 获取 Worker 分支的 commit 信息（合并前）
      const branchLog = await git.log({ from: mainBranch, to: branchName, maxCount: 5 });
      const commits = branchLog.all;

      // 4. 合并本地任务分支
      const mergeMessage = `Merge branch '${branchName}': ${taskTitle}`;
      await git.merge([branchName, '-m', mergeMessage]);

      // 5. 显示合并成功和 commit 信息
      console.log(`\n${'─'.repeat(60)}`);
      console.log(`✅ [Master] 合并成功: ${taskTitle}`);
      console.log(`   分支: ${branchName} → ${mainBranch}`);

      if (commits.length > 0) {
        console.log(`\n📝 Git Commits:`);
        for (const commit of commits) {
          // 显示 commit hash (短)、message、修改的文件数
          const shortHash = commit.hash.substring(0, 7);
          const message = commit.message.split('\n')[0]; // 只取第一行
          console.log(`   ${shortHash} ${message}`);
        }

        // 获取修改的文件列表
        const diffSummary = await git.diffSummary([`${mainBranch}~${commits.length}`, mainBranch]);
        if (diffSummary.files.length > 0) {
          console.log(`\n📁 修改的文件 (${diffSummary.files.length}):`);
          for (const file of diffSummary.files.slice(0, 10)) {
            // 类型安全处理：binary 文件没有 insertions/deletions
            const insertions = 'insertions' in file ? file.insertions : 0;
            const deletions = 'deletions' in file ? file.deletions : 0;
            console.log(`   ${file.file} (+${insertions} -${deletions})`);
          }
          if (diffSummary.files.length > 10) {
            console.log(`   ... 还有 ${diffSummary.files.length - 10} 个文件`);
          }
        }
      }

      this.emit('merge_completed', {
        workerId,
        taskId,
        branchName,
        commits: commits.map(c => ({ hash: c.hash, message: c.message })),
        timestamp: new Date().toISOString(),
      });

      // 6. 推送合并后的主分支
      await git.push('origin', mainBranch);
      console.log(`\n📤 已推送到远程: origin/${mainBranch}`);

      this.emit('merge_pushed', {
        workerId,
        taskId,
        branchName,
        mainBranch,
        timestamp: new Date().toISOString(),
      });

      // 7. 删除本地任务分支（保持整洁）
      try {
        await git.deleteLocalBranch(branchName, true);
      } catch {
        // 删除分支失败不影响结果
      }

      // 8. 删除 worktree（合并成功后清理）
      try {
        await this.gitService.removeWorktree(taskId);
        console.log(`🗑️ 已删除 worktree: task/${taskId}`);
      } catch {
        // worktree 删除失败不影响结果（可能已被删除）
      }

      console.log(`${'─'.repeat(60)}\n`);

    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error);

      // 检测是否为冲突错误
      if (errorMsg.includes('CONFLICTS') || errorMsg.includes('conflict')) {
        console.log(`\n${'─'.repeat(60)}`);
        console.log(`⚠️ [Master] 检测到合并冲突: ${taskTitle}`);
        console.log(`   分支: ${branchName} → ${mainBranch}`);

        // 尝试自动解决冲突
        if (this.conflictResolver) {
          console.log(`\n🔧 尝试自动解决冲突...`);

          try {
            const resolveResult = await this.conflictResolver.resolve(this.projectRoot);

            if (resolveResult.success) {
              console.log(`\n✅ 冲突已自动解决`);
              console.log(`   ${resolveResult.summary}`);

              // 冲突解决后，完成合并提交
              await git.commit(`Merge branch '${branchName}': ${taskTitle} (conflicts resolved)`);

              // 继续推送和清理流程
              await git.push('origin', mainBranch);
              console.log(`\n📤 已推送到远程: origin/${mainBranch}`);

              try {
                await git.deleteLocalBranch(branchName, true);
              } catch {
                // 删除分支失败不影响结果
              }

              // 删除 worktree（冲突解决成功后清理）
              try {
                await this.gitService.removeWorktree(taskId);
                console.log(`🗑️ 已删除 worktree: task/${taskId}`);
              } catch {
                // worktree 删除失败不影响结果
              }

              this.emit('merge_completed', {
                workerId,
                taskId,
                branchName,
                conflictsResolved: true,
                timestamp: new Date().toISOString(),
              });

              console.log(`${'─'.repeat(60)}\n`);
              return;
            } else {
              // 冲突无法自动解决
              console.log(`\n❌ 部分冲突无法自动解决`);
              console.log(`   ${resolveResult.summary}`);

              const unresolvedFiles: string[] = [];
              if (resolveResult.needsHumanReview.length > 0) {
                console.log(`\n📋 需要人工处理的文件:`);
                for (const conflict of resolveResult.needsHumanReview) {
                  console.log(`   - ${conflict.file}: ${conflict.description}`);
                  unresolvedFiles.push(conflict.file);
                }
              }

              // 记录未解决的冲突
              this.unresolvedConflicts.push({
                taskId,
                branchName,
                files: unresolvedFiles,
                reason: resolveResult.summary,
                timestamp: new Date().toISOString(),
              });

              // 发出冲突未解决事件
              this.emit('conflict_unresolved', {
                taskId,
                branchName,
                files: unresolvedFiles,
                reason: resolveResult.summary,
                needsHumanReview: resolveResult.needsHumanReview,
                timestamp: new Date().toISOString(),
              });

              // 中止合并
              try {
                await git.merge(['--abort']);
              } catch {
                // 中止失败，可能没有进行中的合并
              }
            }
          } catch (resolveError) {
            console.log(`\n❌ 冲突解决过程出错: ${resolveError}`);
            // 尝试中止合并
            try {
              await git.merge(['--abort']);
            } catch {
              // 忽略中止错误
            }
          }
        }
      }

      // 原有的错误处理（冲突未解决或其他错误）
      console.log(`\n${'─'.repeat(60)}`);
      console.log(`❌ [Master] 合并失败: ${taskTitle}`);
      console.log(`   分支: ${branchName} → ${mainBranch}`);
      console.log(`   错误: ${errorMsg}`);
      console.log(`${'─'.repeat(60)}\n`);
      this.emit('merge_failed', {
        workerId,
        taskId,
        branchName,
        error: errorMsg,
        timestamp: new Date().toISOString(),
      });
    }
  }

  /**
   * 处理任务完成事件
   */
  async handleTaskCompleted(event: WorkerEvent): Promise<void> {
    const { workerId, taskId } = event;

    if (!taskId) {
      return;
    }

    // 1. 更新任务状态
    this.taskManager.markTaskCompleted(taskId);

    // 2. 更新 Worker 状态
    this.workerPool.setWorkerStatus(workerId, 'idle');
    this.workerPool.incrementCompletedTasks(workerId);

    // 3. 发出事件
    this.emit('task_completed', {
      taskId,
      workerId,
      timestamp: new Date().toISOString(),
    });

    // 4. 更新状态
    this.updateSystemState();

    // 5. 检查是否全部完成
    if (this.taskManager.isAllCompleted()) {
      await this.finalize();
      return;
    }

    // 6. 尝试分配新任务
    await this.tryAssignTasks();
  }

  /**
   * 处理任务失败事件
   */
  async handleTaskFailed(event: WorkerEvent): Promise<void> {
    const { workerId, taskId, payload } = event;

    if (!taskId) {
      return;
    }

    const task = this.taskManager.getTask(taskId);
    const taskTitle = task?.title || taskId;
    const errorMsg = payload?.error || 'Unknown error';

    // 显示任务失败信息
    console.log(`\n${'─'.repeat(60)}`);
    console.log(`❌ [Master] 任务失败: ${taskTitle}`);
    console.log(`   Worker: ${workerId} | 任务ID: ${taskId}`);
    console.log(`   错误: ${errorMsg}`);
    console.log(`${'─'.repeat(60)}\n`);

    // 1. 更新任务状态
    this.taskManager.markTaskFailed(taskId, errorMsg);

    // 2. 更新 Worker 状态
    this.workerPool.setWorkerStatus(workerId, 'idle');
    this.workerPool.incrementFailedTasks(workerId);

    // 3. 发出事件
    this.emit('task_failed', {
      taskId,
      workerId,
      error: payload?.error,
      timestamp: new Date().toISOString(),
    });

    // 4. 更新状态
    this.updateSystemState();

    // 5. 尝试分配新任务
    await this.tryAssignTasks();
  }

  /**
   * 分配任务给 Worker
   */
  private async assignTask(worker: Worker, task: Task): Promise<void> {
    try {
      // 1. 创建 Worktree
      const worktree = await this.gitService.createWorktree(
        task.id,
        this.config.mainBranch
      );

      // 2. 创建 Tmux 会话（使用 task.id 作为会话 ID，即 worktree 名）
      const tmuxSession = await this.tmuxController.createSession(
        task.id,
        worktree.path
      );

      // 3. 更新 Worker 信息
      worker.worktreePath = worktree.path;
      worker.tmuxSession = tmuxSession;
      worker.currentTaskId = task.id;

      // 4. 更新状态
      this.workerPool.setWorkerStatus(worker.id, 'busy');
      this.taskManager.markTaskStarted(task.id, worker.id);

      // 5. 创建任务执行器并启动
      // 注意：传入 task.id（不是 tmuxSession），因为 HybridExecutor 内部会调用 getSessionName()
      const monitor = new SessionMonitor(this.tmuxController);
      const executor = new HybridExecutor(
        this.tmuxController,
        monitor,
        task.id,
        {
          timeout: this.config.taskTimeout,
          permissionMode: 'acceptEdits',
          enableHooks: true,
          // WorkerRunner 模式配置
          masterPort: this.config.socketPort,
          useWorkerRunner: true,
          gitConfig: {
            autoCommit: true,
            autoPush: true,
            autoMerge: true,  // 启用自动创建 PR 并合并
          },
        }
      );

      // 6. 启动异步执行
      // fireAndForget 模式：只启动不等待，用户通过 pdev status 监控
      const fireAndForget = this.config.fireAndForget ?? true;
      this.executeTaskAsync(executor, task, worker, worktree.path, fireAndForget);

      // 7. 发出事件
      this.emit('task_assigned', {
        taskId: task.id,
        workerId: worker.id,
        timestamp: new Date().toISOString(),
      });
    } catch (error) {
      // 分配失败，恢复状态
      this.workerPool.setWorkerStatus(worker.id, 'idle');
      throw error;
    }
  }

  /**
   * 异步执行任务
   * @param fireAndForget 如果为 true，只启动不等待完成
   */
  private async executeTaskAsync(
    executor: HybridExecutor,
    task: Task,
    worker: Worker,
    worktreePath: string,
    fireAndForget: boolean = false
  ): Promise<void> {
    try {
      const result = await executor.execute(task, worktreePath, fireAndForget);

      // fireAndForget 模式：任务已启动但未完成，不触发完成/失败事件
      // 任务状态由用户通过 pdev status 监控，或后续轮询机制处理
      if (fireAndForget) {
        // 任务已启动，保持 running 状态
        return;
      }

      // 等待模式：根据执行结果处理任务状态
      if (result.success) {
        await this.handleTaskCompleted({
          type: 'task_completed',
          workerId: worker.id,
          taskId: task.id,
          timestamp: new Date().toISOString(),
          payload: { output: result.output },
        });
      } else {
        await this.handleTaskFailed({
          type: 'task_failed',
          workerId: worker.id,
          taskId: task.id,
          timestamp: new Date().toISOString(),
          payload: { error: result.error },
        });
      }
    } catch (error) {
      // fireAndForget 模式下的启动错误仍需处理
      if (!fireAndForget) {
        await this.handleTaskFailed({
          type: 'task_failed',
          workerId: worker.id,
          taskId: task.id,
          timestamp: new Date().toISOString(),
          payload: {
            error: error instanceof Error ? error.message : String(error),
          },
        });
      } else {
        // fireAndForget 模式下记录错误但不改变状态
        this.emit('error', {
          message: `任务 ${task.id} 启动失败`,
          error,
          timestamp: new Date().toISOString(),
        });
      }
    }
  }

  /**
   * 尝试分配待执行任务（核心调度逻辑）
   */
  private async tryAssignTasks(): Promise<void> {
    if (!this.isRunning) {
      return;
    }

    // 获取空闲 Worker
    let idleWorker = this.workerPool.getIdleWorker();

    while (idleWorker) {
      // 获取下一个可执行任务
      const scheduler = this.taskManager.getScheduler();
      const nextTask = scheduler.getNextTask();

      if (!nextTask) {
        // 没有可执行的任务了
        break;
      }

      try {
        await this.assignTask(idleWorker, nextTask);
      } catch (error) {
        this.emit('error', {
          message: `Failed to assign task ${nextTask.id}`,
          error,
          timestamp: new Date().toISOString(),
        });
      }

      // 获取下一个空闲 Worker
      idleWorker = this.workerPool.getIdleWorker();
    }
  }

  /**
   * 生成完成报告并通知
   */
  private async finalize(): Promise<void> {
    const stats = this.taskManager.getStats();

    // 显示最终完成信息
    const hasUnresolvedConflicts = this.unresolvedConflicts.length > 0;

    console.log('\n' + '═'.repeat(50));
    if (stats.failed > 0 || hasUnresolvedConflicts) {
      console.log('🔴 [Master] 并行开发完成（有失败任务或未解决冲突）');
    } else {
      console.log('🎉 [Master] 并行开发全部完成！');
    }
    console.log('═'.repeat(50));
    console.log(`📊 统计信息:`);
    console.log(`   总任务: ${stats.total}`);
    console.log(`   已完成: ${stats.completed} ✅`);
    console.log(`   已失败: ${stats.failed} ❌`);
    if (hasUnresolvedConflicts) {
      console.log(`   未解决冲突: ${this.unresolvedConflicts.length} ⚠️`);
    }
    console.log('═'.repeat(50));

    // 显示未解决冲突的详细信息
    if (hasUnresolvedConflicts) {
      console.log('\n📋 未解决的合并冲突:');
      for (const conflict of this.unresolvedConflicts) {
        console.log(`   分支: ${conflict.branchName}`);
        console.log(`   文件: ${conflict.files.join(', ')}`);
        console.log(`   原因: ${conflict.reason}`);
        console.log('');
      }
    }
    console.log('');

    // 更新状态
    this.stateManager.updateState({
      currentPhase: stats.failed > 0 ? 'failed' : 'completed',
      updatedAt: new Date().toISOString(),
    });

    // 保存最终状态
    await this.stateManager.saveState(this.stateManager.getState());

    // 发出完成事件
    this.emit('all_completed', {
      stats,
      unresolvedConflicts: this.unresolvedConflicts,
      timestamp: new Date().toISOString(),
    });

    // 停止编排器
    await this.stop();
  }

  /**
   * 更新系统状态
   */
  private updateSystemState(): void {
    const dag = this.taskManager.getDAG();

    this.stateManager.updateState({
      tasks: dag.getAllTasks(),
      workers: this.workerPool.getAllWorkers(),
      updatedAt: new Date().toISOString(),
    });
  }

  /**
   * 获取当前统计信息
   */
  getStats(): ReturnType<TaskManager['getStats']> {
    return this.taskManager.getStats();
  }

  /**
   * 获取系统状态
   */
  getSystemState(): SystemState {
    return this.stateManager.getState();
  }
}
