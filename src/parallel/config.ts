/**
 * ParallelDev 配置管理
 * @module parallel/config
 */

import * as fs from 'fs';
import * as path from 'path';
import { ParallelDevConfig, SchedulingStrategy } from './types';

/** 默认配置 */
export const DEFAULT_CONFIG: ParallelDevConfig = {
  maxWorkers: 3,
  worktreeDir: '.worktrees',
  mainBranch: 'main',
  socketPort: 3001,
  heartbeatInterval: 30000,
  taskTimeout: 600000,
  schedulingStrategy: 'priority_first'
};

/** 配置文件路径 */
const CONFIG_FILE = '.paralleldev/config.json';

/**
 * 加载配置
 * @param projectRoot 项目根目录
 * @returns 合并后的配置
 */
export function loadConfig(projectRoot: string): ParallelDevConfig {
  const configPath = path.join(projectRoot, CONFIG_FILE);

  if (!fs.existsSync(configPath)) {
    return { ...DEFAULT_CONFIG };
  }

  try {
    const fileContent = fs.readFileSync(configPath, 'utf-8');
    const userConfig = JSON.parse(fileContent);
    return { ...DEFAULT_CONFIG, ...userConfig };
  } catch (error) {
    console.warn(`⚠️  配置文件读取失败，使用默认配置: ${error}`);
    return { ...DEFAULT_CONFIG };
  }
}

/**
 * 保存配置
 * @param projectRoot 项目根目录
 * @param config 配置对象
 */
export function saveConfig(
  projectRoot: string,
  config: Partial<ParallelDevConfig>
): void {
  const configDir = path.join(projectRoot, '.paralleldev');
  const configPath = path.join(configDir, 'config.json');

  // 确保目录存在
  if (!fs.existsSync(configDir)) {
    fs.mkdirSync(configDir, { recursive: true });
  }

  const fullConfig = { ...DEFAULT_CONFIG, ...config };
  fs.writeFileSync(configPath, JSON.stringify(fullConfig, null, 2));
}

/**
 * 验证配置有效性
 * @param config 配置对象
 * @returns 验证结果
 */
export function validateConfig(config: ParallelDevConfig): {
  valid: boolean;
  errors: string[];
} {
  const errors: string[] = [];

  if (config.maxWorkers < 1 || config.maxWorkers > 10) {
    errors.push('maxWorkers 必须在 1-10 之间');
  }

  if (config.socketPort < 1024 || config.socketPort > 65535) {
    errors.push('socketPort 必须在 1024-65535 之间');
  }

  if (config.heartbeatInterval < 5000) {
    errors.push('heartbeatInterval 不能小于 5000ms');
  }

  if (config.taskTimeout < 60000) {
    errors.push('taskTimeout 不能小于 60000ms (1分钟)');
  }

  return {
    valid: errors.length === 0,
    errors
  };
}
