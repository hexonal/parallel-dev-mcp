---
name: quality-assurance
description: 代码质量保证能力 - TypeScript、ESLint、测试验证
triggers:
  - 质量检查
  - quality
  - lint
  - typecheck
  - test
---

# Quality Assurance Skill

启用 ParallelDev 质量保证能力。

## 检查项目

### TypeScript 类型检查
```bash
tsc --noEmit --pretty
```

### ESLint 代码规范
```bash
eslint src --ext .ts --format stylish
```

### 单元测试
```bash
vitest run --reporter=verbose
```

## 质量门禁

所有检查必须通过才能：
1. 合并代码到主分支
2. 标记任务为完成
3. 推送到远程仓库
