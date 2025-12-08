/**
 * 加密模块测试
 *
 * 测试从 Happy 爆改的加密功能
 */

import {
  SimpleEncryption,
  generateSecretKey,
  initSodium,
  encryptSecretBox,
  decryptSecretBox,
  encodeBase64,
  decodeBase64,
} from '../encryption';

describe('Encryption Module (爆改自 Happy)', () => {
  // 在所有测试前初始化 libsodium
  beforeAll(async () => {
    await initSodium();
  });

  describe('Base64 编解码', () => {
    it('应该正确编码和解码 Base64', () => {
      const original = new Uint8Array([1, 2, 3, 4, 5]);
      const encoded = encodeBase64(original);
      const decoded = decodeBase64(encoded);

      expect(decoded).toEqual(original);
    });

    it('应该支持 Base64URL 编码', () => {
      const original = new Uint8Array([255, 254, 253]);
      const encoded = encodeBase64(original, 'base64url');
      const decoded = decodeBase64(encoded, 'base64url');

      expect(decoded).toEqual(original);
      // Base64URL 不应包含 +, /, =
      expect(encoded).not.toContain('+');
      expect(encoded).not.toContain('/');
      expect(encoded).not.toContain('=');
    });
  });

  describe('SecretBox 加密', () => {
    it('应该正确加密和解密数据', () => {
      const key = generateSecretKey();
      const data = { message: 'Hello, World!', number: 42 };

      const encrypted = encryptSecretBox(data, key);
      const decrypted = decryptSecretBox(encrypted, key);

      expect(decrypted).toEqual(data);
    });

    it('应该使用不同密钥无法解密', () => {
      const key1 = generateSecretKey();
      const key2 = generateSecretKey();
      const data = { secret: 'password' };

      const encrypted = encryptSecretBox(data, key1);
      const decrypted = decryptSecretBox(encrypted, key2);

      expect(decrypted).toBeNull();
    });

    it('应该正确处理复杂数据结构', () => {
      const key = generateSecretKey();
      const data = {
        string: 'test',
        number: 123,
        boolean: true,
        array: [1, 2, 3],
        nested: { a: 1, b: 2 },
        nullValue: null,
      };

      const encrypted = encryptSecretBox(data, key);
      const decrypted = decryptSecretBox(encrypted, key);

      expect(decrypted).toEqual(data);
    });
  });

  describe('SimpleEncryption 类', () => {
    it('应该正确创建实例', () => {
      const key = generateSecretKey();
      const encryption = new SimpleEncryption(key);

      expect(encryption).toBeInstanceOf(SimpleEncryption);
    });

    it('应该在密钥长度错误时抛出异常', () => {
      const shortKey = new Uint8Array(16);

      expect(() => new SimpleEncryption(shortKey)).toThrow('Secret key must be 32 bytes');
    });

    it('应该正确加密和解密', async () => {
      const encryption = await SimpleEncryption.generate();
      const data = { task: 'test', id: 123 };

      const encrypted = await encryption.encryptRaw(data);
      const decrypted = await encryption.decryptRaw(encrypted);

      expect(decrypted).toEqual(data);
    });

    it('应该正确导出和导入密钥', async () => {
      const encryption1 = await SimpleEncryption.generate();
      const keyBase64 = encryption1.getKeyBase64();

      const encryption2 = SimpleEncryption.fromBase64(keyBase64);
      const data = { shared: 'secret' };

      const encrypted = await encryption1.encryptRaw(data);
      const decrypted = await encryption2.decryptRaw(encrypted);

      expect(decrypted).toEqual(data);
    });

    it('应该使用不同密钥无法解密', async () => {
      const encryption1 = await SimpleEncryption.generate();
      const encryption2 = await SimpleEncryption.generate();
      const data = { private: 'data' };

      const encrypted = await encryption1.encryptRaw(data);
      const decrypted = await encryption2.decryptRaw(encrypted);

      expect(decrypted).toBeNull();
    });
  });

  describe('生成密钥', () => {
    it('应该生成 32 字节密钥', () => {
      const key = generateSecretKey();

      expect(key.length).toBe(32);
    });

    it('应该每次生成不同的密钥', () => {
      const key1 = generateSecretKey();
      const key2 = generateSecretKey();

      expect(key1).not.toEqual(key2);
    });
  });
});

describe('加密通信集成测试', () => {
  // 在所有测试前初始化 libsodium
  beforeAll(async () => {
    await initSodium();
  });

  it('应该支持 Master-Worker 共享密钥场景', async () => {
    // 模拟 Master 生成密钥
    const masterEncryption = await SimpleEncryption.generate();
    const keyBase64 = masterEncryption.getKeyBase64();

    // 模拟 Worker 接收密钥
    const workerEncryption = SimpleEncryption.fromBase64(keyBase64);

    // Master 发送加密任务到 Worker
    const task = {
      id: 'task-001',
      command: 'execute',
      params: { file: 'src/index.ts' },
    };
    const encryptedTask = await masterEncryption.encryptRaw(task);

    // Worker 解密任务
    const decryptedTask = await workerEncryption.decryptRaw(encryptedTask);
    expect(decryptedTask).toEqual(task);

    // Worker 发送加密结果到 Master
    const result = {
      taskId: 'task-001',
      status: 'completed',
      output: 'Success',
    };
    const encryptedResult = await workerEncryption.encryptRaw(result);

    // Master 解密结果
    const decryptedResult = await masterEncryption.decryptRaw(encryptedResult);
    expect(decryptedResult).toEqual(result);
  });

  it('应该正确处理 RPC 请求/响应加密', async () => {
    const encryption = await SimpleEncryption.generate();

    // 模拟 RPC 请求
    const request = {
      id: 'req-001',
      method: 'worker-001:execute',
      params: { taskId: 'task-001', command: 'build' },
      timestamp: Date.now(),
    };

    // 只加密 params
    const encryptedParams = await encryption.encryptRaw(request.params);
    const encryptedRequest = { ...request, params: encryptedParams };

    // 解密 params
    const decryptedParams = await encryption.decryptRaw(String(encryptedRequest.params));
    expect(decryptedParams).toEqual(request.params);

    // 模拟 RPC 响应
    const response = {
      id: 'req-001',
      result: { status: 'success', data: [1, 2, 3] },
      timestamp: Date.now(),
    };

    // 加密 result
    const encryptedResult = await encryption.encryptRaw(response.result);
    const encryptedResponse = { ...response, result: encryptedResult };

    // 解密 result
    const decryptedResult = await encryption.decryptRaw(String(encryptedResponse.result));
    expect(decryptedResult).toEqual(response.result);
  });
});
