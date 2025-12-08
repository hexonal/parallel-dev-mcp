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

  let prompt = `你是一个专业的 AI 助手，擅长分析产品需求文档（PRD）并生成结构化、逻辑有序、具有依赖关系和执行顺序的 JSON 格式开发任务列表。`;

  if (research) {
    prompt += `

在将 PRD 分解为任务之前，你需要：
1. 研究和分析适合该项目的最新技术、库、框架和最佳实践
2. 识别 PRD 中未明确提及的潜在技术挑战、安全问题或可扩展性问题，但不要丢弃任何明确的需求，也不要过度复杂化 - 始终提供最直接的实现路径，避免过度工程或迂回方案
3. 考虑与该项目相关的当前行业标准和发展趋势（此步骤旨在解决 LLM 幻觉和由于训练数据截止日期导致的过时信息）
4. 评估替代实现方案并推荐最有效的路径
5. 基于你的研究，包含具体的库版本、有用的 API 和具体的实现指导
6. 始终提供最直接的实现路径，避免过度工程或迂回方案

你的任务分解应结合这些研究成果，提供比单纯基于 PRD 文本更详细的实现指导、更准确的依赖映射和更精确的技术建议，同时保留所有明确的需求、最佳实践以及 PRD 的所有细节和细微差别。`;
  }

  prompt += `

分析提供的 PRD 内容并生成 ${numTasks > 0 ? `大约 ${numTasks}` : '适当数量的'} 个顶层开发任务。如果 PRD 的复杂度或详细程度较高，应相应生成更多任务。
每个任务应代表实现需求所需的逻辑工作单元，专注于最直接有效的实现方式，避免不必要的复杂性或过度工程。为每个任务包含伪代码、实现细节和测试策略。查找最新信息来实现每个任务。
从 ${nextId} 开始分配顺序 ID。仅基于 PRD 内容推断每个任务的标题、描述、详情和测试策略。
所有任务的初始状态设为 'pending'，依赖设为空数组 []，优先级设为 '${defaultTaskPriority}'。
生成一个包含单个键 "tasks" 的响应，其值为遵循提供的 schema 的任务对象数组。

每个任务应遵循以下 JSON 结构：
{
	"id": number,
	"title": string,
	"description": string,
	"status": "pending",
	"dependencies": number[] (该任务依赖的其他任务 ID),
	"priority": "high" | "medium" | "low",
	"details": string (实现细节),
	"testStrategy": string (验证方案)
}

指导原则：
1. ${numTasks > 0 ? '除非复杂度需要' : '根据复杂度'}，创建 ${numTasks > 0 ? `恰好 ${numTasks}` : '适当数量的'} 个任务，从 ${nextId} 开始顺序编号
2. 每个任务应该是原子化的，专注于单一职责，遵循最新的最佳实践和标准
3. 逻辑排序任务 - 考虑依赖关系和实现顺序
4. 前期任务应专注于设置，先实现核心功能，然后是高级功能
5. 为每个任务包含清晰的验证/测试方案
6. 设置适当的依赖 ID（一个任务只能依赖 ID 较小的任务，如果适用，可能包括 ID 小于 ${nextId} 的现有任务）
7. 根据关键性和依赖顺序分配优先级（high/medium/low）
8. 在 "details" 字段中包含详细的实现指导${research ? '，基于你的研究提供具体的库和版本建议' : ''}
9. 如果 PRD 包含对库、数据库 schema、框架、技术栈或任何其他实现细节的具体要求，必须严格遵守这些要求，在任何情况下都不要丢弃
10. 专注于填补 PRD 遗留的空白或未完全指定的领域，同时保留所有明确的需求
11. 始终提供最直接的实现路径，避免过度工程或迂回方案${research ? '\n12. 对于每个任务，基于研究发现的当前行业标准和最佳实践，提供具体、可操作的指导' : ''}`;

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
    prompt += `## 重要：需要进行代码库分析

你可以使用强大的代码库分析工具。在生成任务之前：

1. 使用 Glob 工具探索项目结构（例如 "**/*.js"、"**/*.json"、"**/README.md"）
2. 使用 Grep 工具搜索现有实现、模式和技术
3. 使用 Read 工具检查关键文件如 package.json、README.md 和主入口文件
4. 分析当前的实现状态以了解已有内容

基于你的分析：
- 识别已实现的组件/功能
- 了解使用的技术栈、框架和模式
- 生成基于现有代码库构建的任务，而不是重复工作
- 确保任务与项目当前的架构和约定保持一致

项目根目录：${projectRoot || ''}

`;
  }

  prompt += `以下是需要分解为 ${numTasks > 0 ? `大约 ${numTasks}` : '适当数量的'} 个任务的产品需求文档（PRD），ID 从 ${nextId} 开始：`;

  if (research) {
    prompt += `

请记住在任务分解之前彻底研究当前的最佳实践和技术，以提供具体、可操作的实现细节。`;
  }

  prompt += `

${prdContent}

重要：你的响应必须是一个包含 "tasks" 属性的 JSON 对象，该属性包含任务对象数组。你可以选择性地包含一个 "metadata" 对象。不要包含其他属性。`;

  return prompt;
}

export const parsePrdPrompt = {
  id: 'parse-prd',
  version: '1.0.0',
  description: '将产品需求文档解析为结构化任务',
  getSystemPrompt,
  getUserPrompt
};
