/**
 * ParallelDev 通信层类型定义
 *
 * 爆改自 Happy 通信层，新增双向 RPC 支持
 */

// ============ 连接状态 ============

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

// ============ RPC 请求/响应 ============

/**
 * RPC 请求消息
 */
export interface RpcRequest {
  /** 请求唯一 ID（用于匹配响应） */
  id: string;
  /** 方法名 */
  method: string;
  /** 参数（加密后的） */
  params: unknown;
  /** 时间戳 */
  timestamp: number;
}

/**
 * RPC 响应消息
 */
export interface RpcResponse {
  /** 对应的请求 ID */
  id: string;
  /** 结果（成功时） */
  result?: unknown;
  /** 错误信息（失败时） */
  error?: string;
  /** 时间戳 */
  timestamp: number;
}

/**
 * 待处理的 RPC 请求
 */
export interface PendingRequest {
  resolve: (value: unknown) => void;
  reject: (error: Error) => void;
  timeout: NodeJS.Timeout;
  method: string;
  createdAt: number;
}

/**
 * RPC 处理器函数类型
 */
export type RpcHandler<TRequest = unknown, TResponse = unknown> =
  (params: TRequest) => Promise<TResponse>;

// ============ Master → Worker 命令 ============

export type MasterCommandType =
  | 'assign_task'
  | 'cancel_task'
  | 'request_status'
  | 'shutdown'
  | 'pause'
  | 'resume';

export interface MasterCommand {
  type: MasterCommandType;
  payload: unknown;
  timestamp: string;
}

// ============ Worker → Master 事件 ============

export type WorkerEventType =
  | 'ready'
  | 'task_started'
  | 'task_progress'
  | 'task_completed'
  | 'task_failed'
  | 'status_update'
  | 'log'
  | 'error';

export interface WorkerEvent {
  type: WorkerEventType;
  workerId: string;
  payload: unknown;
  timestamp: string;
}

// ============ Socket 配置 ============

export interface SocketClientConfig {
  /** 服务器地址 */
  endpoint: string;
  /** 认证令牌 */
  token?: string;
  /** Worker ID（用于标识） */
  workerId: string;
  /** RPC 超时时间（毫秒） */
  rpcTimeoutMs?: number;
  /** 是否启用加密 */
  enableEncryption?: boolean;
  /** 加密密钥 */
  encryptionKey?: Uint8Array;
}

export interface SocketServerConfig {
  /** 监听端口 */
  port: number;
  /** 是否启用加密 */
  enableEncryption?: boolean;
  /** 加密密钥（与 Worker 共享） */
  encryptionKey?: Uint8Array;
  /** RPC 超时时间（毫秒） */
  rpcTimeoutMs?: number;
}

// ============ 事件类型 ============

export type SocketEventType =
  | 'connect'
  | 'disconnect'
  | 'error'
  | 'rpc-request'
  | 'rpc-response'
  | 'worker:register'
  | 'worker:heartbeat'
  | 'worker:task_started'
  | 'worker:task_completed'
  | 'worker:task_failed';
