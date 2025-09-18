# Repository Guidelines

This guide helps contributors and automation agents work consistently in this repo.

## Project Structure & Module Organization
- Source code: `src/parallel_dev_mcp/` (four-layer tools: tmux, session, monitoring, orchestrator) and aggregator exports in `src/mcp_tools/`.
- Entry points: `src/parallel_dev_mcp/server.py` (`main()`), `src/mcp_tools/__main__.py`.
- Tests: `tests/` (unittest-style, pytest-compatible).
- Examples & docs: `examples/`, `docs/`.
- Config: `pyproject.toml` (deps, black, ruff), `uv.lock`, optional `mcp.json` for MCP server configs.

## Build, Test, and Development Commands
- Install deps (with dev tools): `uv sync --extra dev`
- Run MCP server locally: `uv run python -m src.parallel_dev_mcp.server`
- Use tools module: `uv run python -m src.mcp_tools`
- Console script (if installed): `uv run parallel-dev-mcp`
- Tests: `uv run pytest -q`
- Lint: `uv run ruff check .`
- Format: `uv run black .` (check only: `--check`)

## Coding Style & Naming Conventions
- Python 3.11+, 4-space indentation, line length 88 (black/ruff).
- Modules and files: `snake_case`. Classes: `CamelCase`. Functions/vars: `snake_case`.
- Session names (tmux/MCP): `parallel_{PROJECT_ID}_task_master` and `parallel_{PROJECT_ID}_task_child_{TASK_ID}`.
- Keep functions small; place tmux/session/monitoring/orchestrator code in their respective subpackages.

## Testing Guidelines
- Framework: pytest discovering unittest tests in `tests/` (files: `test_*.py`).
- Run all: `uv run pytest -q`. Focused run: `uv run pytest -k session_coordinator -q`.
- Prefer fast, isolated unit tests; avoid external tmux dependencies in unit tests.

## Commit & Pull Request Guidelines
- Commit messages: prefer Conventional Commits (`feat:`, `fix:`, `refactor:`, `docs:`). Keep subject ≤ 72 chars; add a brief body when needed.
- PRs should include: clear description, linked issues, test coverage for changes, before/after logs or screenshots if behavior changes, and notes on configuration/env vars touched (e.g., `PROJECT_ID`, `MCP_CONFIG`, `DANGEROUSLY_SKIP_PERMISSIONS`).

## Security & Configuration Tips
- Do not hard-code absolute paths; accept `PROJECT_ID`, `MCP_CONFIG`, `HOOKS_CONFIG_DIR` via env.
- Be cautious with tmux operations; never destructively kill sessions outside tests.
- Validate and parse session names using the established patterns before acting.

## Agent-Specific Instructions
- Respect this structure when editing files; avoid cross-layer coupling.
- Run ruff/black before proposing changes. Keep patches minimal and focused.
- When adding tools, export via `src/mcp_tools/__init__.py` and document usage in `README.md`.

## Engineering Norms

- Function Limits
  - Keep each function/method ≤ 50 lines (including blank lines). Split complex logic into small, named helpers in the same module.
  - Prefer single-responsibility helpers with clear inputs/outputs. Avoid deep call chains across layers.

- Documentation & Comments
  - Add docstrings for all public functions and any non-trivial helpers (what it does, key args, returns, error paths).
  - Add brief inline comments for non-obvious decisions or protocol specifics (e.g., tmux two-step send, pre-send limit checks).

- Tmux Sending Rules
  - Only `src/parallel_dev_mcp/_internal/tmux_send_gateway.py` may execute `tmux send-keys`.
  - Always perform pre-send limit checks (pane capture + “5-hour limit” parsing). If limited, do not send; return structured info (limit_triggered, limit_reset_time).
  - CONTROL keys bypass limit check; other modes must check before sending.

- Health & Messaging
  - Health reports use `/message/health` only. Do not use `/message/send` as a fallback for health.
  - Child sessions report health every 5s to the master’s web service.
  - Code-activity detection is an internal heuristic only (non-blocking, no-wait). It must not be exposed as a public tool; only summarized activity labels may appear in read-only resources.
  - Monitoring resources use the `monitoring://` scheme (e.g., `monitoring://sessions`).

- Master Binding & Web Port (mcp.json env)
  - Configure via `mcp.json` env, not shell exports:
    - `MASTER_BASE`: master session name is `{MASTER_BASE}_master`. Binding failure must fail MCP startup.
    - `TMUX_WEB_PORT`: HTTP port for the master’s web service. If set but service fails to start, MCP startup fails.
  - Only the master owns `web_port`. Child sessions must not set it.

- Config Source Order
  - When reading env-like settings, follow: `loaded_config.env` → `loaded_config.environment.env/variables` → `loaded_config.mcpServers.*.env` → `os.environ`.

- Validation Before Merge
  - Self-check new/changed functions for line count (≤ 50) and clear docstrings/comments.
  - Ensure ruff/black pass, and limit surface area of changes to the requested scope.

## FastMCP 2.0 Quick Guide

This repo integrates with MCP tooling. Below is a concise, up-to-date reference for FastMCP 2.0 based on the latest docs gathered via Context7 and DeepWiki.

- Install
  - `uv pip install fastmcp`

- Minimal server
  - Python (`server.py`):
    ```python
    from fastmcp import FastMCP

    mcp = FastMCP("Demo 🚀")

    @mcp.tool
    def add(a: int, b: int) -> int:
        """Add two numbers"""
        return a + b

    if __name__ == "__main__":
        mcp.run()
    ```

- CLI essentials
  - Help: `fastmcp --help`
  - Run directly: `uv run fastmcp run server.py`
  - Inspect server: `uv run fastmcp inspect server.py`
  - Install into MCP clients (detects entrypoint automatically):
    - `fastmcp install claude-code server.py`
    - `fastmcp install claude-desktop server.py`
    - `fastmcp install cursor server.py`
    - Generate config: `fastmcp install mcp-json server.py`
  - Advanced install options:
    - Specify entrypoint: `fastmcp install claude-desktop server.py:mcp`
    - Name + deps: `fastmcp install claude-desktop server.py:mcp --server-name "My Server" --with pandas`
    - Env vars: `--env KEY=VALUE` or `--env-file .env`
    - Python version: `--python 3.11`
    - Requirements: `--with-requirements requirements.txt`

- `fastmcp.json` (example)
  ```json
  {
    "$schema": "https://gofastmcp.com/public/schemas/fastmcp.json/v1.json",
    "source": { "type": "filesystem", "path": "server.py", "entrypoint": "mcp" },
    "environment": { "type": "uv", "python": ">=3.10", "dependencies": ["pandas", "numpy"] },
    "deployment": { "transport": "stdio", "log_level": "INFO" }
  }
  ```

- HTTP deployment (recommended transport: streamable-http)
  - Programmatic: use `mcp.run(transport="http")` or `run_async()`
  - Key env/settings (defaults in parentheses):
    - `FASTMCP_HOST` (`127.0.0.1`), `FASTMCP_PORT` (`8000`)
    - `FASTMCP_STREAMABLE_HTTP_PATH` (`/mcp`)
    - `FASTMCP_SSE_PATH` (`/sse`) – legacy
    - `FASTMCP_DEBUG` (`false`), `FASTMCP_JSON_RESPONSE` (`false`)

- Client usage
  ```python
  from fastmcp import Client

  async def main():
    async with Client("stdio:python server.py") as client:
      result = await client.call_tool("add", {"a": 5, "b": 3})
      print(result.data)  # 8
  ```

- Resources and prompts
  ```python
  @mcp.resource("config://version")
  def get_version() -> str:
      return "2.0.1"

  @mcp.prompt
  def greet(name: str):
      return [
          {"role": "system", "content": "You are a helpful assistant."},
          {"role": "user", "content": f"Greet {name}"},
      ]
  ```

- Tool transformation (high level)
  - Create variants of existing tools by changing arg types/defaults, mapping names, or adding hidden args. See `fastmcp.tools.tool_transform` (ArgTransform, TransformedTool).

- Authentication (HTTP)
  - Supports Bearer/OAuth via providers (e.g., JWT verifier, RemoteAuthProvider). Configure via env like `FASTMCP_SERVER_AUTH_JWT_*`.

- Migration tip
  - Update imports from SDK to FastMCP 2.0:
    ```python
    # Before: from mcp.server.fastmcp import FastMCP
    from fastmcp import FastMCP
    ```

- Common tasks in this repo with FastMCP
  - Run a sample FastMCP server locally: `uv run fastmcp run server.py`
  - Generate MCP JSON for integration: `fastmcp install mcp-json server.py`
  - Use our test harnesses with stdio transports to avoid external dependencies.

Sources: Context7 /jlowin/fastmcp and DeepWiki jlowin/fastmcp (latest indexed).
### MCP工具集成开发

#### 自动化类注解生成

**MCP Git集成**：

- 自动获取Git用户信息作为author
- 自动获取提交时间作为创建时间
- 禁止手动设置作者和时间信息

**MCP DateTime集成**：

- 自动生成标准时间戳
- 支持多种日期格式
- 用于类创建时间字段
              
##### **标准类代码注释模板**：

```java
#if (${PACKAGE_NAME} && ${PACKAGE_NAME} != "")
package ${PACKAGE_NAME};
#end
#parse("File Header.java")
/**
 * 普通类
 *
 * @author {{通过MCP Git自动获取}}
 * @date {{通过MCP DateTime自动获取}}
 * @description ${NAME} 类
 */
public class ${NAME} {
}
```

```java
#if (${PACKAGE_NAME} && ${PACKAGE_NAME} != "")
package ${PACKAGE_NAME};
#end
#parse("File Header.java")
/**
 * 接口
 *
 * @author {{通过MCP Git自动获取}}
 * @date {{通过MCP DateTime自动获取}}
 * @description ${NAME} 接口
 */
public interface ${NAME} {
}
```

```java
#if (${PACKAGE_NAME} && ${PACKAGE_NAME} != "")
package ${PACKAGE_NAME};
#end
#parse("File Header.java")
/**
 * 枚举类
 * 
 * @author {{通过MCP Git自动获取}}
 * @date {{通过MCP DateTime自动获取}}
 * @description ${NAME} 枚举
 */
public enum ${NAME} {
}
```

```java
#if (${PACKAGE_NAME} && ${PACKAGE_NAME} != "")
package ${PACKAGE_NAME};
#end
#parse("File Header.java")
/**
 * 注解
 * 
 * @author {{通过MCP Git自动获取}}
 * @date {{通过MCP DateTime自动获取}}
 * @description ${NAME} 注解
 */
public @interface ${NAME} {
}
```

```java
#if (${PACKAGE_NAME} && ${PACKAGE_NAME} != "")
package ${PACKAGE_NAME};
#end
#parse("File Header.java")
/**
 * 自定义运行时异常类
 * 
 * @author {{通过MCP Git自动获取}}
 * @date {{通过MCP DateTime自动获取}}
 * @description ${NAME} 异常
 */
public class ${NAME} extends RuntimeException {
    public ${NAME}(String message) {
        super(message);
    }
}
```

```java
#parse("File Header.java")
/**
 * 主函数模板
 * 
 * @author {{通过MCP Git自动获取}}
 * @date {{通过MCP DateTime自动获取}}
 * @description 程序入口
 */
void main() {
  #[[$END$]]#
}
```

```java
#if (${PACKAGE_NAME} && ${PACKAGE_NAME} != "")
package ${PACKAGE_NAME};
#end
#parse("File Header.java")
/**
 * Record 类
 * 
 * @author {{通过MCP Git自动获取}}
 * @date {{通过MCP DateTime自动获取}}
 * @description ${NAME} 记录类
 */
public record ${NAME}() {
}
```


### 🟨 Go 模板
```go
// Package ${PACKAGE_NAME} 
//
// ${NAME} 模块
//
// @author {{通过MCP Git自动获取}}
// @date   {{通过MCP DateTime自动获取}}
// @description ${NAME} 功能实现
package ${PACKAGE_NAME}

// ${NAME} 结构体
type ${NAME} struct {
    // 字段定义
}
```

```go
// Package ${PACKAGE_NAME} 
//
// ${NAME} 接口
//
// @author {{通过MCP Git自动获取}}
// @date   {{通过MCP DateTime自动获取}}
// @description ${NAME} 接口定义
package ${PACKAGE_NAME}

// ${NAME} 接口
type ${NAME} interface {
    // 方法定义
}

```

```go
// Package ${PACKAGE_NAME} 
//
// ${NAME} 枚举常量
//
// @author {{通过MCP Git自动获取}}
// @date   {{通过MCP DateTime自动获取}}
// @description ${NAME} 枚举
package ${PACKAGE_NAME}

const (
    ${NAME}A = iota
    ${NAME}B
    ${NAME}C
)
```

```go
// Package ${PACKAGE_NAME} 
//
// ${NAME} 错误类型
//
// @author {{通过MCP Git自动获取}}
// @date   {{通过MCP DateTime自动获取}}
// @description ${NAME} 自定义错误
package ${PACKAGE_NAME}

import "fmt"

// ${NAME} 错误
type ${NAME} struct {
    msg string
}

func (e *${NAME}) Error() string {
    return fmt.Sprintf("${NAME} error: %s", e.msg)
}

```
         
## python 模板
```python
# -*- coding: utf-8 -*-
"""
${NAME} 模块

@author {{通过MCP Git自动获取}}
@date   {{通过MCP DateTime自动获取}}
@description ${NAME} 功能实现
"""

class ${NAME}:
    """
    ${NAME} 类
    """
    def __init__(self):
        # 属性初始化
        pass

```

```python
# -*- coding: utf-8 -*-
"""
${NAME} 接口 (抽象基类)

@author {{通过MCP Git自动获取}}
@date   {{通过MCP DateTime自动获取}}
@description ${NAME} 接口定义
"""

from abc import ABC, abstractmethod

class ${NAME}(ABC):
    @abstractmethod
    def execute(self):
        pass

```

```python
# -*- coding: utf-8 -*-
"""
${NAME} 枚举类

@author {{通过MCP Git自动获取}}
@date   {{通过MCP DateTime自动获取}}
@description ${NAME} 枚举
"""

from enum import Enum

class ${NAME}(Enum):
    OPTION_A = 1
    OPTION_B = 2
    OPTION_C = 3

```

```python
# -*- coding: utf-8 -*-
"""
${NAME} 自定义异常类

@author {{通过MCP Git自动获取}}
@date   {{通过MCP DateTime自动获取}}
@description ${NAME} 异常
"""

class ${NAME}(Exception):
    def __init__(self, message: str):
        super().__init__(message)


```
         
```python
# -*- coding: utf-8 -*-
"""
${NAME} 主函数脚本

@author {{通过MCP Git自动获取}}
@date   {{通过MCP DateTime自动获取}}
@description 程序入口
"""

def main():
    pass

if __name__ == "__main__":
    main()

```
