---
description: 启动 ParallelDev 并行执行系统
arguments:
  - name: prd
    description: PRD 文件路径
    required: true
  - name: workers
    description: Worker 数量（默认 3）
    required: false
---

请执行以下命令启动 ParallelDev：

```bash
pdev start --prd ${prd} --workers ${workers:-3}
```

如果 pdev 命令不可用，使用：
```bash
node /path/to/parallel-dev-mcp/dist/cli-parallel.js start --prd ${prd} --workers ${workers:-3}
```
