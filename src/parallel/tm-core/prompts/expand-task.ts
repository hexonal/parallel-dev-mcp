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

  let prompt = `You are an AI assistant specialized in breaking down development tasks into detailed, actionable subtasks.`;

  if (useResearch) {
    prompt += `

Before breaking down the task into subtasks, you will:
1. Research current best practices, patterns, and common approaches for this type of implementation
2. Consider potential edge cases, error handling, and testing requirements
3. Identify any dependencies or prerequisites that should be addressed
4. Recommend specific implementation approaches based on industry standards`;
  }

  if (expansionPrompt) {
    prompt += `

COMPLEXITY ANALYSIS GUIDANCE:
${expansionPrompt}`;
  }

  prompt += `

Generate exactly ${subtaskCount} subtasks for the given task. Each subtask should:
1. Be atomic and focused on a single piece of functionality
2. Have a clear, specific title describing what needs to be done
3. Include detailed implementation guidance in the description
4. Have appropriate dependencies on other subtasks (if any)
5. Be numbered sequentially starting from ${nextSubtaskId}

Each subtask should follow this JSON structure:
{
  "id": number,
  "title": string,
  "description": string,
  "status": "pending",
  "dependencies": number[] (IDs of subtasks this depends on)
}

Guidelines:
1. Break down the task into logical, implementable units
2. Consider the implementation order - earlier subtasks should be prerequisites
3. Include setup, core implementation, testing, and cleanup subtasks as appropriate
4. Each subtask should take roughly equal effort when possible
5. Ensure all aspects of the parent task are covered by the subtasks`;

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
    prompt += `## CODEBASE CONTEXT

You have access to the codebase. Consider the existing code structure and patterns when breaking down this task.

Project Root: ${projectRoot || ''}

`;
  }

  prompt += `## TASK TO EXPAND

ID: ${task.id}
Title: ${task.title}
Description: ${task.description}
${task.details ? `Details: ${task.details}` : ''}
${task.testStrategy ? `Test Strategy: ${task.testStrategy}` : ''}
Priority: ${task.priority}
Status: ${task.status}
Dependencies: ${JSON.stringify(task.dependencies || [])}`;

  if (additionalContext) {
    prompt += `

## ADDITIONAL CONTEXT
${additionalContext}`;
  }

  if (complexityReasoningContext) {
    prompt += `

## COMPLEXITY ANALYSIS
${complexityReasoningContext}`;
  }

  if (gatheredContext) {
    prompt += `

## PROJECT CONTEXT
${gatheredContext}`;
  }

  if (useResearch) {
    prompt += `

Remember to research and incorporate current best practices for this type of implementation.`;
  }

  prompt += `

Break this task into exactly ${subtaskCount} subtasks, starting IDs from ${nextSubtaskId}.

IMPORTANT: Your response must be a JSON object with a "subtasks" property containing an array of subtask objects. Do not include any other properties.`;

  return prompt;
}

export const expandTaskPrompt = {
  id: 'expand-task',
  version: '1.0.0',
  description: 'Expand a task into detailed subtasks',
  getSystemPrompt,
  getUserPrompt
};
