/**
 * Libsodium 库封装
 *
 * 爆改自 happy/sources/encryption/libsodium.lib.ts
 * 原始: import sodium from '@more-tech/react-native-libsodium'
 * 爆改: 使用 libsodium-wrappers (Node.js 版本)
 */

import sodium from 'libsodium-wrappers';

// 导出初始化函数，确保 libsodium 已准备好
export async function initSodium(): Promise<typeof sodium> {
  await sodium.ready;
  return sodium;
}

// 导出 sodium 实例（使用前需要先调用 initSodium）
export default sodium;
