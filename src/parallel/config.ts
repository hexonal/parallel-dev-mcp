/**
 * ParallelDev 配置管理
 * @module parallel/config
 */

import * as fs from 'fs';
import * as path from 'path';
import { ParallelDevConfig, SchedulingStrategy } from './types';

// ============================================
// .pdev 目录结构常量
// ============================================

/** ParallelDev 数据目录名称 */
export const PDEV_DIR = '.pdev';

/** .pdev 目录结构 */
export const PDEV_PATHS = {
  /** 根目录 */
  root: PDEV_DIR,
  /** 配置文件 */
  config: `${PDEV_DIR}/config.json`,
  /** 状态文件 */
  state: `${PDEV_DIR}/state.json`,
  /** 任务目录 */
  tasks: `${PDEV_DIR}/tasks`,
  /** 任务文件 */
  tasksJson: `${PDEV_DIR}/tasks/tasks.json`,
  /** 文档目录 */
  docs: `${PDEV_DIR}/docs`,
  /** PRD 文件 */
  prd: `${PDEV_DIR}/docs/prd.md`,
  /** Workers 状态目录 */
  workers: `${PDEV_DIR}/workers`,
  /** Worker 级 CLAUDE.md */
  claudeMd: `${PDEV_DIR}/CLAUDE.md`
} as const;

/** Claude Code 插件目录 */
export const CLAUDE_PATHS = {
  /** .claude 目录 */
  root: '.claude',
  /** settings.json */
  settings: '.claude/settings.json',
  /** 本地插件目录 */
  plugin: '.claude/paralleldev-plugin'
} as const;

// ============================================
// 默认配置
// ============================================

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
const CONFIG_FILE = PDEV_PATHS.config;

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
  const configDir = path.join(projectRoot, PDEV_DIR);
  const configPath = path.join(projectRoot, PDEV_PATHS.config);

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
