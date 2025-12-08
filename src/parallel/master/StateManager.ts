/**
 * StateManager - 状态管理器
 *
 * Layer 2: 编排层组件
 * 负责系统状态的持久化和恢复
 */

import * as fs from 'fs/promises';
import * as path from 'path';
import { EventEmitter } from 'events';
import { Worker, Task, SchedulerStats } from '../types';

/**
 * 系统状态接口
 */
export interface SystemState {
  workers: Worker[];
  tasks: Task[];
  currentPhase: 'idle' | 'running' | 'completed' | 'failed';
  startedAt: string | null;
  updatedAt: string | null;
  stats: SchedulerStats;
}

/**
 * StateManager 类
 *
 * 管理系统状态的保存、加载和自动持久化
 */
export class StateManager extends EventEmitter {
  private projectRoot: string;
  private stateFilePath: string;
  private state: SystemState;
  private autoSaveInterval: NodeJS.Timeout | null = null;

  constructor(projectRoot: string) {
    super();
    this.projectRoot = projectRoot;
    this.stateFilePath = path.join(projectRoot, '.paralleldev', 'state.json');
    this.state = this.createInitialState();
  }

  /**
   * 创建初始状态
   */
  private createInitialState(): SystemState {
    return {
      workers: [],
      tasks: [],
      currentPhase: 'idle',
      startedAt: null,
      updatedAt: null,
      stats: {
        totalTasks: 0,
        pendingTasks: 0,
        runningTasks: 0,
        completedTasks: 0,
        failedTasks: 0,
        activeWorkers: 0,
        idleWorkers: 0,
      },
    };
  }

  /**
   * 保存状态到文件
   */
  async saveState(state: SystemState): Promise<void> {
    try {
      // 确保目录存在
      const dir = path.dirname(this.stateFilePath);
      await fs.mkdir(dir, { recursive: true });

      // 写入状态文件
      const content = JSON.stringify(state, null, 2);
      await fs.writeFile(this.stateFilePath, content, 'utf-8');

      this.emit('saved', { path: this.stateFilePath });
    } catch (error) {
      this.emit('error', { message: 'Failed to save state', error });
      throw error;
    }
  }

  /**
   * 从文件加载状态
   */
  async loadState(): Promise<SystemState | null> {
    try {
      const content = await fs.readFile(this.stateFilePath, 'utf-8');
      const state = JSON.parse(content) as SystemState;

      this.state = state;
      this.emit('loaded', { path: this.stateFilePath });

      return state;
    } catch (error) {
      // 文件不存在或解析失败，返回 null
      return null;
    }
  }

  /**
   * 获取当前状态
   */
  getState(): SystemState {
    return { ...this.state };
  }

  /**
   * 更新状态
   */
  updateState(partial: Partial<SystemState>): void {
    this.state = {
      ...this.state,
      ...partial,
      updatedAt: new Date().toISOString(),
    };

    this.emit('updated', { state: this.state });
  }

  /**
   * 重置状态
   */
  resetState(): void {
    this.state = this.createInitialState();
    this.emit('reset');
  }

  /**
   * 启动自动保存
   */
  startAutoSave(intervalMs: number = 30000): void {
    if (this.autoSaveInterval) {
      this.stopAutoSave();
    }

    this.autoSaveInterval = setInterval(async () => {
      try {
        await this.saveState(this.state);
      } catch {
        // 自动保存失败时只发出事件，不抛出异常
        this.emit('auto_save_failed');
      }
    }, intervalMs);

    this.emit('auto_save_started', { intervalMs });
  }

  /**
   * 停止自动保存
   */
  stopAutoSave(): void {
    if (this.autoSaveInterval) {
      clearInterval(this.autoSaveInterval);
      this.autoSaveInterval = null;
      this.emit('auto_save_stopped');
    }
  }

  /**
   * 获取状态文件路径
   */
  getStateFilePath(): string {
    return this.stateFilePath;
  }

  /**
   * 检查状态文件是否存在
   */
  async stateFileExists(): Promise<boolean> {
    try {
      await fs.access(this.stateFilePath);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * 删除状态文件
   */
  async deleteStateFile(): Promise<void> {
    try {
      await fs.unlink(this.stateFilePath);
      this.emit('deleted', { path: this.stateFilePath });
    } catch {
      // 文件不存在时忽略
    }
  }
}
