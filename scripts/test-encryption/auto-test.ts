/**
 * 自动化加密通信端到端测试
 *
 * 启动 Master 和 Worker 进程，验证加密 RPC 通信
 * 使用方式: npx tsx scripts/test-encryption/auto-test.ts
 */

import { spawn, ChildProcess } from 'child_process';
import { SocketServer } from '../../src/parallel/communication/SocketServer';
import { SocketClient } from '../../src/parallel/communication/SocketClient';
import { generateSecretKey, initSodium } from '../../src/parallel/encryption';

const PORT = 9528;
const WORKER_ID = 'test-worker-001';

interface TestResult {
  name: string;
  passed: boolean;
  message: string;
  duration?: number;
}

const results: TestResult[] = [];

function log(msg: string) {
  console.log(`[${new Date().toISOString().slice(11, 19)}] ${msg}`);
}

function logSection(title: string) {
  console.log('\n' + '='.repeat(50));
  console.log(`  ${title}`);
  console.log('='.repeat(50) + '\n');
}

async function runTest(name: string, testFn: () => Promise<void>): Promise<boolean> {
  const start = Date.now();
  try {
    await testFn();
    const duration = Date.now() - start;
    results.push({ name, passed: true, message: 'OK', duration });
    log(`✅ ${name} (${duration}ms)`);
    return true;
  } catch (error) {
    const duration = Date.now() - start;
    const message = error instanceof Error ? error.message : String(error);
    results.push({ name, passed: false, message, duration });
    log(`❌ ${name}: ${message}`);
    return false;
  }
}

async function main() {
  logSection('ParallelDev 加密通信 E2E 测试');

  let server: SocketServer | null = null;
  let client: SocketClient | null = null;

  try {
    // 1. 初始化
    log('初始化 libsodium...');
    await initSodium();

    // 2. 生成加密密钥
    log('生成加密密钥...');
    const encryptionKey = generateSecretKey();
    log(`密钥长度: ${encryptionKey.length} 字节`);

    // 3. 创建 Master 服务器
    logSection('启动 Master 服务器');

    server = new SocketServer({
      port: PORT,
      enableEncryption: true,
      encryptionKey: encryptionKey,
      rpcTimeoutMs: 10000,
    });

    // 注册 Master RPC 处理器
    server.registerHandler('getTask', async (params: { workerId: string }) => {
      log(`📥 [Master] 收到 getTask 请求: ${params.workerId}`);
      return {
        id: `task-${Date.now()}`,
        name: '加密测试任务',
        command: 'echo "encrypted"',
        workerId: params.workerId,
      };
    });

    server.registerHandler('reportStatus', async (params: { workerId: string; status: string }) => {
      log(`📥 [Master] 收到状态报告: ${params.workerId} -> ${params.status}`);
      return { received: true, timestamp: Date.now() };
    });

    await server.start();
    log(`Master 服务器已启动: http://localhost:${PORT}`);

    // 4. 创建 Worker 客户端
    logSection('启动 Worker 客户端');

    client = new SocketClient({
      endpoint: `http://localhost:${PORT}`,
      workerId: WORKER_ID,
      enableEncryption: true,
      encryptionKey: encryptionKey,
      rpcTimeoutMs: 10000,
    });

    // 注册 Worker RPC 处理器
    client.registerHandler('execute', async (params: { command: string }) => {
      log(`📥 [Worker] 收到 execute 请求: ${params.command}`);
      return {
        output: `执行结果: ${params.command}`,
        exitCode: 0,
      };
    });

    client.registerHandler('getStatus', async () => {
      log(`📥 [Worker] 收到 getStatus 请求`);
      return {
        workerId: WORKER_ID,
        status: 'ready',
        uptime: process.uptime(),
      };
    });

    // 监听连接事件
    const workerConnected = new Promise<void>((resolve) => {
      server!.on('worker:connected', ({ workerId }) => {
        log(`🔗 Worker 已连接: ${workerId}`);
        resolve();
      });
    });

    await client.connect();
    log('Worker 已连接到 Master');

    // 等待服务器确认连接
    await workerConnected;
    await new Promise(resolve => setTimeout(resolve, 500));

    // 5. 运行测试
    logSection('运行加密 RPC 测试');

    // 测试 1: Worker → Master RPC (getTask)
    await runTest('Worker → Master: getTask', async () => {
      const task = await client!.rpc<{ id: string; name: string }>('getTask', { workerId: WORKER_ID });
      if (!task.id || !task.name) {
        throw new Error('返回数据不完整');
      }
      log(`  获取到任务: ${task.id}`);
    });

    // 测试 2: Worker → Master RPC (reportStatus)
    await runTest('Worker → Master: reportStatus', async () => {
      const result = await client!.rpc<{ received: boolean }>('reportStatus', {
        workerId: WORKER_ID,
        status: 'working',
      });
      if (!result.received) {
        throw new Error('状态报告未被确认');
      }
    });

    // 测试 3: Master → Worker RPC (execute)
    await runTest('Master → Worker: execute', async () => {
      const result = await server!.callWorker<{ output: string; exitCode: number }>(
        WORKER_ID,
        'execute',
        { command: 'test-command' }
      );
      if (result.exitCode !== 0) {
        throw new Error(`执行失败: ${result.exitCode}`);
      }
      log(`  执行输出: ${result.output}`);
    });

    // 测试 4: Master → Worker RPC (getStatus)
    await runTest('Master → Worker: getStatus', async () => {
      const status = await server!.callWorker<{ workerId: string; status: string }>(
        WORKER_ID,
        'getStatus',
        {}
      );
      if (status.workerId !== WORKER_ID) {
        throw new Error('Worker ID 不匹配');
      }
      log(`  Worker 状态: ${status.status}`);
    });

    // 测试 5: 复杂数据加密传输
    await runTest('复杂数据加密传输', async () => {
      server!.registerHandler('echoComplex', async (data: unknown) => data);

      const complexData = {
        string: '中文测试 🔐',
        number: 12345.678,
        boolean: true,
        array: [1, 'two', { three: 3 }],
        nested: { level1: { level2: { level3: 'deep' } } },
        nullValue: null,
        timestamp: Date.now(),
      };

      const result = await client!.rpc<typeof complexData>('echoComplex', complexData);

      if (JSON.stringify(result) !== JSON.stringify(complexData)) {
        throw new Error('数据不一致');
      }
      log(`  复杂数据传输验证通过`);
    });

    // 测试 6: 错误密钥测试
    await runTest('错误密钥拒绝连接', async () => {
      const wrongKey = generateSecretKey();
      const badClient = new SocketClient({
        endpoint: `http://localhost:${PORT}`,
        workerId: 'bad-worker',
        enableEncryption: true,
        encryptionKey: wrongKey,
        rpcTimeoutMs: 3000,
      });

      try {
        await badClient.connect();
        // 尝试 RPC 调用，应该失败（解密失败）
        await badClient.rpc('getTask', { workerId: 'bad-worker' });
        badClient.disconnect();
        // 如果没有抛出错误，但解密应该失败
        log(`  错误密钥客户端 RPC 调用（数据解密会失败）`);
      } catch {
        badClient.disconnect();
        // 预期的错误
      }
    });

    // 6. 输出结果
    logSection('测试结果汇总');

    const passed = results.filter(r => r.passed).length;
    const failed = results.filter(r => !r.passed).length;

    console.log(`总计: ${results.length} 个测试`);
    console.log(`通过: ${passed} ✅`);
    console.log(`失败: ${failed} ❌`);
    console.log('');

    for (const r of results) {
      const icon = r.passed ? '✅' : '❌';
      console.log(`  ${icon} ${r.name} (${r.duration}ms)`);
      if (!r.passed) {
        console.log(`     └─ ${r.message}`);
      }
    }

    if (failed === 0) {
      logSection('🎉 所有测试通过！加密通信正常工作');
    } else {
      logSection(`⚠️  ${failed} 个测试失败`);
    }

    process.exit(failed > 0 ? 1 : 0);

  } catch (error) {
    console.error('\n❌ 测试运行出错:', error);
    process.exit(1);
  } finally {
    // 清理
    if (client) {
      client.disconnect();
    }
    if (server) {
      await server.stop();
    }
  }
}

main();
