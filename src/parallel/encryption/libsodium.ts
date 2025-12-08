/**
 * Libsodium 加密函数
 *
 * 爆改自 happy/sources/encryption/libsodium.ts
 * 爆改内容:
 * - 移除 expo-crypto 依赖，使用 Node.js crypto.randomBytes
 * - 导入路径调整
 */

import * as crypto from 'crypto';
import sodium, { initSodium } from './libsodium.lib';

/**
 * 获取随机字节（替代 expo-crypto.getRandomBytes）
 */
export function getRandomBytes(length: number): Uint8Array {
  return new Uint8Array(crypto.randomBytes(length));
}

/**
 * 获取 Box 公钥
 */
export function getPublicKeyForBox(secretKey: Uint8Array): Uint8Array {
  return sodium.crypto_box_seed_keypair(secretKey).publicKey;
}

/**
 * Box 加密（非对称加密）
 */
export function encryptBox(
  data: Uint8Array,
  recipientPublicKey: Uint8Array
): Uint8Array {
  const ephemeralKeyPair = sodium.crypto_box_keypair();
  const nonce = getRandomBytes(sodium.crypto_box_NONCEBYTES);
  const encrypted = sodium.crypto_box_easy(
    data,
    nonce,
    recipientPublicKey,
    ephemeralKeyPair.privateKey
  );

  // Bundle format: ephemeral public key (32 bytes) + nonce (24 bytes) + encrypted data
  const result = new Uint8Array(
    ephemeralKeyPair.publicKey.length + nonce.length + encrypted.length
  );
  result.set(ephemeralKeyPair.publicKey, 0);
  result.set(nonce, ephemeralKeyPair.publicKey.length);
  result.set(encrypted, ephemeralKeyPair.publicKey.length + nonce.length);

  return result;
}

/**
 * Box 解密（非对称解密）
 */
export function decryptBox(
  encryptedBundle: Uint8Array,
  recipientSecretKey: Uint8Array
): Uint8Array | null {
  // Extract components from bundle
  const ephemeralPublicKey = encryptedBundle.slice(
    0,
    sodium.crypto_box_PUBLICKEYBYTES
  );
  const nonce = encryptedBundle.slice(
    sodium.crypto_box_PUBLICKEYBYTES,
    sodium.crypto_box_PUBLICKEYBYTES + sodium.crypto_box_NONCEBYTES
  );
  const encrypted = encryptedBundle.slice(
    sodium.crypto_box_PUBLICKEYBYTES + sodium.crypto_box_NONCEBYTES
  );

  try {
    const decrypted = sodium.crypto_box_open_easy(
      encrypted,
      nonce,
      ephemeralPublicKey,
      recipientSecretKey
    );
    return decrypted;
  } catch {
    return null;
  }
}

/**
 * SecretBox 加密（对称加密）- Master-Worker 通信使用
 */
export function encryptSecretBox(data: unknown, secret: Uint8Array): Uint8Array {
  const nonce = getRandomBytes(sodium.crypto_secretbox_NONCEBYTES);
  const message = new TextEncoder().encode(JSON.stringify(data));
  const encrypted = sodium.crypto_secretbox_easy(message, nonce, secret);

  // Bundle format: nonce (24 bytes) + encrypted data
  const result = new Uint8Array(nonce.length + encrypted.length);
  result.set(nonce);
  result.set(encrypted, nonce.length);
  return result;
}

/**
 * SecretBox 解密（对称解密）- Master-Worker 通信使用
 */
export function decryptSecretBox(
  data: Uint8Array,
  secret: Uint8Array
): unknown | null {
  const nonce = data.slice(0, sodium.crypto_secretbox_NONCEBYTES);
  const encrypted = data.slice(sodium.crypto_secretbox_NONCEBYTES);

  try {
    const decrypted = sodium.crypto_secretbox_open_easy(encrypted, nonce, secret);
    if (!decrypted) {
      return null;
    }
    return JSON.parse(new TextDecoder().decode(decrypted));
  } catch {
    return null;
  }
}

/**
 * 生成随机密钥（32 字节）
 */
export function generateSecretKey(): Uint8Array {
  return getRandomBytes(sodium.crypto_secretbox_KEYBYTES);
}

// 重新导出 initSodium
export { initSodium };
