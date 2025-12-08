# 通信层深度爆改方案（Layer 4）

> 返回 [索引](00-index.md) | 上一篇: [Task Master 融合](01-task-master-fusion.md)

> 🔴 **用户确认**：不需要加密，本地 Master-Worker 通信简化实现

---

## Happy 通信架构分析

```
┌──────────────────────────────────────────────────────────────────┐
│                    Happy 原始架构                                 │
│  ┌─────────────┐     Socket.IO      ┌─────────────────────────┐ │
│  │  apiSocket  │←─────────────────→│  Server (api.happy-*.com)│ │
│  │  (Client)   │                    │                         │ │
│  └─────────────┘                    └─────────────────────────┘ │
│  Key Features:                                                   │
│  • sessionRPC(sessionId, method, params) - 加密 RPC 调用         │
│  • machineRPC(machineId, method, params) - 加密 RPC 调用         │
│  • Encryption with TweetNaCl                                     │
│  • Token-based authentication                                    │
│  • Auto-reconnection                                             │
└──────────────────────────────────────────────────────────────────┘
```

---

## ParallelDev 目标架构

```
┌──────────────────────────────────────────────────────────────────┐
│                  ParallelDev 通信架构                             │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              MasterSocketServer (新建)                      ││
│  │  • 监听 Worker 连接                                         ││
│  │  • 广播任务状态更新                                          ││
│  │  • RPC 请求处理                                             ││
│  └─────────────────────────────────────────────────────────────┘│
│              ↑                    ↑                    ↑         │
│          Worker 1             Worker 2             Worker 3      │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐      │
│  │WorkerSocket │      │WorkerSocket │      │WorkerSocket │      │
│  │  Client     │      │  Client     │      │  Client     │      │
│  └─────────────┘      └─────────────┘      └─────────────┘      │
│                                                                  │
│  Key Differences from Happy:                                     │
│  • NO encryption (本地通信)                                       │
│  • workerId instead of sessionId                                 │
│  • Master → Worker commands (assign_task, cancel_task)           │
│  • Worker → Master events (task_completed, task_failed)          │
│  • Bidirectional RPC                                             │
└──────────────────────────────────────────────────────────────────┘
```

---

## 1. SocketClient 爆改（Worker 端）

**源文件**: `happy/sources/sync/apiSocket.ts` (262 行)

### 爆改清单

| Happy 原始 | ParallelDev 爆改 | 说明 |
|-----------|-----------------|------|
| `sessionRPC()` | `workerRPC()` | 移除加密，改用 workerId |
| `machineRPC()` | 删除 | 不需要 |
| `Encryption` | 删除 | 不需要加密 |
| `TokenStorage` | 删除 | 不需要认证 |
| `onReconnected` | 保留 | 重连通知 |
| `onStatusChange` | 保留 | 状态监听 |
| `onMessage` | 扩展 | 增加 Master 命令监听 |

### 爆改代码

```typescript
// 源文件: happy/sources/sync/apiSocket.ts
// 目标文件: src/parallel/communication/SocketClient.ts

import { io, Socket } from 'socket.io-client';
import { EventEmitter } from 'events';

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

export interface WorkerSocketConfig {
  masterUrl: string;
  workerId: string;
  reconnection?: boolean;
}

export class WorkerSocketClient extends EventEmitter {
  private socket: Socket | null = null;
  private config: WorkerSocketConfig;
  private currentStatus: ConnectionStatus = 'disconnected';

  constructor(config: WorkerSocketConfig) {
    super();
    this.config = config;
  }

  connect(): void {
    if (this.socket) return;
    this.updateStatus('connecting');

    // 爆改：移除 auth.token，改用 workerId
    this.socket = io(this.config.masterUrl, {
      path: '/parallel',
      query: {
        workerId: this.config.workerId,
        clientType: 'worker'
      },
      transports: ['websocket'],
      reconnection: this.config.reconnection ?? true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      reconnectionAttempts: Infinity
    });

    this.setupEventHandlers();
  }

  async workerRPC<R, A>(method: string, params: A): Promise<R> {
    if (!this.socket) {
      throw new Error('Socket not connected');
    }

    // 爆改：直接发送，无加密
    const result = await this.socket.emitWithAck('rpc-call', {
      method: `${this.config.workerId}:${method}`,
      params
    });

    if (result.ok) {
      return result.result as R;
    }
    throw new Error(result.error || 'RPC call failed');
  }

  send(event: string, data: unknown): void {
    if (this.socket) {
      this.socket.emit(event, {
        workerId: this.config.workerId,
        ...data
      });
    }
  }

  onMasterCommand(handler: (command: MasterCommand) => void): () => void {
    this.on('master_command', handler);
    return () => this.off('master_command', handler);
  }

  onStatusChange(listener: (status: ConnectionStatus) => void): () => void {
    listener(this.currentStatus);
    this.on('status_change', listener);
    return () => this.off('status_change', listener);
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
    this.updateStatus('disconnected');
  }

  private updateStatus(status: ConnectionStatus): void {
    if (this.currentStatus !== status) {
      this.currentStatus = status;
      this.emit('status_change', status);
    }
  }

  private setupEventHandlers(): void {
    if (!this.socket) return;

    this.socket.on('connect', () => {
      this.updateStatus('connected');
      this.emit('connected');
    });

    this.socket.on('disconnect', () => {
      this.updateStatus('disconnected');
      this.emit('disconnected');
    });

    this.socket.on('connect_error', (error) => {
      this.updateStatus('error');
      this.emit('error', error);
    });

    this.socket.on('master_command', (command: MasterCommand) => {
      this.emit('master_command', command);
    });
  }
}

export interface MasterCommand {
  type: 'assign_task' | 'cancel_task' | 'request_status' | 'shutdown';
  payload: unknown;
}
```

---

## 2. SocketServer（Master 端 - 新建）

**目标文件**: `src/parallel/communication/SocketServer.ts`

```typescript
import { Server, Socket } from 'socket.io';
import { EventEmitter } from 'events';

export interface MasterSocketConfig {
  port: number;
  path?: string;
}

export interface WorkerConnection {
  id: string;
  socket: Socket;
  status: ConnectionStatus;
  connectedAt: Date;
  lastHeartbeat: Date;
}

export class MasterSocketServer extends EventEmitter {
  private io: Server | null = null;
  private workers: Map<string, WorkerConnection> = new Map();
  private config: MasterSocketConfig;

  constructor(config: MasterSocketConfig) {
    super();
    this.config = config;
  }

  start(): void {
    this.io = new Server(this.config.port, {
      path: this.config.path || '/parallel',
      cors: { origin: '*', methods: ['GET', 'POST'] }
    });

    this.io.on('connection', (socket) => this.handleConnection(socket));
    console.log(`✅ Master Socket Server started on port ${this.config.port}`);
  }

  private handleConnection(socket: Socket): void {
    const workerId = socket.handshake.query.workerId as string;
    if (!workerId) {
      socket.disconnect();
      return;
    }

    const connection: WorkerConnection = {
      id: workerId,
      socket,
      status: 'connected',
      connectedAt: new Date(),
      lastHeartbeat: new Date()
    };

    this.workers.set(workerId, connection);
    this.emit('worker_connected', workerId);
    this.setupWorkerHandlers(socket, workerId);
  }

  private setupWorkerHandlers(socket: Socket, workerId: string): void {
    socket.on('worker_event', (event: WorkerEvent) => {
      this.emit('worker_event', { workerId, event });
    });

    socket.on('rpc-call', async (request, callback) => {
      try {
        const result = await this.handleRpcRequest(workerId, request);
        callback({ ok: true, result });
      } catch (error) {
        callback({ ok: false, error: (error as Error).message });
      }
    });

    socket.on('heartbeat', () => {
      const connection = this.workers.get(workerId);
      if (connection) connection.lastHeartbeat = new Date();
    });

    socket.on('disconnect', () => {
      this.workers.delete(workerId);
      this.emit('worker_disconnected', workerId);
    });
  }

  async sendCommand(workerId: string, command: MasterCommand): Promise<void> {
    const connection = this.workers.get(workerId);
    if (!connection) throw new Error(`Worker ${workerId} not connected`);
    connection.socket.emit('master_command', command);
  }

  broadcast(event: string, data: unknown): void {
    this.io?.emit(event, data);
  }

  getConnectedWorkers(): string[] {
    return Array.from(this.workers.keys());
  }

  stop(): void {
    for (const connection of this.workers.values()) {
      connection.socket.disconnect();
    }
    this.workers.clear();
    this.io?.close();
    this.io = null;
  }
}
```

---

## 3. RpcManager 爆改

**源文件**: `happy-cli/src/api/rpc/RpcHandlerManager.ts` (135 行)

### 爆改清单

| Happy 原始 | ParallelDev 爆改 | 说明 |
|-----------|-----------------|------|
| `encryptionKey` | 删除 | 不需要加密 |
| `encryptionVariant` | 删除 | 不需要加密 |
| `decrypt()/encrypt()` | 删除 | 直接传输 |
| `scopePrefix` | 改为 `workerId` | Worker 级别作用域 |

### 爆改代码

```typescript
// 目标文件: src/parallel/communication/rpc/RpcManager.ts

export type RpcHandler<TRequest = unknown, TResponse = unknown> = (
  data: TRequest
) => TResponse | Promise<TResponse>;

export type RpcHandlerMap = Map<string, RpcHandler>;

export interface RpcRequest {
  method: string;
  params: unknown;
}

export class RpcManager {
  private handlers: RpcHandlerMap = new Map();
  private readonly scopePrefix: string;

  constructor(config: { scopePrefix: string }) {
    this.scopePrefix = config.scopePrefix;
  }

  registerHandler<TRequest = unknown, TResponse = unknown>(
    method: string,
    handler: RpcHandler<TRequest, TResponse>
  ): void {
    const prefixedMethod = `${this.scopePrefix}:${method}`;
    this.handlers.set(prefixedMethod, handler as RpcHandler);
  }

  async handleRequest(request: RpcRequest): Promise<unknown> {
    const handler = this.handlers.get(request.method);
    if (!handler) {
      return { error: 'Method not found' };
    }
    // 爆改：直接使用 params，不解密
    return await handler(request.params);
  }

  hasHandler(method: string): boolean {
    return this.handlers.has(`${this.scopePrefix}:${method}`);
  }

  clearHandlers(): void {
    this.handlers.clear();
  }
}
```

---

## 4. 通信协议定义

**目标文件**: `src/parallel/communication/types.ts`

```typescript
// ============ 连接状态 ============
export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

// ============ Master → Worker 命令 ============
export type MasterCommandType =
  | 'assign_task' | 'cancel_task' | 'request_status'
  | 'shutdown' | 'pause' | 'resume';

export interface MasterCommand {
  type: MasterCommandType;
  payload: unknown;
  timestamp: string;
}

export interface AssignTaskPayload {
  taskId: string;
  task: Task;
  worktreePath: string;
}

// ============ Worker → Master 事件 ============
export type WorkerEventType =
  | 'ready' | 'task_started' | 'task_progress'
  | 'task_completed' | 'task_failed' | 'status_update' | 'log' | 'error';

export interface WorkerEvent {
  type: WorkerEventType;
  workerId: string;
  payload: unknown;
  timestamp: string;
}

export interface TaskCompletedPayload {
  taskId: string;
  result?: unknown;
  duration: number;
  commitHash?: string;
}

export interface TaskFailedPayload {
  taskId: string;
  error: string;
  duration: number;
}
```

---

## 5. 通信层文件结构

```
src/parallel/communication/
├── index.ts                    # 导出
├── types.ts                    # 协议类型定义
├── SocketClient.ts             # Worker 客户端（爆改自 apiSocket.ts）
├── SocketServer.ts             # Master 服务器（新建）
└── rpc/
    ├── index.ts
    ├── RpcManager.ts           # RPC 管理器（爆改自 RpcHandlerManager.ts）
    └── types.ts                # RPC 类型
```

---

## 6. 爆改验证策略

### 6.1 验证阶段划分

**阶段 A：单元级验证**

| 验证项 | 验证方法 | 通过标准 |
|--------|----------|----------|
| SocketClient 类型安全 | `tsc --noEmit` | 零类型错误 |
| SocketServer 类型安全 | `tsc --noEmit` | 零类型错误 |
| RpcManager 类型安全 | `tsc --noEmit` | 零类型错误 |

**阶段 B：模块级验证**

| 模块 | 验证脚本 | 通过标准 |
|------|----------|----------|
| SocketServer | `test-socket-server.ts` | 能启动监听、接受连接 |
| SocketClient | `test-socket-client.ts` | 能连接 Server、发送消息 |
| RpcManager | `test-rpc.ts` | RPC 调用正确路由 |

**阶段 C：集成级验证**

| 场景 | 通过标准 |
|------|----------|
| Master-Worker 连接 | Worker 成功注册到 Master |
| 双向通信 | 消息正确传递，无丢失 |
| RPC 调用 | 返回值正确 |
| 断线重连 | 自动重连成功 |
| 多 Worker | 所有 Worker 正确注册 |

### 6.2 Happy 爆改检查清单

| 检查项 | 检查方法 | 必须满足 |
|--------|----------|----------|
| 移除 encryption 导入 | `grep -r "encryption"` | 无结果 |
| 移除 Happy session 依赖 | `grep -r "sessionId\|sessionRPC"` | 无结果 |
| 移除 Happy machine 依赖 | `grep -r "machineId\|machineRPC"` | 无结果 |
| workerId 替换正确 | `grep -r "workerId"` | 有结果 |
| 导入路径修正 | `grep -r "@/sync\|@/api"` | 无结果 |

### 6.3 需求满足矩阵

| ParallelDev 需求 | 通信层支持 |
|------------------|------------|
| Master 管理多 Worker | `MasterSocketServer.getConnections()` |
| Worker 注册到 Master | `worker_connected` 事件 |
| Master 分发任务 | `sendCommand('assign_task')` |
| Worker 上报状态 | `send('worker_event')` |
| 断线自动重连 | `autoReconnect: true` |
| RPC 调用 | `RpcManager.handleRequest()` |

### 6.4 验证执行顺序

```
Phase 1: 代码爆改
├── 1.1 创建 communication/ 目录
├── 1.2 爆改 SocketClient.ts
├── 1.3 新建 SocketServer.ts
├── 1.4 爆改 RpcManager.ts
└── 1.5 类型检查 → tsc --noEmit

Phase 2: 单元验证
├── 2.1 运行 test-socket-server.ts
├── 2.2 运行 test-socket-client.ts
└── 2.3 运行 test-rpc.ts

Phase 3: 集成验证
├── 3.1 运行 test-e2e-communication.ts
├── 3.2 手动断线重连测试
└── 3.3 爆改检查清单逐项确认

Phase 4: 需求验证
└── 4.1 需求满足矩阵逐项确认 ✅
```

**验证通过标准**：
- ✅ 所有单元测试脚本通过
- ✅ 端到端测试脚本通过
- ✅ Happy 爆改检查清单全部满足
- ✅ 需求满足矩阵全部打勾

---

> 下一步: [验证策略](03-verification-strategy.md)
