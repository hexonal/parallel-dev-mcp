/**
 * Task Master 日志实现
 * 爆改自 claude-task-master/packages/tm-core/src/common/logger/logger.ts
 */

import chalk from 'chalk';

export enum LogLevel {
  SILENT = 0,
  ERROR = 1,
  WARN = 2,
  INFO = 3,
  DEBUG = 4
}

/**
 * 日志对象接口
 */
export interface LogObject {
  info: (message: string) => void;
  warn: (message: string) => void;
  error: (message: string) => void;
  debug: (message: string) => void;
}

/**
 * 日志回调可以是函数或日志对象
 */
export type LogCallback =
  | ((level: string, message: string) => void)
  | LogObject;

export interface LoggerConfig {
  level?: LogLevel;
  silent?: boolean;
  prefix?: string;
  timestamp?: boolean;
  colors?: boolean;
  mcpMode?: boolean;
  logCallback?: LogCallback;
}

export class Logger {
  private config: LoggerConfig & {
    level: LogLevel;
    silent: boolean;
    prefix: string;
    timestamp: boolean;
    colors: boolean;
    mcpMode: boolean;
  };

  private static readonly DEFAULT_CONFIG = {
    level: LogLevel.SILENT,
    silent: false,
    prefix: '',
    timestamp: false,
    colors: true,
    mcpMode: false,
    logCallback: undefined as LogCallback | undefined
  };

  constructor(config: LoggerConfig = {}) {
    const envConfig: LoggerConfig = {};

    // 检查 MCP 模式
    if (
      process.env.MCP_MODE === 'true' ||
      process.env.TASK_MASTER_MCP === 'true'
    ) {
      envConfig.mcpMode = true;
    }

    // 检查静默模式
    if (
      process.env.TASK_MASTER_SILENT === 'true' ||
      process.env.TM_SILENT === 'true'
    ) {
      envConfig.silent = true;
    }

    // 检查日志级别
    if (process.env.TASK_MASTER_LOG_LEVEL || process.env.TM_LOG_LEVEL) {
      const levelStr = (
        process.env.TASK_MASTER_LOG_LEVEL ||
        process.env.TM_LOG_LEVEL ||
        ''
      ).toUpperCase();
      if (levelStr in LogLevel) {
        envConfig.level = LogLevel[levelStr as keyof typeof LogLevel];
      }
    }

    // 检查无颜色
    if (
      process.env.NO_COLOR === 'true' ||
      process.env.TASK_MASTER_NO_COLOR === 'true'
    ) {
      envConfig.colors = false;
    }

    // 合并配置
    this.config = {
      ...Logger.DEFAULT_CONFIG,
      ...config,
      ...envConfig
    };

    // MCP 模式覆盖为静默
    if (this.config.mcpMode && !this.config.logCallback) {
      this.config.silent = true;
    }
  }

  /**
   * 检查是否应该记录给定级别的日志
   */
  private shouldLog(level: LogLevel): boolean {
    if (this.config.logCallback) {
      return level <= this.config.level;
    }

    if (this.config.silent || this.config.mcpMode) {
      return false;
    }
    return level <= this.config.level;
  }

  /**
   * 格式化日志消息
   */
  private formatMessage(
    level: LogLevel,
    message: string,
    ...args: unknown[]
  ): string {
    let formatted = '';

    if (this.config.timestamp) {
      const timestamp = new Date().toISOString();
      formatted += this.config.colors
        ? chalk.gray(`[${timestamp}] `)
        : `[${timestamp}] `;
    }

    if (this.config.prefix) {
      formatted += this.config.colors
        ? chalk.cyan(`[${this.config.prefix}] `)
        : `[${this.config.prefix}] `;
    }

    if (this.config.colors) {
      switch (level) {
        case LogLevel.ERROR:
          message = chalk.red(message);
          break;
        case LogLevel.WARN:
          message = chalk.yellow(message);
          break;
        case LogLevel.INFO:
          break;
        case LogLevel.DEBUG:
          message = chalk.gray(message);
          break;
      }
    }

    formatted += message;

    if (args.length > 0) {
      formatted +=
        ' ' +
        args
          .map((arg) =>
            typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg)
          )
          .join(' ');
    }

    return formatted;
  }

  /**
   * 检查回调是否为日志对象
   */
  private isLogObject(callback: LogCallback): callback is LogObject {
    return (
      typeof callback === 'object' &&
      callback !== null &&
      'info' in callback &&
      'warn' in callback &&
      'error' in callback &&
      'debug' in callback
    );
  }

  /**
   * 输出日志消息
   */
  private output(
    level: LogLevel,
    levelName: string,
    message: string,
    ...args: unknown[]
  ): void {
    const formatted = this.formatMessage(level, message, ...args);

    if (this.config.logCallback) {
      if (this.isLogObject(this.config.logCallback)) {
        const method = levelName.toLowerCase() as keyof LogObject;
        if (method in this.config.logCallback) {
          this.config.logCallback[method](formatted);
        }
      } else {
        this.config.logCallback(levelName.toLowerCase(), formatted);
      }
      return;
    }

    switch (level) {
      case LogLevel.ERROR:
        console.error(formatted);
        break;
      case LogLevel.WARN:
        console.warn(formatted);
        break;
      default:
        console.log(formatted);
        break;
    }
  }

  error(message: string, ...args: unknown[]): void {
    if (!this.shouldLog(LogLevel.ERROR)) return;
    this.output(LogLevel.ERROR, 'ERROR', message, ...args);
  }

  warn(message: string, ...args: unknown[]): void {
    if (!this.shouldLog(LogLevel.WARN)) return;
    this.output(LogLevel.WARN, 'WARN', message, ...args);
  }

  info(message: string, ...args: unknown[]): void {
    if (!this.shouldLog(LogLevel.INFO)) return;
    this.output(LogLevel.INFO, 'INFO', message, ...args);
  }

  debug(message: string, ...args: unknown[]): void {
    if (!this.shouldLog(LogLevel.DEBUG)) return;
    this.output(LogLevel.DEBUG, 'DEBUG', message, ...args);
  }

  log(message: string, ...args: unknown[]): void {
    if (this.config.logCallback) {
      const fullMessage =
        args.length > 0 ? [message, ...args].join(' ') : message;

      if (this.isLogObject(this.config.logCallback)) {
        this.config.logCallback.info(fullMessage);
      } else {
        this.config.logCallback('log', fullMessage);
      }
      return;
    }

    if (this.config.silent || this.config.mcpMode) return;

    if (args.length > 0) {
      console.log(message, ...args);
    } else {
      console.log(message);
    }
  }

  setConfig(config: Partial<LoggerConfig>): void {
    this.config = {
      ...this.config,
      ...config
    };

    if (this.config.mcpMode && !this.config.logCallback) {
      this.config.silent = true;
    }
  }

  getConfig(): Readonly<
    LoggerConfig & {
      level: LogLevel;
      silent: boolean;
      prefix: string;
      timestamp: boolean;
      colors: boolean;
      mcpMode: boolean;
    }
  > {
    return { ...this.config };
  }

  child(prefix: string, config?: Partial<LoggerConfig>): Logger {
    const childPrefix = this.config.prefix
      ? `${this.config.prefix}:${prefix}`
      : prefix;

    return new Logger({
      ...this.config,
      ...config,
      prefix: childPrefix
    });
  }
}
