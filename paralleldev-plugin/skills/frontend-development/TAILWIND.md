# Tailwind CSS v4 参考

## 目录
- [布局](#布局)
- [间距](#间距)
- [颜色](#颜色)
- [排版](#排版)
- [响应式](#响应式)
- [状态变体](#状态变体)
- [常用组合](#常用组合)

---

## 布局

### Flexbox
```html
<!-- 水平居中 -->
<div class="flex justify-center">

<!-- 垂直居中 -->
<div class="flex items-center">

<!-- 水平垂直居中 -->
<div class="flex items-center justify-center">

<!-- 两端对齐 -->
<div class="flex justify-between">

<!-- 均匀分布 -->
<div class="flex justify-evenly">

<!-- 间距 -->
<div class="flex gap-4">

<!-- 方向 -->
<div class="flex flex-col">
<div class="flex flex-row">

<!-- 换行 -->
<div class="flex flex-wrap">

<!-- 增长/收缩 -->
<div class="flex-1">      <!-- grow + shrink -->
<div class="flex-none">   <!-- 不增长不收缩 -->
<div class="grow">        <!-- 只增长 -->
<div class="shrink-0">    <!-- 不收缩 -->
```

### Grid
```html
<!-- 基础网格 -->
<div class="grid grid-cols-3 gap-4">

<!-- 响应式列数 -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3">

<!-- 跨列 -->
<div class="col-span-2">
<div class="col-span-full">

<!-- 自动填充 -->
<div class="grid grid-cols-[repeat(auto-fill,minmax(200px,1fr))]">
```

### 定位
```html
<div class="relative">
<div class="absolute top-0 right-0">
<div class="fixed inset-0">
<div class="sticky top-0">

<!-- 层级 -->
<div class="z-10">
<div class="z-50">
```

---

## 间距

### Padding
```html
<div class="p-4">      <!-- 四周 16px -->
<div class="px-4">     <!-- 左右 16px -->
<div class="py-4">     <!-- 上下 16px -->
<div class="pt-4">     <!-- 上 16px -->
<div class="pb-4">     <!-- 下 16px -->
<div class="pl-4">     <!-- 左 16px -->
<div class="pr-4">     <!-- 右 16px -->
```

### Margin
```html
<div class="m-4">      <!-- 四周 16px -->
<div class="mx-auto">  <!-- 水平居中 -->
<div class="my-4">     <!-- 上下 16px -->
<div class="mt-4">     <!-- 上 16px -->
<div class="mb-4">     <!-- 下 16px -->
<div class="-mt-4">    <!-- 负边距 -->
```

### 间距值对照
| 类名 | 值 |
|------|-----|
| 0 | 0px |
| 1 | 4px |
| 2 | 8px |
| 3 | 12px |
| 4 | 16px |
| 5 | 20px |
| 6 | 24px |
| 8 | 32px |
| 10 | 40px |
| 12 | 48px |
| 16 | 64px |

### Space Between
```html
<!-- 子元素间距 -->
<div class="space-y-4">  <!-- 垂直间距 -->
<div class="space-x-4">  <!-- 水平间距 -->
```

---

## 颜色

### 文字颜色
```html
<span class="text-gray-900">     <!-- 深灰 -->
<span class="text-gray-500">     <!-- 中灰 -->
<span class="text-blue-600">     <!-- 蓝色 -->
<span class="text-red-500">      <!-- 红色 -->
<span class="text-green-500">    <!-- 绿色 -->
<span class="text-white">        <!-- 白色 -->
```

### 背景颜色
```html
<div class="bg-white">
<div class="bg-gray-100">
<div class="bg-blue-500">
<div class="bg-transparent">
<div class="bg-black/50">       <!-- 50% 透明度 -->
```

### 边框颜色
```html
<div class="border border-gray-200">
<div class="border-2 border-blue-500">
```

---

## 排版

### 字体大小
```html
<span class="text-xs">     <!-- 12px -->
<span class="text-sm">     <!-- 14px -->
<span class="text-base">   <!-- 16px -->
<span class="text-lg">     <!-- 18px -->
<span class="text-xl">     <!-- 20px -->
<span class="text-2xl">    <!-- 24px -->
<span class="text-3xl">    <!-- 30px -->
```

### 字重
```html
<span class="font-light">     <!-- 300 -->
<span class="font-normal">    <!-- 400 -->
<span class="font-medium">    <!-- 500 -->
<span class="font-semibold">  <!-- 600 -->
<span class="font-bold">      <!-- 700 -->
```

### 文本对齐
```html
<p class="text-left">
<p class="text-center">
<p class="text-right">
```

### 截断
```html
<p class="truncate">           <!-- 单行截断 -->
<p class="line-clamp-2">       <!-- 多行截断 -->
```

---

## 响应式

### 断点
| 前缀 | 最小宽度 |
|------|----------|
| sm | 640px |
| md | 768px |
| lg | 1024px |
| xl | 1280px |
| 2xl | 1536px |

### 使用
```html
<!-- 移动优先 -->
<div class="w-full md:w-1/2 lg:w-1/3">

<!-- 隐藏/显示 -->
<div class="hidden md:block">    <!-- 移动端隐藏 -->
<div class="block md:hidden">    <!-- 桌面端隐藏 -->

<!-- 响应式字体 -->
<h1 class="text-xl md:text-2xl lg:text-3xl">

<!-- 响应式间距 -->
<div class="p-4 md:p-6 lg:p-8">
```

---

## 状态变体

### 交互状态
```html
<button class="bg-blue-500 hover:bg-blue-600">
<button class="opacity-100 active:opacity-80">
<input class="border focus:border-blue-500 focus:ring-2">
<button class="disabled:opacity-50 disabled:cursor-not-allowed">
```

### 组状态
```html
<div class="group">
  <span class="group-hover:text-blue-500">
</div>
```

### 深色模式
```html
<div class="bg-white dark:bg-gray-900">
<span class="text-gray-900 dark:text-white">
```

---

## 常用组合

### 卡片
```html
<div class="bg-white rounded-lg shadow p-6">
  <h2 class="text-lg font-semibold mb-2">标题</h2>
  <p class="text-gray-600">内容</p>
</div>
```

### 按钮
```html
<!-- 主按钮 -->
<button class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50">
  提交
</button>

<!-- 次按钮 -->
<button class="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50">
  取消
</button>
```

### 输入框
```html
<input
  class="w-full px-3 py-2 border border-gray-300 rounded focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
  placeholder="请输入"
/>
```

### 头像
```html
<img class="w-10 h-10 rounded-full object-cover" src="..." alt="avatar" />
```

### Badge
```html
<span class="px-2 py-1 text-xs bg-green-100 text-green-800 rounded-full">
  成功
</span>
```

### 列表
```html
<ul class="divide-y divide-gray-200">
  <li class="py-3">Item 1</li>
  <li class="py-3">Item 2</li>
</ul>
```

### 弹性容器
```html
<div class="min-h-screen flex flex-col">
  <header class="h-16">Header</header>
  <main class="flex-1">Content</main>
  <footer class="h-16">Footer</footer>
</div>
```
