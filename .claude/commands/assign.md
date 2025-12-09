---
description: 手动分配任务给指定 Worker
arguments:
  - name: taskId
    description: 任务 ID
    required: true
  - name: workerId
    description: Worker ID
    required: true
---

请执行以下命令分配任务：

```bash
pdev assign --task "${taskId}" --worker "${workerId}"
```
