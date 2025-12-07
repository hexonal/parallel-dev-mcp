---
description: 启动 ParallelDev 并行执行系统
arguments:
  - name: tasks
    description: 任务文件路径（默认 .taskmaster/tasks/tasks.json）
    required: false
  - name: workers
    description: Worker 数量（默认 3）
    required: false
---

# /pd:start - 启动并行执行

启动 ParallelDev 系统，开始并行执行任务。

## 执行步骤

1. 加载任务文件 `${tasks:-.taskmaster/tasks/tasks.json}`
2. 验证任务依赖图无循环
3. 启动 ${workers:-3} 个 Worker
4. 开始事件驱动调度循环

## 命令

```bash
cd ${projectRoot}
node dist/cli-parallel.js run --tasks "${tasks}" --workers ${workers:-3}
```
