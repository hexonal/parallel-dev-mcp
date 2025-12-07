---
name: conflict-resolution
description: Git 冲突解决能力 - 分层策略自动解决 merge 冲突
triggers:
  - conflict
  - 冲突
  - merge
  - rebase
  - CONFLICT
---

# Conflict Resolution Skill

启用 ParallelDev 冲突解决能力。

## 分层策略

### Level 1: 自动解决
文件类型：
- `package-lock.json` → 重新生成
- `yarn.lock` → 重新生成
- `.prettierrc` 等配置 → 保留 ours

命令：
```bash
git checkout --ours package-lock.json
npm install
```

### Level 2: AI 辅助
使用 conflict-resolver Agent 分析并解决。

### Level 3: 人工介入
生成冲突报告，通知用户手动处理。
