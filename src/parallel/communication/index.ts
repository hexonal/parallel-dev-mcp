/**
 * ParallelDev 通信层
 *
 * Layer 4: 爆改自 Happy 通信层
 * - 保留 Socket.IO + TweetNaCl 加密
 * - 新增双向 RPC 支持（父子进程互调）
 */

// 类型
export * from './types';

// Socket 客户端（Worker 端）
export { SocketClient } from './SocketClient';

// Socket 服务器（Master 端）
export { SocketServer } from './SocketServer';

// RPC 管理器
export { RpcManager, type RpcManagerConfig, type RpcSendFunction } from './rpc';
