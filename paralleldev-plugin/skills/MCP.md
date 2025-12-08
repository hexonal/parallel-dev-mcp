# MCP 工具参考

本文档定义了 ParallelDev Skills 可用的 MCP 服务器及其用途映射。

---

## 可用 MCP 服务器

| 工具 | 命令 | 用途 |
|------|------|------|
| sequential-thinking | `bunx @modelcontextprotocol/server-sequential-thinking` | 复杂问题分析、架构设计、多步推理 |
| context7 | `bunx @upstash/context7-mcp@latest` | 官方文档查询、API 参考、框架最佳实践 |
| git-config | `uvx mcp-git-config` | Git 用户信息获取、仓库配置 |
| mcp-datetime | `uvx mcp-datetime` | 时间戳生成、日期格式化 |
| deepwiki | `bunx mcp-deepwiki@latest` | 深度技术知识查询、开源项目文档 |
| playwright | `npx @anthropic-ai/mcp-server-playwright` | E2E 测试、浏览器自动化、可视化验证 |

---

## Skill → MCP 全量映射

| Skill | MCP 工具 |
|-------|----------|
| typescript-development | sequential-thinking, context7, deepwiki, git-config, mcp-datetime |
| frontend-development | sequential-thinking, context7, deepwiki, playwright, git-config, mcp-datetime |
| go-development | sequential-thinking, context7, deepwiki, git-config, mcp-datetime |
| java-development | sequential-thinking, context7, deepwiki, git-config, mcp-datetime |
| parallel-executor | sequential-thinking, context7, deepwiki, git-config, mcp-datetime |
| conflict-resolution | sequential-thinking, context7, deepwiki, git-config, mcp-datetime |
| quality-assurance | sequential-thinking, context7, deepwiki, playwright, git-config, mcp-datetime |

---

## 工具用途说明

### sequential-thinking
- 架构设计和系统分析
- 复杂问题拆解和多步推理
- 依赖关系分析和决策支持

### context7
- 官方框架文档查询（React、Vue、Spring、Go 等）
- API 参考和最佳实践获取
- 版本特定的文档查阅

### deepwiki
- 开源项目深度文档
- 技术栈知识库查询
- 生态系统工具文档

### git-config
- Git 用户信息获取
- 仓库配置检查
- 分支和远程配置

### mcp-datetime
- 时间戳生成（报告、日志）
- 日期格式化
- 时区处理

### playwright
- E2E 测试执行
- 浏览器自动化
- 可视化验证和截图

---

## 使用原则

1. **按需使用**: 根据当前任务选择合适的 MCP 工具
2. **组合使用**: 复杂任务可组合多个工具（如 sequential-thinking + context7）
3. **优先级**: context7 > deepwiki（官方文档优先）
4. **效率考虑**: 简单任务无需启用所有 MCP
