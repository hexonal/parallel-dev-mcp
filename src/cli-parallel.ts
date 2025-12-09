#!/usr/bin/env node
/**
 * pdev CLI - ParallelDev 命令行工具
 *
 * 提供并行开发系统的完整控制接口：
 * - (默认): 进入持久交互式 REPL
 * - init: 初始化项目
 * - generate: 从 PRD 生成任务
 * - run: 启动并行执行
 * - start: 完整流程（generate + run）
 * - status/stop/report: 状态管理
 */

import { Command } from 'commander';
import chalk from 'chalk';
import * as path from 'path';
import * as fs from 'fs';
import {
  loadConfig,
  MasterOrchestrator,
  StateManager,
  ReportGenerator,
  NotificationManager,
  TaskManager,
  PDEV_PATHS,
} from './parallel';
import { initProject } from './parallel/init';
import { ParallelDevConfig } from './parallel/types';
import { REPLShell } from './repl';

const program = new Command();

// 版本和描述
program
  .name('pdev')
  .description('Claude Code 自动化并行开发系统')
  .version('1.0.0');

// ============================================================
// init 命令 - 初始化项目
// ============================================================
program
  .command('init')
  .description('初始化 ParallelDev 项目')
  .option('-f, --force', '强制重新初始化')
  .option('-s, --silent', '静默模式')
  .action(async (options) => {
    const projectRoot = process.cwd();

    console.log(chalk.blue('🚀 初始化 ParallelDev...'));
    console.log();

    const result = await initProject(projectRoot, {
      force: options.force,
      silent: options.silent
    });

    if (!result.success) {
      process.exit(1);
    }
  });

// ============================================================
// doctor 命令 - 环境诊断
// ============================================================
program
  .command('doctor')
  .description('诊断 ParallelDev 环境配置')
  .option('-c, --check <category>', '检查类别 (config|claude|mcp|git|all)', 'all')
  .option('--fix', '自动修复（重新运行 init）')
  .option('--json', 'JSON 格式输出')
  .action(async (options) => {
    const { HealthChecker } = await import('./parallel/health');
    const projectRoot = process.cwd();
    const checker = new HealthChecker(projectRoot);

    // 如果指定了 --fix，先尝试修复
    if (options.fix) {
      console.log(chalk.blue('🔧 正在修复环境配置...'));
      const fixed = await checker.fix();
      if (fixed) {
        console.log(chalk.green('✅ 修复完成'));
        console.log();
      } else {
        console.log(chalk.red('❌ 修复失败'));
        process.exit(1);
      }
    }

    // 运行诊断
    let result;
    if (options.check && options.check !== 'all') {
      const categoryResult = await checker.runCategory(options.check);
      if (!categoryResult) {
        console.error(chalk.red(`❌ 未知的检查类别: ${options.check}`));
        console.log('可用类别: config, claude, mcp, git');
        process.exit(1);
      }
      result = {
        categories: [categoryResult],
        totalPassed: categoryResult.passed,
        totalWarnings: categoryResult.warnings,
        totalFailed: categoryResult.failed,
        healthy: categoryResult.failed === 0
      };
    } else {
      result = await checker.runAllChecks();
    }

    // 输出结果
    if (options.json) {
      checker.printJson(result);
    } else {
      checker.printResult(result);
    }

    // 如果有失败项且没有 --fix，提示修复命令
    if (!result.healthy && !options.fix) {
      process.exit(1);
    }
  });

// ============================================================
// generate 命令 - 从 PRD 生成任务
// ============================================================
program
  .command('generate')
  .description('从 PRD 文件生成任务列表')
  .requiredOption('-p, --prd <file>', 'PRD 文件路径')
  .option('-o, --output <file>', '输出文件路径', PDEV_PATHS.tasksJson)
  .option('-n, --num-tasks <number>', '目标任务数', '10')
  .option('--research', '启用研究模式')
  .option('--append', '追加到现有任务')
  .action(async (options) => {
    const projectRoot = process.cwd();
    const prdPath = path.resolve(projectRoot, options.prd);
    const outputPath = path.resolve(projectRoot, options.output);

    // 检查 PRD 文件
    if (!fs.existsSync(prdPath)) {
      console.error(chalk.red(`❌ PRD 文件不存在: ${prdPath}`));
      process.exit(1);
    }

    // 检查是否已初始化
    if (!fs.existsSync(path.join(projectRoot, PDEV_PATHS.root))) {
      console.error(chalk.red('❌ 项目未初始化，请先运行 pdev init'));
      process.exit(1);
    }

    console.log(chalk.blue('📝 生成任务列表...'));
    console.log();
    console.log(chalk.gray(`  PRD 文件: ${prdPath}`));
    console.log(chalk.gray(`  输出文件: ${outputPath}`));
    console.log(chalk.gray(`  目标任务数: ${options.numTasks}`));
    console.log();

    try {
      // 加载配置
      const config = await loadConfig(projectRoot);

      // 创建任务管理器
      const taskManager = new TaskManager(projectRoot, config);

      // 初始化 AI（如果支持）
      if (typeof taskManager.initializeAI === 'function') {
        taskManager.initializeAI({
          provider: 'anthropic',
          model: 'claude-sonnet-4-20250514'
        });
      }

      // 解析 PRD
      const response = await taskManager.parsePRD(prdPath, {
        numTasks: parseInt(options.numTasks, 10),
        research: options.research,
        append: options.append
      });

      // 复制 PRD 到 .pdev/docs/
      const docsDir = path.join(projectRoot, PDEV_PATHS.docs);
      if (!fs.existsSync(docsDir)) {
        fs.mkdirSync(docsDir, { recursive: true });
      }
      fs.copyFileSync(prdPath, path.join(projectRoot, PDEV_PATHS.prd));

      const taskCount = response.result?.length || 0;
      console.log(chalk.green(`✅ 生成了 ${taskCount} 个任务`));
      console.log(chalk.gray(`   任务文件: ${outputPath}`));
    } catch (error) {
      console.error(chalk.red('❌ 生成任务失败:'), error);
      process.exit(1);
    }
  });

// ============================================================
// start 命令 - 完整流程（generate + run）
// ============================================================
program
  .command('start')
  .description('从 PRD 启动完整的并行开发流程')
  .requiredOption('-p, --prd <file>', 'PRD 文件路径')
  .option('-w, --workers <number>', 'Worker 数量', '3')
  .option('-n, --num-tasks <number>', '目标任务数', '10')
  .action(async (options) => {
    const projectRoot = process.cwd();

    console.log(chalk.blue('🚀 启动 ParallelDev 完整流程...'));
    console.log();

    // 1. 检查是否已初始化，如果没有则自动初始化
    if (!fs.existsSync(path.join(projectRoot, PDEV_PATHS.root))) {
      console.log(chalk.yellow('📦 项目未初始化，正在自动初始化...'));
      const initResult = await initProject(projectRoot, { silent: true });
      if (!initResult.success) {
        console.error(chalk.red('❌ 初始化失败:', initResult.error));
        process.exit(1);
      }
      console.log(chalk.green('✅ 初始化完成'));
      console.log();
    }

    // 2. 生成任务
    console.log(chalk.blue('📝 Step 1: 从 PRD 生成任务...'));
    // 调用 generate 命令逻辑
    const prdPath = path.resolve(projectRoot, options.prd);
    if (!fs.existsSync(prdPath)) {
      console.error(chalk.red(`❌ PRD 文件不存在: ${prdPath}`));
      process.exit(1);
    }

    try {
      const config = await loadConfig(projectRoot);
      const taskManager = new TaskManager(projectRoot, config);

      if (typeof taskManager.initializeAI === 'function') {
        taskManager.initializeAI({
          provider: 'anthropic',
          model: 'claude-sonnet-4-20250514'
        });
      }

      const response = await taskManager.parsePRD(prdPath, {
        numTasks: parseInt(options.numTasks, 10)
      });

      const taskCount = response.result?.length || 0;
      if (taskCount === 0) {
        console.error(chalk.red('❌ 未能生成任务'));
        process.exit(1);
      }

      console.log(chalk.green(`✅ 生成了 ${taskCount} 个任务`));
      console.log();

      // 3. 启动并行执行
      console.log(chalk.blue('🔧 Step 2: 启动并行执行...'));
      config.maxWorkers = parseInt(options.workers, 10);

      const orchestrator = new MasterOrchestrator(config, projectRoot);

      orchestrator.on('task_assigned', (event) => {
        console.log(chalk.blue(`📦 任务分配: ${event.taskId} → ${event.workerId}`));
      });

      orchestrator.on('task_completed', (event) => {
        console.log(chalk.green(`✅ 任务完成: ${event.taskId}`));
      });

      orchestrator.on('task_failed', (event) => {
        console.log(chalk.red(`❌ 任务失败: ${event.taskId} - ${event.error}`));
      });

      orchestrator.on('all_completed', () => {
        console.log();
        console.log(chalk.green('🎉 所有任务完成!'));
      });

      await orchestrator.start();

    } catch (error) {
      console.error(chalk.red('❌ 执行失败:'), error);
      process.exit(1);
    }
  });

// ============================================================
// run 命令 - 启动并行执行
// ============================================================
program
  .command('run')
  .description('启动并行任务执行')
  .option('-w, --workers <number>', 'Worker 数量', '3')
  .option('-t, --tasks <file>', '任务文件路径', PDEV_PATHS.tasksJson)
  .option('-c, --config <file>', '配置文件路径')
  .option('--dry-run', '模拟运行，不实际执行')
  .action(async (options) => {
    console.log(chalk.blue('🚀 启动 ParallelDev...'));
    console.log();

    const projectRoot = process.cwd();
    const tasksFile = path.resolve(projectRoot, options.tasks);
    const workers = parseInt(options.workers, 10);

    // 检查任务文件
    if (!fs.existsSync(tasksFile)) {
      console.error(chalk.red(`❌ 任务文件不存在: ${tasksFile}`));
      process.exit(1);
    }

    // 加载配置
    let config: ParallelDevConfig;
    try {
      config = await loadConfig(projectRoot);
      config.maxWorkers = workers;
    } catch (error) {
      console.error(chalk.red('❌ 加载配置失败:'), error);
      process.exit(1);
    }

    console.log(chalk.gray(`  项目目录: ${projectRoot}`));
    console.log(chalk.gray(`  任务文件: ${tasksFile}`));
    console.log(chalk.gray(`  Worker 数: ${workers}`));
    console.log();

    if (options.dryRun) {
      console.log(chalk.yellow('⚠️  模拟运行模式，不实际执行任务'));

      // 加载并显示任务信息
      const taskManager = new TaskManager(projectRoot, config);
      try {
        await taskManager.loadTasks();
        const readyTasks = taskManager.getReadyTasks();

        console.log();
        console.log(chalk.green(`📋 发现 ${readyTasks.length} 个可执行任务:`));
        for (const task of readyTasks.slice(0, 10)) {
          console.log(chalk.gray(`   - [${task.id}] ${task.title}`));
        }
        if (readyTasks.length > 10) {
          console.log(chalk.gray(`   ... 还有 ${readyTasks.length - 10} 个任务`));
        }
      } catch (error) {
        console.error(chalk.red('❌ 加载任务失败:'), error);
        process.exit(1);
      }

      return;
    }

    // 默认使用 fireAndForget 模式
    config.fireAndForget = true;

    // 启动编排器
    try {
      const orchestrator = new MasterOrchestrator(config, projectRoot);

      // 监听事件
      orchestrator.on('task_assigned', (event) => {
        console.log(
          chalk.blue(`📦 任务分配: ${event.taskId} → ${event.workerId}`)
        );
      });

      orchestrator.on('task_completed', (event) => {
        console.log(chalk.green(`✅ 任务完成: ${event.taskId}`));
      });

      orchestrator.on('task_failed', (event) => {
        console.log(
          chalk.red(`❌ 任务失败: ${event.taskId} - ${event.error}`)
        );
      });

      orchestrator.on('all_completed', () => {
        console.log();
        console.log(chalk.green('🎉 所有任务完成!'));
      });

      // 启动
      const result = await orchestrator.start();

      // fireAndForget 模式：打印会话信息后退出
      if (result && result.sessions) {
        console.log();
        console.log(chalk.green('✅ 所有任务已启动！'));
        console.log();
        console.log(chalk.bold('📺 Worker 会话:'));
        for (const session of result.sessions) {
          console.log(chalk.cyan(`   tmux attach -t ${session}`));
        }
        console.log();
        console.log(chalk.gray('使用 pdev status 查看执行状态'));
        console.log(chalk.gray('使用 pdev stop 停止所有任务'));
      }
    } catch (error) {
      console.error(chalk.red('❌ 启动失败:'), error);
      process.exit(1);
    }
  });

// ============================================================
// status 命令 - 查看状态
// ============================================================
program
  .command('status')
  .description('查看当前执行状态')
  .option('-f, --format <type>', '输出格式 (json | text)', 'text')
  .action(async (options) => {
    const projectRoot = process.cwd();
    const stateManager = new StateManager(projectRoot);

    try {
      const state = await stateManager.loadState();

      if (!state) {
        console.log(chalk.yellow('⚠️  没有运行中的任务'));
        return;
      }

      if (options.format === 'json') {
        console.log(JSON.stringify(state, null, 2));
      } else {
        console.log(chalk.blue('📊 ParallelDev 状态'));
        console.log();
        console.log(chalk.gray(`  阶段: ${state.currentPhase}`));
        console.log(chalk.gray(`  开始时间: ${state.startedAt || 'N/A'}`));
        console.log(chalk.gray(`  更新时间: ${state.updatedAt || 'N/A'}`));
        console.log();

        console.log(chalk.blue('📋 任务统计:'));
        console.log(chalk.gray(`  总任务: ${state.stats.totalTasks}`));
        console.log(chalk.green(`  已完成: ${state.stats.completedTasks}`));
        console.log(chalk.red(`  失败: ${state.stats.failedTasks}`));
        console.log(chalk.gray(`  等待中: ${state.stats.pendingTasks}`));
        console.log();

        console.log(chalk.blue('👷 Worker 状态:'));
        for (const worker of state.workers) {
          const statusIcon = getStatusIcon(worker.status);
          console.log(
            chalk.gray(`  ${statusIcon} ${worker.id}: ${worker.status}`)
          );
        }
      }
    } catch (error) {
      console.error(chalk.red('❌ 获取状态失败:'), error);
      process.exit(1);
    }
  });

// ============================================================
// stop 命令 - 停止执行
// ============================================================
program
  .command('stop')
  .description('停止并行执行')
  .option('--force', '强制停止，不等待当前任务完成')
  .action(async (options) => {
    console.log(chalk.yellow('🛑 停止 ParallelDev...'));

    const projectRoot = process.cwd();
    const stateManager = new StateManager(projectRoot);

    try {
      const state = await stateManager.loadState();

      if (!state || state.currentPhase === 'idle') {
        console.log(chalk.gray('没有运行中的任务'));
        return;
      }

      if (options.force) {
        console.log(chalk.red('⚠️  强制停止所有 Worker...'));
      } else {
        console.log(chalk.yellow('等待当前任务完成...'));
      }

      // 更新状态
      stateManager.updateState({
        currentPhase: 'idle',
        updatedAt: new Date().toISOString(),
      });

      await stateManager.saveState(stateManager.getState());

      console.log(chalk.green('✅ 已停止'));
    } catch (error) {
      console.error(chalk.red('❌ 停止失败:'), error);
      process.exit(1);
    }
  });

// ============================================================
// report 命令 - 生成报告
// ============================================================
program
  .command('report')
  .description('生成执行报告')
  .option('-f, --format <type>', '输出格式 (markdown | json)', 'markdown')
  .option('-o, --output <file>', '输出文件路径')
  .action(async (options) => {
    const projectRoot = process.cwd();
    const stateManager = new StateManager(projectRoot);
    const reportGenerator = new ReportGenerator(projectRoot);

    try {
      const state = await stateManager.loadState();

      if (!state) {
        console.log(chalk.yellow('⚠️  没有可用的执行记录'));
        return;
      }

      const report = reportGenerator.generateReport(state);

      let output: string;
      if (options.format === 'json') {
        output = reportGenerator.formatJson(report);
      } else {
        output = reportGenerator.formatMarkdown(report);
      }

      if (options.output) {
        const outputPath = path.resolve(projectRoot, options.output);
        fs.writeFileSync(outputPath, output, 'utf-8');
        console.log(chalk.green(`✅ 报告已保存到: ${outputPath}`));
      } else {
        console.log(output);
      }
    } catch (error) {
      console.error(chalk.red('❌ 生成报告失败:'), error);
      process.exit(1);
    }
  });

// ============================================================
// 辅助函数
// ============================================================

/**
 * 获取状态图标
 */
function getStatusIcon(status: string): string {
  switch (status) {
    case 'idle':
      return '⚪';
    case 'busy':
      return '🔵';
    case 'error':
      return '🔴';
    default:
      return '⚫';
  }
}

// ============================================================
// 默认行为：无子命令时进入 REPL
// ============================================================

/**
 * 启动 REPL 交互式界面
 */
async function startREPL(): Promise<void> {
  const projectRoot = process.cwd();

  // 检查项目是否已初始化
  if (!fs.existsSync(path.join(projectRoot, PDEV_PATHS.root))) {
    console.log(chalk.yellow('⚠️  项目未初始化'));
    console.log(chalk.gray('运行 pdev init 初始化项目'));
    console.log();
  }

  // 加载配置
  let config: ParallelDevConfig;
  try {
    config = await loadConfig(projectRoot);
  } catch {
    // 使用默认配置
    config = {
      maxWorkers: 3,
      worktreeDir: '.worktrees',
      mainBranch: 'main',
      socketPort: 3000,
      schedulingStrategy: 'priority_first',
      heartbeatInterval: 30000,
      taskTimeout: 600000,
    };
  }

  // 创建并启动 REPL
  const repl = new REPLShell({
    projectRoot,
    socketPort: config.socketPort || 3000,
  });

  // 处理退出信号
  process.on('SIGINT', async () => {
    await repl.stop();
    process.exit(0);
  });

  process.on('SIGTERM', async () => {
    await repl.stop();
    process.exit(0);
  });

  try {
    await repl.start();
  } catch (error) {
    console.error(chalk.red('❌ REPL 启动失败:'), error);
    process.exit(1);
  }
}

// 解析命令行参数
// 如果没有提供子命令，则启动 REPL
if (process.argv.length <= 2) {
  startREPL();
} else {
  program.parse();
}
