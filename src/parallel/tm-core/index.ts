/**
 * tm-core 主入口
 * 爆改自 claude-task-master/packages/tm-core
 * 集成了 AI 能力：PRD 解析、任务展开、AI 更新
 */

// ========== Common ==========
export { TaskMasterError, ERROR_CODES } from './common/errors';
export { createLogger, LogLevel, type Logger } from './common/logger';
export { generateTaskId, generateSubtaskId, isValidTaskId } from './common/utils';
export type { IStorage, LoadTasksOptions } from './common/interfaces/storage.interface';
export type {
  Task,
  Subtask,
  TaskStatus,
  TaskPriority,
  TaskMetadata,
  StorageType
} from './common/types';

// ========== Entities ==========
export { TaskEntity } from './entities';

// ========== Storage ==========
export { FileStorage } from './storage';
export { PathResolver } from './storage/path-resolver';
export { FormatHandler } from './storage/format-handler';
export { FileOperations } from './storage/file-operations';

// ========== Services ==========
export {
  TaskService,
  type TaskListResult,
  type GetTaskListOptions
} from './services';
export {
  TaskExecutionService,
  type StartTaskOptions,
  type StartTaskResult,
  type ConflictCheckResult
} from './services';
export {
  TagService,
  type CreateTagOptions,
  type DeleteTagOptions,
  type CopyTagOptions
} from './services';
export {
  TaskAIService,
  type ParsePRDOptions,
  type ExpandTaskOptions
} from './services';

// ========== Git ==========
export { GitAdapter } from './git';
export { GitDomain } from './git';

// ========== AI ==========
export { AIService, getAIService, resetAIService } from './ai';
export type {
  AIConfig,
  AIProvider,
  AIRequestOptions,
  AIResponse,
  GenerateObjectParams,
  GenerateTextParams
} from './ai';

// ========== Schemas ==========
export {
  ParsePRDResponseSchema,
  ExpandTaskResponseSchema,
  SubtaskSchema,
  ParsedTaskSchema,
  type ParsePRDResponse,
  type ExpandTaskResponse,
  type ParsedTask
} from './schemas';

// ========== Prompts ==========
export {
  parsePrdPrompt,
  expandTaskPrompt,
  getParsePrdSystemPrompt,
  getParsePrdUserPrompt,
  getExpandTaskSystemPrompt,
  getExpandTaskUserPrompt,
  type ParsePrdParams,
  type ExpandTaskParams
} from './prompts';
