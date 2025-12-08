/**
 * 任务展开 Prompt 模板
 * @module tm-core/prompts/expand-task
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
 * 生成任务展开的 system prompt
 */
export function getSystemPrompt(params: ExpandTaskParams): string {
  const { subtaskCount, nextSubtaskId, useResearch, expansionPrompt } = params;

  let prompt = `你是一个专业的 AI 助手，擅长将开发任务分解为详细、可执行的子任务。`;

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

为给定任务生成恰好 ${subtaskCount} 个子任务。每个子任务应该：
1. 原子化且专注于单一功能点
2. 有清晰、具体的标题描述需要完成的工作
3. 在描述中包含详细的实现指导
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
5. 确保所有子任务覆盖父任务的全部内容`;

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

将此任务分解为恰好 ${subtaskCount} 个子任务，ID 从 ${nextSubtaskId} 开始。

重要：你的响应必须是一个包含 "subtasks" 属性的 JSON 对象，该属性包含子任务对象数组。不要包含其他属性。`;

  return prompt;
}

export const expandTaskPrompt = {
  id: 'expand-task',
  version: '1.0.0',
  description: '将任务展开为详细的子任务',
  getSystemPrompt,
  getUserPrompt
};
