/**
 * AI 能力测试脚本
 * 测试 TaskMaster AI 功能集成
 */

import * as path from 'path';
import { TaskAIService } from '../../src/parallel/tm-core/services/task-ai.service';
import { FileStorage } from '../../src/parallel/tm-core/storage';

// 配置
const TEST_PROJECT_ROOT = path.join(__dirname, '../../test-demo');
const PRD_PATH = 'docs/prd.md';

// AI 配置 - AIService 会自动从环境变量读取:
// - ANTHROPIC_AUTH_TOKEN (Bearer 认证)
// - ANTHROPIC_BASE_URL (代理地址)
const AI_CONFIG = {
  provider: 'anthropic' as const,
  model: 'claude-sonnet-4-20250514'
};

async function main() {
  console.log('═══════════════════════════════════════════════════════════════');
  console.log('  ParallelDev AI 能力测试');
  console.log('═══════════════════════════════════════════════════════════════');
  console.log('');
  console.log(`📁 项目目录: ${TEST_PROJECT_ROOT}`);
  console.log(`📄 PRD 文件: ${PRD_PATH}`);
  console.log(`🤖 AI 模型: ${AI_CONFIG.model}`);
  console.log(`🌐 API URL: ${process.env.ANTHROPIC_BASE_URL || '(默认)'}`);
  console.log(`🔑 认证方式: ${process.env.ANTHROPIC_AUTH_TOKEN ? 'Bearer Token' : 'API Key'}`);
  console.log('');

  // 检查认证配置
  if (!process.env.ANTHROPIC_AUTH_TOKEN && !process.env.ANTHROPIC_API_KEY) {
    console.error('❌ 错误: 未设置 ANTHROPIC_AUTH_TOKEN 或 ANTHROPIC_API_KEY 环境变量');
    process.exit(1);
  }

  // 创建服务
  const taskAIService = new TaskAIService(TEST_PROJECT_ROOT, AI_CONFIG);
  const storage = new FileStorage(TEST_PROJECT_ROOT);

  // 检查 AI 服务是否可用
  if (!taskAIService.isAvailable()) {
    console.error('❌ 错误: AI 服务不可用');
    process.exit(1);
  }

  console.log('✅ AI 服务初始化成功');
  console.log('');

  // ========== 测试 1: 解析 PRD ==========
  console.log('───────────────────────────────────────────────────────────────');
  console.log('📋 测试 1: 解析 PRD 生成任务');
  console.log('───────────────────────────────────────────────────────────────');

  try {
    console.log('⏳ 正在解析 PRD...');
    const startTime = Date.now();

    const result = await taskAIService.parsePRD(PRD_PATH, {
      numTasks: 5,
      defaultPriority: 'medium',
      force: true
    });

    const duration = ((Date.now() - startTime) / 1000).toFixed(2);

    console.log(`✅ PRD 解析完成 (耗时: ${duration}s)`);
    console.log('');
    console.log('📊 生成的任务:');
    console.log('');

    for (const task of result.result) {
      console.log(`  [${task.id}] ${task.title}`);
      console.log(`      优先级: ${task.priority} | 状态: ${task.status}`);
      console.log(`      描述: ${task.description.substring(0, 80)}...`);
      console.log('');
    }

    console.log('📈 Token 使用:');
    console.log(`  - 输入: ${result.usage.inputTokens}`);
    console.log(`  - 输出: ${result.usage.outputTokens}`);
    console.log(`  - 总计: ${result.usage.totalTokens}`);
    console.log('');

  } catch (error) {
    console.error('❌ PRD 解析失败:', error);
    process.exit(1);
  }

  // ========== 测试 2: 展开任务 ==========
  console.log('───────────────────────────────────────────────────────────────');
  console.log('📋 测试 2: 展开任务为子任务');
  console.log('───────────────────────────────────────────────────────────────');

  try {
    // 加载任务
    const tasks = await storage.loadTasks();
    if (tasks.length === 0) {
      console.log('⚠️  没有可展开的任务');
    } else {
      const taskToExpand = tasks[0];
      console.log(`⏳ 正在展开任务 [${taskToExpand.id}]: ${taskToExpand.title}...`);

      const startTime = Date.now();

      const result = await taskAIService.expandTask(taskToExpand.id, {
        numSubtasks: 3,
        force: true
      });

      const duration = ((Date.now() - startTime) / 1000).toFixed(2);

      console.log(`✅ 任务展开完成 (耗时: ${duration}s)`);
      console.log('');
      console.log('📊 生成的子任务:');
      console.log('');

      for (const subtask of result.result.subtasks || []) {
        console.log(`  [${subtask.id}] ${subtask.title}`);
        console.log(`      状态: ${subtask.status}`);
        console.log(`      描述: ${subtask.description.substring(0, 80)}...`);
        console.log('');
      }

      console.log('📈 Token 使用:');
      console.log(`  - 输入: ${result.usage.inputTokens}`);
      console.log(`  - 输出: ${result.usage.outputTokens}`);
      console.log(`  - 总计: ${result.usage.totalTokens}`);
      console.log('');
    }

  } catch (error) {
    console.error('❌ 任务展开失败:', error);
  }

  // ========== 测试 3: AI 更新任务 ==========
  console.log('───────────────────────────────────────────────────────────────');
  console.log('📋 测试 3: AI 更新任务');
  console.log('───────────────────────────────────────────────────────────────');

  try {
    const tasks = await storage.loadTasks();
    if (tasks.length === 0) {
      console.log('⚠️  没有可更新的任务');
    } else {
      const taskToUpdate = tasks[0];
      console.log(`⏳ 正在更新任务 [${taskToUpdate.id}]: ${taskToUpdate.title}...`);

      const startTime = Date.now();

      const result = await taskAIService.updateTaskWithAI(
        taskToUpdate.id,
        '将这个任务的优先级提高到 high，并添加更详细的测试策略'
      );

      const duration = ((Date.now() - startTime) / 1000).toFixed(2);

      console.log(`✅ 任务更新完成 (耗时: ${duration}s)`);
      console.log('');
      console.log('📊 更新后的任务:');
      console.log(`  标题: ${result.result.title}`);
      console.log(`  优先级: ${result.result.priority}`);
      console.log(`  测试策略: ${result.result.testStrategy || '无'}`);
      console.log('');

      console.log('📈 Token 使用:');
      console.log(`  - 输入: ${result.usage.inputTokens}`);
      console.log(`  - 输出: ${result.usage.outputTokens}`);
      console.log(`  - 总计: ${result.usage.totalTokens}`);
      console.log('');
    }

  } catch (error) {
    console.error('❌ 任务更新失败:', error);
  }

  // ========== 显示最终任务列表 ==========
  console.log('───────────────────────────────────────────────────────────────');
  console.log('📋 最终任务列表');
  console.log('───────────────────────────────────────────────────────────────');

  try {
    const finalTasks = await storage.loadTasks();
    console.log('');
    for (const task of finalTasks) {
      console.log(`[${task.id}] ${task.title}`);
      console.log(`    优先级: ${task.priority} | 状态: ${task.status}`);
      if (task.subtasks && task.subtasks.length > 0) {
        console.log(`    子任务数: ${task.subtasks.length}`);
        for (const st of task.subtasks) {
          console.log(`      └─ [${st.id}] ${st.title}`);
        }
      }
      console.log('');
    }
  } catch (error) {
    console.error('❌ 加载任务列表失败:', error);
  }

  console.log('═══════════════════════════════════════════════════════════════');
  console.log('  测试完成');
  console.log('═══════════════════════════════════════════════════════════════');
}

main().catch(console.error);
