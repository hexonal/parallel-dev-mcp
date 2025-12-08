# Quality Assurance 详细参考

## 目录
- [详细命令](#详细命令)
- [错误修复指南](#错误修复指南)
- [CI 集成](#ci-集成)

---

## 详细命令

### TypeScript 检查
```bash
# 基础检查
tsc --noEmit --pretty

# 严格模式
tsc --noEmit --strict

# 带项目引用
tsc --build --noEmit

# 增量检查（更快）
tsc --noEmit --incremental

# 指定配置文件
tsc --noEmit --project tsconfig.build.json

# 输出诊断信息
tsc --noEmit --extendedDiagnostics
```

### ESLint 检查
```bash
# 检查所有文件
eslint src --ext .ts,.tsx

# 自动修复
eslint src --ext .ts,.tsx --fix

# 指定格式化输出
eslint src --ext .ts,.tsx --format stylish
eslint src --ext .ts,.tsx --format json > eslint-report.json

# 使用缓存（加速）
eslint src --ext .ts,.tsx --cache

# 只显示错误
eslint src --ext .ts,.tsx --quiet

# 最大警告数
eslint src --ext .ts,.tsx --max-warnings 10
```

### Prettier 格式化
```bash
# 检查格式
prettier --check "src/**/*.{ts,tsx}"

# 格式化
prettier --write "src/**/*.{ts,tsx}"

# 忽略文件
prettier --check "src/**/*.{ts,tsx}" --ignore-path .prettierignore
```

### 组合命令
```bash
# 完整检查流程
npm run typecheck && npm run lint && npm run test:e2e

# 使用 npm-run-all
npm-run-all --parallel typecheck lint --serial test:e2e
```

---

## 错误修复指南

### TypeScript 常见错误

#### TS2304: Cannot find name
```typescript
// 错误
const result = someFunction(); // TS2304

// 修复：添加导入
import { someFunction } from './utils';
const result = someFunction();
```

#### TS2322: Type is not assignable
```typescript
// 错误
const user: User = { name: 'John' }; // TS2322: missing 'id'

// 修复：补全属性
const user: User = { id: '1', name: 'John' };

// 或使用 Partial
const user: Partial<User> = { name: 'John' };
```

#### TS2339: Property does not exist
```typescript
// 错误
const value = obj.unknownProp; // TS2339

// 修复：扩展类型定义
interface MyObj {
    unknownProp: string;
}

// 或使用类型断言
const value = (obj as any).unknownProp;
```

#### TS7006: Implicit any
```typescript
// 错误
function process(data) { } // TS7006

// 修复：添加类型注解
function process(data: ProcessData): void { }
```

### ESLint 常见错误

#### no-unused-vars
```typescript
// 错误
const unused = 'value'; // no-unused-vars

// 修复：删除或使用
// 如果是有意保留，使用下划线前缀
const _unused = 'value';
```

#### @typescript-eslint/no-explicit-any
```typescript
// 错误
const data: any = fetchData(); // no-explicit-any

// 修复：使用具体类型
const data: UserData = fetchData();

// 或使用 unknown
const data: unknown = fetchData();
```

#### prefer-const
```typescript
// 错误
let value = 'constant'; // prefer-const

// 修复
const value = 'constant';
```

---

## CI 集成

### GitHub Actions
```yaml
# .github/workflows/qa.yml
name: Quality Assurance

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  qa:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: TypeScript check
        run: npm run typecheck

      - name: ESLint check
        run: npm run lint

      - name: Install Playwright
        run: npx playwright install --with-deps

      - name: E2E tests
        run: npm run test:e2e
```

### package.json scripts
```json
{
    "scripts": {
        "typecheck": "tsc --noEmit",
        "lint": "eslint src --ext .ts,.tsx",
        "lint:fix": "eslint src --ext .ts,.tsx --fix",
        "format": "prettier --write \"src/**/*.{ts,tsx}\"",
        "format:check": "prettier --check \"src/**/*.{ts,tsx}\"",
        "test:e2e": "playwright test",
        "qa": "npm-run-all --parallel typecheck lint format:check"
    }
}
```

### Pre-commit Hook
```bash
# .husky/pre-commit
#!/bin/sh
. "$(dirname "$0")/_/husky.sh"

npm run typecheck
npm run lint
npm run format:check
```

### 配置文件模板

#### tsconfig.json
```json
{
    "compilerOptions": {
        "target": "ES2022",
        "module": "ESNext",
        "moduleResolution": "bundler",
        "strict": true,
        "noEmit": true,
        "esModuleInterop": true,
        "skipLibCheck": true,
        "forceConsistentCasingInFileNames": true,
        "noUnusedLocals": true,
        "noUnusedParameters": true,
        "noImplicitReturns": true
    },
    "include": ["src/**/*"],
    "exclude": ["node_modules", "dist"]
}
```

#### eslint.config.js
```javascript
import eslint from '@eslint/js';
import tseslint from 'typescript-eslint';

export default tseslint.config(
    eslint.configs.recommended,
    ...tseslint.configs.recommended,
    {
        rules: {
            '@typescript-eslint/no-explicit-any': 'error',
            '@typescript-eslint/explicit-function-return-type': 'warn',
            'no-console': 'warn'
        }
    }
);
```

#### .prettierrc
```json
{
    "semi": true,
    "singleQuote": true,
    "tabWidth": 4,
    "trailingComma": "es5",
    "printWidth": 100
}
```
