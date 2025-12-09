/**
 * 测试 HybridExecutor 使用 Happy SDK 模式
 * 在 test-demo 目录下执行简单任务
 */

import { HybridExecutor } from './src/parallel/worker/HybridExecutor';
import { TmuxController } from './src/parallel/tmux/TmuxController';
import { SessionMonitor } from './src/parallel/tmux/SessionMonitor';
import type { Task } from './src/parallel/types';

async function main() {
  console.log('🧪 测试 HybridExecutor (Happy SDK 模式)\n');

  // 创建 Tmux 依赖（虽然 SDK 模式不直接使用）
  const tmux = new TmuxController();
  const monitor = new SessionMonitor(tmux);

  // 创建 HybridExecutor
  const executor = new HybridExecutor(tmux, monitor, 'test-session', {
    permissionMode: 'acceptEdits',
    maxTurns: 10,
    timeout: 120000
  });

  // 创建测试任务
  const testTask: Task = {
    id: 'test-001',
    title: '列出目录结构',
    description: '请简要列出当前目录下的所有文件和文件夹，说明每个文件的用途。不需要使用任何工具，只需根据你对项目结构的了解进行描述即可。回答要简洁，不超过100字。',
    dependencies: [],
    priority: 1,
    status: 'pending',
    createdAt: new Date().toISOString()
  };

  console.log('📋 任务信息:');
  console.log(`   ID: ${testTask.id}`);
  console.log(`   标题: ${testTask.title}`);
  console.log('');

  try {
    console.log('🚀 开始执行任务...\n');

    const result = await executor.execute(
      testTask,
      '/Users/flink/PycharmProjects/parallel-dev-mcp/test-demo'
    );

    console.log('\n📊 执行结果:');
    console.log(`   成功: ${result.success}`);
    console.log(`   耗时: ${result.duration}ms`);

    if (result.success) {
      console.log(`   输出: ${result.output?.substring(0, 300)}...`);
      if (result.metadata?.usage) {
        console.log(`   Token: 输入 ${result.metadata.usage.inputTokens}, 输出 ${result.metadata.usage.outputTokens}`);
        console.log(`   费用: $${result.metadata.usage.totalCost?.toFixed(4)}`);
      }
      if (result.metadata?.sessionId) {
        console.log(`   Session: ${result.metadata.sessionId}`);
      }
    } else {
      console.log(`   错误: ${result.error}`);
    }

    console.log('\n✅ 测试完成！');

  } catch (error) {
    console.error('❌ 测试失败:', error);
    await executor.cancel();
  }
}

main();
