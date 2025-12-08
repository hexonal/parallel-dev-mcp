/**
 * Task 模块导出
 */

export { TaskManager } from './TaskManager';
export { TaskDAG } from './TaskDAG';
export { TaskScheduler } from './TaskScheduler';

// 类型适配器
export {
  toTmCoreStatus,
  toParallelDevStatus,
  toTmCorePriority,
  toNumericPriority,
  toTmCoreTask,
  toParallelDevTask,
  toTmCoreTasks,
  toParallelDevTasks,
  parseTaskId,
  formatTaskId,
  parseDependencies,
  formatDependencies,
  isParallelDevStatus,
  isTmCoreStatus,
  isTmCorePriority
} from './type-adapters';
