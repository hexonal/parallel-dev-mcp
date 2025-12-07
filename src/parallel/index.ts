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
// export { TaskDAG } from './task/TaskDAG';
// export { TaskScheduler } from './task/TaskScheduler';
// export { TaskManager } from './task/TaskManager';

// Layer 2: Orchestration (后续 Phase 实现)
// export { MasterOrchestrator } from './master/MasterOrchestrator';
// export { WorkerPool } from './master/WorkerPool';
// export { StateManager } from './master/StateManager';

// Layer 3: Execution (后续 Phase 实现)
// export { WorktreeManager } from './git/WorktreeManager';
// export { TmuxController } from './tmux/TmuxController';
// export { TaskExecutor } from './worker/TaskExecutor';

// Layer 4: Communication (后续 Phase 实现)
// export { SocketServer } from './communication/SocketServer';
// export { SocketClient } from './communication/SocketClient';
// export { StatusReporter } from './worker/StatusReporter';

// Layer 5: Quality Assurance (后续 Phase 实现)
// export { ConflictResolver } from './quality/ConflictResolver';
// export { CodeValidator } from './quality/CodeValidator';

// Layer 6: Notification (后续 Phase 实现)
// export { NotificationManager } from './notification/NotificationManager';
// export { ReportGenerator } from './notification/ReportGenerator';
