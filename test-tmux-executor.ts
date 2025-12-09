/**
 * 通过 Tmux 触发 HybridExecutor 测试
 * 在 test-demo 项目中完成一个实际的小需求
 *
 * 使用新的 Tmux 架构：HybridExecutor 在 Tmux 会话中运行 Claude CLI
 */

import { HybridExecutor } from './src/parallel/worker/HybridExecutor';
import { TmuxController } from './src/parallel/tmux/TmuxController';
import { SessionMonitor } from './src/parallel/tmux/SessionMonitor';
import type { Task } from './src/parallel/types';

// 会话 ID（不含前缀，TmuxController 会自动添加前缀）
const TEST_SESSION_ID = 'test-worker-1';
const TEST_DEMO_PATH = '/Users/flink/PycharmProjects/parallel-dev-mcp/test-demo';

async function main() {
  console.log('========================================');
  console.log('🧪 Tmux + HybridExecutor 集成测试');
  console.log('========================================\n');

  // 1. 创建 Tmux 控制器（使用 'pdev' 前缀）
  const tmux = new TmuxController('pdev');
  const monitor = new SessionMonitor(tmux);

  // 2. 显示 Tmux 会话信息
  console.log('📺 Tmux 会话配置:');
  const fullSessionName = tmux.getSessionName(TEST_SESSION_ID);
  console.log(`   会话 ID: ${TEST_SESSION_ID}`);
  console.log(`   完整名称: ${fullSessionName}`);
  console.log(`   可通过 'tmux attach -t ${fullSessionName}' 观察执行过程\n`);

  // 3. 创建 HybridExecutor（会自动管理 Tmux 会话）
  console.log('⚙️  创建 HybridExecutor...');
  const executor = new HybridExecutor(tmux, monitor, TEST_SESSION_ID, {
    permissionMode: 'acceptEdits',
    maxTurns: 20,
    timeout: 300000  // 5 分钟超时
  });
  console.log('   ✓ Executor 已就绪');

  // 4. 定义实际任务：为 task.ts 添加新功能
  const realTask: Task = {
    id: 'real-task-001',
    title: '添加 filterTasksByStatus 函数',
    description: `请在 src/task.ts 文件中添加一个新函数 filterTasksByStatus：

功能要求：
1. 函数签名：filterTasksByStatus(tasks: Task[], status: TaskStatus): Task[]
2. 功能：根据状态过滤任务数组
3. 返回匹配指定状态的所有任务

请：
1. 在文件末尾的 export 之前添加此函数
2. 添加适当的 JSDoc 注释
3. 在 export 语句中导出这个新函数

完成后，简要说明你做了什么修改。`,
    dependencies: [],
    priority: 1,
    status: 'pending',
    createdAt: new Date().toISOString()
  };

  console.log('\n📋 任务信息:');
  console.log(`   ID: ${realTask.id}`);
  console.log(`   标题: ${realTask.title}`);
  console.log('   描述: 在 task.ts 中添加按状态过滤任务的函数');

  // 5. 执行任务
  console.log('\n🚀 开始执行任务...');
  console.log('   (通过 Tmux + Claude CLI 模式)\n');

  try {
    const startTime = Date.now();
    const result = await executor.execute(realTask, TEST_DEMO_PATH);
    const duration = Date.now() - startTime;

    console.log('\n========================================');
    console.log('📊 执行结果');
    console.log('========================================');
    console.log(`   状态: ${result.success ? '✅ 成功' : '❌ 失败'}`);
    console.log(`   耗时: ${(duration / 1000).toFixed(1)} 秒`);

    if (result.success) {
      console.log('\n📝 输出摘要:');
      const output = result.output || '';
      // 显示前 500 个字符
      console.log(output.substring(0, 500));
      if (output.length > 500) {
        console.log('   ... (输出已截断)');
      }

      if (result.metadata?.usage) {
        console.log('\n💰 Token 使用:');
        console.log(`   输入: ${result.metadata.usage.inputTokens}`);
        console.log(`   输出: ${result.metadata.usage.outputTokens}`);
        console.log(`   费用: $${result.metadata.usage.totalCost?.toFixed(4)}`);
      }

      if (result.metadata?.sessionId) {
        console.log(`\n🔗 Session ID: ${result.metadata.sessionId}`);
      }
    } else {
      console.log(`\n❌ 错误: ${result.error}`);
    }

    // 6. 验证文件是否被修改
    console.log('\n🔍 验证修改结果...');
    const { execSync } = await import('child_process');
    const gitStatus = execSync('git status --short', {
      cwd: TEST_DEMO_PATH,
      encoding: 'utf-8'
    });

    if (gitStatus.includes('task.ts')) {
      console.log('   ✅ task.ts 已被修改');

      // 显示 diff
      try {
        const diff = execSync('git diff src/task.ts', {
          cwd: TEST_DEMO_PATH,
          encoding: 'utf-8'
        });
        console.log('\n📄 Git Diff:');
        console.log(diff.substring(0, 1000));
      } catch {
        console.log('   (无法获取 diff)');
      }
    } else {
      console.log('   ⚠️  task.ts 未被修改');
    }

    console.log('\n========================================');
    console.log('✅ 测试完成！');
    console.log('========================================');

    // 7. 可选：关闭 Tmux 会话
    // await executor.closeSession();

  } catch (error) {
    console.error('\n❌ 测试失败:', error);
    await executor.cancel();
  } finally {
    // 显示如何查看会话
    const sessionName = executor.getCurrentSessionName();
    if (sessionName) {
      console.log(`\n💡 提示: 会话 '${sessionName}' 仍然存在`);
      console.log(`   查看: tmux attach -t ${sessionName}`);
      console.log(`   关闭: tmux kill-session -t ${sessionName}`);
    }
  }
}

main().catch(console.error);
