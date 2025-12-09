---
name: typescript-development
description: TypeScript 严格模式开发规范 - 类型安全、代码质量标准。用于 .ts 文件、Node.js 后端、TypeScript 库开发。
triggers:
  - TypeScript
  - ts
  - Node.js
  - npm
  - yarn
  - .ts
  - tsconfig
---

# TypeScript Development Skill

TypeScript 严格模式开发规范，适用于 Node.js 后端和通用库开发。

## 快速参考

**详细规范**: 见 [REFERENCE.md](REFERENCE.md)
**代码模板**: 见 [TEMPLATES.md](TEMPLATES.md)

---

## 核心原则

| 原则 | 说明 |
|------|------|
| **SOLID** | 单一职责、开闭、里氏替换、接口隔离、依赖倒置 |
| **DRY** | 不重复自己，抽象公共逻辑 |
| **KISS** | 保持简单，避免过度设计 |
| **YAGNI** | 不实现当前不需要的功能 |

---

## 🔴 强制规则

### 类型安全
```typescript
// ✅ 正确：使用具体类型或 unknown
function process(data: unknown): void { }
function parse<T>(json: string): T { }

// ❌ 禁止：any 类型
function process(data: any): void { }
```

### 函数长度
- **所有函数不得超过 50 行**
- 超长必须拆分为多个私有函数

### 注释规范
```typescript
// ✅ 正确：注释独立成行
// 检查任务状态
const isReady = checkStatus(task);

// ❌ 禁止：行尾注释
const isReady = checkStatus(task); // 检查状态
```

### JSDoc 必须
```typescript
/**
 * 执行任务
 * @param task - 任务对象
 * @returns 执行结果
 */
async function execute(task: Task): Promise<Result> { }
```

---

## 命名规范速查

| 类型 | 规范 | 示例 |
|------|------|------|
| 接口/类型 | PascalCase | `Task`, `TaskResult` |
| 函数/变量 | camelCase | `executeTask`, `isReady` |
| 常量 | UPPER_SNAKE_CASE | `MAX_WORKERS` |
| 文件（类） | PascalCase | `TaskExecutor.ts` |
| 文件（工具） | kebab-case | `string-utils.ts` |

---

## tsconfig.json 必须配置

```json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "noImplicitReturns": true
  }
}
```

---

## Zod 运行时验证

```typescript
import { z } from 'zod';

const TaskSchema = z.object({
  id: z.string().min(1),
  title: z.string(),
  status: z.enum(['pending', 'running', 'completed']),
  priority: z.number().min(1).max(5).default(3)
});

type Task = z.infer<typeof TaskSchema>;
```

---

## 错误处理模式

```typescript
async function executeTask(task: Task): Promise<TaskResult> {
  try {
    const result = await doExecute(task);
    return { success: true, output: result };
  } catch (error) {
    console.error(`❌ 任务失败: ${task.id}`, error);
    await cleanup(task);
    return {
      success: false,
      error: error instanceof Error ? error.message : String(error)
    };
  }
}
```

---

## 项目结构

```
project/
├── src/
│   ├── index.ts        # 主入口
│   ├── types.ts        # 类型定义
│   ├── config.ts       # 配置
│   └── modules/        # 业务模块
├── tests/              # 测试
├── dist/               # 编译输出
├── package.json
└── tsconfig.json
```

---

## 常用命令

```bash
# 类型检查
npx tsc --noEmit

# 运行测试
npm test

# 代码检查
npm run lint

# 构建
npm run build
```

---

## ❌ 禁止清单

- `any` 类型
- 行尾注释
- 函数超过 50 行
- 未处理的 Promise
- `Map<string, any>` 或 `Record<string, any>`
- 没有 JSDoc 的公共 API

---

## ✅ 检查清单

- [ ] 所有函数 < 50 行
- [ ] 所有公共 API 有 JSDoc
- [ ] 没有 `any` 类型
- [ ] 没有行尾注释
- [ ] 测试覆盖率 > 80%
- [ ] ESLint 无错误

---

## MCP 工具集成

| 工具 | 用途 |
|------|------|
| sequential-thinking | 架构设计、复杂问题分析 |
| context7 | TypeScript/Node.js 官方文档查询 |
| deepwiki | Node.js 生态、开源库文档 |
| git-config | Git 用户信息获取 |
| mcp-datetime | 时间戳生成 |

---

## 参考文档

- **[REFERENCE.md](REFERENCE.md)** - 完整命名规范、类型系统、错误处理详解
- **[TEMPLATES.md](TEMPLATES.md)** - 类、接口、测试代码模板
