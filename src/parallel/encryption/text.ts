/**
 * UTF-8 编解码工具
 *
 * 爆改自 happy/sources/encryption/text.ts
 * 无需修改，直接使用 TextEncoder/TextDecoder
 */

export function encodeUTF8(value: string): Uint8Array {
  return new TextEncoder().encode(value);
}

export function decodeUTF8(value: Uint8Array): string {
  return new TextDecoder().decode(value);
}

export function normalizeNFKD(value: string): string {
  return value.normalize('NFKD');
}
