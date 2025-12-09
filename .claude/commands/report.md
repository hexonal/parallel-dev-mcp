---
description: 生成执行报告
arguments:
  - name: format
    description: 输出格式（markdown/json）
    required: false
---

请执行以下命令生成报告：

```bash
pdev report --format "${format:-markdown}"
```
