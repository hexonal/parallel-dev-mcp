---
name: conflict-resolution
description: Git 冲突解决能力 - 分层策略自动解决 merge 冲突。启用 ParallelDev 冲突解决系统。
triggers:
  - conflict
  - 冲突
  - merge
  - rebase
  - CONFLICT
  - 合并冲突
---

# Conflict Resolution Skill

启用 ParallelDev 冲突解决能力，采用分层策略自动解决 merge 冲突。

## 快速参考

**详细规范**: 见 [REFERENCE.md](REFERENCE.md)

---

## 分层策略

| 级别 | 策略 | 适用场景 |
|------|------|----------|
| Level 1 | 自动解决 | Lock 文件、配置文件 |
| Level 2 | AI 辅助 | 代码冲突、逻辑冲突 |
| Level 3 | 人工介入 | 复杂业务逻辑、安全敏感 |

---

## Level 1: 自动解决

### 可自动解决的文件
| 文件类型 | 解决策略 | 命令 |
|----------|----------|------|
| `package-lock.json` | 重新生成 | `npm install` |
| `yarn.lock` | 重新生成 | `yarn install` |
| `pnpm-lock.yaml` | 重新生成 | `pnpm install` |
| `.prettierrc` | 保留 ours | `git checkout --ours` |
| `.eslintrc` | 保留 ours | `git checkout --ours` |
| `tsconfig.json` | 保留 ours | `git checkout --ours` |

### 执行流程
```bash
# 1. 检测冲突文件类型
git diff --name-only --diff-filter=U

# 2. 对于 lock 文件
git checkout --ours package-lock.json
npm install
git add package-lock.json

# 3. 对于配置文件
git checkout --ours .prettierrc
git add .prettierrc

# 4. 继续合并
git merge --continue
```

---

## Level 2: AI 辅助

### 触发条件
- 源代码文件冲突 (`.ts`, `.tsx`, `.js`, `.go`, `.java`)
- Level 1 无法处理的配置冲突
- 需要理解代码逻辑的冲突

### AI 分析流程
```
1. 提取冲突块
2. 分析 ours 和 theirs 的意图
3. 生成合并方案
4. 验证合并结果
5. 应用或回退
```

### 冲突块格式
```
<<<<<<< HEAD (ours)
// 当前分支的代码
=======
// 合入分支的代码
>>>>>>> feature-branch (theirs)
```

### AI 提示模板
```
分析以下 Git 冲突并提供合并方案：

文件: {file_path}
冲突块:
{conflict_block}

ours 分支目的: {ours_purpose}
theirs 分支目的: {theirs_purpose}

请提供:
1. 冲突原因分析
2. 推荐的合并代码
3. 合并理由
```

---

## Level 3: 人工介入

### 触发条件
- AI 无法确定合并策略
- 安全敏感代码（认证、授权）
- 复杂业务逻辑
- 数据库迁移文件

### 通知内容
```
⚠️ 需要人工处理的冲突

文件: src/auth/service.ts
原因: 安全敏感代码，建议人工审查

冲突详情:
- ours: 实现 JWT 刷新逻辑
- theirs: 修改 token 过期时间

建议操作:
1. git checkout feature-branch -- src/auth/service.ts
2. 手动合并需要的更改
3. git add src/auth/service.ts
4. git merge --continue
```

---

## 冲突检测

### 检测命令
```bash
# 检查是否有冲突
git diff --check

# 列出冲突文件
git diff --name-only --diff-filter=U

# 查看冲突详情
git diff --diff-filter=U
```

### 冲突分类
```typescript
interface Conflict {
    file: string;
    type: 'lock' | 'config' | 'code' | 'security';
    level: 1 | 2 | 3;
    blocks: ConflictBlock[];
}

interface ConflictBlock {
    startLine: number;
    endLine: number;
    ours: string;
    theirs: string;
}
```

---

## 合并策略选择

### 决策流程
```
检测冲突文件
    │
    ├─ Lock 文件? ─────────> Level 1 (重新生成)
    │
    ├─ 配置文件? ─────────> Level 1 (保留 ours)
    │
    ├─ 安全敏感? ─────────> Level 3 (人工)
    │
    └─ 普通代码 ──────────> Level 2 (AI 辅助)
```

### 安全敏感文件识别
```typescript
const SECURITY_PATTERNS = [
    /auth/i,
    /security/i,
    /permission/i,
    /credential/i,
    /secret/i,
    /password/i,
    /token/i,
    /\.env/
];
```

---

## MCP 工具集成

| 工具 | 用途 |
|------|------|
| sequential-thinking | 冲突分析、合并策略设计 |
| context7 | Git 官方文档查询 |
| deepwiki | Git 合并策略、冲突解决文档 |
| git-config | Git 用户信息获取 |
| mcp-datetime | 报告时间戳生成 |

---

## 检查清单

### 冲突解决前
- [ ] 识别所有冲突文件
- [ ] 分类冲突级别
- [ ] 确认安全敏感文件

### 冲突解决后
- [ ] 所有冲突已解决
- [ ] 代码可正常编译
- [ ] 测试通过
- [ ] 提交合并结果

---

## 参考文档

- **[REFERENCE.md](REFERENCE.md)** - 详细命令、报告格式、错误处理
