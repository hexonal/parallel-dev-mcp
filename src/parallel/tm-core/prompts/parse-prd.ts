/**
 * PRD 解析 Prompt 模板
 * @module tm-core/prompts/parse-prd
 *
 * 严格遵守 ParallelDev Skills 规则：
 * - typescript-development: TypeScript 严格模式开发规范
 * - quality-assurance: 代码质量保证标准
 * - parallel-executor: 并行执行器生命周期
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
 * TypeScript Skill 强制规则
 */
const TYPESCRIPT_SKILL_RULES = `
## TypeScript 开发强制规则（生成的任务必须遵守）

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
- 复杂逻辑必须有步骤注释

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
## 质量保证标准（每个任务必须包含验证方案）

### 质量门禁
所有任务完成前必须通过：
1. \`tsc --noEmit\` 类型检查
2. \`eslint src\` 代码规范
3. 单元测试（覆盖率 > 80%）

### 禁止清单
- ❌ \`any\` 类型
- ❌ 行尾注释
- ❌ 函数超过 50 行
- ❌ 未处理的 Promise
- ❌ 没有 JSDoc 的公共 API
`;

/**
 * 边界控制规则（YAGNI + 测试简洁性）
 */
const BOUNDARY_CONTROL_RULES = `
## 🚨 边界控制规则（严格遵守）

### 🔴 YAGNI 原则（You Aren't Gonna Need It）
- **只做需求要求的**：严格按照 PRD 描述实现，不添加任何额外功能
- **禁止过度设计**：不要为"可能的未来需求"预留扩展点
- **禁止额外抽象**：不要创建需求中未要求的接口、工厂、策略模式
- **最小实现**：选择能满足需求的最简单方案

### 🔴 测试简洁性原则
- **只测试核心路径**：正常流程 + 主要错误场景，不测试边缘情况
- **禁止过度 mock**：只 mock 必要的外部依赖，不要 mock 内部实现
- **测试数量限制**：每个功能模块 3-5 个测试用例足够
- **禁止测试实现细节**：只测试公共 API 行为，不测试私有方法

### 🔴 禁止清单
- ❌ "以后可能需要" 的功能
- ❌ 需求中没有的配置选项
- ❌ 过度的错误处理（只处理可能发生的错误）
- ❌ 复杂的测试 setup/teardown
- ❌ 为了测试覆盖率而写的无意义测试
`;

/**
 * 并行执行 Skill 规则
 */
const PARALLEL_EXECUTOR_RULES = `
## 并行执行规范（任务设计必须考虑）

### 任务独立性
- 每个任务应该能在独立的 Git Worktree 中执行
- 任务之间通过依赖关系协调，而非共享状态
- 避免任务间的文件冲突

### 任务生命周期
PENDING → ASSIGNED → RUNNING → DONE/FAILED

### 任务设计原则
1. 单一职责：每个任务专注一个功能
2. 原子性：任务要么完全完成，要么完全回滚
3. 可测试：每个任务都有明确的验收标准
`;

/**
 * 生成 PRD 解析的 system prompt
 */
export function getSystemPrompt(params: ParsePrdParams): string {
  const { numTasks, nextId, research, defaultTaskPriority = 'medium' } = params;

  let prompt = `你是一个专业的 AI 助手，擅长分析产品需求文档（PRD）并生成结构化、逻辑有序、具有依赖关系和执行顺序的 JSON 格式开发任务列表。

你必须严格遵守 ParallelDev Skills 定义的开发规范。`;

  if (research) {
    prompt += `

在将 PRD 分解为任务之前，你需要：
1. 研究和分析适合该项目的最新技术、库、框架和最佳实践
2. 识别 PRD 中未明确提及的潜在技术挑战、安全问题或可扩展性问题
3. 考虑与该项目相关的当前行业标准和发展趋势
4. 评估替代实现方案并推荐最有效的路径
5. 基于你的研究，包含具体的库版本、有用的 API 和具体的实现指导
6. 始终提供最直接的实现路径，避免过度工程`;
  }

  prompt += `

${TYPESCRIPT_SKILL_RULES}

${QUALITY_ASSURANCE_RULES}

${BOUNDARY_CONTROL_RULES}

${PARALLEL_EXECUTOR_RULES}

---

## 任务生成要求

分析提供的 PRD 内容并生成 ${numTasks > 0 ? `大约 ${numTasks}` : '适当数量的'} 个顶层开发任务。

每个任务应遵循以下 JSON 结构：
{
  "id": number,
  "title": string,
  "description": string,
  "status": "pending",
  "dependencies": number[] (该任务依赖的其他任务 ID),
  "priority": "high" | "medium" | "low",
  "details": string (实现细节，必须包含 TypeScript 规范指导),
  "testStrategy": string (验证方案，必须包含质量检查点)
}

指导原则：
1. ${numTasks > 0 ? '除非复杂度需要' : '根据复杂度'}，创建 ${numTasks > 0 ? `恰好 ${numTasks}` : '适当数量的'} 个任务，从 ${nextId} 开始顺序编号
2. 每个任务应该是原子化的，专注于单一职责，遵循最新的最佳实践和标准
3. 逻辑排序任务 - 考虑依赖关系和实现顺序
4. 前期任务应专注于设置，先实现核心功能，然后是高级功能
5. **每个任务的 details 必须包含 TypeScript 规范指导**
6. **每个任务的 testStrategy 必须包含质量门禁检查点**
7. 设置适当的依赖 ID（任务只能依赖 ID 较小的任务）
8. 根据关键性和依赖顺序分配优先级（high/medium/low）
9. 如果 PRD 包含具体技术要求，必须严格遵守
10. **严格遵守 YAGNI 原则**：只实现 PRD 明确要求的功能，不添加额外功能
11. **测试保持简洁**：每个任务的测试策略只包含核心测试用例（3-5 个）

任务 details 示例格式：
\`\`\`
实现用户认证 API。

技术要求：
- 使用 Zod 定义请求/响应 schema
- JWT token 管理
- bcrypt 密码哈希

TypeScript 规范：
- 禁止 any，使用 unknown 或具体类型
- 每个函数 < 50 行
- 所有 API 添加 JSDoc
- 使用 try-catch 处理异步错误
\`\`\`

任务 testStrategy 示例格式（保持简洁，3-5 个测试）：
\`\`\`
质量检查：
- [ ] tsc --noEmit 通过
- [ ] eslint 无错误

核心测试用例（只测试主要路径）：
- 正常登录流程
- 无效凭证返回错误
- Token 生成正确
\`\`\``;

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

1. 使用 Glob 工具探索项目结构
2. 使用 Grep 工具搜索现有实现、模式和技术
3. 使用 Read 工具检查关键文件如 package.json、README.md
4. 分析当前的实现状态以了解已有内容

基于你的分析：
- 识别已实现的组件/功能
- 了解使用的技术栈、框架和模式
- 生成基于现有代码库构建的任务
- 确保任务与项目当前的架构和约定保持一致

项目根目录：${projectRoot || ''}

`;
  }

  prompt += `以下是需要分解为 ${numTasks > 0 ? `大约 ${numTasks}` : '适当数量的'} 个任务的产品需求文档（PRD），ID 从 ${nextId} 开始：`;

  if (research) {
    prompt += `

请记住在任务分解之前彻底研究当前的最佳实践和技术。`;
  }

  prompt += `

${prdContent}

---

## 重要提醒

1. 响应必须是包含 "tasks" 属性的 JSON 对象
2. **严格遵守 TypeScript Skill 规则**
3. **严格遵守 YAGNI 原则**：只实现需求明确要求的，不添加任何额外功能
4. **测试保持简洁**：每个任务 3-5 个核心测试用例，不要过度测试
5. 任务设计需考虑并行执行的独立性
6. 你可以选择性地包含 "metadata" 对象`;

  return prompt;
}

export const parsePrdPrompt = {
  id: 'parse-prd',
  version: '2.1.0',
  description: '将产品需求文档解析为结构化任务（遵守 ParallelDev Skills + YAGNI 规范）',
  getSystemPrompt,
  getUserPrompt
};
