# React 18+ 开发规范

## 目录
- [Hooks 规范](#hooks-规范)
- [组件模式](#组件模式)
- [性能优化](#性能优化)
- [测试规范](#测试规范)

---

## Hooks 规范

### useState
```tsx
// ✅ 正确：类型明确
const [user, setUser] = useState<User | null>(null);
const [count, setCount] = useState(0);

// ✅ 正确：惰性初始化
const [data, setData] = useState(() => expensiveComputation());

// ❌ 错误：类型不明确
const [user, setUser] = useState();
```

### useEffect
```tsx
// ✅ 正确：明确依赖项
useEffect(() => {
  fetchUser(userId);
}, [userId]);

// ✅ 正确：清理函数
useEffect(() => {
  const subscription = subscribe();
  return () => subscription.unsubscribe();
}, []);

// ❌ 错误：缺少依赖
useEffect(() => {
  fetchUser(userId);
}, []); // userId 应该在依赖数组中
```

### useMemo / useCallback
```tsx
// ✅ 正确：昂贵计算使用 useMemo
const sortedList = useMemo(() => {
  return list.sort((a, b) => a.name.localeCompare(b.name));
}, [list]);

// ✅ 正确：回调函数使用 useCallback
const handleClick = useCallback((id: string) => {
  onSelect(id);
}, [onSelect]);

// ❌ 避免：简单值不需要 useMemo
const total = useMemo(() => a + b, [a, b]); // 过度优化
```

### 自定义 Hook
```tsx
/**
 * 用户信息 Hook
 */
function useUser(userId: string) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    setLoading(true);
    fetchUser(userId)
      .then(setUser)
      .catch(setError)
      .finally(() => setLoading(false));
  }, [userId]);

  return { user, loading, error };
}

// 使用
function UserProfile({ userId }: Props) {
  const { user, loading, error } = useUser(userId);

  if (loading) return <Spinner />;
  if (error) return <Error message={error.message} />;
  return <Profile user={user} />;
}
```

---

## 组件模式

### 函数组件标准结构
```tsx
import { useState, useCallback } from 'react';
import type { FC } from 'react';

interface Props {
  title: string;
  onSubmit: (data: FormData) => void;
}

export const MyComponent: FC<Props> = ({ title, onSubmit }) => {
  // 1. State
  const [value, setValue] = useState('');

  // 2. 派生状态
  const isValid = value.length > 0;

  // 3. 事件处理
  const handleChange = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    setValue(e.target.value);
  }, []);

  const handleSubmit = useCallback(() => {
    if (isValid) {
      onSubmit({ value });
    }
  }, [isValid, value, onSubmit]);

  // 4. 渲染
  return (
    <div>
      <h1>{title}</h1>
      <input value={value} onChange={handleChange} />
      <button onClick={handleSubmit} disabled={!isValid}>
        Submit
      </button>
    </div>
  );
};
```

### 组合组件模式
```tsx
// 父组件
interface CardProps {
  children: React.ReactNode;
}

function Card({ children }: CardProps) {
  return <div className="card">{children}</div>;
}

// 子组件
Card.Header = function CardHeader({ children }: { children: React.ReactNode }) {
  return <div className="card-header">{children}</div>;
};

Card.Body = function CardBody({ children }: { children: React.ReactNode }) {
  return <div className="card-body">{children}</div>;
};

// 使用
<Card>
  <Card.Header>Title</Card.Header>
  <Card.Body>Content</Card.Body>
</Card>
```

### Render Props 模式
```tsx
interface RenderProps<T> {
  data: T;
  loading: boolean;
  error: Error | null;
}

interface FetcherProps<T> {
  url: string;
  children: (props: RenderProps<T>) => React.ReactNode;
}

function Fetcher<T>({ url, children }: FetcherProps<T>) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    fetch(url)
      .then(res => res.json())
      .then(setData)
      .catch(setError)
      .finally(() => setLoading(false));
  }, [url]);

  return <>{children({ data: data as T, loading, error })}</>;
}

// 使用
<Fetcher<User[]> url="/api/users">
  {({ data, loading, error }) => {
    if (loading) return <Spinner />;
    if (error) return <Error />;
    return <UserList users={data} />;
  }}
</Fetcher>
```

---

## 性能优化

### React.memo
```tsx
// 仅当 props 变化时重新渲染
const ExpensiveList = React.memo(function ExpensiveList({ items }: Props) {
  return (
    <ul>
      {items.map(item => <li key={item.id}>{item.name}</li>)}
    </ul>
  );
});

// 自定义比较函数
const UserCard = React.memo(
  function UserCard({ user }: Props) {
    return <div>{user.name}</div>;
  },
  (prevProps, nextProps) => prevProps.user.id === nextProps.user.id
);
```

### 虚拟列表
```tsx
import { useVirtualizer } from '@tanstack/react-virtual';

function VirtualList({ items }: Props) {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 50,
  });

  return (
    <div ref={parentRef} style={{ height: '400px', overflow: 'auto' }}>
      <div style={{ height: virtualizer.getTotalSize() }}>
        {virtualizer.getVirtualItems().map((virtualRow) => (
          <div
            key={virtualRow.key}
            style={{
              position: 'absolute',
              top: virtualRow.start,
              height: virtualRow.size,
            }}
          >
            {items[virtualRow.index].name}
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

## 测试规范

### 组件测试
```tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { Button } from './Button';

describe('Button', () => {
  it('renders with text', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Click</Button>);

    fireEvent.click(screen.getByText('Click'));

    expect(onClick).toHaveBeenCalledOnce();
  });

  it('is disabled when loading', () => {
    render(<Button loading>Submit</Button>);
    expect(screen.getByRole('button')).toBeDisabled();
  });
});
```

### Hook 测试
```tsx
import { renderHook, act } from '@testing-library/react';
import { useCounter } from './useCounter';

describe('useCounter', () => {
  it('increments counter', () => {
    const { result } = renderHook(() => useCounter());

    act(() => {
      result.current.increment();
    });

    expect(result.current.count).toBe(1);
  });
});
```
