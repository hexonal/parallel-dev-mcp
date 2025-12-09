---
name: quality-assurance
description: 代码质量保证能力 - TypeScript 类型检查、ESLint、E2E 测试验证。启用 ParallelDev 质量门禁。
triggers:
  - 质量检查
  - quality
  - lint
  - typecheck
  - test
  - QA
  - 代码检查
---

# Quality Assurance Skill

启用 ParallelDev 质量保证能力，包括 TypeScript 类型检查、ESLint 代码规范、E2E 测试验证。

## 快速参考

**详细规范**: 见 [REFERENCE.md](REFERENCE.md)

---

## 检查项目

| 检查类型 | 工具 | 用途 |
|----------|------|------|
| 类型检查 | TypeScript | 静态类型安全 |
| 代码规范 | ESLint | 代码风格一致性 |
| E2E 测试 | Playwright MCP | 浏览器自动化验证 |
| 格式化 | Prettier | 代码格式统一 |

---

## TypeScript 类型检查

### 执行命令
```bash
# 基础检查
tsc --noEmit --pretty

# 带项目引用
tsc --build --noEmit

# 增量检查
tsc --noEmit --incremental
```

### 常见错误修复
| 错误代码 | 描述 | 修复方法 |
|----------|------|----------|
| TS2304 | 找不到名称 | 检查导入、类型定义 |
| TS2322 | 类型不匹配 | 修正类型或添加断言 |
| TS2339 | 属性不存在 | 检查对象类型定义 |
| TS2345 | 参数类型错误 | 修正参数类型 |
| TS7006 | 隐式 any | 添加类型注解 |

---

## ESLint 代码规范

### 执行命令
```bash
# 检查
eslint src --ext .ts,.tsx --format stylish

# 自动修复
eslint src --ext .ts,.tsx --fix

# 缓存检查
eslint src --ext .ts,.tsx --cache
```

### 推荐配置
```javascript
// eslint.config.js (ESLint 9+)
export default [
    {
        files: ['**/*.ts', '**/*.tsx'],
        rules: {
            'no-console': 'warn',
            'no-unused-vars': 'error',
            '@typescript-eslint/explicit-function-return-type': 'warn',
            '@typescript-eslint/no-explicit-any': 'error'
        }
    }
];
```

---

## E2E 测试 (Playwright MCP)

### 验证策略
- **优先 E2E 验证**: 使用 Playwright MCP 进行浏览器自动化
- **完整用户流程**: 验证真实环境下的行为
- **可视化验证**: 截图对比确保 UI 正确

### 测试流程
```
1. browser_navigate → 打开目标页面
2. browser_snapshot → 获取页面状态
3. 执行交互操作
4. browser_screenshot → 截取结果
5. 验证预期结果
```

### 关键验证点
- [ ] 页面正确加载
- [ ] 组件正确渲染
- [ ] 交互响应正常
- [ ] 表单提交成功
- [ ] 错误状态显示

---

## 质量门禁

### 门禁规则
所有检查必须通过才能：
1. 合并代码到主分支
2. 标记任务为完成
3. 推送到远程仓库

### 门禁流程
```
代码提交
    │
    ├─ TypeScript 检查 ───> 失败 → 阻止
    │
    ├─ ESLint 检查 ───────> 失败 → 阻止
    │
    ├─ E2E 测试 ──────────> 失败 → 阻止
    │
    └─ 全部通过 ──────────> 允许合并
```

### 跳过规则（谨慎使用）
```bash
# 跳过特定检查（需要说明原因）
# --skip-typecheck: 临时跳过类型检查
# --skip-lint: 临时跳过 lint 检查
# --skip-test: 临时跳过测试

# 记录跳过原因
echo "SKIP_REASON: 紧急修复，后续补充测试" >> .qa-log
```

---

## 检查报告

### 报告格式
```typescript
interface QAReport {
    timestamp: string;
    taskId: string;
    checks: {
        typescript: CheckResult;
        eslint: CheckResult;
        e2e: CheckResult;
    };
    passed: boolean;
    duration: number;
}

interface CheckResult {
    name: string;
    status: 'pass' | 'fail' | 'skip';
    errors?: string[];
    warnings?: string[];
    duration: number;
}
```

### 报告示例
```json
{
    "timestamp": "2025-01-08T10:30:00Z",
    "taskId": "task-001",
    "checks": {
        "typescript": {
            "name": "TypeScript",
            "status": "pass",
            "duration": 5200
        },
        "eslint": {
            "name": "ESLint",
            "status": "pass",
            "warnings": ["2 warnings"],
            "duration": 3100
        },
        "e2e": {
            "name": "E2E Tests",
            "status": "pass",
            "duration": 15000
        }
    },
    "passed": true,
    "duration": 23300
}
```

---

## MCP 工具集成

| 工具 | 用途 |
|------|------|
| sequential-thinking | 问题分析、修复策略 |
| context7 | TypeScript/ESLint 官方文档 |
| deepwiki | 测试框架、CI/CD 文档 |
| playwright | E2E 测试、浏览器自动化验证 |
| git-config | Git 用户信息获取 |
| mcp-datetime | 报告时间戳生成 |

---

## 快速修复指南

### TypeScript 错误
```bash
# 重新生成类型
npm run build:types

# 更新依赖类型
npm install @types/xxx
```

### ESLint 错误
```bash
# 自动修复
eslint src --fix

# 更新 ESLint 配置
npx eslint --init
```

### E2E 测试失败
```
1. 检查页面是否正确加载
2. 检查选择器是否正确
3. 增加等待时间
4. 检查网络请求
```

---

## 检查清单

### 提交前
- [ ] `tsc --noEmit` 通过
- [ ] `eslint src` 无错误
- [ ] E2E 测试通过
- [ ] 无未处理的 TODO

### 合并前
- [ ] 所有门禁检查通过
- [ ] Code Review 完成
- [ ] 冲突已解决

---

## 参考文档

- **[REFERENCE.md](REFERENCE.md)** - 详细命令、错误修复、CI 集成
