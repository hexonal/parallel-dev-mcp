# CLAUDE_FE.md

本文件为前端 TypeScript 项目的通用开发规范

对话时，始终使用中文。

## 本项目为前端项目，采用 TypeScript + 现代框架 (React/Vue/Svelte/Angular 等)

* 所有组件和逻辑层均基于 TypeScript 实现，禁止使用纯 JS 文件
* 优先使用最新的 ECMAScript 特性与类型系统特性

---

## 🚨 严格开发规范（2025 最新标准）

## 🎯 核心设计原则

### 1. YAGNI 原则（You Aren't Gonna Need It）

* ✅ 只实现当前需要的功能，不做预期功能扩展
* ✅ 禁止为了“未来可能用到”而提前设计复杂逻辑

### 2. KISS 原则（Keep It Simple, Stupid）

* ✅ 保持组件、函数、模块简洁、单一职责
* ✅ 避免多层嵌套、过度封装、抽象泛滥

### 3. SOLID 原则实践

- **Single Responsibility**: 组件职责单一，避免超过 300 行
- **Open/Closed**: 通过 Props 和插槽扩展组件功能
- **Liskov Substitution**: 子组件可替换父组件
- **Interface Segregation**: 拆分大型接口为小接口
- **Dependency Inversion**: 依赖抽象而非具体实现

---

## 目录结构与模块化标准

### 📁 推荐目录结构



### 🧱 命名规范

* 文件名：全小写 + 连字符（如 `user-list.tsx`）
* 组件名：大驼峰（如 `UserList`）
* 接口 / 类型名：大驼峰 + 后缀（如 `UserResp`, `LoginReq`）
* 变量名：小驼峰（如 `userName`, `isLoading`）
* 常量：全大写 + 下划线（如 `MAX_PAGE_SIZE`）

### 代码风格

- **缩进**: 2 个空格
- **最大行长**: 120 字符
- **文件最大行数**: 500 行
- **函数最大行数**: 50 行
- **组件最大行数**: 300 行
---


## 代码质量严格标准

### 函数长度限制

**🔴 强制要求：**

* 所有函数不得超过 **50 行**（含注释与空行）
* 超出必须拆分为多个私有函数或 hooks
* 复杂逻辑建议使用策略模式或组合模式

### 注释规范

**🔴 强制要求：**

* 禁止行尾注释，所有注释必须独立成行
* 每个函数、类、组件都必须添加 JSDoc 注释
* 逻辑步骤需逐步编号（// 1.、// 2.、// 3.）

示例：

```ts
/**
 * 登录接口调用
 * @param req 登录请求参数
 * @returns 登录响应数据
 */
export async function login(req: LoginReq): Promise<LoginResp> {
  // 1. 参数校验
  if (!req.username || !req.password) throw new Error('参数缺失');

  // 2. 发起请求
  const resp = await http.post<LoginResp>('/api/login', req);

  // 3. 返回结果
  return resp.data;
}
```

---

## 类型安全严格标准

**🔴 严禁使用：**

* `any` 类型（除非显式标注为 `// TODO: 临时类型`）
* `Object`、`Function` 等不安全类型
* 未定义类型的 JSON 解析结果（必须通过接口类型声明）

**✅ 推荐使用：**

* 明确的 `interface` 或 `type`
* `Partial<T>` / `Pick<T>` / `Omit<T>` 等 TS 工具类型
* 泛型函数、泛型组件的类型约束

---

## 组件开发规范

### 结构标准（React/Vue 通用）

**🔴 强制要求：**

* 每个组件目录下必须包含：

  * `index.tsx` / `index.vue`
  * `style.(css|scss)`（如有样式）
  * `types.ts`（如有专用类型）
* 组件代码必须类型化
* 禁止在组件内部直接操作 DOM（除非在 Hook 内封装）

示例（React）：

```tsx
/**
 * 用户信息卡片组件
 * @description 展示用户头像与基本信息
 */
export const UserCard: React.FC<UserCardProps> = ({ user }) => {
  // 1. 渲染用户头像
  // 2. 渲染基本信息
  // 3. 返回卡片 UI
  return (
    <div className="user-card">
      <img src={user.avatar} alt="avatar" />
      <div>{user.name}</div>
    </div>
  );
};
```

---

## 接口与请求封装标准

**🔴 强制要求：**

* 所有请求必须经过统一封装（如 `api/http.ts`）
* 响应结构必须类型化
* 请求函数必须带有 Req/Resp 类型约束

示例：

```ts
export interface LoginReq {
  username: string;
  password: string;
}

export interface LoginResp {
  token: string;
  expiresAt: string;
}

export const login = (data: LoginReq) =>
  http.post<LoginResp>('/login', data);
```

---

## 状态管理标准

**推荐：**

* 轻量项目使用 Zustand / Pinia
* 中大型项目使用 Redux Toolkit / Vuex 5
* 状态必须类型化（Store 类型独立定义）
* 禁止在 Store 外直接修改状态

---

## 异常与日志标准

**🔴 强制要求：**

* 全局捕获未处理错误（window.onerror / ErrorBoundary）
* 接口错误必须统一拦截并包装
* 日志打印使用封装模块（如 `logger.ts`）

---

## 🏗️ 工程化标准

### 版本控制

**分支命名:**

- `feat/xxx`: 新功能分支
- `fix/xxx`: 问题修复分支
- `release/xxx`: 发布分支
- `hotfix/xxx`: 紧急修复分支

**提交信息规范:**

```
feat: 添加新功能
fix: 修复问题
docs: 文档更新
style: 代码格式调整
refactor: 代码重构
perf: 性能优化
test: 测试相关
chore: 构建/工具
```

### 测试要求

- 单元测试覆盖率 > 80%
- 快照测试覆盖所有组件
- 集成测试覆盖主要流程
- E2E 测试覆盖关键路径
- 性能测试达到指标要求

### 性能指标

- **First Contentful Paint** < 1.5s
- **Time to Interactive** < 3.5s
- **Largest Contentful Paint** < 2.5s
- **Cumulative Layout Shift** < 0.1
- **First Input Delay** < 100ms

### 构建优化

**代码分割策略:**

- 路由级别分割
- 组件级别分割
- 第三方库分割

**Tree Shaking:**

- 使用 ES Module
- 移除未使用代码

**资源优化:**

- 图片压缩
- 懒加载策略
- 预加载关键资源

### 编译与质量检测

**🔴 强制要求:**

- 构建工具必须无警告通过（Vite / Webpack）
- 格式化: `eslint . --fix`
- 静态检查: `eslint .`

**推荐命令:**

```bash
# 代码格式化
eslint . --fix

# Lint 检查
eslint .

```

---


## 🔒 安全规范

### 输入处理

**XSS 防护:**

- 使用 DOMPurify
- 避免 innerHTML
- 转义特殊字符

**输入验证:**

- 客户端验证
- 服务端验证
- 类型检查

### 认证授权

**CSRF 防护:**

- Token 验证
- SameSite Cookie

**敏感信息:**

- 使用 HTTPS
- 加密存储
- 传输加密

### 依赖管理

- 定期更新依赖
- 漏洞扫描
- 依赖审查
- 最小依赖原则

---

## 🎨 样式规范 - Tailwind CSS v4

### 核心理念

Tailwind CSS v4 采用全新的 CSS-first 配置方式,摒弃了传统的 JavaScript 配置文件,使用原生 CSS 特性实现更快的构建速度和更好的开发体验。

### 安装与配置

**安装:**

```bash
pnpm add tailwindcss@next @tailwindcss/vite@next
```

**Vite 配置 (vite.config.ts):**

```typescript
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [
    tailwindcss(),
  ],
})
```

**主样式文件 (app.css):**

```css
@import "tailwindcss";

/* 自定义主题 */
@theme {
  --color-primary: #3b82f6;
  --color-secondary: #8b5cf6;
  --font-display: "Inter", system-ui, sans-serif;
  --breakpoint-3xl: 1920px;
}

/* 自定义工具类 */
@layer utilities {
  .text-balance {
    text-wrap: balance;
  }
}
```

### 文件组织规范

**推荐结构:**

```
assets/
├── main.css                 # 主入口
├── themes/
│   ├── default.css        # 默认主题
│   └── dark.css           # 暗黑主题
```

### 主题系统规范

**🔴 强制要求:**

- 所有设计令牌必须使用 `@theme` 指令定义
- 颜色命名使用语义化名称,避免具体颜色名
- 主题变量必须支持暗黑模式

**主题定义:**

```css
@theme {
  /* 颜色系统 - 语义化命名 */
  --color-primary-*: initial;
  --color-primary-50: #eff6ff;
  --color-primary-500: #3b82f6;
  --color-primary-900: #1e3a8a;

  /* 间距系统 */
  --spacing-xs: 0.5rem;
  --spacing-sm: 0.75rem;
  --spacing-md: 1rem;
  --spacing-lg: 1.5rem;
  --spacing-xl: 2rem;

  /* 断点系统 */
  --breakpoint-sm: 640px;
  --breakpoint-md: 768px;
  --breakpoint-lg: 1024px;
  --breakpoint-xl: 1280px;
  --breakpoint-2xl: 1536px;

  /* 字体系统 */
  --font-sans: system-ui, sans-serif;
  --font-mono: ui-monospace, monospace;
  
  /* 圆角系统 */
  --radius-sm: 0.25rem;
  --radius-md: 0.375rem;
  --radius-lg: 0.5rem;
  --radius-xl: 1rem;

  /* 阴影系统 */
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
  --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1);
}
```

**暗黑模式:**

```css
@media (prefers-color-scheme: dark) {
  @theme {
    --color-primary-50: #1e3a8a;
    --color-primary-900: #eff6ff;
  }
}

/* 或使用 class 策略 */
.dark {
  @theme {
    --color-bg: #1a1a1a;
    --color-text: #ffffff;
  }
}
```

### 组件样式规范

**🔴 强制要求:**

- 组件样式使用 `@layer components` 定义
- class 名称必须语义化,避免缩写
- 复杂组件必须拆分为多个 CSS 层级

**组件定义:**

```css
@layer components {
  .btn {
    @apply inline-flex items-center justify-center;
    @apply px-4 py-2 rounded-md;
    @apply font-medium transition-colors;
    @apply focus:outline-none focus:ring-2 focus:ring-offset-2;
  }

  .btn-primary {
    @apply bg-primary-500 text-white;
    @apply hover:bg-primary-600;
    @apply focus:ring-primary-500;
  }

  .btn-secondary {
    @apply bg-secondary-500 text-white;
    @apply hover:bg-secondary-600;
    @apply focus:ring-secondary-500;
  }

  .card {
    @apply bg-white dark:bg-gray-800;
    @apply rounded-lg shadow-md;
    @apply p-6 space-y-4;
  }
}
```

**在 Vue3 组件中使用:**

```vue
<template>
  <button class="btn btn-primary">
    <span>点击按钮</span>
  </button>
</template>

<!-- 不推荐在 scoped 中重复定义已有组件样式 -->
<style scoped>
/* ❌ 避免 - 与 Tailwind 组件冲突 */
.btn {
  padding: 1rem;
}
</style>
```

### Class 管理规范

**🔴 强制要求:**

- 每行 class 不超过 120 字符
- 使用 `clsx` 或 `classnames` 管理动态 class
- 响应式 class 按顺序排列: `base -> sm -> md -> lg -> xl -> 2xl`

**Vue3 组件示例:**

```vue
<script setup lang="ts">
import { computed } from 'vue'
import clsx from 'clsx'

interface Props {
  variant?: 'primary' | 'secondary'
  size?: 'sm' | 'md' | 'lg'
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'primary',
  size: 'md',
  disabled: false
})

const buttonClasses = computed(() => clsx(
  // 基础样式
  'inline-flex items-center justify-center',
  'font-medium transition-colors',
  'focus:outline-none focus:ring-2',
  
  // 变体样式
  {
    'bg-primary-500 text-white hover:bg-primary-600': props.variant === 'primary',
    'bg-secondary-500 text-white hover:bg-secondary-600': props.variant === 'secondary',
  },
  
  // 尺寸样式
  {
    'px-3 py-1.5 text-sm': props.size === 'sm',
    'px-4 py-2 text-base': props.size === 'md',
    'px-6 py-3 text-lg': props.size === 'lg',
  },
  
  // 状态样式
  {
    'opacity-50 cursor-not-allowed': props.disabled,
  }
))
</script>

<template>
  <button :class="buttonClasses" :disabled="disabled">
    <slot />
  </button>
</template>
```

**React 组件示例:**

```tsx
import { type FC } from 'react'
import clsx from 'clsx'

interface ButtonProps {
  variant?: 'primary' | 'secondary'
  size?: 'sm' | 'md' | 'lg'
  disabled?: boolean
  children: React.ReactNode
}

export const Button: FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  disabled = false,
  children
}) => {
  return (
    <button
      className={clsx(
        'inline-flex items-center justify-center',
        'font-medium transition-colors',
        'focus:outline-none focus:ring-2',
        {
          'bg-primary-500 text-white hover:bg-primary-600': variant === 'primary',
          'bg-secondary-500 text-white hover:bg-secondary-600': variant === 'secondary',
        },
        {
          'px-3 py-1.5 text-sm': size === 'sm',
          'px-4 py-2 text-base': size === 'md',
          'px-6 py-3 text-lg': size === 'lg',
        },
        {
          'opacity-50 cursor-not-allowed': disabled,
        }
      )}
      disabled={disabled}
    >
      {children}
    </button>
  )
}
```

### 响应式设计规范

**断点使用顺序:**

```vue
<template>
  <!-- ✅ 推荐: Mobile First - 从小到大 -->
  <div class="
    w-full
    sm:w-1/2
    md:w-1/3
    lg:w-1/4
    xl:w-1/5
  ">
    内容
  </div>

  <!-- ❌ 避免: 无序排列 -->
  <div class="w-full lg:w-1/4 sm:w-1/2 xl:w-1/5 md:w-1/3">
    内容
  </div>
</template>
```

### 调试技巧

**开发环境配置:**

```typescript
// vite.config.ts
export default defineConfig({
  plugins: [
    tailwindcss(),
  ],
  
  css: {
    devSourcemap: true, // 开启 sourcemap
  }
})
```

**使用浏览器扩展:**

- Tailwind CSS IntelliSense (VSCode)
- Tailwind Fold (代码折叠)
- Headwind (class 排序)

---


## 💎 TypeScript 规范

### 类型安全严格标准

**🔴 严禁使用:**

- `any` 类型（除非显式标注为 `// TODO: 临时类型`）
- `Object`、`Function` 等不安全类型
- 未定义类型的 JSON 解析结果（必须通过接口类型声明）
- `eval()`、`with`、全局变量
- 混用 JS/TS 文件

**✅ 推荐使用:**

- 明确的 `interface` 或 `type`
- `Partial<T>` / `Pick<T>` / `Omit<T>` 等 TS 工具类型
- 泛型函数、泛型组件的类型约束

### 类型定义

```typescript
// 通用类型
type Nullable<T> = T | null
type Optional<T> = T | undefined
type AsyncData<T> = {
  data: Nullable<T>
  loading: boolean
  error: Nullable<Error>
}

// 工具类型
type Pick<T, K extends keyof T> = {
  [P in K]: T[P]
}
```

### 类型保护

```typescript
function isError(value: unknown): value is Error {
  return value instanceof Error
}

function assertNonNull<T>(value: T | null): asserts value is T {
  if (value === null) {
    throw new Error('Value cannot be null')
  }
}
```

### 接口与请求封装

**🔴 强制要求:**

- 所有请求必须经过统一封装（如 `api/http.ts`）
- 响应结构必须类型化
- 请求函数必须带有 Req/Resp 类型约束

**示例:**

```typescript
export interface LoginReq {
  username: string
  password: string
}

export interface LoginResp {
  token: string
  expiresAt: string
}

export const login = (data: LoginReq) =>
  http.post<LoginResp>('/login', data)
```

---

## ⚛️ React 技术栈

### 组件开发规范

**🔴 强制要求:**

- 每个组件目录下必须包含:
  - `index.tsx`
  - `style.(css|scss)`（如有样式）
  - `types.ts`（如有专用类型）
- 组件代码必须类型化
- 禁止在组件内部直接操作 DOM（除非在 Hook 内封装）

**最佳实践示例:**

```typescript
import React, { memo, useCallback } from 'react'
import type { FC } from 'react'

interface IButtonProps {
  onClick: () => void
  children: React.ReactNode
  disabled?: boolean
  loading?: boolean
}

/**
 * 按钮组件
 * @description 支持加载状态和禁用状态的通用按钮
 */
export const Button: FC<IButtonProps> = memo(({ 
  onClick, 
  children,
  disabled = false,
  loading = false 
}) => {
  const handleClick = useCallback(() => {
    if (!disabled && !loading) {
      onClick()
    }
  }, [onClick, disabled, loading])

  return (
    <button 
      onClick={handleClick} 
      disabled={disabled || loading}
      className={styles.button}
      type="button"
    >
      {loading ? <Spinner /> : children}
    </button>
  )
})

Button.displayName = 'Button'
```

**反模式示例（避免）:**

```typescript
// ❌ 避免的做法
class Button extends React.Component {
  state = { clicked: false }
  
  handleClick() {
    // 直接操作DOM
    document.getElementById('root').style.display = 'none'
    // 直接修改props
    this.props.data.value = 'new value'
    // 未处理loading状态
    this.props.onClick()
  }
  
  render() {
    // 内联样式
    return (
      <button 
        onClick={this.handleClick} 
        style={{ backgroundColor: 'blue' }}
      >
        {this.props.children}
      </button>
    )
  }
}
```

### 自定义 Hooks

```typescript
function useAsync<T>(asyncFn: () => Promise<T>) {
  const [state, setState] = useState<AsyncData<T>>({
    data: null,
    loading: false,
    error: null
  })

  const execute = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true }))
    try {
      const data = await asyncFn()
      setState({ data, loading: false, error: null })
    } catch (error) {
      setState({ data: null, loading: false, error })
    }
  }, [asyncFn])

  return { ...state, execute }
}
```

### 性能优化

**组件优化:**

```typescript
// 优化前
const Component = (props) => {
  const value = heavyCalculation(props.data)
  return <div>{value}</div>
}

// 优化后
const Component = memo((props) => {
  const value = useMemo(() => 
    heavyCalculation(props.data), 
    [props.data]
  )
  return <div>{value}</div>
})
```

**代码分割:**

```typescript
// 路由级别分割
const UserModule = lazy(() => import('./features/User'))

// 组件级别分割
const HeavyChart = lazy(() => import('./components/Chart'))
```

---

## 🟢 Vue3 技术栈

### 组合式 API 规范

**文件结构标准:**

```vue
<script setup lang="ts">
// 1. 类型导入
import type { PropType } from 'vue'

// 2. 组件导入
import { ElButton } from 'element-plus'

// 3. 工具函数导入
import { useUserStore } from '@/stores/user'

// 4. Props/Emits 定义
interface Props {
  modelValue?: string
  placeholder?: string
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: '',
  placeholder: '请输入'
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'change', value: string): void
}>()

// 5. 响应式数据
const visible = ref(false)
const form = reactive({
  username: '',
  password: ''
})

// 6. 计算属性
const computedValue = computed(() => {
  return props.modelValue.trim()
})

// 7. 生命周期钩子
onMounted(() => {
  // 初始化逻辑
})

// 8. 方法定义
const handleSubmit = async () => {
  try {
    await validate()
    emit('submit', form)
  } catch (err) {
    // 错误处理
  }
}
</script>

<template>
  <div class="component-container">
    <!-- 内容模板 -->
  </div>
</template>

<style lang="scss" scoped>
// 样式定义
</style>
```

### 组合式函数规范

**标准组合式函数结构:**

```typescript
export const useCustomFeature = (options: Options) => {
  // 状态定义
  const state = reactive({
    loading: false,
    data: null as Data | null,
    error: null as Error | null
  })

  // 计算属性
  const computedData = computed(() => 
    state.data?.someComputation
  )

  // 方法
  const loadData = async () => {
    try {
      state.loading = true
      state.data = await fetchData()
    } catch (err) {
      state.error = err as Error
    } finally {
      state.loading = false
    }
  }

  // 生命周期
  onMounted(() => {
    loadData()
  })

  // 暴露接口
  return {
    ...toRefs(state),
    computedData,
    loadData
  }
}
```

**状态管理组合式函数:**

```typescript
export const useStore = defineStore('main', () => {
  // 状态
  const count = ref(0)
  const items = reactive<Item[]>([])

  // 计算属性
  const doubleCount = computed(() => count.value * 2)

  // actions
  function increment() {
    count.value++
  }

  return { count, doubleCount, increment }
})
```

**组件懒加载:**

```typescript
const AsyncComponent = defineAsyncComponent({
  loader: () => import('./HeavyComponent.vue'),
  loadingComponent: LoadingSpinner,
  errorComponent: ErrorComponent,
  delay: 200,
  timeout: 3000
})
```

---

## 🚀 Nuxt3 技术栈

### 路由规范

**动态路由:**

```typescript
// pages/[id].vue
definePageMeta({
  validate: async (route) => {
    // 返回 false 或抛出错误将显示 404 页面
    return /^\d+$/.test(route.params.id as string)
  }
})
```

**中间件:**

```typescript
export default defineNuxtRouteMiddleware((to, from) => {
  const auth = useAuth()
  if (!auth.isAuthenticated.value) {
    return navigateTo('/login')
  }
})
```

### 状态管理

**useState:**

```typescript
export const useCounter = () => useState('counter', () => ({
  count: 0,
  increment: () => counter.value.count++
}))
```

**Pinia Store:**

```typescript
export const useStore = defineStore('main', () => {
  // 状态
  const count = ref(0)
  const items = reactive<Item[]>([])

  // 计算属性
  const doubleCount = computed(() => count.value * 2)

  // actions
  function increment() {
    count.value++
  }

  return { count, doubleCount, increment }
})
```

### SEO 优化

**页面元数据:**

```typescript
useHead({
  title: computed(() => post.value?.title),
  meta: [
    {
      name: 'description',
      content: computed(() => post.value?.description)
    }
  ],
  link: [
    {
      rel: 'canonical',
      href: computed(() => `https://example.com/posts/${post.value?.id}`)
    }
  ]
})
```

**结构化数据:**

```typescript
useSeoMeta({
  title: 'My Amazing Site',
  ogTitle: 'My Amazing Site',
  description: 'This is my amazing site, let me tell you all about it.',
  ogDescription: 'This is my amazing site, let me tell you all about it.',
  ogImage: 'https://example.com/image.png',
  twitterCard: 'summary_large_image',
})
```

### 性能优化

**组件懒加载:**

```typescript
const LazyComponent = defineNuxtComponent({
  lazy: true,
  suspensible: true,
  asyncData: async () => {
    // 异步数据获取
  }
})
```

**预加载:**

```vue
<NuxtLink 
  to="/about"
  prefetch
  preload
>
  About
</NuxtLink>
```

### 错误处理

**错误页面:**

```vue
<!-- error.vue -->
<template>
  <div class="error-page">
    <h1>{{ error.statusCode }}</h1>
    <p>{{ error.message }}</p>
    <button @click="handleError">重试</button>
  </div>
</template>

<script setup>
const props = defineProps({
  error: Object
})

const handleError = () => {
  clearError({ redirect: '/' })
}
</script>

```

**错误处理:**

```typescript
try {
  await callApi()
} catch (err) {
  throw createError({
    statusCode: 500,
    statusMessage: 'Internal Server Error',
    message: err.message
  })
}
```

---

## 禁用功能清单

**❌ 严禁使用：**

* `any`、`eval()`、`with`、全局变量
* 行尾注释
* 混用 JS/TS 文件
* 嵌套三层以上的组件或回调地狱
* DDD / 过度设计
* 魔法字符串与硬编码

---

## MCP 工具集成

本项目集成以下 MCP 工具以支持自动化开发与文档生成：

* **mcp-git**：自动获取提交人信息
* **mcp-datetime**：自动生成时间戳
* **mcp-docgen**：自动生成 API / 类型文档
* **mcp-stylecheck**：统一风格检查
* **mcp-ci**：持续集成检查

---

## 🟨 标准注释模板

### 🟨 TypeScript 文件模板

```ts
/**
 * 模块：${NAME}
 * 描述：${DESCRIPTION}
 * @author {{通过 MCP Git 自动}}
 * @date {{通过 MCP DateTime 自动}}
 */
```

### 🟨 组件模板

```tsx
/**
 * 组件：${COMPONENT_NAME}
 * 描述：${DESCRIPTION}
 * @props ${PROPS_DESCRIPTION}
 * @returns JSX.Element
 */
export const ${COMPONENT_NAME}: React.FC<${COMPONENT_NAME}Props> = (props) => {
  // 1. 初始化
  // 2. 渲染内容
  // 3. 返回 UI
  return <div></div>;
};
```

### 🟨 类型定义模板

```ts
/**
 * 类型：${TYPE_NAME}
 * 描述：${DESCRIPTION}
 */
export interface ${TYPE_NAME} {
  // 字段定义
}
```
## 🚨 重要事项说明
- 任何时候在修改完代码后不允许主动提交到git
- 不允许使用git commit, git push, git merge，git reset等会直接影响git分支的操作，需要操作前只能提供操作说明人工手动操作
