/**
 * ParallelDev 模块导出
 * @module parallel
 */

// 类型导出
export * from './types';

// 配置导出
export {
  DEFAULT_CONFIG,
  loadConfig,
  saveConfig,
  validateConfig
} from './config';

// Layer 1: Task Management
export { TaskDAG } from './task/TaskDAG';
export { TaskScheduler } from './task/TaskScheduler';
export { TaskManager } from './task/TaskManager';

// Layer 2: Orchestration
export {
  MasterOrchestrator,
  OrchestratorEventType,
  WorkerPool,
  WorkerPoolStats,
  StateManager,
  SystemState,
} from './master';

// Layer 3: Execution
export { WorktreeManager, WorktreeInfo } from './git/WorktreeManager';
export { ConflictDetector } from './git/ConflictDetector';
export { TmuxController } from './tmux/TmuxController';
export { SessionMonitor } from './tmux/SessionMonitor';
export { TaskExecutor, TaskExecutorConfig } from './worker/TaskExecutor';

// Layer 4: Communication (爆改自 Happy)
export {
  SocketClient,
  SocketServer,
  RpcManager,
  type RpcManagerConfig,
  type RpcSendFunction,
  type ConnectionStatus,
  type RpcRequest,
  type RpcResponse,
  type PendingRequest,
  type RpcHandler,
  type MasterCommand,
  type MasterCommandType,
  type WorkerEvent,
  type WorkerEventType,
  type SocketClientConfig,
  type SocketServerConfig,
} from './communication';
export { StatusReporter, type TaskResult, type StatusReporterConfig } from './worker/StatusReporter';

// Layer 5: Quality Assurance
export {
  SubagentRunner,
  SubagentResult,
  QualityCheckResult,
  ConflictInfo,
  ResolveResult,
  SubagentRunnerConfig,
  ConflictResolver,
  ConflictDetectionResult,
  ConflictResolverConfig,
  CodeValidator,
  CheckResult,
  TestResult,
  ValidationResult,
  CodeValidatorConfig,
} from './quality';

// Layer 6: Notification
export {
  NotificationManager,
  NotificationChannel,
  NotificationLevel,
  NotificationOptions,
  WebhookConfig,
  ReportGenerator,
  ExecutionReport,
  ReportFormat,
} from './notification';
