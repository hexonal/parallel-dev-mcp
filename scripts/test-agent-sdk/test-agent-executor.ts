/**
 * AgentExecutor 测试脚本
 *
 * 使用方式:
 * npx tsx scripts/test-agent-sdk/test-agent-executor.ts
 */

import { AgentExecutor } from '../../src/parallel/worker/AgentExecutor';
import type { Task } from '../../src/parallel/types';

async function main() {
  console.log('🚀 AgentExecutor 测试\n');

  // 创建执行器
  const executor = new AgentExecutor({
    permissionMode: 'bypassPermissions',
    allowedTools: ['Read', 'Glob', 'Grep'],
    timeout: 60000,
    maxTurns: 10,
    loadProjectSettings: false,
    enableHooks: true
  });

  // 设置进度回调
  executor.setProgressCallback((progress) => {
    console.log(`[${progress.type}] ${progress.content.substring(0, 100)}...`);
  });

  // 创建测试任务
  const task: Task = {
    id: 'test-001',
    title: '列出项目文件',
    description: '请列出当前目录下的所有 .ts 文件，并报告文件数量。',
    dependencies: [],
    priority: 1,
    status: 'pending',
    createdAt: new Date().toISOString()
  };

  console.log('📋 任务信息:');
  console.log(`   ID: ${task.id}`);
  console.log(`   标题: ${task.title}`);
  console.log(`   描述: ${task.description}`);
  console.log('');

  // 执行任务
  console.log('⏳ 开始执行任务...\n');
  const startTime = Date.now();

  try {
    const result = await executor.execute(task, process.cwd());

    console.log('\n' + '='.repeat(50));
    console.log('📊 执行结果:');
    console.log(`   成功: ${result.success ? '✅ 是' : '❌ 否'}`);
    console.log(`   耗时: ${result.duration}ms`);

    if (result.metadata?.usage) {
      console.log(`   输入 tokens: ${result.metadata.usage.inputTokens}`);
      console.log(`   输出 tokens: ${result.metadata.usage.outputTokens}`);
      console.log(`   总费用: $${result.metadata.usage.totalCost.toFixed(4)}`);
    }

    if (result.error) {
      console.log(`   错误: ${result.error}`);
    }

    if (result.output) {
      console.log('\n📝 输出摘要:');
      console.log(result.output.substring(0, 500));
      if (result.output.length > 500) {
        console.log('... (截断)');
      }
    }

  } catch (error) {
    console.error('❌ 执行失败:', error);
  }

  console.log('\n✅ 测试完成');
}

main().catch(console.error);
