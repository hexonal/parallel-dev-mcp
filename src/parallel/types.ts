/**
 * ParallelDev 核心类型定义
 * @module parallel/types
 */

import { z } from 'zod';

// ============================================
// 任务相关类型
// ============================================

/** 任务状态 */
export type TaskStatus =
  | 'pending'     // 等待执行
  | 'ready'       // 依赖已满足，可执行
  | 'running'     // 正在执行
  | 'completed'   // 已完成
  | 'failed'      // 已失败
  | 'cancelled';  // 已取消

/** 任务定义 */
export interface Task {
  /** 任务唯一标识 */
  id: string;
  /** 任务标题 */
  title: string;
  /** 任务详细描述 */
  description: string;
  /** 依赖的任务 ID 列表 */
  dependencies: string[];
  /** 优先级 (1-5, 1最高) */
  priority: number;
  /** 当前状态 */
  status: TaskStatus;
  /** 分配的 Worker ID */
  assignedWorker?: string;
  /** 创建时间 (ISO 8601) */
  createdAt: string;
  /** 开始执行时间 */
  startedAt?: string;
  /** 完成时间 */
  completedAt?: string;
  /** 错误信息 */
  error?: string;
  /** 预估工时（小时） */
  estimatedHours?: number;
  /** 任务标签 */
  tags?: string[];
}

/** 任务 Zod Schema（运行时验证） */
export const TaskSchema = z.object({
  id: z.string().min(1),
  title: z.string().min(1),
  description: z.string(),
  status: z.enum([
    'pending',
    'ready',
    'running',
    'completed',
    'failed',
    'cancelled'
  ]),
  dependencies: z.array(z.string()),
  priority: z.number().min(1).max(5).default(3),
  assignedWorker: z.string().optional(),
  createdAt: z.string().datetime().optional(),
  startedAt: z.string().datetime().optional(),
  completedAt: z.string().datetime().optional(),
  error: z.string().optional(),
  estimatedHours: z.number().positive().optional()
});

/** tasks.json 文件 Schema */
export const TasksFileSchema = z.object({
  tasks: z.array(TaskSchema),
  meta: z.object({
    generatedAt: z.string().datetime(),
    projectName: z.string().optional(),
    version: z.string().optional()
  }).optional()
});

// ============================================
// Worker 相关类型
// ============================================

/** Worker 状态 */
export type WorkerStatus =
  | 'idle'      // 空闲
  | 'busy'      // 忙碌
  | 'error'     // 错误
  | 'offline';  // 离线

/** Worker 定义 */
export interface Worker {
  /** Worker 唯一标识 */
  id: string;
  /** 当前状态 */
  status: WorkerStatus;
  /** Git Worktree 路径 */
  worktreePath: string;
  /** Tmux 会话名称 */
  tmuxSession: string;
  /** 当前执行的任务 ID */
  currentTaskId?: string;
  /** 最后心跳时间 (ISO 8601) */
  lastHeartbeat: string;
  /** 已完成任务数 */
  completedTasks: number;
  /** 失败任务数 */
  failedTasks: number;
}

// ============================================
// 调度相关类型
// ============================================

/** 调度策略 */
export type SchedulingStrategy =
  | 'priority_first'    // 高优先级优先
  | 'dependency_first'; // 解除更多依赖的任务优先

/** 任务分配结果 */
export interface TaskAssignment {
  task: Task;
  worker: Worker;
  assignedAt: string;
}

/** 调度器统计 */
export interface SchedulerStats {
  totalTasks: number;
  pendingTasks: number;
  runningTasks: number;
  completedTasks: number;
  failedTasks: number;
  activeWorkers: number;
  idleWorkers: number;
}

// ============================================
// 通信相关类型（Socket.IO 事件）
// ============================================

/** Worker → Master 事件类型 */
export type WorkerEventType =
  | 'task_started'
  | 'task_completed'
  | 'task_failed'
  | 'heartbeat'
  | 'progress';

/** Worker 事件 */
export interface WorkerEvent {
  type: WorkerEventType;
  workerId: string;
  taskId?: string;
  timestamp: string;
  payload?: {
    output?: string;
    error?: string;
    progress?: number;
    message?: string;
  };
}

/** Master → Worker 命令类型 */
export type MasterCommandType =
  | 'task_assign'
  | 'task_cancel'
  | 'worker_terminate';

/** Master 命令 */
export interface MasterCommand {
  type: MasterCommandType;
  taskId?: string;
  task?: Task;
  timestamp: string;
}

// ============================================
// 质量保证相关类型
// ============================================

/** 冲突级别 */
export type ConflictLevel = 1 | 2 | 3;
// Level 1: 自动解决（lockfiles, 格式化）
// Level 2: AI 辅助解决
// Level 3: 需要人工介入

/** 冲突信息 */
export interface ConflictInfo {
  file: string;
  level: ConflictLevel;
  conflictMarkers: string[];
  suggestedResolution?: string;
}

/** 解决结果 */
export interface ResolveResult {
  resolved: boolean;
  level?: ConflictLevel;
  conflicts?: string[];
  message?: string;
}

/** 任务执行结果 */
export interface TaskResult {
  success: boolean;
  output?: string;
  error?: string;
  duration?: number;
  filesChanged?: string[];
  /** 执行元数据 */
  metadata?: {
    /** Token 使用情况 */
    usage?: {
      inputTokens: number;
      outputTokens: number;
      totalCost: number;
    };
    /** 使用的模型 */
    model?: string;
    /** 执行器类型 */
    executor?: ExecutorType;
    /** Claude Code 会话 ID */
    sessionId?: string | null;
    /** 执行模式 */
    mode?: string;
    /** Tmux 会话名称 */
    sessionName?: string | null;
  };
}

/** 执行器类型 */
export type ExecutorType = 'agent-sdk' | 'tmux-cli' | 'hybrid' | 'hybrid-sdk' | 'hybrid-tmux';

// ============================================
// 配置相关类型
// ============================================

/** 配置接口 */
export interface ParallelDevConfig {
  /** 最大 Worker 数量 */
  maxWorkers: number;
  /** Worktree 目录 */
  worktreeDir: string;
  /** 主分支名称 */
  mainBranch: string;
  /** Socket 服务端口 */
  socketPort: number;
  /** 心跳间隔（毫秒） */
  heartbeatInterval: number;
  /** 任务超时时间（毫秒） */
  taskTimeout: number;
  /** 调度策略 */
  schedulingStrategy: SchedulingStrategy;
  /** Fire-and-forget 模式：启动任务后立即返回，不等待完成 */
  fireAndForget?: boolean;
}
