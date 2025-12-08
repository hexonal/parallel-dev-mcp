/**
 * MasterOrchestrator - 主编排控制器
 *
 * Layer 2: 编排层核心组件
 * 负责事件驱动的任务调度和 Worker 协调
 */

import { EventEmitter } from 'events';
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
import { WorktreeManager } from '../git/WorktreeManager';
import { TmuxController } from '../tmux/TmuxController';
import { HybridExecutor } from '../worker/HybridExecutor';
import { SessionMonitor } from '../tmux/SessionMonitor';

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
  private worktreeManager: WorktreeManager;
  private tmuxController: TmuxController;
  private isRunning: boolean = false;

  constructor(config: ParallelDevConfig, projectRoot: string) {
    super();
    this.config = config;
    this.projectRoot = projectRoot;

    // 初始化各组件
    this.taskManager = new TaskManager(projectRoot, config);
    this.workerPool = new WorkerPool(config.maxWorkers);
    this.stateManager = new StateManager(projectRoot);
    this.worktreeManager = new WorktreeManager(projectRoot, config.worktreeDir);
    this.tmuxController = new TmuxController('parallel-dev');
  }

  /**
   * 启动编排器（事件驱动主循环）
   */
  async start(): Promise<void> {
    if (this.isRunning) {
      throw new Error('Orchestrator is already running');
    }

    this.isRunning = true;
    this.emit('started', { timestamp: new Date().toISOString() });

    try {
      // 1. 加载任务
      const tasks = await this.taskManager.loadTasks();

      // 2. 初始化 Worker 池
      await this.workerPool.initialize(this.projectRoot, this.config);

      // 3. 更新状态
      this.stateManager.updateState({
        currentPhase: 'running',
        startedAt: new Date().toISOString(),
        tasks,
        workers: this.workerPool.getAllWorkers(),
      });

      // 4. 启动自动保存
      this.stateManager.startAutoSave(30000);

      // 5. 开始分配任务
      await this.tryAssignTasks();
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

    // 清理 Worker 池
    await this.workerPool.cleanup();

    // 保存最终状态
    await this.stateManager.saveState(this.stateManager.getState());

    this.emit('stopped', { timestamp: new Date().toISOString() });
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

    // 1. 更新任务状态
    this.taskManager.markTaskFailed(taskId, payload?.error || 'Unknown error');

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
      const worktree = await this.worktreeManager.create(
        task.id,
        this.config.mainBranch
      );

      // 2. 创建 Tmux 会话
      const tmuxSession = await this.tmuxController.createSession(
        worker.id,
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
      const monitor = new SessionMonitor(this.tmuxController);
      const executor = new HybridExecutor(
        this.tmuxController,
        monitor,
        tmuxSession,
        {
          timeout: this.config.taskTimeout,
          permissionMode: 'acceptEdits',
          enableHooks: true
        }
      );

      // 6. 启动异步执行（不阻塞）
      this.executeTaskAsync(executor, task, worker, worktree.path);

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
   */
  private async executeTaskAsync(
    executor: HybridExecutor,
    task: Task,
    worker: Worker,
    worktreePath: string
  ): Promise<void> {
    try {
      const result = await executor.execute(task, worktreePath);

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
      await this.handleTaskFailed({
        type: 'task_failed',
        workerId: worker.id,
        taskId: task.id,
        timestamp: new Date().toISOString(),
        payload: {
          error: error instanceof Error ? error.message : String(error),
        },
      });
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
