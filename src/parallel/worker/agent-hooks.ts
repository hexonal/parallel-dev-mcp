/**
 * Agent SDK Hooks
 * @module parallel/worker/agent-hooks
 *
 * 提供安全检查和日志记录的 Hooks
 */

import type { HookCallback, HookJSONOutput } from '@anthropic-ai/claude-agent-sdk';

/**
 * 危险命令模式列表
 */
const DANGEROUS_PATTERNS = [
  // 文件系统危险操作
  /rm\s+-rf\s+\/(?!tmp)/,
  /rm\s+-rf\s+~\//,
  /rm\s+-rf\s+\.\.\//,
  // Git 危险操作
  /git\s+push\s+--force\s+origin\s+(main|master)/,
  /git\s+reset\s+--hard\s+origin/,
  /git\s+clean\s+-fd/,
  // 数据库危险操作
  /DROP\s+DATABASE/i,
  /DROP\s+TABLE/i,
  /TRUNCATE\s+TABLE/i,
  /DELETE\s+FROM\s+\w+\s*;?\s*$/i,
  // 系统危险操作
  /chmod\s+-R\s+777/,
  /chown\s+-R\s+root/,
  // 网络危险操作
  /curl.*\|\s*(bash|sh)/,
  /wget.*\|\s*(bash|sh)/
];

/**
 * 敏感文件路径模式
 */
const SENSITIVE_PATHS = [
  /\.env$/,
  /credentials\.(json|yaml|yml)$/,
  /secrets?\.(json|yaml|yml)$/,
  /\.pem$/,
  /\.key$/,
  /id_rsa/,
  /\.ssh\//
];

/**
 * 创建 Agent Hooks
 */
export function createAgentHooks() {
  return {
    preToolUse: createPreToolUseHook(),
    postToolUse: createPostToolUseHook()
  };
}

/**
 * PreToolUse Hook - 工具使用前安全检查
 */
function createPreToolUseHook(): HookCallback {
  return async (input, toolUseID, { signal }): Promise<HookJSONOutput> => {
    // 类型检查
    if (!('hook_event_name' in input) || input.hook_event_name !== 'PreToolUse') {
      return { continue: true };
    }

    const { tool_name, tool_input } = input as {
      hook_event_name: 'PreToolUse';
      tool_name: string;
      tool_input: Record<string, unknown>;
    };

    // 1. 检查 Bash 命令
    if (tool_name === 'Bash') {
      const command = (tool_input.command as string) || '';
      const blockReason = checkDangerousCommand(command);

      if (blockReason) {
        console.warn(`[Hook] 🚫 阻止危险命令: ${command.substring(0, 100)}`);
        return {
          continue: false,
          hookSpecificOutput: {
            hookEventName: 'PreToolUse',
            permissionDecision: 'deny',
            permissionDecisionReason: blockReason
          }
        };
      }
    }

    // 2. 检查文件写入敏感路径
    if (tool_name === 'Write' || tool_name === 'Edit') {
      const filePath = (tool_input.file_path as string) || '';
      const blockReason = checkSensitivePath(filePath);

      if (blockReason) {
        console.warn(`[Hook] 🚫 阻止写入敏感文件: ${filePath}`);
        return {
          continue: false,
          hookSpecificOutput: {
            hookEventName: 'PreToolUse',
            permissionDecision: 'deny',
            permissionDecisionReason: blockReason
          }
        };
      }
    }

    // 3. 检查 Read 敏感文件
    if (tool_name === 'Read') {
      const filePath = (tool_input.file_path as string) || '';
      for (const pattern of SENSITIVE_PATHS) {
        if (pattern.test(filePath)) {
          console.warn(`[Hook] ⚠️ 读取敏感文件: ${filePath}`);
          // 允许读取但记录警告
          break;
        }
      }
    }

    return { continue: true };
  };
}

/**
 * PostToolUse Hook - 工具使用后记录
 */
function createPostToolUseHook(): HookCallback {
  return async (input, toolUseID, { signal }): Promise<HookJSONOutput> => {
    // 类型检查
    if (!('hook_event_name' in input) || input.hook_event_name !== 'PostToolUse') {
      return { continue: true };
    }

    const { tool_name, tool_input, tool_response } = input as {
      hook_event_name: 'PostToolUse';
      tool_name: string;
      tool_input: Record<string, unknown>;
      tool_response: unknown;
    };

    // 记录工具使用
    const summary = getToolSummary(tool_name, tool_input);
    console.log(`[Hook] ✅ ${tool_name}: ${summary}`);

    return { continue: true };
  };
}

/**
 * 检查危险命令
 */
function checkDangerousCommand(command: string): string | null {
  for (const pattern of DANGEROUS_PATTERNS) {
    if (pattern.test(command)) {
      return `危险命令被阻止: 匹配模式 ${pattern.toString()}`;
    }
  }
  return null;
}

/**
 * 检查敏感路径
 */
function checkSensitivePath(filePath: string): string | null {
  for (const pattern of SENSITIVE_PATHS) {
    if (pattern.test(filePath)) {
      return `禁止写入敏感文件: ${filePath}`;
    }
  }
  return null;
}

/**
 * 获取工具使用摘要
 */
function getToolSummary(toolName: string, input: Record<string, unknown>): string {
  switch (toolName) {
    case 'Read':
      return `读取 ${input.file_path}`;
    case 'Write':
      return `写入 ${input.file_path}`;
    case 'Edit':
      return `编辑 ${input.file_path}`;
    case 'Bash':
      return `执行 ${(input.command as string)?.substring(0, 50)}...`;
    case 'Grep':
      return `搜索 "${input.pattern}" in ${input.path || 'cwd'}`;
    case 'Glob':
      return `匹配 ${input.pattern}`;
    default:
      return JSON.stringify(input).substring(0, 50);
  }
}

/**
 * 导出危险模式（用于测试）
 */
export const dangerousPatterns = DANGEROUS_PATTERNS;
export const sensitivePaths = SENSITIVE_PATHS;
