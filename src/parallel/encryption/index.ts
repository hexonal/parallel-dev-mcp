/**
 * 加密模块导出
 *
 * 爆改自 Happy 加密系统，专为 ParallelDev Master-Worker 通信设计
 */

// 主加密类
export { SimpleEncryption, generateSecretKey, initSodium } from './SimpleEncryption';

// 底层加密函数
export {
  encryptSecretBox,
  decryptSecretBox,
  encryptBox,
  decryptBox,
  getRandomBytes,
} from './libsodium';

// 编解码工具
export { encodeBase64, decodeBase64 } from './base64';
export { encodeUTF8, decodeUTF8 } from './text';
