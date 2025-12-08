/**
 * Worker 测试客户端
 *
 * 用于测试加密 RPC 通信
 * 使用方式: npx tsx scripts/test-encryption/worker.ts <encryptionKeyBase64>
 */

import { SocketClient } from '../../src/parallel/communication/SocketClient';
import { initSodium, decodeBase64 } from '../../src/parallel/encryption';

const MASTER_ENDPOINT = 'http://localhost:9527';
const WORKER_ID = `worker-${Date.now().toString(36)}`;

async function main() {
  console.log('========================================');
  console.log('   Worker 加密通信测试客户端');
  console.log('========================================\n');

  // 获取密钥参数
  const keyBase64 = process.argv[2];
  if (!keyBase64) {
    console.error('❌ 错误: 请提供加密密钥');
    console.error('使用方式: npx tsx scripts/test-encryption/worker.ts <encryptionKeyBase64>');
    process.exit(1);
  }

  // 1. 初始化 libsodium
  console.log('[1/5] 初始化 libsodium...');
  await initSodium();
  console.log('  ✅ libsodium 初始化完成\n');

  // 2. 解码密钥
  console.log('[2/5] 解码加密密钥...');
  const encryptionKey = decodeBase64(keyBase64, 'base64');
  console.log(`  ✅ 密钥长度: ${encryptionKey.length} 字节\n`);

  // 3. 创建客户端
  console.log('[3/5] 创建 SocketClient...');
  console.log(`  Worker ID: ${WORKER_ID}`);
  console.log(`  Master: ${MASTER_ENDPOINT}`);

  const client = new SocketClient({
    endpoint: MASTER_ENDPOINT,
    workerId: WORKER_ID,
    enableEncryption: true,
    encryptionKey: encryptionKey,
    rpcTimeoutMs: 30000,
  });
  console.log('  ✅ 客户端创建完成\n');

  // 4. 注册 Worker 端 RPC 处理器
  console.log('[4/5] 注册 RPC 处理器...');

  // Worker 提供的方法：执行命令
  client.registerHandler('execute', async (params: { command: string; timeout?: number }) => {
    console.log(`\n📥 [RPC] Master 请求执行命令:`);
    console.log(`    Command: ${params.command}`);

    // 模拟执行命令
    const output = `执行结果: ${params.command}`;
    console.log(`📤 [RPC] 返回执行结果`);

    return {
      output: output,
      exitCode: 0,
      executedAt: new Date().toISOString(),
    };
  });

  // Worker 提供的方法：获取状态
  client.registerHandler('getStatus', async () => {
    console.log(`\n📥 [RPC] Master 请求 Worker 状态`);
    const status = {
      workerId: WORKER_ID,
      status: 'idle',
      uptime: process.uptime(),
      memory: process.memoryUsage(),
    };
    console.log(`📤 [RPC] 返回状态信息`);
    return status;
  });

  console.log('  ✅ 已注册: execute, getStatus\n');

  // 5. 连接到 Master
  console.log('[5/5] 连接到 Master...');
  try {
    await client.connect();
    console.log('  ✅ 连接成功！\n');
  } catch (error) {
    console.error('  ❌ 连接失败:', error);
    process.exit(1);
  }

  // 监听状态变化
  client.onStatusChange((status) => {
    console.log(`📶 连接状态: ${status}`);
  });

  // 等待连接稳定后，主动调用 Master RPC
  console.log('========================================');
  console.log('   测试 Worker → Master RPC 调用');
  console.log('========================================\n');

  await new Promise(resolve => setTimeout(resolve, 1000));

  // 测试调用 Master 的 getTask 方法
  try {
    console.log('📤 [Worker→Master] 调用 getTask 方法...');
    const task = await client.rpc<{ id: string; name: string; command: string }>('getTask', { workerId: WORKER_ID });
    console.log('📥 [Worker←Master] 获取到任务:');
    console.log(`    Task ID: ${task.id}`);
    console.log(`    Name: ${task.name}`);
    console.log(`    Command: ${task.command}`);
    console.log('\n✅ Worker→Master 加密 RPC 调用成功！\n');
  } catch (error) {
    console.error('❌ 调用 Master RPC 失败:', error);
  }

  // 测试调用 Master 的 reportStatus 方法
  try {
    console.log('📤 [Worker→Master] 调用 reportStatus 方法...');
    const result = await client.rpc<{ received: boolean; timestamp: number }>('reportStatus', {
      workerId: WORKER_ID,
      status: 'ready',
      data: { testData: '加密测试数据', timestamp: Date.now() },
    });
    console.log('📥 [Worker←Master] 状态报告结果:');
    console.log(`    Received: ${result.received}`);
    console.log(`    Timestamp: ${result.timestamp}`);
    console.log('\n✅ reportStatus 加密 RPC 调用成功！\n');
  } catch (error) {
    console.error('❌ 调用 reportStatus 失败:', error);
  }

  console.log('========================================');
  console.log('   等待 Master 调用...');
  console.log('========================================');
  console.log('\n按 Ctrl+C 退出\n');

  // 保持进程运行
  process.on('SIGINT', () => {
    console.log('\n正在断开连接...');
    client.disconnect();
    console.log('已断开连接');
    process.exit(0);
  });
}

main().catch(console.error);
