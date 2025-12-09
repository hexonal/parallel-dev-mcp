#!/usr/bin/env node
/**
 * WorkerRunner 程序入口
 *
 * 薄壳入口点，核心逻辑在 WorkerRunner 类中
 *
 * 用法:
 *   npx tsx src/parallel/worker/worker-runner-entry.ts --config=/tmp/pdev-worker-xxx.json
 *
 * @module parallel/worker/worker-runner-entry
 */

import { readFileSync } from 'fs';
import { WorkerRunner, WorkerRunnerConfig } from './WorkerRunner';

/**
 * 解析命令行参数
 */
function parseArgs(): { configPath: string } {
  const args = process.argv.slice(2);

  // 支持 --config=path 或 --config path 两种格式
  let configPath: string | undefined;

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];

    if (arg.startsWith('--config=')) {
      configPath = arg.split('=')[1];
    } else if (arg === '--config' && args[i + 1]) {
      configPath = args[i + 1];
      i++;
    }
  }

  if (!configPath) {
    console.error('Usage: worker-runner-entry --config=<config-file>');
    console.error('');
    console.error('Options:');
    console.error('  --config=<path>  Path to JSON config file');
    process.exit(1);
  }

  return { configPath };
}

/**
 * 加载配置文件
 */
function loadConfig(configPath: string): WorkerRunnerConfig {
  try {
    const content = readFileSync(configPath, 'utf-8');
    return JSON.parse(content) as WorkerRunnerConfig;
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : String(error);
    console.error(`Failed to load config from ${configPath}: ${errorMsg}`);
    process.exit(1);
  }
}

/**
 * 主函数
 */
async function main(): Promise<void> {
  console.log('[worker-runner-entry] Starting...');

  // 1. 解析参数
  const { configPath } = parseArgs();
  console.log(`[worker-runner-entry] Config: ${configPath}`);

  // 2. 加载配置
  const config = loadConfig(configPath);
  console.log(`[worker-runner-entry] Worker ID: ${config.workerId}`);
  console.log(`[worker-runner-entry] Task: ${config.task.title}`);

  // 3. 创建并运行 WorkerRunner
  const runner = new WorkerRunner(config);

  // 4. 处理信号
  const handleSignal = async (signal: string) => {
    console.log(`[worker-runner-entry] Received ${signal}, cancelling...`);
    await runner.cancel();
    process.exit(0);
  };

  process.on('SIGINT', () => handleSignal('SIGINT'));
  process.on('SIGTERM', () => handleSignal('SIGTERM'));

  // 5. 运行
  try {
    const result = await runner.run();

    if (result.success) {
      console.log('[worker-runner-entry] Task completed successfully');
      process.exit(0);
    } else {
      console.error(`[worker-runner-entry] Task failed: ${result.error}`);
      process.exit(1);
    }
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : String(error);
    console.error(`[worker-runner-entry] Fatal error: ${errorMsg}`);
    process.exit(1);
  }
}

// 运行
main();
