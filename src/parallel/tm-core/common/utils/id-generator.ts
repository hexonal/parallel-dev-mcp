/**
 * ID 生成工具
 * 爆改自 claude-task-master/packages/tm-core/src/common/utils/id-generator.ts
 */

import { randomBytes } from 'node:crypto';

/**
 * 生成唯一任务 ID，格式：TASK-{timestamp}-{random}
 */
export function generateTaskId(): string {
  const timestamp = Date.now();
  const random = generateRandomString(4);
  return `TASK-${timestamp}-${random}`;
}

/**
 * 生成子任务 ID，格式：{parentId}.{sequential}
 */
export function generateSubtaskId(
  parentId: string,
  existingSubtasks: string[] = []
): string {
  const parentSubtasks = existingSubtasks.filter((id) =>
    id.startsWith(`${parentId}.`)
  );

  const sequentialNumbers = parentSubtasks
    .map((id) => {
      const parts = id.split('.');
      const lastPart = parts[parts.length - 1];
      return Number.parseInt(lastPart, 10);
    })
    .filter((num) => !Number.isNaN(num))
    .sort((a, b) => a - b);

  const nextSequential =
    sequentialNumbers.length > 0 ? Math.max(...sequentialNumbers) + 1 : 1;

  return `${parentId}.${nextSequential}`;
}

/**
 * 生成随机字符串
 */
function generateRandomString(length: number): string {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  const bytes = randomBytes(length);
  let result = '';

  for (let i = 0; i < length; i++) {
    result += chars[bytes[i] % chars.length];
  }

  return result;
}

/**
 * 验证任务 ID 格式
 */
export function isValidTaskId(id: string): boolean {
  const taskIdRegex = /^TASK-\d{13}-[A-Z0-9]{4}$/;
  return taskIdRegex.test(id);
}

/**
 * 验证子任务 ID 格式
 */
export function isValidSubtaskId(id: string): boolean {
  const parts = id.split('.');
  if (parts.length < 2) return false;

  const taskIdPart = parts[0];
  if (!isValidTaskId(taskIdPart)) return false;

  const sequentialParts = parts.slice(1);
  return sequentialParts.every((part) => {
    const num = Number.parseInt(part, 10);
    return !Number.isNaN(num) && num > 0 && part === num.toString();
  });
}

/**
 * 从子任务 ID 提取父任务 ID
 */
export function getParentTaskId(subtaskId: string): string | null {
  if (!isValidSubtaskId(subtaskId)) return null;
  const parts = subtaskId.split('.');
  return parts[0];
}

/**
 * 规范化显示 ID
 * 处理多种输入格式：
 * - "ham31" → "HAM-31"
 * - "HAM31" → "HAM-31"
 * - "ham-31" → "HAM-31"
 * - "31" → "31"
 */
export function normalizeDisplayId(id: string): string {
  if (!id) return id;

  const trimmed = id.trim();

  // 模式：3字母 + 数字（无连字符）
  const noHyphenPattern = /^([a-zA-Z]{3})(\d+)$/;
  const noHyphenMatch = trimmed.match(noHyphenPattern);
  if (noHyphenMatch) {
    const prefix = noHyphenMatch[1].toUpperCase();
    const number = noHyphenMatch[2];
    return `${prefix}-${number}`;
  }

  // 模式：3字母 + 连字符 + 数字
  const withHyphenPattern = /^([a-zA-Z]{3})-(\d+)$/;
  const withHyphenMatch = trimmed.match(withHyphenPattern);
  if (withHyphenMatch) {
    const prefix = withHyphenMatch[1].toUpperCase();
    const number = withHyphenMatch[2];
    return `${prefix}-${number}`;
  }

  // 子任务格式：ham31.1, HAM-31.1
  const subtaskNoHyphenPattern = /^([a-zA-Z]{3})(\d+)\.(\d+)$/;
  const subtaskNoHyphenMatch = trimmed.match(subtaskNoHyphenPattern);
  if (subtaskNoHyphenMatch) {
    const prefix = subtaskNoHyphenMatch[1].toUpperCase();
    const taskNum = subtaskNoHyphenMatch[2];
    const subtaskNum = subtaskNoHyphenMatch[3];
    return `${prefix}-${taskNum}.${subtaskNum}`;
  }

  const subtaskWithHyphenPattern = /^([a-zA-Z]{3})-(\d+)\.(\d+)$/;
  const subtaskWithHyphenMatch = trimmed.match(subtaskWithHyphenPattern);
  if (subtaskWithHyphenMatch) {
    const prefix = subtaskWithHyphenMatch[1].toUpperCase();
    const taskNum = subtaskWithHyphenMatch[2];
    const subtaskNum = subtaskWithHyphenMatch[3];
    return `${prefix}-${taskNum}.${subtaskNum}`;
  }

  return trimmed;
}
