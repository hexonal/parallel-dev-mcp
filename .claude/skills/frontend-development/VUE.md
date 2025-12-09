# Vue 3 / Nuxt 3 开发规范

## 目录
- [Composition API](#composition-api)
- [组件规范](#组件规范)
- [Nuxt 3 规范](#nuxt-3-规范)
- [Pinia 状态管理](#pinia-状态管理)

---

## Composition API

### 基础用法
```vue
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';

// Props
interface Props {
  title: string;
  count?: number;
}
const props = withDefaults(defineProps<Props>(), {
  count: 0
});

// Emits
const emit = defineEmits<{
  update: [value: string];
  submit: [];
}>();

// State
const value = ref('');
const loading = ref(false);

// Computed
const isValid = computed(() => value.value.length > 0);

// Methods
const handleSubmit = () => {
  if (isValid.value) {
    emit('submit');
  }
};

// Lifecycle
onMounted(() => {
  console.log('mounted');
});
</script>

<template>
  <div>
    <h1>{{ title }}</h1>
    <input v-model="value" />
    <button @click="handleSubmit" :disabled="!isValid">
      Submit
    </button>
  </div>
</template>
```

### Composables
```typescript
// composables/useUser.ts
import { ref, computed } from 'vue';
import type { User } from '@/types';

export function useUser(userId: string) {
  const user = ref<User | null>(null);
  const loading = ref(true);
  const error = ref<Error | null>(null);

  const displayName = computed(() => {
    return user.value?.name ?? 'Unknown';
  });

  const fetchUser = async () => {
    try {
      loading.value = true;
      const res = await fetch(`/api/users/${userId}`);
      user.value = await res.json();
    } catch (e) {
      error.value = e as Error;
    } finally {
      loading.value = false;
    }
  };

  // 立即获取
  fetchUser();

  return {
    user,
    loading,
    error,
    displayName,
    refresh: fetchUser
  };
}

// 使用
const { user, loading, displayName } = useUser('123');
```

### watch / watchEffect
```typescript
import { ref, watch, watchEffect } from 'vue';

const userId = ref('');
const user = ref<User | null>(null);

// watch: 显式依赖
watch(userId, async (newId) => {
  if (newId) {
    user.value = await fetchUser(newId);
  }
});

// watchEffect: 自动依赖收集
watchEffect(async () => {
  if (userId.value) {
    user.value = await fetchUser(userId.value);
  }
});

// 立即执行
watch(userId, callback, { immediate: true });

// 深度监听
watch(user, callback, { deep: true });
```

---

## 组件规范

### SFC 结构顺序
```vue
<script setup lang="ts">
// 1. 类型导入
import type { User } from '@/types';

// 2. 组件导入
import UserCard from './UserCard.vue';

// 3. Composables
import { useUser } from '@/composables/useUser';

// 4. Props & Emits
const props = defineProps<{ id: string }>();
const emit = defineEmits<{ update: [User] }>();

// 5. State (ref/reactive)
const loading = ref(false);

// 6. Computed
const isValid = computed(() => true);

// 7. Methods
const handleSubmit = () => {};

// 8. Lifecycle
onMounted(() => {});

// 9. Expose (如需要)
defineExpose({ refresh });
</script>

<template>
  <!-- 模板 -->
</template>

<style scoped>
/* 样式 - 优先使用 Tailwind */
</style>
```

### Props 定义
```typescript
// ✅ 正确：TypeScript 类型定义
interface Props {
  title: string;
  count?: number;
  user: User;
  items: string[];
}

const props = withDefaults(defineProps<Props>(), {
  count: 0,
  items: () => []
});

// ❌ 避免：运行时定义（除非需要验证器）
const props = defineProps({
  title: { type: String, required: true }
});
```

### Emits 定义
```typescript
// ✅ 正确：类型化 emits
const emit = defineEmits<{
  'update:modelValue': [value: string];
  submit: [data: FormData];
  cancel: [];
}>();

// 使用
emit('update:modelValue', newValue);
emit('submit', formData);
```

---

## Nuxt 3 规范

### 目录结构
```
nuxt-app/
├── components/          # 自动导入
│   ├── ui/
│   │   └── Button.vue   # <UiButton />
│   └── TheHeader.vue    # <TheHeader />
├── composables/         # 自动导入
│   └── useUser.ts       # useUser()
├── pages/               # 文件路由
│   ├── index.vue        # /
│   ├── users/
│   │   ├── index.vue    # /users
│   │   └── [id].vue     # /users/:id
├── layouts/             # 布局
│   └── default.vue
├── middleware/          # 路由中间件
├── plugins/             # 插件
├── server/              # 服务端 API
│   └── api/
│       └── users.ts     # /api/users
└── nuxt.config.ts
```

### 数据获取
```vue
<script setup lang="ts">
// useFetch: 自动处理 SSR
const { data: user, pending, error, refresh } = await useFetch<User>(
  `/api/users/${route.params.id}`
);

// useAsyncData: 更灵活
const { data } = await useAsyncData('user', () => {
  return $fetch(`/api/users/${route.params.id}`);
});

// 仅客户端
const { data } = await useFetch('/api/data', {
  server: false
});

// 懒加载
const { data, pending } = await useLazyFetch('/api/data');
</script>
```

### 路由
```vue
<script setup lang="ts">
const route = useRoute();
const router = useRouter();

// 路由参数
const userId = route.params.id;
const query = route.query.search;

// 导航
router.push('/users');
router.push({ name: 'users-id', params: { id: '123' } });

// 中间件
definePageMeta({
  middleware: 'auth',
  layout: 'admin'
});
</script>
```

### Server API
```typescript
// server/api/users/[id].ts
export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id');
  const query = getQuery(event);

  // POST body
  const body = await readBody(event);

  // 响应
  return { id, name: 'User' };

  // 错误
  throw createError({
    statusCode: 404,
    message: 'User not found'
  });
});
```

---

## Pinia 状态管理

### Store 定义
```typescript
// stores/user.ts
import { defineStore } from 'pinia';

interface UserState {
  user: User | null;
  token: string | null;
}

export const useUserStore = defineStore('user', () => {
  // State
  const user = ref<User | null>(null);
  const token = ref<string | null>(null);

  // Getters
  const isLoggedIn = computed(() => !!token.value);
  const displayName = computed(() => user.value?.name ?? 'Guest');

  // Actions
  async function login(credentials: LoginReq) {
    const res = await authApi.login(credentials);
    user.value = res.user;
    token.value = res.token;
  }

  function logout() {
    user.value = null;
    token.value = null;
  }

  return {
    user,
    token,
    isLoggedIn,
    displayName,
    login,
    logout
  };
});
```

### Store 使用
```vue
<script setup lang="ts">
import { useUserStore } from '@/stores/user';
import { storeToRefs } from 'pinia';

const userStore = useUserStore();

// ✅ 正确：响应式解构
const { user, isLoggedIn } = storeToRefs(userStore);

// Actions 直接使用
const handleLogout = () => userStore.logout();
</script>
```

### Store 持久化
```typescript
// plugins/pinia-persist.ts
import { createPinia } from 'pinia';
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate';

const pinia = createPinia();
pinia.use(piniaPluginPersistedstate);

// store 中启用
export const useUserStore = defineStore('user', () => {
  // ...
}, {
  persist: {
    storage: localStorage,
    paths: ['token']
  }
});
```
