/**
 * Git 模块导出
 */

export { GitService } from './GitService';
export type {
  WorktreeInfo,
  GitStatusSummary,
  CommitOptions,
  CommitInfo
} from './GitService';

// 向后兼容：导出 WorktreeManager 别名
export { GitService as WorktreeManager } from './GitService';
