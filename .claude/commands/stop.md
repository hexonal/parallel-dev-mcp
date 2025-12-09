---
description: 停止 ParallelDev 执行
arguments:
  - name: force
    description: 强制停止（不等待当前任务完成）
    required: false
---

请执行以下命令停止 ParallelDev：

```bash
pdev stop ${force:+--force}
```
