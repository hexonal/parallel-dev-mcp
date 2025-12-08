---
name: frontend-development
description: 前端开发规范 - React/Vue/Nuxt3、Tailwind CSS v4、TypeScript。用于 .tsx/.vue 文件、组件开发、前端项目。
triggers:
  - React
  - Vue
  - Nuxt
  - Next.js
  - 前端
  - component
  - Tailwind
  - .tsx
  - .vue
---

# Frontend Development Skill

前端 TypeScript 项目通用规范，支持 React/Vue/Nuxt3。

## 快速参考

**React 规范**: 见 [REACT.md](REACT.md)
**Vue/Nuxt 规范**: 见 [VUE.md](VUE.md)
**Tailwind 规范**: 见 [TAILWIND.md](TAILWIND.md)
**组件模板**: 见 [TEMPLATES.md](TEMPLATES.md)
**E2E 测试**: 见 [E2E.md](E2E.md)

---

## 核心原则

| 原则 | 要求 |
|------|------|
| **YAGNI** | 只实现当前需要的功能 |
| **KISS** | 组件职责单一，避免多层嵌套 |
| **单一职责** | 每个组件只做一件事 |

---

## 🔴 强制规则

### 代码行数限制
| 类型 | 最大行数 |
|------|----------|
| 函数 | 50 行 |
| 组件 | 300 行 |
| 单文件 | 500 行 |

### 注释规范
```typescript
// ✅ 正确：注释独立成行
// 处理用户提交
const handleSubmit = () => { };

// ❌ 禁止：行尾注释
const handleSubmit = () => { }; // 处理提交
```

### 类型安全
```typescript
// ✅ 正确：明确类型
interface Props {
  title: string;
  onClick: () => void;
}

// ❌ 禁止：any 类型
interface Props {
  data: any;
}
```

---

## 目录结构

```
src/
├── components/       # 通用组件
│   ├── ui/          # 基础 UI
│   └── business/    # 业务组件
├── hooks/           # React Hooks
├── composables/     # Vue Composables
├── pages/           # 页面
├── stores/          # 状态管理
├── services/        # API 服务
├── types/           # 类型定义
└── utils/           # 工具函数
```

---

## 命名规范速查

| 类型 | 规范 | 示例 |
|------|------|------|
| 文件名 | kebab-case | `user-list.tsx` |
| 组件名 | PascalCase | `UserList` |
| Hook/Composable | use 前缀 | `useUser`, `useAuth` |
| 事件处理 | handle 前缀 | `handleClick` |
| 布尔变量 | is/has 前缀 | `isLoading`, `hasError` |

---

## 组件设计原则

### 单一职责
```tsx
// ✅ 正确：职责单一
function UserAvatar({ url, name }: Props) {
  return <img src={url} alt={name} />;
}

// ❌ 错误：职责过多
function UserCard({ user }: Props) {
  // 同时处理：头像、信息、操作、弹窗...
}
```

### Props 优于状态
```tsx
// ✅ 正确：受控组件
function Input({ value, onChange }: Props) {
  return <input value={value} onChange={onChange} />;
}

// ❌ 避免：过多内部状态
function Input() {
  const [value, setValue] = useState('');
  // 难以从外部控制
}
```

---

## Tailwind CSS v4 快速参考

### 常用类名
```tsx
// 布局
<div className="flex items-center justify-between gap-4">

// 间距
<div className="p-4 m-2 space-y-4">

// 响应式
<div className="w-full md:w-1/2 lg:w-1/3">

// 状态
<button className="hover:bg-blue-600 disabled:opacity-50">
```

### 禁止内联样式
```tsx
// ✅ 正确：Tailwind 类
<div className="p-4 bg-white rounded-lg shadow">

// ❌ 禁止：内联样式
<div style={{ padding: '16px', background: 'white' }}>
```

---

## 状态管理

### React (Zustand)
```typescript
import { create } from 'zustand';

interface UserStore {
  user: User | null;
  setUser: (user: User) => void;
}

export const useUserStore = create<UserStore>((set) => ({
  user: null,
  setUser: (user) => set({ user })
}));
```

### Vue (Pinia)
```typescript
import { defineStore } from 'pinia';

export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null);
  const setUser = (newUser: User) => { user.value = newUser; };
  return { user, setUser };
});
```

---

## API 调用模式

```typescript
// services/api/user.ts
export const userApi = {
  async getUser(id: string): Promise<User> {
    const res = await http.get<UserResp>(`/users/${id}`);
    return res.data;
  },

  async updateUser(id: string, data: UpdateUserReq): Promise<User> {
    const res = await http.put<UserResp>(`/users/${id}`, data);
    return res.data;
  }
};
```

---

## ❌ 禁止清单

- `any` 类型
- 行尾注释
- 内联样式 `style={{}}`
- 组件超过 300 行
- Props 超过 10 个
- 嵌套超过 3 层
- `!important` 覆盖样式

---

## ✅ 检查清单

- [ ] 组件 < 300 行
- [ ] 函数 < 50 行
- [ ] 无 `any` 类型
- [ ] 无行尾注释
- [ ] 使用 Tailwind 而非内联样式
- [ ] Hook/Composable 以 `use` 开头
- [ ] 事件处理以 `handle` 开头

---

## MCP 工具集成

| 工具 | 用途 |
|------|------|
| sequential-thinking | 组件架构设计、复杂问题分析 |
| context7 | React/Vue/Nuxt 官方文档查询 |
| deepwiki | 前端生态、UI 库文档 |
| playwright | E2E 测试、浏览器自动化验证 |
| git-config | Git 用户信息获取 |
| mcp-datetime | 时间戳生成 |

### 测试策略
- **优先 E2E 验证**: 使用 Playwright MCP 进行浏览器自动化测试
- **完整用户流程**: 验证真实浏览器环境下的行为
- **可视化验证**: 截图对比确保 UI 正确渲染

---

## 参考文档

- **[REACT.md](REACT.md)** - React 18+ Hooks、组件模式
- **[VUE.md](VUE.md)** - Vue 3 Composition API、Nuxt 3
- **[TAILWIND.md](TAILWIND.md)** - Tailwind CSS v4 完整类名
- **[TEMPLATES.md](TEMPLATES.md)** - 组件、页面代码模板
- **[E2E.md](E2E.md)** - Playwright MCP E2E 测试规范
