/**
 * 任务展开 Prompt 模板
 * @module tm-core/prompts/expand-task
 *
 * 严格遵守 ParallelDev Skills 规则：
 * - typescript-development: TypeScript 严格模式开发规范
 * - quality-assurance: 代码质量保证标准
 * - parallel-executor: 并行执行器生命周期
 */

import type { Task } from '../common/types';

export interface ExpandTaskParams {
  task: Task;
  subtaskCount: number;
  nextSubtaskId: number;
  additionalContext?: string;
  complexityReasoningContext?: string;
  gatheredContext?: string;
  useResearch?: boolean;
  expansionPrompt?: string;
  hasCodebaseAnalysis?: boolean;
  projectRoot?: string;
}

/**
 * TypeScript Skill 强制规则
 */
const TYPESCRIPT_SKILL_RULES = `
## TypeScript 开发强制规则（必须遵守）

### 🔴 类型安全
- 禁止使用 \`any\` 类型，使用 \`unknown\` 或具体类型
- 所有函数必须有明确的返回类型
- 使用 Zod 进行运行时验证

### 🔴 函数长度
- 所有函数不得超过 50 行（包含注释和空行）
- 超长函数必须拆分为多个私有函数

### 🔴 注释规范
- 禁止行尾注释，所有注释必须独立成行
- 所有公共 API 必须有 JSDoc 注释
- 复杂逻辑必须有步骤注释（如 \`// 1. 初始化参数\`）

### 🔴 命名规范
- 接口/类型: PascalCase（如 \`Task\`, \`TaskResult\`）
- 函数/变量: camelCase（如 \`executeTask\`, \`isReady\`）
- 常量: UPPER_SNAKE_CASE（如 \`MAX_WORKERS\`）

### 🔴 错误处理
- 所有异步操作必须有 try-catch
- 错误消息必须清晰描述问题
- 失败时必须清理资源
`;

/**
 * 质量保证 Skill 规则
 */
const QUALITY_ASSURANCE_RULES = `
## 质量保证检查清单（每个子任务必须考虑）

### 提交前检查
- [ ] \`tsc --noEmit\` 类型检查通过
- [ ] \`eslint src\` 无错误
- [ ] 测试覆盖率 > 80%
- [ ] 无未处理的 TODO

### 禁止清单
- ❌ \`any\` 类型
- ❌ 行尾注释
- ❌ 函数超过 50 行
- ❌ 未处理的 Promise
- ❌ 没有 JSDoc 的公共 API
`;

/**
 * 生成任务展开的 system prompt
 */
export function getSystemPrompt(params: ExpandTaskParams): string {
  const { subtaskCount, nextSubtaskId, useResearch, expansionPrompt } = params;

  let prompt = `你是一个专业的 AI 助手，擅长将开发任务分解为详细、可执行的子任务。

你必须严格遵守 ParallelDev Skills 定义的开发规范。`;

  if (useResearch) {
    prompt += `

在将任务分解为子任务之前，你需要：
1. 研究当前该类型实现的最佳实践、设计模式和常见方法
2. 考虑潜在的边界情况、错误处理和测试需求
3. 识别需要处理的依赖项或前置条件
4. 基于行业标准推荐具体的实现方案`;
  }

  if (expansionPrompt) {
    prompt += `

复杂度分析指南：
${expansionPrompt}`;
  }

  prompt += `

${TYPESCRIPT_SKILL_RULES}

${QUALITY_ASSURANCE_RULES}

---

## 子任务生成要求

为给定任务生成恰好 ${subtaskCount} 个子任务。每个子任务应该：
1. 原子化且专注于单一功能点
2. 有清晰、具体的标题描述需要完成的工作
3. 在描述中包含详细的实现指导，**必须遵守上述 TypeScript 规范**
4. 适当设置对其他子任务的依赖关系（如有）
5. 从 ${nextSubtaskId} 开始顺序编号

每个子任务应遵循以下 JSON 结构：
{
  "id": number,
  "title": string,
  "description": string,
  "status": "pending",
  "dependencies": number[] (该子任务依赖的其他子任务 ID)
}

指导原则：
1. 将任务分解为逻辑清晰、可实现的单元
2. 考虑实现顺序 - 前面的子任务应该是后面子任务的前置条件
3. 根据需要包含设置、核心实现、测试和清理等子任务
4. 尽可能使每个子任务的工作量相当
5. 确保所有子任务覆盖父任务的全部内容
6. **每个子任务的描述中必须包含如何遵守 TypeScript 规范的指导**`;

  return prompt;
}

/**
 * 生成任务展开的 user prompt
 */
export function getUserPrompt(params: ExpandTaskParams): string {
  const {
    task,
    subtaskCount,
    nextSubtaskId,
    additionalContext,
    complexityReasoningContext,
    gatheredContext,
    useResearch,
    hasCodebaseAnalysis,
    projectRoot
  } = params;

  let prompt = '';

  if (hasCodebaseAnalysis) {
    prompt += `## 代码库上下文

你可以访问代码库。在分解任务时，请考虑现有的代码结构和模式。

项目根目录：${projectRoot || ''}

`;
  }

  prompt += `## 待展开的任务

ID：${task.id}
标题：${task.title}
描述：${task.description}
${task.details ? `详情：${task.details}` : ''}
${task.testStrategy ? `测试策略：${task.testStrategy}` : ''}
优先级：${task.priority}
状态：${task.status}
依赖：${JSON.stringify(task.dependencies || [])}`;

  if (additionalContext) {
    prompt += `

## 附加上下文
${additionalContext}`;
  }

  if (complexityReasoningContext) {
    prompt += `

## 复杂度分析
${complexityReasoningContext}`;
  }

  if (gatheredContext) {
    prompt += `

## 项目上下文
${gatheredContext}`;
  }

  if (useResearch) {
    prompt += `

请记住研究并结合当前该类型实现的最佳实践。`;
  }

  prompt += `

---

## 重要提醒

1. 将此任务分解为恰好 ${subtaskCount} 个子任务，ID 从 ${nextSubtaskId} 开始
2. **严格遵守 TypeScript Skill 规则**（禁止 any、函数 < 50 行、必须 JSDoc）
3. **每个子任务必须包含质量保证检查点**
4. 响应必须是包含 "subtasks" 属性的 JSON 对象

示例子任务描述格式：
\`\`\`
实现用户认证模块。

实现要求：
- 使用 Zod 定义 UserCredentials schema
- 函数拆分：validateCredentials(), hashPassword(), createSession()
- 每个函数不超过 50 行
- 所有公共 API 添加 JSDoc

质量检查：
- [ ] tsc --noEmit 通过
- [ ] 无 any 类型
- [ ] 测试覆盖率 > 80%
\`\`\``;

  return prompt;
}

export const expandTaskPrompt = {
  id: 'expand-task',
  version: '2.0.0',
  description: '将任务展开为详细的子任务（遵守 ParallelDev Skills 规范）',
  getSystemPrompt,
  getUserPrompt
};
