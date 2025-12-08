/**
 * PRD 解析 Prompt 模板
 * @module tm-core/prompts/parse-prd
 */

export interface ParsePrdParams {
  numTasks: number;
  nextId: number;
  prdContent: string;
  prdPath: string;
  research?: boolean;
  defaultTaskPriority?: 'high' | 'medium' | 'low';
  hasCodebaseAnalysis?: boolean;
  projectRoot?: string;
}

/**
 * 生成 PRD 解析的 system prompt
 */
export function getSystemPrompt(params: ParsePrdParams): string {
  const { numTasks, nextId, research, defaultTaskPriority = 'medium' } = params;

  let prompt = `You are an AI assistant specialized in analyzing Product Requirements Documents (PRDs) and generating a structured, logically ordered, dependency-aware and sequenced list of development tasks in JSON format.`;

  if (research) {
    prompt += `
Before breaking down the PRD into tasks, you will:
1. Research and analyze the latest technologies, libraries, frameworks, and best practices that would be appropriate for this project
2. Identify any potential technical challenges, security concerns, or scalability issues not explicitly mentioned in the PRD without discarding any explicit requirements or going overboard with complexity -- always aim to provide the most direct path to implementation, avoiding over-engineering or roundabout approaches
3. Consider current industry standards and evolving trends relevant to this project (this step aims to solve LLM hallucinations and out of date information due to training data cutoff dates)
4. Evaluate alternative implementation approaches and recommend the most efficient path
5. Include specific library versions, helpful APIs, and concrete implementation guidance based on your research
6. Always aim to provide the most direct path to implementation, avoiding over-engineering or roundabout approaches

Your task breakdown should incorporate this research, resulting in more detailed implementation guidance, more accurate dependency mapping, and more precise technology recommendations than would be possible from the PRD text alone, while maintaining all explicit requirements and best practices and all details and nuances of the PRD.`;
  }

  prompt += `

Analyze the provided PRD content and generate ${numTasks > 0 ? `approximately ${numTasks}` : 'an appropriate number of'} top-level development tasks. If the complexity or the level of detail of the PRD is high, generate more tasks relative to the complexity of the PRD
Each task should represent a logical unit of work needed to implement the requirements and focus on the most direct and effective way to implement the requirements without unnecessary complexity or overengineering. Include pseudo-code, implementation details, and test strategy for each task. Find the most up to date information to implement each task.
Assign sequential IDs starting from ${nextId}. Infer title, description, details, and test strategy for each task based *only* on the PRD content.
Set status to 'pending', dependencies to an empty array [], and priority to '${defaultTaskPriority}' initially for all tasks.
Generate a response containing a single key "tasks", where the value is an array of task objects adhering to the provided schema.

Each task should follow this JSON structure:
{
	"id": number,
	"title": string,
	"description": string,
	"status": "pending",
	"dependencies": number[] (IDs of tasks this depends on),
	"priority": "high" | "medium" | "low",
	"details": string (implementation details),
	"testStrategy": string (validation approach)
}

Guidelines:
1. ${numTasks > 0 ? 'Unless complexity warrants otherwise' : 'Depending on the complexity'}, create ${numTasks > 0 ? `exactly ${numTasks}` : 'an appropriate number of'} tasks, numbered sequentially starting from ${nextId}
2. Each task should be atomic and focused on a single responsibility following the most up to date best practices and standards
3. Order tasks logically - consider dependencies and implementation sequence
4. Early tasks should focus on setup, core functionality first, then advanced features
5. Include clear validation/testing approach for each task
6. Set appropriate dependency IDs (a task can only depend on tasks with lower IDs, potentially including existing tasks with IDs less than ${nextId} if applicable)
7. Assign priority (high/medium/low) based on criticality and dependency order
8. Include detailed implementation guidance in the "details" field${research ? ', with specific libraries and version recommendations based on your research' : ''}
9. If the PRD contains specific requirements for libraries, database schemas, frameworks, tech stacks, or any other implementation details, STRICTLY ADHERE to these requirements in your task breakdown and do not discard them under any circumstance
10. Focus on filling in any gaps left by the PRD or areas that aren't fully specified, while preserving all explicit requirements
11. Always aim to provide the most direct path to implementation, avoiding over-engineering or roundabout approaches${research ? '\n12. For each task, include specific, actionable guidance based on current industry standards and best practices discovered through research' : ''}`;

  return prompt;
}

/**
 * 生成 PRD 解析的 user prompt
 */
export function getUserPrompt(params: ParsePrdParams): string {
  const {
    numTasks,
    nextId,
    prdContent,
    research,
    hasCodebaseAnalysis,
    projectRoot
  } = params;

  let prompt = '';

  if (hasCodebaseAnalysis) {
    prompt += `## IMPORTANT: Codebase Analysis Required

You have access to powerful codebase analysis tools. Before generating tasks:

1. Use the Glob tool to explore the project structure (e.g., "**/*.js", "**/*.json", "**/README.md")
2. Use the Grep tool to search for existing implementations, patterns, and technologies
3. Use the Read tool to examine key files like package.json, README.md, and main entry points
4. Analyze the current state of implementation to understand what already exists

Based on your analysis:
- Identify what components/features are already implemented
- Understand the technology stack, frameworks, and patterns in use
- Generate tasks that build upon the existing codebase rather than duplicating work
- Ensure tasks align with the project's current architecture and conventions

Project Root: ${projectRoot || ''}

`;
  }

  prompt += `Here's the Product Requirements Document (PRD) to break down into ${numTasks > 0 ? `approximately ${numTasks}` : 'an appropriate number of'} tasks, starting IDs from ${nextId}:`;

  if (research) {
    prompt += `

Remember to thoroughly research current best practices and technologies before task breakdown to provide specific, actionable implementation details.`;
  }

  prompt += `

${prdContent}

IMPORTANT: Your response must be a JSON object with a "tasks" property containing an array of task objects. You may optionally include a "metadata" object. Do not include any other properties.`;

  return prompt;
}

export const parsePrdPrompt = {
  id: 'parse-prd',
  version: '1.0.0',
  description: 'Parse a Product Requirements Document into structured tasks',
  getSystemPrompt,
  getUserPrompt
};
