---
description: 停止 ParallelDev 执行
arguments:
  - name: force
    description: 强制停止（不等待当前任务完成）
    required: false
---

# /pd:stop - 停止执行

停止并行执行系统。

## 命令

```bash
node dist/cli-parallel.js stop ${force:+--force}
```
