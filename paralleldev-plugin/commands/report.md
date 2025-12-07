---
description: 生成执行报告
arguments:
  - name: format
    description: 输出格式（markdown/json）
    required: false
---

# /pd:report - 生成报告

生成当前执行会话的报告。

## 命令

```bash
node dist/cli-parallel.js report --format "${format:-markdown}"
```
