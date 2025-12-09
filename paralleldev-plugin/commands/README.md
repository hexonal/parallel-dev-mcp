# ParallelDev 斜杠命令编写规范

## 命令文件格式

```markdown
---
description: 简短描述（必需）
arguments:       # 可选
  - name: argName
    description: 参数说明
    required: true/false
---

请执行以下命令：   <-- 使用祈使句！

```bash
实际要执行的命令
```

然后说明期望的输出格式。
```

## 正确示例 ✅

```markdown
请执行以下命令查看状态：
```bash
cat .pdev/state.json
```
根据结果以表格展示。
```

## 错误示例 ❌

```markdown
# /status - 查看状态
这个命令用于显示状态...
## 命令
```bash
pdev status
```
```

**问题**：这是描述性文档，Claude 会自己编造输出而不是执行命令。

## 核心原则

1. **使用祈使句**：「请执行」「运行」「读取」
2. **明确数据来源**：指定要读取的文件或执行的命令
3. **指定输出格式**：告诉 Claude 如何展示结果
4. **避免描述性文字**：不要写"这个命令是..."
