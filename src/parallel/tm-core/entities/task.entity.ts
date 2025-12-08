/**
 * Task Entity
 * 爆改自 claude-task-master/packages/tm-core/src/modules/tasks/entities/task.entity.ts
 */

import {
  ERROR_CODES,
  TaskMasterError
} from '../common/errors/task-master-error';
import type {
  Subtask,
  Task,
  TaskPriority,
  TaskStatus
} from '../common/types';

/**
 * 任务实体类，包含业务逻辑
 */
export class TaskEntity implements Task {
  readonly id: string;
  title: string;
  description: string;
  status: TaskStatus;
  priority: TaskPriority;
  dependencies: string[];
  details: string;
  testStrategy: string;
  subtasks: Subtask[];

  createdAt?: string;
  updatedAt?: string;
  effort?: number;
  actualEffort?: number;
  tags?: string[];
  assignee?: string;
  complexity?: Task['complexity'];
  recommendedSubtasks?: number;
  expansionPrompt?: string;
  complexityReasoning?: string;

  constructor(data: Task | (Omit<Task, 'id'> & { id: number | string })) {
    this.validate(data);

    this.id = String(data.id);
    this.title = data.title;
    this.description = data.description;
    this.status = data.status;
    this.priority = data.priority;
    this.dependencies = (data.dependencies || []).map((dep) => String(dep));
    this.details = data.details;
    this.testStrategy = data.testStrategy;
    this.subtasks = (data.subtasks || []).map((subtask) => ({
      ...subtask,
      id: String(subtask.id),
      parentId: String(subtask.parentId)
    }));

    this.createdAt = data.createdAt;
    this.updatedAt = data.updatedAt;
    this.effort = data.effort;
    this.actualEffort = data.actualEffort;
    this.tags = data.tags;
    this.assignee = data.assignee;
    this.complexity = data.complexity;
    this.recommendedSubtasks = data.recommendedSubtasks;
    this.expansionPrompt = data.expansionPrompt;
    this.complexityReasoning = data.complexityReasoning;
  }

  /**
   * 验证任务数据
   */
  private validate(
    data: Partial<Task> | Partial<Omit<Task, 'id'> & { id: number | string }>
  ): void {
    if (
      data.id === undefined ||
      data.id === null ||
      (typeof data.id !== 'string' && typeof data.id !== 'number')
    ) {
      throw new TaskMasterError(
        'Task ID is required and must be a string or number',
        ERROR_CODES.VALIDATION_ERROR
      );
    }

    if (!data.title || data.title.trim().length === 0) {
      throw new TaskMasterError(
        'Task title is required',
        ERROR_CODES.VALIDATION_ERROR
      );
    }

    if (!data.description || data.description.trim().length === 0) {
      throw new TaskMasterError(
        'Task description is required',
        ERROR_CODES.VALIDATION_ERROR
      );
    }

    if (!this.isValidStatus(data.status)) {
      throw new TaskMasterError(
        `Invalid task status: ${data.status}`,
        ERROR_CODES.VALIDATION_ERROR
      );
    }

    if (!this.isValidPriority(data.priority)) {
      throw new TaskMasterError(
        `Invalid task priority: ${data.priority}`,
        ERROR_CODES.VALIDATION_ERROR
      );
    }
  }

  private isValidStatus(status: unknown): status is TaskStatus {
    return [
      'pending',
      'in-progress',
      'done',
      'deferred',
      'cancelled',
      'blocked',
      'review',
      'completed'
    ].includes(status as string);
  }

  private isValidPriority(priority: unknown): priority is TaskPriority {
    return ['low', 'medium', 'high', 'critical'].includes(priority as string);
  }

  canComplete(): boolean {
    if (this.status === 'done' || this.status === 'cancelled') {
      return false;
    }

    if (this.status === 'blocked') {
      return false;
    }

    const allSubtasksComplete = this.subtasks.every(
      (subtask) => subtask.status === 'done' || subtask.status === 'cancelled'
    );

    return allSubtasksComplete;
  }

  markAsComplete(): void {
    if (!this.canComplete()) {
      throw new TaskMasterError(
        'Task cannot be marked as complete',
        ERROR_CODES.TASK_STATUS_ERROR,
        {
          taskId: this.id,
          currentStatus: this.status,
          hasIncompleteSubtasks: this.subtasks.some(
            (s) => s.status !== 'done' && s.status !== 'cancelled'
          )
        }
      );
    }

    this.status = 'done';
    this.updatedAt = new Date().toISOString();
  }

  hasDependencies(): boolean {
    return this.dependencies.length > 0;
  }

  hasSubtasks(): boolean {
    return this.subtasks.length > 0;
  }

  addSubtask(subtask: Omit<Subtask, 'id' | 'parentId'>): void {
    const nextId = this.subtasks.length + 1;
    this.subtasks.push({
      ...subtask,
      id: nextId,
      parentId: this.id
    });
    this.updatedAt = new Date().toISOString();
  }

  updateStatus(newStatus: TaskStatus): void {
    if (!this.isValidStatus(newStatus)) {
      throw new TaskMasterError(
        `Invalid status: ${newStatus}`,
        ERROR_CODES.VALIDATION_ERROR
      );
    }

    if (this.status === 'done' && newStatus === 'pending') {
      throw new TaskMasterError(
        'Cannot move completed task back to pending',
        ERROR_CODES.TASK_STATUS_ERROR
      );
    }

    this.status = newStatus;
    this.updatedAt = new Date().toISOString();
  }

  toJSON(): Task {
    return {
      id: this.id,
      title: this.title,
      description: this.description,
      status: this.status,
      priority: this.priority,
      dependencies: this.dependencies,
      details: this.details,
      testStrategy: this.testStrategy,
      subtasks: this.subtasks,
      createdAt: this.createdAt,
      updatedAt: this.updatedAt,
      effort: this.effort,
      actualEffort: this.actualEffort,
      tags: this.tags,
      assignee: this.assignee,
      complexity: this.complexity,
      recommendedSubtasks: this.recommendedSubtasks,
      expansionPrompt: this.expansionPrompt,
      complexityReasoning: this.complexityReasoning
    };
  }

  static fromObject(data: Task): TaskEntity {
    return new TaskEntity(data);
  }

  static fromArray(data: Task[]): TaskEntity[] {
    return data.map((task) => new TaskEntity(task));
  }
}
