# Claude Agent SDK 迁移计划

## 背景

当前项目使用 Tmux + CLI 方式执行 Claude Code 任务，官方已发布 `@anthropic-ai/claude-agent-sdk`，提供更强大的编程式接口。

---

## 一、SDK 对比

| 特性 | 当前方式 (Tmux + CLI) | Agent SDK |
|------|----------------------|-----------|
| 执行方式 | Tmux 会话 + `claude` 命令 | `query()` 函数 |
| 流式输出 | 解析 Tmux 输出 + stream-json | 原生 AsyncGenerator |
| 类型安全 | 手动解析 JSON | 完整 TypeScript 类型 |
| 错误处理 | 字符串匹配 | 结构化错误对象 |
| 工具控制 | CLI 参数 | `allowedTools` / `canUseTool()` |
| 权限模式 | CLI 参数 | `permissionMode` 配置 |
| Hooks | 无 | 原生支持 7 种事件钩子 |
| 子代理 | 无 | `agents` 配置 |
| MCP 集成 | 无 | `createSdkMcpServer()` |

---

## 二、迁移范围

### 需要修改的文件

| 文件 | 修改内容 |
|------|----------|
| `package.json` | 添加 `@anthropic-ai/claude-agent-sdk` |
| `src/parallel/worker/TaskExecutor.ts` | 重写为使用 Agent SDK |
| `src/parallel/worker/AgentExecutor.ts` | 新建：基于 Agent SDK 的执行器 |
| `src/parallel/types.ts` | 添加 Agent SDK 相关类型 |
| `src/parallel/master/WorkerPool.ts` | 适配新执行器 |

### 保留不变的文件

| 文件 | 原因 |
|------|------|
| `TmuxController.ts` | 仍用于会话隔离和日志捕获 |
| `SessionMonitor.ts` | 保留用于资源监控 |
| `tm-core/ai/ai-service.ts` | PRD 解析等功能继续使用 Anthropic API |

---

## 三、新架构设计

### 3.1 AgentExecutor 类

```typescript
// src/parallel/worker/AgentExecutor.ts
import { query, type SDKMessage, type Options } from '@anthropic-ai/claude-agent-sdk';
import type { Task, TaskResult } from '../types';

export interface AgentExecutorConfig {
  permissionMode: 'acceptEdits' | 'bypassPermissions' | 'default';
  allowedTools: string[];
  timeout: number;
  maxTurns?: number;
  model?: string;
}

export class AgentExecutor {
  private config: AgentExecutorConfig;
  private abortController: AbortController | null = null;

  constructor(config: Partial<AgentExecutorConfig> = {}) {
    this.config = {
      permissionMode: 'acceptEdits',
      allowedTools: ['Read', 'Edit', 'Write', 'Bash', 'Grep', 'Glob'],
      timeout: 600000,
      ...config
    };
  }

  async execute(task: Task, worktreePath: string): Promise<TaskResult> {
    const startTime = Date.now();
    this.abortController = new AbortController();

    try {
      const prompt = this.buildTaskPrompt(task);

      const options: Options = {
        cwd: worktreePath,
        permissionMode: this.config.permissionMode,
        allowedTools: this.config.allowedTools,
        abortController: this.abortController,
        maxTurns: this.config.maxTurns,
        model: this.config.model,
        // 加载项目 CLAUDE.md
        settingSources: ['project'],
        systemPrompt: {
          type: 'preset',
          preset: 'claude_code'
        }
      };

      const result = query({ prompt, options });
      let output = '';
      let success = false;

      for await (const message of result) {
        const processed = this.processMessage(message);
        if (processed.output) {
          output += processed.output;
        }
        if (processed.isResult) {
          success = processed.success;
          break;
        }
      }

      return {
        success,
        output,
        duration: Date.now() - startTime
      };

    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : String(error),
        duration: Date.now() - startTime
      };
    }
  }

  private buildTaskPrompt(task: Task): string {
    return `你是 ParallelDev Worker，正在执行任务。

## 任务信息
- ID: ${task.id}
- 标题: ${task.title}
- 描述: ${task.description}

## 执行要求
1. 完成任务描述中的所有需求
2. 遵循项目代码规范
3. 确保代码质量

开始执行任务。`;
  }

  private processMessage(message: SDKMessage): {
    output?: string;
    isResult: boolean;
    success: boolean;
  } {
    switch (message.type) {
      case 'result':
        return {
          output: message.subtype === 'success' ? message.result : undefined,
          isResult: true,
          success: message.subtype === 'success'
        };

      case 'assistant':
        // 提取助手消息中的文本
        const textContent = message.message.content.find(c => c.type === 'text');
        return {
          output: textContent?.type === 'text' ? textContent.text : undefined,
          isResult: false,
          success: false
        };

      default:
        return { isResult: false, success: false };
    }
  }

  async cancel(): Promise<void> {
    this.abortController?.abort();
  }
}
```

### 3.2 Hooks 集成

```typescript
// src/parallel/worker/agent-hooks.ts
import type { HookCallback, HookInput } from '@anthropic-ai/claude-agent-sdk';

/**
 * PreToolUse Hook - 工具使用前验证
 */
export const preToolUseHook: HookCallback = async (input, toolUseID, { signal }) => {
  if (input.hook_event_name !== 'PreToolUse') {
    return { continue: true };
  }

  // 阻止危险操作
  const dangerousPatterns = [
    /rm\s+-rf\s+\//,
    /git\s+push\s+--force/,
    /DROP\s+TABLE/i
  ];

  if (input.tool_name === 'Bash') {
    const command = (input.tool_input as { command?: string }).command || '';
    for (const pattern of dangerousPatterns) {
      if (pattern.test(command)) {
        return {
          continue: false,
          hookSpecificOutput: {
            hookEventName: 'PreToolUse',
            permissionDecision: 'deny',
            permissionDecisionReason: `危险命令被阻止: ${command}`
          }
        };
      }
    }
  }

  return { continue: true };
};

/**
 * PostToolUse Hook - 工具使用后记录
 */
export const postToolUseHook: HookCallback = async (input, toolUseID, { signal }) => {
  if (input.hook_event_name !== 'PostToolUse') {
    return { continue: true };
  }

  // 记录工具使用情况
  console.log(`[Hook] Tool used: ${input.tool_name}`);

  return { continue: true };
};
```

### 3.3 与 WorkerPool 集成

```typescript
// src/parallel/master/WorkerPool.ts 修改
import { AgentExecutor } from '../worker/AgentExecutor';

export class WorkerPool {
  private executor: AgentExecutor;

  constructor(config: WorkerPoolConfig) {
    // ...existing code...

    this.executor = new AgentExecutor({
      permissionMode: 'acceptEdits',
      allowedTools: config.allowedTools,
      timeout: config.taskTimeout
    });
  }

  async executeTask(workerId: string, task: Task): Promise<TaskResult> {
    const worker = this.workers.get(workerId);
    if (!worker) {
      throw new Error(`Worker ${workerId} not found`);
    }

    // 使用 AgentExecutor 代替 TaskExecutor
    return this.executor.execute(task, worker.worktreePath);
  }
}
```

---

## 四、实施步骤

### Phase 1: 添加依赖 (5 分钟)
```bash
npm install @anthropic-ai/claude-agent-sdk
```

### Phase 2: 创建 AgentExecutor (30 分钟)
1. 创建 `src/parallel/worker/AgentExecutor.ts`
2. 实现基于 `query()` 的任务执行
3. 实现消息处理和结果提取

### Phase 3: 创建 Hooks (15 分钟)
1. 创建 `src/parallel/worker/agent-hooks.ts`
2. 实现 PreToolUse 安全检查
3. 实现 PostToolUse 日志记录

### Phase 4: 集成到 Worker 系统 (20 分钟)
1. 修改 `WorkerPool.ts` 使用 AgentExecutor
2. 保留 TaskExecutor 作为备选方案
3. 添加配置切换选项

### Phase 5: 测试验证 (30 分钟)
1. 单元测试 AgentExecutor
2. 集成测试 Worker 执行流程
3. 端到端测试任务完成

---

## 五、回退方案

如果 Agent SDK 遇到问题，保留现有 TaskExecutor：

```typescript
// src/parallel/types.ts
export type ExecutorType = 'agent-sdk' | 'tmux-cli';

// src/parallel/config.ts
export const DEFAULT_CONFIG = {
  executor: 'agent-sdk' as ExecutorType,
  fallbackToTmux: true
};
```

---

## 六、依赖版本

```json
{
  "dependencies": {
    "@anthropic-ai/claude-agent-sdk": "^0.1.61",
    "@anthropic-ai/sdk": "^0.71.2"
  }
}
```

**注意**: 移除 `@anthropic-ai/claude-code`，因为 `claude-agent-sdk` 已包含其功能。

---

## 七、预期收益

1. **代码简化**: 移除 Tmux 输出解析逻辑
2. **类型安全**: 完整 TypeScript 支持
3. **更好的错误处理**: 结构化错误对象
4. **Hooks 支持**: 安全检查、日志记录
5. **子代理**: 未来可支持任务分解
6. **MCP 集成**: 可扩展工具能力
