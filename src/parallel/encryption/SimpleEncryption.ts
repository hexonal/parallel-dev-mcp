/**
 * 简化版加密类
 *
 * 爆改自 Happy 的 Encryption 类，专为 ParallelDev Master-Worker 通信设计
 *
 * 简化内容：
 * - 只保留 SecretBox 对称加密（Master-Worker 使用共享密钥）
 * - 移除 Session/Machine 概念
 * - 移除 AES256 相关代码（依赖 rn-encryption）
 *
 * 使用方式：
 * 1. Master 启动时生成密钥：const key = generateSecretKey()
 * 2. Master 将密钥传递给 Worker（通过启动参数或初始握手）
 * 3. 双方使用相同密钥进行加密通信
 */

import {
  encryptSecretBox,
  decryptSecretBox,
  generateSecretKey,
  initSodium,
} from './libsodium';
import { encodeBase64, decodeBase64 } from './base64';

export class SimpleEncryption {
  private secretKey: Uint8Array;
  private initialized: boolean = false;

  /**
   * 创建加密实例
   * @param secretKey 32 字节共享密钥
   */
  constructor(secretKey: Uint8Array) {
    if (secretKey.length !== 32) {
      throw new Error('Secret key must be 32 bytes');
    }
    this.secretKey = secretKey;
  }

  /**
   * 初始化 libsodium（必须在使用加密功能前调用）
   */
  async init(): Promise<void> {
    if (!this.initialized) {
      await initSodium();
      this.initialized = true;
    }
  }

  /**
   * 加密任意数据
   * @param data 要加密的数据（会被 JSON 序列化）
   * @returns Base64 编码的加密数据
   */
  async encryptRaw(data: unknown): Promise<string> {
    await this.init();
    const encrypted = encryptSecretBox(data, this.secretKey);
    return encodeBase64(encrypted, 'base64');
  }

  /**
   * 解密数据
   * @param encrypted Base64 编码的加密数据
   * @returns 解密后的数据，失败返回 null
   */
  async decryptRaw(encrypted: string): Promise<unknown | null> {
    await this.init();
    try {
      const data = decodeBase64(encrypted, 'base64');
      return decryptSecretBox(data, this.secretKey);
    } catch {
      return null;
    }
  }

  /**
   * 获取密钥的 Base64 表示（用于传递给 Worker）
   */
  getKeyBase64(): string {
    return encodeBase64(this.secretKey, 'base64');
  }

  /**
   * 从 Base64 字符串创建加密实例
   */
  static fromBase64(keyBase64: string): SimpleEncryption {
    const key = decodeBase64(keyBase64, 'base64');
    return new SimpleEncryption(key);
  }

  /**
   * 生成新的随机密钥并创建加密实例
   */
  static async generate(): Promise<SimpleEncryption> {
    await initSodium();
    const key = generateSecretKey();
    return new SimpleEncryption(key);
  }
}

// 重新导出工具函数
export { generateSecretKey, initSodium };
