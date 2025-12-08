/**
 * Master 测试服务器
 *
 * 用于测试加密 RPC 通信
 * 使用方式: npx tsx scripts/test-encryption/master.ts
 */

import { SocketServer } from '../../src/parallel/communication/SocketServer';
import { generateSecretKey, initSodium } from '../../src/parallel/encryption';
import { encodeBase64 } from '../../src/parallel/encryption';

const PORT = 9527;

async function main() {
  console.log('========================================');
  console.log('   Master 加密通信测试服务器');
  console.log('========================================\n');

  // 1. 初始化 libsodium
  console.log('[1/5] 初始化 libsodium...');
  await initSodium();
  console.log('  ✅ libsodium 初始化完成\n');

  // 2. 生成加密密钥
  console.log('[2/5] 生成加密密钥...');
  const encryptionKey = generateSecretKey();
  const keyBase64 = encodeBase64(encryptionKey, 'base64');
  console.log(`  ✅ 密钥生成完成`);
  console.log(`  📋 密钥 (Base64): ${keyBase64}\n`);

  // 3. 创建服务器
  console.log('[3/5] 创建 SocketServer...');
  const server = new SocketServer({
    port: PORT,
    enableEncryption: true,
    encryptionKey: encryptionKey,
    rpcTimeoutMs: 30000,
  });

  // 4. 注册 Master 端 RPC 处理器
  console.log('[4/5] 注册 RPC 处理器...');

  // Master 提供的方法：获取任务
  server.registerHandler('getTask', async (params: { workerId: string }) => {
    console.log(`\n📥 [RPC] Worker 请求任务: ${params.workerId}`);
    const task = {
      id: `task-${Date.now()}`,
      name: '测试任务',
      command: 'echo "Hello from Master"',
      assignedTo: params.workerId,
      createdAt: new Date().toISOString(),
    };
    console.log(`📤 [RPC] 返回任务: ${task.id}`);
    return task;
  });

  // Master 提供的方法：报告状态
  server.registerHandler('reportStatus', async (params: { workerId: string; status: string; data?: unknown }) => {
    console.log(`\n📥 [RPC] Worker 状态报告:`);
    console.log(`    Worker: ${params.workerId}`);
    console.log(`    Status: ${params.status}`);
    if (params.data) {
      console.log(`    Data: ${JSON.stringify(params.data)}`);
    }
    return { received: true, timestamp: Date.now() };
  });

  console.log('  ✅ 已注册: getTask, reportStatus\n');

  // 5. 启动服务器
  console.log('[5/5] 启动服务器...');
  await server.start();
  console.log(`  ✅ 服务器已启动: http://localhost:${PORT}`);
  console.log(`  📡 Socket.IO 路径: /v1/parallel\n`);

  // 监听 Worker 连接事件
  server.on('worker:connected', async ({ workerId }) => {
    console.log(`\n🔗 Worker 已连接: ${workerId}`);
    console.log('  正在等待 3 秒后调用 Worker RPC...\n');

    // 等待 Worker 注册处理器
    await new Promise(resolve => setTimeout(resolve, 3000));

    // 测试调用 Worker 的 RPC 方法
    try {
      console.log('📤 [Master→Worker] 调用 execute 方法...');
      const result = await server.callWorker<{ output: string; exitCode: number }>(
        workerId,
        'execute',
        { command: 'echo "测试加密通信"', timeout: 5000 }
      );
      console.log('📥 [Master←Worker] 执行结果:');
      console.log(`    Output: ${result.output}`);
      console.log(`    Exit Code: ${result.exitCode}`);
      console.log('\n✅ 加密 RPC 调用成功！\n');
    } catch (error) {
      console.error('❌ 调用 Worker RPC 失败:', error);
    }
  });

  server.on('worker:disconnected', ({ workerId }) => {
    console.log(`\n🔌 Worker 已断开: ${workerId}`);
  });

  server.on('worker:heartbeat', ({ workerId }) => {
    console.log(`💓 Worker 心跳: ${workerId}`);
  });

  // 输出连接说明
  console.log('========================================');
  console.log('   等待 Worker 连接...');
  console.log('========================================');
  console.log('\n请在另一个终端运行:');
  console.log(`  npx tsx scripts/test-encryption/worker.ts "${keyBase64}"\n`);
  console.log('按 Ctrl+C 退出\n');

  // 保持进程运行
  process.on('SIGINT', async () => {
    console.log('\n正在关闭服务器...');
    await server.stop();
    console.log('服务器已关闭');
    process.exit(0);
  });
}

main().catch(console.error);
