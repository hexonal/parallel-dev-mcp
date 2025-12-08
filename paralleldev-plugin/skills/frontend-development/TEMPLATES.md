# 前端代码模板

## 目录
- [React 组件](#react-组件)
- [Vue 组件](#vue-组件)
- [Hook/Composable](#hookcomposable)
- [API 服务](#api-服务)
- [Store](#store)

---

## React 组件

### 基础组件
```tsx
import { memo } from 'react';
import type { FC } from 'react';

interface Props {
  title: string;
  children: React.ReactNode;
}

export const Card: FC<Props> = memo(function Card({ title, children }) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-lg font-semibold mb-4">{title}</h2>
      <div>{children}</div>
    </div>
  );
});
```

### 表单组件
```tsx
import { useState, useCallback } from 'react';
import type { FC, FormEvent } from 'react';

interface Props {
  onSubmit: (data: FormData) => void;
  loading?: boolean;
}

interface FormData {
  name: string;
  email: string;
}

export const UserForm: FC<Props> = ({ onSubmit, loading = false }) => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');

  const handleSubmit = useCallback((e: FormEvent) => {
    e.preventDefault();
    onSubmit({ name, email });
  }, [name, email, onSubmit]);

  const isValid = name.trim() !== '' && email.includes('@');

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium mb-1">
          Name
        </label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full px-3 py-2 border rounded focus:ring-2 focus:ring-blue-500"
          disabled={loading}
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-1">
          Email
        </label>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full px-3 py-2 border rounded focus:ring-2 focus:ring-blue-500"
          disabled={loading}
        />
      </div>

      <button
        type="submit"
        disabled={!isValid || loading}
        className="w-full py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
      >
        {loading ? 'Submitting...' : 'Submit'}
      </button>
    </form>
  );
};
```

### 列表组件
```tsx
import type { FC } from 'react';

interface Item {
  id: string;
  name: string;
}

interface Props {
  items: Item[];
  onSelect: (id: string) => void;
  selectedId?: string;
}

export const ItemList: FC<Props> = ({ items, onSelect, selectedId }) => {
  if (items.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No items found
      </div>
    );
  }

  return (
    <ul className="divide-y">
      {items.map((item) => (
        <li
          key={item.id}
          onClick={() => onSelect(item.id)}
          className={`
            py-3 px-4 cursor-pointer hover:bg-gray-50
            ${selectedId === item.id ? 'bg-blue-50' : ''}
          `}
        >
          {item.name}
        </li>
      ))}
    </ul>
  );
};
```

---

## Vue 组件

### 基础组件
```vue
<script setup lang="ts">
interface Props {
  title: string;
}

defineProps<Props>();
</script>

<template>
  <div class="bg-white rounded-lg shadow p-6">
    <h2 class="text-lg font-semibold mb-4">{{ title }}</h2>
    <slot />
  </div>
</template>
```

### 表单组件
```vue
<script setup lang="ts">
import { ref, computed } from 'vue';

interface FormData {
  name: string;
  email: string;
}

interface Props {
  loading?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  loading: false
});

const emit = defineEmits<{
  submit: [data: FormData];
}>();

const name = ref('');
const email = ref('');

const isValid = computed(() => {
  return name.value.trim() !== '' && email.value.includes('@');
});

const handleSubmit = () => {
  if (isValid.value) {
    emit('submit', {
      name: name.value,
      email: email.value
    });
  }
};
</script>

<template>
  <form @submit.prevent="handleSubmit" class="space-y-4">
    <div>
      <label class="block text-sm font-medium mb-1">Name</label>
      <input
        v-model="name"
        type="text"
        :disabled="loading"
        class="w-full px-3 py-2 border rounded focus:ring-2 focus:ring-blue-500"
      />
    </div>

    <div>
      <label class="block text-sm font-medium mb-1">Email</label>
      <input
        v-model="email"
        type="email"
        :disabled="loading"
        class="w-full px-3 py-2 border rounded focus:ring-2 focus:ring-blue-500"
      />
    </div>

    <button
      type="submit"
      :disabled="!isValid || loading"
      class="w-full py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
    >
      {{ loading ? 'Submitting...' : 'Submit' }}
    </button>
  </form>
</template>
```

---

## Hook/Composable

### React Hook
```tsx
import { useState, useEffect, useCallback } from 'react';

interface UseAsyncResult<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
  refresh: () => void;
}

export function useAsync<T>(
  asyncFn: () => Promise<T>,
  deps: unknown[] = []
): UseAsyncResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const execute = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await asyncFn();
      setData(result);
    } catch (e) {
      setError(e as Error);
    } finally {
      setLoading(false);
    }
  }, deps);

  useEffect(() => {
    execute();
  }, [execute]);

  return { data, loading, error, refresh: execute };
}

// 使用
const { data: users, loading } = useAsync(() => fetchUsers(), []);
```

### Vue Composable
```typescript
import { ref, onMounted } from 'vue';

interface UseAsyncResult<T> {
  data: Ref<T | null>;
  loading: Ref<boolean>;
  error: Ref<Error | null>;
  refresh: () => Promise<void>;
}

export function useAsync<T>(
  asyncFn: () => Promise<T>
): UseAsyncResult<T> {
  const data = ref<T | null>(null) as Ref<T | null>;
  const loading = ref(true);
  const error = ref<Error | null>(null);

  const execute = async () => {
    try {
      loading.value = true;
      error.value = null;
      data.value = await asyncFn();
    } catch (e) {
      error.value = e as Error;
    } finally {
      loading.value = false;
    }
  };

  onMounted(execute);

  return { data, loading, error, refresh: execute };
}

// 使用
const { data: users, loading } = useAsync(() => fetchUsers());
```

---

## API 服务

### HTTP 客户端
```typescript
// services/http.ts
import axios from 'axios';
import type { AxiosInstance, AxiosRequestConfig } from 'axios';

const http: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
});

// 请求拦截器
http.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截器
http.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      // 处理未授权
    }
    return Promise.reject(error);
  }
);

export { http };
```

### API 模块
```typescript
// services/api/user.ts
import { http } from '../http';
import type { User, CreateUserReq, UpdateUserReq } from '@/types';

export const userApi = {
  async list(): Promise<User[]> {
    return http.get('/users');
  },

  async getById(id: string): Promise<User> {
    return http.get(`/users/${id}`);
  },

  async create(data: CreateUserReq): Promise<User> {
    return http.post('/users', data);
  },

  async update(id: string, data: UpdateUserReq): Promise<User> {
    return http.put(`/users/${id}`, data);
  },

  async delete(id: string): Promise<void> {
    return http.delete(`/users/${id}`);
  }
};
```

---

## Store

### Zustand (React)
```typescript
// stores/user.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User } from '@/types';

interface UserState {
  user: User | null;
  token: string | null;
  isLoggedIn: boolean;
  login: (user: User, token: string) => void;
  logout: () => void;
  updateUser: (data: Partial<User>) => void;
}

export const useUserStore = create<UserState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isLoggedIn: false,

      login: (user, token) => set({
        user,
        token,
        isLoggedIn: true
      }),

      logout: () => set({
        user: null,
        token: null,
        isLoggedIn: false
      }),

      updateUser: (data) => set((state) => ({
        user: state.user ? { ...state.user, ...data } : null
      }))
    }),
    {
      name: 'user-storage',
      partialize: (state) => ({ token: state.token })
    }
  )
);
```

### Pinia (Vue)
```typescript
// stores/user.ts
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { User } from '@/types';

export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null);
  const token = ref<string | null>(null);

  const isLoggedIn = computed(() => !!token.value);

  function login(newUser: User, newToken: string) {
    user.value = newUser;
    token.value = newToken;
  }

  function logout() {
    user.value = null;
    token.value = null;
  }

  function updateUser(data: Partial<User>) {
    if (user.value) {
      user.value = { ...user.value, ...data };
    }
  }

  return {
    user,
    token,
    isLoggedIn,
    login,
    logout,
    updateUser
  };
}, {
  persist: {
    paths: ['token']
  }
});
```
