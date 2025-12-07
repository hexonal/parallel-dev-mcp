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

# /pd:assign - 手动分配任务

将指定任务分配给指定 Worker。

## 命令

```bash
node dist/cli-parallel.js assign --task "${taskId}" --worker "${workerId}"
```
