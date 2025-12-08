# 计划：复制 Happy 源码并进行真正的爆改（支持加密 + 双向 RPC）

## 任务目标

将 Happy 的源码复制到项目中，然后进行真正的"爆改"，实现：
1. ✅ **保留 TweetNaCl/Libsodium 加密功能**
2. ✅ **支持 Master↔Worker 双向 RPC 调用**

## 问题诊断

**当前问题**：
- `src/parallel/communication/SocketClient.ts` 声称是"爆改自 Happy"，但实际上是从头写的
- **完全没有加密功能** - 没有使用 Happy 的 `Encryption` 类
- 违背了 `00-index.md` 和 `02-design.md` 中的"爆改"承诺

**根本原因**：没有先复制 Happy 源码，而是直接写了新代码

---

## 实施计划

### Phase 1：复制 Happy 加密系统（基础依赖）

**目标目录**：`src/parallel/encryption/`

**需要复制的文件**：

| Happy 源文件 | 目标文件 | 说明 |
|-------------|---------|------|
| `happy/sources/encryption/libsodium.ts` | `src/parallel/encryption/libsodium.ts` | SecretBox/Box 加密 |
| `happy/sources/encryption/libsodium.lib.ts` | `src/parallel/encryption/libsodium.lib.ts` | Libsodium 库封装 |
| `happy/sources/encryption/base64.ts` | `src/parallel/encryption/base64.ts` | Base64 编解码 |
| `happy/sources/encryption/text.ts` | `src/parallel/encryption/text.ts` | UTF-8 编解码 |
| `happy/sources/encryption/hex.ts` | `src/parallel/encryption/hex.ts` | Hex 编解码 |
| `happy/sources/encryption/deriveKey.ts` | `src/parallel/encryption/deriveKey.ts` | 密钥派生 |

**爆改内容**：
- 移除 expo-crypto 依赖，改用 Node.js crypto
- 移除 rn-encryption 依赖，使用纯 libsodium
- 调整 import 路径

### Phase 2：复制 Happy 高级加密管理

**目标目录**：`src/parallel/encryption/`

**需要复制的文件**：

| Happy 源文件 | 目标文件 | 说明 |
|-------------|---------|------|
| `happy/sources/sync/encryption/encryptor.ts` | `src/parallel/encryption/encryptor.ts` | 加密器接口和实现 |
| `happy/sources/sync/encryption/encryption.ts` | `src/parallel/encryption/encryption.ts` | 主加密管理类 |
| `happy/sources/sync/encryption/encryptionCache.ts` | `src/parallel/encryption/encryptionCache.ts` | 加密缓存 |

**爆改内容**：
- 简化为只支持 SecretBox 加密（Master-Worker 通信只需对称加密）
- 移除 Session/Machine 概念，改为 Worker 概念
- 移除 AES256 相关代码（依赖 rn-encryption）

### Phase 3：爆改 SocketClient.ts（添加加密）

**文件**：`src/parallel/communication/SocketClient.ts`

**当前状态**：
- 有双向 RPC 支持 ✅
- **没有加密功能** ❌

**爆改内容**：
```typescript
// 当前（无加密）
async rpc<TResult, TParams>(method: string, params: TParams): Promise<TResult> {
  const request = { id, method, params, timestamp };  // 明文！
  this.socket.emit('rpc-request', request);
}

// 爆改后（加密）
async rpc<TResult, TParams>(method: string, params: TParams): Promise<TResult> {
  const encrypted = await this.encryption.encryptRaw(params);  // 加密！
  const request = { id, method, params: encrypted, timestamp };
  this.socket.emit('rpc-request', request);
}
```

**新增内容**：
1. 添加 `encryption: SimpleEncryption` 属性
2. 修改 `initialize()` 接受加密密钥
3. 修改 `rpc()` 加密请求参数
4. 修改 `handleRpcRequest()` 解密请求参数
5. 修改 `handleRpcResponse()` 解密响应结果

### Phase 4：创建简化的加密类

**新文件**：`src/parallel/encryption/SimpleEncryption.ts`

```typescript
/**
 * 简化版加密类（爆改自 Happy Encryption）
 *
 * 只保留 SecretBox 对称加密，用于 Master-Worker 通信
 */
export class SimpleEncryption {
  private secretKey: Uint8Array;

  constructor(secretKey: Uint8Array) {
    this.secretKey = secretKey;
  }

  async encryptRaw(data: any): Promise<string> {
    const encrypted = encryptSecretBox(data, this.secretKey);
    return encodeBase64(encrypted);
  }

  async decryptRaw(encrypted: string): Promise<any> {
    const data = decodeBase64(encrypted);
    return decryptSecretBox(data, this.secretKey);
  }
}
```

### Phase 5：更新 SocketServer.ts（Master 端）

**文件**：`src/parallel/communication/SocketServer.ts`

**新增内容**：
1. 添加 `encryption: SimpleEncryption` 属性
2. 修改 `handleRpcRequest()` 解密/加密
3. 修改 `callWorker()` 加密请求

---

## 文件变更清单

### 新增文件（从 Happy 复制）

```
src/parallel/encryption/
├── index.ts              # 导出
├── libsodium.ts          # ← happy/sources/encryption/libsodium.ts
├── libsodium.lib.ts      # ← happy/sources/encryption/libsodium.lib.ts
├── base64.ts             # ← happy/sources/encryption/base64.ts
├── text.ts               # ← happy/sources/encryption/text.ts
├── hex.ts                # ← happy/sources/encryption/hex.ts
├── encryptor.ts          # ← happy/sources/sync/encryption/encryptor.ts (简化)
└── SimpleEncryption.ts   # 新建（简化版加密管理）
```

### 修改文件

```
src/parallel/communication/
├── SocketClient.ts       # 添加加密支持
├── SocketServer.ts       # 添加加密支持
└── types.ts              # 添加加密相关类型
```

### 依赖安装

```bash
npm install libsodium-wrappers
npm install -D @types/libsodium-wrappers
```

### 依赖替换表

| Happy 依赖 (React Native) | ParallelDev 依赖 (Node.js) | 说明 |
|--------------------------|---------------------------|------|
| `@more-tech/react-native-libsodium` | `libsodium-wrappers` | Libsodium 库 |
| `expo-crypto.digest()` | `crypto.createHash()` | SHA512 哈希 |
| `expo-crypto.getRandomBytes()` | `crypto.randomBytes()` | 随机数生成 |
| `rn-encryption` | ❌ 移除 | AES-GCM（不需要）|

---

## 爆改架构图

### 完整架构图（符合 02-design.md 设计）

```
┌──────────────────────────────────────────────────────────────────┐
│                  ParallelDev 通信架构（爆改后）                    │
├──────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              MasterSocketServer（爆改，双向 RPC）             │ │
│  │  • 监听 Worker 连接                                         │ │
│  │  • 主动调用 Worker RPC（父→子）                              │ │
│  │  • 响应 Worker RPC 调用（子→父）                             │ │
│  │  • 请求 ID 追踪（匹配请求和响应）                             │ │
│  │  • SimpleEncryption 加密所有通信                             │ │
│  └─────────────────────────────────────────────────────────────┘ │
│              ↕                    ↕                    ↕         │
│          Worker 1             Worker 2             Worker 3      │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐      │
│  │SocketClient │      │SocketClient │      │SocketClient │      │
│  │(爆改apiSocket)     │(爆改apiSocket)     │(爆改apiSocket)      │
│  │ +双向RPC    │      │ +双向RPC    │      │ +双向RPC    │      │
│  │ +加密       │      │ +加密       │      │ +加密       │      │
│  └─────────────┘      └─────────────┘      └─────────────┘      │
│                                                                  │
│  爆改后特性:                                                      │
│  ✅ 保留加密（TweetNaCl/Libsodium SecretBox）                    │
│  ✅ Master → Worker RPC（父调用子）                              │
│  ✅ Worker → Master RPC（子调用父/子回复父）                      │
│  ✅ 请求 ID 追踪（匹配请求-响应）                                  │
│  ✅ 超时处理和重试机制                                            │
└──────────────────────────────────────────────────────────────────┘
```

### 加密层详细架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    Encryption Layer (爆改自 Happy)               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ SimpleEncryption.ts (新建，简化版加密管理)                    ││
│  │  • encryptRaw(data) → 加密任意数据                           ││
│  │  • decryptRaw(encrypted) → 解密数据                         ││
│  │  • 使用共享密钥（Master-Worker 启动时协商）                   ││
│  └─────────────────────────────────────────────────────────────┘│
│                              ↓                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ 底层加密工具 (从 Happy 复制并爆改)                            ││
│  │                                                              ││
│  │  libsodium.ts      base64.ts       text.ts                  ││
│  │  ├─encryptSecretBox├─encodeBase64  ├─encodeUTF8             ││
│  │  └─decryptSecretBox└─decodeBase64  └─decodeUTF8             ││
│  │                                                              ││
│  │  依赖: libsodium-wrappers (替代 @more-tech/react-native...)  ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 验收标准

- [ ] `src/parallel/encryption/` 目录包含从 Happy 复制并爆改的加密代码
- [ ] `SocketClient.ts` 使用 `SimpleEncryption` 加密所有 RPC 通信
- [ ] `SocketServer.ts` 使用 `SimpleEncryption` 加密所有 RPC 通信
- [ ] 端到端测试：Master↔Worker 加密通信正常
- [ ] 没有明文传输敏感数据

---

## 执行顺序

1. **Phase 1**: 复制基础加密工具 → 安装 libsodium-wrappers
2. **Phase 2**: 创建 SimpleEncryption.ts
3. **Phase 3**: 修改 SocketClient.ts 添加加密
4. **Phase 4**: 修改 SocketServer.ts 添加加密
5. **Phase 5**: 更新测试验证加密通信
