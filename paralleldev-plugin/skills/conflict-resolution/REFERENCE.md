# Conflict Resolution 详细参考

## 目录
- [命令参考](#命令参考)
- [报告格式](#报告格式)
- [错误处理](#错误处理)

---

## 命令参考

### 冲突检测
```bash
# 检查是否有冲突
git diff --check

# 列出所有冲突文件
git diff --name-only --diff-filter=U

# 查看冲突内容
git diff --diff-filter=U

# 查看特定文件冲突
git diff -- path/to/file.ts
```

### 冲突解决
```bash
# 保留当前分支版本
git checkout --ours path/to/file

# 保留合入分支版本
git checkout --theirs path/to/file

# 标记为已解决
git add path/to/file

# 继续合并
git merge --continue

# 放弃合并
git merge --abort
```

### Lock 文件处理
```bash
# npm
git checkout --ours package-lock.json
npm install
git add package-lock.json

# yarn
git checkout --ours yarn.lock
yarn install
git add yarn.lock

# pnpm
git checkout --ours pnpm-lock.yaml
pnpm install
git add pnpm-lock.yaml
```

### 批量处理
```bash
# 批量保留 ours
git checkout --ours -- *.json
git add *.json

# 批量保留 theirs
git checkout --theirs -- *.config.js
git add *.config.js
```

---

## 报告格式

### 冲突报告
```typescript
interface ConflictReport {
    timestamp: string;
    branch: {
        ours: string;
        theirs: string;
    };
    conflicts: ConflictDetail[];
    summary: {
        total: number;
        level1: number;
        level2: number;
        level3: number;
        resolved: number;
        pending: number;
    };
}

interface ConflictDetail {
    file: string;
    level: 1 | 2 | 3;
    type: 'lock' | 'config' | 'code' | 'security';
    status: 'resolved' | 'pending' | 'manual';
    resolution?: {
        strategy: string;
        command: string;
        timestamp: string;
    };
}
```

### 报告示例
```json
{
    "timestamp": "2025-01-08T10:30:00Z",
    "branch": {
        "ours": "main",
        "theirs": "feature/auth"
    },
    "conflicts": [
        {
            "file": "package-lock.json",
            "level": 1,
            "type": "lock",
            "status": "resolved",
            "resolution": {
                "strategy": "regenerate",
                "command": "npm install",
                "timestamp": "2025-01-08T10:30:05Z"
            }
        },
        {
            "file": "src/auth/service.ts",
            "level": 3,
            "type": "security",
            "status": "manual"
        }
    ],
    "summary": {
        "total": 5,
        "level1": 3,
        "level2": 1,
        "level3": 1,
        "resolved": 4,
        "pending": 1
    }
}
```

### 人工介入通知
```markdown
# 冲突解决报告

## 需要人工处理

### 文件: src/auth/service.ts
**原因**: 安全敏感代码
**级别**: Level 3

#### 冲突详情
- **ours (main)**: 实现 JWT 刷新逻辑
- **theirs (feature/auth)**: 修改 token 过期时间

#### 建议操作
1. 检出 theirs 版本进行审查
2. 手动合并需要的更改
3. 确保安全逻辑正确
4. 添加并提交

#### 命令
```bash
git checkout --theirs src/auth/service.ts
# 编辑文件
git add src/auth/service.ts
git merge --continue
```
```

---

## 错误处理

### 常见错误

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| `CONFLICT (content)` | 内容冲突 | 手动解决或 AI 辅助 |
| `CONFLICT (modify/delete)` | 一方修改一方删除 | 确认是否保留文件 |
| `CONFLICT (rename/rename)` | 重命名冲突 | 选择最终文件名 |
| `Automatic merge failed` | 无法自动合并 | 执行冲突解决流程 |

### 错误恢复
```bash
# 放弃当前合并
git merge --abort

# 重置到合并前状态
git reset --hard HEAD

# 查看合并状态
git status

# 重新开始合并
git merge feature-branch
```

### 日志记录
```typescript
// 冲突检测
console.log(`🔍 检测到 ${conflicts.length} 个冲突`);

// Level 1 解决
console.log(`✅ Level 1 自动解决: ${file}`);

// Level 2 解决
console.log(`🤖 Level 2 AI 辅助解决: ${file}`);

// Level 3 通知
console.warn(`⚠️ Level 3 需要人工处理: ${file}`);

// 解决完成
console.log(`✅ 所有冲突已解决，继续合并`);
```
