/**
 * Task Master 错误类
 * 爆改自 claude-task-master/packages/tm-core/src/common/errors/task-master-error.ts
 */

export const ERROR_CODES = {
  FILE_NOT_FOUND: 'FILE_NOT_FOUND',
  FILE_READ_ERROR: 'FILE_READ_ERROR',
  FILE_WRITE_ERROR: 'FILE_WRITE_ERROR',
  PARSE_ERROR: 'PARSE_ERROR',
  JSON_PARSE_ERROR: 'JSON_PARSE_ERROR',
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  TASK_NOT_FOUND: 'TASK_NOT_FOUND',
  TASK_DEPENDENCY_ERROR: 'TASK_DEPENDENCY_ERROR',
  TASK_STATUS_ERROR: 'TASK_STATUS_ERROR',
  STORAGE_ERROR: 'STORAGE_ERROR',
  CONFIG_ERROR: 'CONFIG_ERROR',
  INTERNAL_ERROR: 'INTERNAL_ERROR',
  INVALID_INPUT: 'INVALID_INPUT',
  NOT_IMPLEMENTED: 'NOT_IMPLEMENTED',
  UNKNOWN_ERROR: 'UNKNOWN_ERROR',
  NOT_FOUND: 'NOT_FOUND',
} as const;

export type ErrorCode = (typeof ERROR_CODES)[keyof typeof ERROR_CODES];

export interface ErrorContext {
  details?: unknown;
  timestamp?: Date;
  operation?: string;
  resource?: string;
  userMessage?: string;
  [key: string]: unknown;
}

export class TaskMasterError extends Error {
  public readonly code: string;
  public readonly context: ErrorContext;
  public readonly cause?: Error;
  public readonly timestamp: Date;

  constructor(
    message: string,
    code: string = ERROR_CODES.UNKNOWN_ERROR,
    context: ErrorContext = {},
    cause?: Error
  ) {
    super(message);
    this.name = 'TaskMasterError';
    this.code = code;
    this.cause = cause;
    this.timestamp = new Date();
    this.context = { timestamp: this.timestamp, ...context };

    Object.setPrototypeOf(this, TaskMasterError.prototype);

    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, TaskMasterError);
    }

    if (cause?.stack) {
      this.stack = `${this.stack}\nCaused by: ${cause.stack}`;
    }
  }

  public getUserMessage(): string {
    return (this.context.userMessage as string) || this.message;
  }

  public is(code: string): boolean {
    return this.code === code;
  }

  public hasCode(code: string): boolean {
    if (this.is(code)) return true;
    if (this.cause instanceof TaskMasterError) {
      return this.cause.hasCode(code);
    }
    return false;
  }

  public withContext(additionalContext: Partial<ErrorContext>): TaskMasterError {
    return new TaskMasterError(
      this.message,
      this.code,
      { ...this.context, ...additionalContext },
      this.cause
    );
  }

  public wrap(
    message: string,
    code: string = ERROR_CODES.INTERNAL_ERROR,
    context: ErrorContext = {}
  ): TaskMasterError {
    return new TaskMasterError(message, code, context, this);
  }
}
