# parallel-dev-mcp


---

# ParallelDev 集成

本项目已集成 ParallelDev 并行开发系统。

## 可用命令
- `/status` - 查看 ParallelDev 当前状态
- `/start --prd <file>` - 启动并行开发
- `/stop` - 停止执行
- `/report` - 生成执行报告

## 配置文件
- `.pdev/config.json` - ParallelDev 配置
- `.pdev/state.json` - 当前执行状态
- `.pdev/tasks/tasks.json` - 任务列表
- `.pdev/CLAUDE.md` - Worker 级指令

## 使用流程
1. `pdev generate --prd prd.md` - 从 PRD 生成任务
2. `pdev start --prd prd.md` - 启动并行执行
3. `pdev status` - 监控执行状态
4. `pdev report` - 查看执行报告
