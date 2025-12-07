---
name: go-development
description: Go 开发规范 - Go 1.23+ 最佳实践
triggers:
  - Go
  - Golang
  - go.mod
---

# Go Development Skill

Go 1.23+ 开发规范。

## 代码规范
- 使用 gofmt 格式化
- golangci-lint 检查
- 表驱动测试

## 项目结构
- cmd/：入口点
- internal/：私有包
- pkg/：公共包
