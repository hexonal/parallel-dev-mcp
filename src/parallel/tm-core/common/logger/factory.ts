/**
 * Logger 工厂和单例管理
 * 爆改自 claude-task-master/packages/tm-core/src/common/logger/factory.ts
 */

import { Logger, type LoggerConfig } from './logger';

// 全局 logger 实例
let globalLogger: Logger | null = null;

// 命名 logger 实例
const loggers = new Map<string, Logger>();

/**
 * 创建新的 logger 实例
 */
export function createLogger(config?: LoggerConfig): Logger {
  return new Logger(config);
}

/**
 * 获取或创建命名 logger 实例
 */
export function getLogger(name?: string, config?: LoggerConfig): Logger {
  if (!name) {
    if (!globalLogger) {
      globalLogger = createLogger(config);
    }
    return globalLogger;
  }

  if (!loggers.has(name)) {
    loggers.set(
      name,
      createLogger({
        prefix: name,
        ...config
      })
    );
  }

  return loggers.get(name)!;
}

/**
 * 设置全局 logger 实例
 */
export function setGlobalLogger(logger: Logger): void {
  globalLogger = logger;
}

/**
 * 清除所有 logger 实例（用于测试）
 */
export function clearLoggers(): void {
  globalLogger = null;
  loggers.clear();
}
