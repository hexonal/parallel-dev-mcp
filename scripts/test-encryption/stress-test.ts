/**
 * 加密通信压力测试
 *
 * 持续运行 5 分钟以上，验证加密通信稳定性
 * 使用方式: npx tsx scripts/test-encryption/stress-test.ts
 */

import { SocketServer } from '../../src/parallel/communication/SocketServer';
import { SocketClient } from '../../src/parallel/communication/SocketClient';
import { generateSecretKey, initSodium } from '../../src/parallel/encryption';

const PORT = 9529;
const TEST_DURATION_MS = 5 * 60 * 1000; // 5 分钟
const RPC_INTERVAL_MS = 500; // 每 500ms 发起一次 RPC

interface Stats {
  totalCalls: number;
  successCalls: number;
  failedCalls: number;
  totalLatency: number;
  minLatency: number;
  maxLatency: number;
  bytesTransferred: number;
  startTime: number;
}

const stats: Stats = {
  totalCalls: 0,
  successCalls: 0,
  failedCalls: 0,
  totalLatency: 0,
  minLatency: Infinity,
  maxLatency: 0,
  bytesTransferred: 0,
  startTime: 0,
};

function log(msg: string) {
  const elapsed = Math.floor((Date.now() - stats.startTime) / 1000);
  const mins = Math.floor(elapsed / 60);
  const secs = elapsed % 60;
  console.log(`[${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}] ${msg}`);
}

function printStats() {
  const elapsed = (Date.now() - stats.startTime) / 1000;
  const avgLatency = stats.successCalls > 0 ? stats.totalLatency / stats.successCalls : 0;
  const rps = stats.totalCalls / elapsed;

  console.log('\n' + '─'.repeat(60));
  console.log('📊 统计信息');
  console.log('─'.repeat(60));
  console.log(`运行时间:     ${elapsed.toFixed(1)} 秒`);
  console.log(`总调用次数:   ${stats.totalCalls}`);
  console.log(`成功:         ${stats.successCalls} (${((stats.successCalls / stats.totalCalls) * 100).toFixed(2)}%)`);
  console.log(`失败:         ${stats.failedCalls}`);
  console.log(`平均延迟:     ${avgLatency.toFixed(2)} ms`);
  console.log(`最小延迟:     ${stats.minLatency === Infinity ? 0 : stats.minLatency} ms`);
  console.log(`最大延迟:     ${stats.maxLatency} ms`);
  console.log(`吞吐量:       ${rps.toFixed(2)} RPC/秒`);
  console.log(`数据传输:     ${(stats.bytesTransferred / 1024).toFixed(2)} KB`);
  console.log('─'.repeat(60) + '\n');
}

async function main() {
  console.log('═'.repeat(60));
  console.log('  ParallelDev 加密通信压力测试');
  console.log(`  测试时长: ${TEST_DURATION_MS / 1000 / 60} 分钟`);
  console.log('═'.repeat(60) + '\n');

  let server: SocketServer | null = null;
  let client: SocketClient | null = null;
  let running = true;

  try {
    // 初始化
    log('初始化 libsodium...');
    await initSodium();

    const encryptionKey = generateSecretKey();
    log(`生成加密密钥: ${encryptionKey.length} 字节`);

    // 创建 Master 服务器
    server = new SocketServer({
      port: PORT,
      enableEncryption: true,
      encryptionKey: encryptionKey,
      rpcTimeoutMs: 10000,
    });

    // Master 处理器
    server.registerHandler('processTask', async (params: { taskId: string; data: unknown }) => {
      // 模拟处理
      const result = {
        taskId: params.taskId,
        status: 'completed',
        processedAt: Date.now(),
        dataSize: JSON.stringify(params.data).length,
      };
      stats.bytesTransferred += JSON.stringify(params).length + JSON.stringify(result).length;
      return result;
    });

    server.registerHandler('heartbeat', async (params: { workerId: string; timestamp: number }) => {
      return { received: true, serverTime: Date.now(), latency: Date.now() - params.timestamp };
    });

    await server.start();
    log(`Master 服务器已启动: http://localhost:${PORT}`);

    // 创建 Worker 客户端
    client = new SocketClient({
      endpoint: `http://localhost:${PORT}`,
      workerId: 'stress-test-worker',
      enableEncryption: true,
      encryptionKey: encryptionKey,
      rpcTimeoutMs: 10000,
    });

    // Worker 处理器
    client.registerHandler('executeCommand', async (params: { command: string; args: string[] }) => {
      const result = {
        output: `Executed: ${params.command} ${params.args.join(' ')}`,
        exitCode: 0,
        executedAt: Date.now(),
      };
      stats.bytesTransferred += JSON.stringify(params).length + JSON.stringify(result).length;
      return result;
    });

    // 等待连接
    const workerConnected = new Promise<void>((resolve) => {
      server!.on('worker:connected', () => resolve());
    });

    await client.connect();
    await workerConnected;
    log('Worker 已连接到 Master');

    // 开始压力测试
    stats.startTime = Date.now();
    log('开始压力测试...\n');

    // 定期打印统计
    const statsInterval = setInterval(() => {
      if (running) printStats();
    }, 30000); // 每 30 秒打印一次

    // Worker → Master RPC 循环
    const workerToMasterLoop = async () => {
      while (running && Date.now() - stats.startTime < TEST_DURATION_MS) {
        const start = Date.now();
        stats.totalCalls++;

        try {
          const testData = {
            taskId: `task-${stats.totalCalls}`,
            data: {
              message: '测试加密数据 🔐',
              timestamp: Date.now(),
              random: Math.random(),
              array: [1, 2, 3, 4, 5],
              nested: { level1: { level2: { value: 'deep' } } },
            },
          };

          await client!.rpc('processTask', testData);

          const latency = Date.now() - start;
          stats.successCalls++;
          stats.totalLatency += latency;
          stats.minLatency = Math.min(stats.minLatency, latency);
          stats.maxLatency = Math.max(stats.maxLatency, latency);

          if (stats.totalCalls % 100 === 0) {
            log(`✅ 已完成 ${stats.totalCalls} 次 RPC 调用`);
          }
        } catch (error) {
          stats.failedCalls++;
          log(`❌ RPC 失败: ${error}`);
        }

        await new Promise(resolve => setTimeout(resolve, RPC_INTERVAL_MS));
      }
    };

    // Master → Worker RPC 循环
    const masterToWorkerLoop = async () => {
      await new Promise(resolve => setTimeout(resolve, 250)); // 错开时间

      while (running && Date.now() - stats.startTime < TEST_DURATION_MS) {
        const start = Date.now();
        stats.totalCalls++;

        try {
          await server!.callWorker('stress-test-worker', 'executeCommand', {
            command: 'test',
            args: ['--arg1', '--arg2', `timestamp=${Date.now()}`],
          });

          const latency = Date.now() - start;
          stats.successCalls++;
          stats.totalLatency += latency;
          stats.minLatency = Math.min(stats.minLatency, latency);
          stats.maxLatency = Math.max(stats.maxLatency, latency);
        } catch (error) {
          stats.failedCalls++;
          log(`❌ Master→Worker RPC 失败: ${error}`);
        }

        await new Promise(resolve => setTimeout(resolve, RPC_INTERVAL_MS));
      }
    };

    // 心跳循环
    const heartbeatLoop = async () => {
      while (running && Date.now() - stats.startTime < TEST_DURATION_MS) {
        try {
          stats.totalCalls++;
          const result = await client!.rpc<{ latency: number }>('heartbeat', {
            workerId: 'stress-test-worker',
            timestamp: Date.now(),
          });
          stats.successCalls++;

          if (stats.totalCalls % 60 === 0) {
            log(`💓 心跳延迟: ${result.latency}ms`);
          }
        } catch (error) {
          stats.failedCalls++;
        }

        await new Promise(resolve => setTimeout(resolve, 5000)); // 每 5 秒心跳
      }
    };

    // 并行运行所有循环
    await Promise.all([
      workerToMasterLoop(),
      masterToWorkerLoop(),
      heartbeatLoop(),
    ]);

    running = false;
    clearInterval(statsInterval);

    // 最终统计
    console.log('\n' + '═'.repeat(60));
    console.log('  测试完成');
    console.log('═'.repeat(60));
    printStats();

    const successRate = (stats.successCalls / stats.totalCalls) * 100;
    if (successRate >= 99) {
      console.log('🎉 测试通过！加密通信稳定可靠\n');
      process.exit(0);
    } else {
      console.log(`⚠️  成功率 ${successRate.toFixed(2)}% 低于 99%，需要检查\n`);
      process.exit(1);
    }

  } catch (error) {
    console.error('\n❌ 测试出错:', error);
    process.exit(1);
  } finally {
    if (client) client.disconnect();
    if (server) await server.stop();
  }
}

// 处理中断
process.on('SIGINT', () => {
  console.log('\n\n⚠️  测试被中断');
  printStats();
  process.exit(0);
});

main();
