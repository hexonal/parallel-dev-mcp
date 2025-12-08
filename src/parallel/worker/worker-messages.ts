/**
 * Worker 消息类型定义
 * @module parallel/worker/worker-messages
 *
 * 定义 HybridExecutor Worker 脚本与 Master 之间的消息协议
 * 消息通过 stdout 输出 JSON 格式，每条消息独占一行
 */

/**
 * 消息类型枚举
 */
export type WorkerMessageType =
  | 'init'
  | 'sdk_message'
  | 'progress'
  | 'task_completed'
  | 'task_failed';

/**
 * 消息基础接口
 */
export interface WorkerMessageBase {
  /** 消息类型 */
  type: WorkerMessageType;
  /** 任务 ID */
  taskId: string;
  /** 时间戳 */
  timestamp: number;
}

/**
 * 初始化消息
 * 脚本启动时发送
 */
export interface InitMessage extends WorkerMessageBase {
  type: 'init';
  /** Worktree 路径 */
  worktreePath: string;
  /** Claude 模型 */
  model?: string;
}

/**
 * SDK 流式消息
 * 包装 Agent SDK 的流式输出
 */
export interface SdkMessage extends WorkerMessageBase {
  type: 'sdk_message';
  /** SDK 消息子类型 */
  sdkType: 'system' | 'assistant' | 'result' | 'user';
  /** 消息内容 */
  content?: string;
  /** 工具名称（如果是工具调用） */
  toolName?: string;
  /** 工具输入参数 */
  toolInput?: unknown;
}

/**
 * 进度消息
 * 报告任务执行进度
 */
export interface ProgressMessage extends WorkerMessageBase {
  type: 'progress';
  /** 执行阶段 */
  phase: 'analyzing' | 'coding' | 'testing' | 'reviewing';
  /** 进度详情 */
  detail: string;
}

/**
 * Token 使用统计
 */
export interface TokenUsage {
  /** 输入 token 数 */
  inputTokens: number;
  /** 输出 token 数 */
  outputTokens: number;
  /** 总费用（美元） */
  totalCost: number;
}

/**
 * 任务完成消息
 */
export interface TaskCompletedMessage extends WorkerMessageBase {
  type: 'task_completed';
  /** 任务输出 */
  output: string;
  /** Token 使用统计 */
  usage: TokenUsage;
}

/**
 * 任务失败消息
 */
export interface TaskFailedMessage extends WorkerMessageBase {
  type: 'task_failed';
  /** 错误信息 */
  error: string;
  /** 错误代码 */
  errorCode?: string;
  /** 错误堆栈 */
  stack?: string;
}

/**
 * Worker 消息联合类型
 */
export type WorkerMessage =
  | InitMessage
  | SdkMessage
  | ProgressMessage
  | TaskCompletedMessage
  | TaskFailedMessage;

/**
 * 解析 Worker 消息
 * @param line 输出行
 * @returns 解析后的消息或 null
 */
export function parseWorkerMessage(line: string): WorkerMessage | null {
  try {
    const trimmed = line.trim();

    // 跳过空行
    if (!trimmed) {
      return null;
    }

    // 检查是否是 JSON 格式
    if (!trimmed.startsWith('{') || !trimmed.endsWith('}')) {
      return null;
    }

    const parsed = JSON.parse(trimmed);

    // 验证基本字段
    if (!parsed.type || !parsed.taskId || !parsed.timestamp) {
      return null;
    }

    // 验证消息类型
    const validTypes: WorkerMessageType[] = [
      'init',
      'sdk_message',
      'progress',
      'task_completed',
      'task_failed'
    ];

    if (!validTypes.includes(parsed.type)) {
      return null;
    }

    return parsed as WorkerMessage;
  } catch {
    return null;
  }
}

/**
 * 序列化 Worker 消息
 * @param message 消息对象
 * @returns JSON 字符串
 */
export function serializeMessage(message: WorkerMessage): string {
  return JSON.stringify(message);
}

/**
 * 创建初始化消息
 */
export function createInitMessage(
  taskId: string,
  worktreePath: string,
  model?: string
): InitMessage {
  return {
    type: 'init',
    taskId,
    timestamp: Date.now(),
    worktreePath,
    model
  };
}

/**
 * 创建 SDK 消息
 */
export function createSdkMessage(
  taskId: string,
  sdkType: SdkMessage['sdkType'],
  content?: string,
  toolName?: string
): SdkMessage {
  return {
    type: 'sdk_message',
    taskId,
    timestamp: Date.now(),
    sdkType,
    content,
    toolName
  };
}

/**
 * 创建进度消息
 */
export function createProgressMessage(
  taskId: string,
  phase: ProgressMessage['phase'],
  detail: string
): ProgressMessage {
  return {
    type: 'progress',
    taskId,
    timestamp: Date.now(),
    phase,
    detail
  };
}

/**
 * 创建任务完成消息
 */
export function createTaskCompletedMessage(
  taskId: string,
  output: string,
  usage: TokenUsage
): TaskCompletedMessage {
  return {
    type: 'task_completed',
    taskId,
    timestamp: Date.now(),
    output,
    usage
  };
}

/**
 * 创建任务失败消息
 */
export function createTaskFailedMessage(
  taskId: string,
  error: string,
  errorCode?: string,
  stack?: string
): TaskFailedMessage {
  return {
    type: 'task_failed',
    taskId,
    timestamp: Date.now(),
    error,
    errorCode,
    stack
  };
}

/**
 * 检查是否是完成消息
 */
export function isCompletedMessage(
  message: WorkerMessage
): message is TaskCompletedMessage {
  return message.type === 'task_completed';
}

/**
 * 检查是否是失败消息
 */
export function isFailedMessage(
  message: WorkerMessage
): message is TaskFailedMessage {
  return message.type === 'task_failed';
}

/**
 * 检查是否是终结消息（完成或失败）
 */
export function isTerminalMessage(message: WorkerMessage): boolean {
  return isCompletedMessage(message) || isFailedMessage(message);
}
