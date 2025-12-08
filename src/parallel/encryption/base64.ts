/**
 * Base64 编解码工具
 *
 * 爆改自 happy/sources/encryption/base64.ts
 * 爆改: 使用 Node.js Buffer 代替 atob/btoa
 */

export function decodeBase64(
  base64: string,
  encoding: 'base64' | 'base64url' = 'base64'
): Uint8Array {
  let normalizedBase64 = base64;

  if (encoding === 'base64url') {
    normalizedBase64 = base64.replace(/-/g, '+').replace(/_/g, '/');

    const padding = normalizedBase64.length % 4;
    if (padding) {
      normalizedBase64 += '='.repeat(4 - padding);
    }
  }

  // 使用 Node.js Buffer 代替 atob
  const buffer = Buffer.from(normalizedBase64, 'base64');
  return new Uint8Array(buffer);
}

export function encodeBase64(
  buffer: Uint8Array,
  encoding: 'base64' | 'base64url' = 'base64'
): string {
  // 使用 Node.js Buffer 代替 btoa
  const base64 = Buffer.from(buffer).toString('base64');

  if (encoding === 'base64url') {
    return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
  }

  return base64;
}
