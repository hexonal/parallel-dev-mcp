/**
 * Task Execution Service
 * 爆改自 claude-task-master/packages/tm-core/src/modules/tasks/services/task-execution-service.ts
 */

import type { Task } from '../common/types';
import type { TaskService } from './task.service';

export interface StartTaskOptions {
  subtaskId?: string;
  dryRun?: boolean;
  updateStatus?: boolean;
  force?: boolean;
  silent?: boolean;
}

export interface StartTaskResult {
  task: Task | null;
  found: boolean;
  started: boolean;
  subtaskId?: string;
  subtask?: unknown;
  error?: string;
  executionOutput?: string;
  command?: {
    executable: string;
    args: string[];
    cwd: string;
  };
}

export interface ConflictCheckResult {
  canProceed: boolean;
  conflictingTasks: Task[];
  reason?: string;
}

/**
 * TaskExecutionService 处理启动和执行任务的业务逻辑
 */
export class TaskExecutionService {
  constructor(private taskService: TaskService) {}

  /**
   * 启动任务
   */
  async startTask(
    taskId: string,
    options: StartTaskOptions = {}
  ): Promise<StartTaskResult> {
    try {
      const { parentId, subtaskId } = this.parseTaskId(taskId);

      if (!options.force) {
        const conflictCheck = await this.checkInProgressConflicts(taskId);
        if (!conflictCheck.canProceed) {
          return {
            task: null,
            found: false,
            started: false,
            error: `Conflicting tasks in progress: ${conflictCheck.conflictingTasks.map((t) => `#${t.id}: ${t.title}`).join(', ')}`
          };
        }
      }

      const task = await this.taskService.getTask(parentId);
      if (!task) {
        return {
          task: null,
          found: false,
          started: false,
          error: `Task ${parentId} not found`
        };
      }

      let subtask = undefined;
      if (subtaskId && task.subtasks) {
        subtask = task.subtasks.find((st) => String(st.id) === subtaskId);
      }

      if (options.updateStatus && !options.dryRun) {
        try {
          await this.taskService.updateTaskStatus(parentId, 'in-progress');
        } catch (error) {
          console.warn(
            `Could not update task status: ${error instanceof Error ? error.message : String(error)}`
          );
        }
      }

      let started = false;
      let executionOutput = 'Task ready to execute';
      let command = undefined;

      if (!options.dryRun) {
        command = await this.prepareExecutionCommand(task, subtask);
        started = !!command;
        executionOutput = command
          ? `Command prepared: ${command.executable} ${command.args.join(' ')}`
          : 'Failed to prepare execution command';
      } else {
        started = true;
        executionOutput = 'Dry run - task would be executed';
        command = await this.prepareExecutionCommand(task, subtask);
      }

      return {
        task,
        found: true,
        started,
        subtaskId,
        subtask,
        executionOutput,
        command: command || undefined
      };
    } catch (error) {
      return {
        task: null,
        found: false,
        started: false,
        error: error instanceof Error ? error.message : String(error)
      };
    }
  }

  /**
   * 检查进行中任务冲突
   */
  async checkInProgressConflicts(
    targetTaskId: string
  ): Promise<ConflictCheckResult> {
    const allTasks = await this.taskService.getTaskList();
    const inProgressTasks = allTasks.tasks.filter(
      (task) => task.status === 'in-progress'
    );

    const targetTaskInProgress = inProgressTasks.find(
      (task) => task.id === targetTaskId
    );
    if (targetTaskInProgress) {
      return { canProceed: true, conflictingTasks: [] };
    }

    const isSubtask = targetTaskId.includes('.');
    if (isSubtask) {
      const parentTaskId = targetTaskId.split('.')[0];
      const parentInProgress = inProgressTasks.find(
        (task) => task.id === parentTaskId
      );
      if (parentInProgress) {
        return { canProceed: true, conflictingTasks: [] };
      }
    }

    const conflictingTasks = inProgressTasks.filter((task) => {
      if (task.id === targetTaskId) return false;

      if (isSubtask) {
        const parentTaskId = targetTaskId.split('.')[0];
        if (task.id === parentTaskId) return false;
      }

      if (task.id.toString().includes('.')) {
        const taskParentId = task.id.toString().split('.')[0];
        if (isSubtask && taskParentId === targetTaskId.split('.')[0]) {
          return false;
        }
      }

      return true;
    });

    if (conflictingTasks.length > 0) {
      return {
        canProceed: false,
        conflictingTasks,
        reason: 'Other tasks are already in progress'
      };
    }

    return { canProceed: true, conflictingTasks: [] };
  }

  /**
   * 获取下一个可用任务
   */
  async getNextAvailableTask(): Promise<string | null> {
    const nextTask = await this.taskService.getNextTask();
    return nextTask?.id || null;
  }

  /**
   * 解析任务 ID
   */
  private parseTaskId(taskId: string): {
    parentId: string;
    subtaskId?: string;
  } {
    if (taskId.includes('.')) {
      const [parentId, subtaskId] = taskId.split('.');
      return { parentId, subtaskId };
    }
    return { parentId: taskId };
  }

  /**
   * 检查任务是否可以启动
   */
  async canStartTask(taskId: string, force = false): Promise<boolean> {
    if (force) return true;

    const conflictCheck = await this.checkInProgressConflicts(taskId);
    return conflictCheck.canProceed;
  }

  /**
   * 准备执行命令
   */
  private async prepareExecutionCommand(
    task: Task,
    subtask?: unknown
  ): Promise<{ executable: string; args: string[]; cwd: string } | null> {
    try {
      const taskPrompt = this.formatTaskPrompt(task, subtask);
      const executable = 'claude';
      const args = [taskPrompt];
      const cwd = process.cwd();

      return { executable, args, cwd };
    } catch (error) {
      console.warn(
        `Failed to prepare execution command: ${error instanceof Error ? error.message : String(error)}`
      );
      return null;
    }
  }

  /**
   * 格式化任务提示
   */
  private formatTaskPrompt(task: Task, subtask?: unknown): string {
    const workItem = (subtask as Task) || task;
    const itemType = subtask ? 'Subtask' : 'Task';
    const itemId = subtask
      ? `${task.id}.${(subtask as { id: string | number }).id}`
      : task.id;

    let prompt = `${itemType} #${itemId}: ${workItem.title}\n\n`;

    if (workItem.description) {
      prompt += `Description:\n${workItem.description}\n\n`;
    }

    if (workItem.details) {
      prompt += `Implementation Details:\n${workItem.details}\n\n`;
    }

    if (workItem.testStrategy) {
      prompt += `Test Strategy:\n${workItem.testStrategy}\n\n`;
    }

    if (task.dependencies && task.dependencies.length > 0) {
      prompt += `Dependencies: ${task.dependencies.join(', ')}\n\n`;
    }

    prompt += `Please help me implement this ${itemType.toLowerCase()}.`;

    return prompt;
  }

  /**
   * 获取任务及其子任务
   */
  async getTaskWithSubtask(
    taskId: string
  ): Promise<{ task: Task | null; subtask?: unknown; subtaskId?: string }> {
    const { parentId, subtaskId } = this.parseTaskId(taskId);

    const task = await this.taskService.getTask(parentId);
    if (!task) {
      return { task: null };
    }

    if (subtaskId && task.subtasks) {
      const subtask = task.subtasks.find((st) => String(st.id) === subtaskId);
      return { task, subtask, subtaskId };
    }

    return { task };
  }
}
