# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

对话的时候，始终使用的是中文

## 本项目为 Python 项目，采用 3.12 完成开发迭代 FastMCP 2.11.3+
- 基于最新 FastMCP 2.11.3+ 框架开发
- 采用 Python 优秀风格和最佳实践
- 使用 uv 作为包管理工具

## 🚨 严格开发规范 (2025最新标准)

### Python 代码质量严格标准

#### 函数长度严格限制
**🔴 强制要求**：
- **所有函数**: 不得超过50行（包含注释和空行）
- **超长处理**: 必须拆分为多个私有函数或使用设计模式
- **设计模式**: 优先使用工厂模式、策略模式、依赖注入
- **注释规范**: 禁止使用行尾注释，所有注释必须独立成行
- **函数文档**: 每个函数必须使用标准 docstring，包含功能说明、参数说明、返回值说明
- **步骤注释**: 函数体内部代码必须逐步编号注释（如 # 1. 初始化参数、# 2. 执行核心逻辑），覆盖所有逻辑步骤

#### Python 函数注释模板
```python
def function_name(param1: str, param2: int) -> str:
    """
    函数名：function_name
    描述：函数功能描述

    Args:
        param1 (str): 参数1描述
        param2 (int): 参数2描述

    Returns:
        str: 返回值描述

    Raises:
        ValueError: 参数无效时抛出
    """
    # 1. 初始化参数或对象

    # 2. 校验输入数据

    # 3. 执行核心逻辑

    # 4. 处理结果（如保存、返回、输出）

    # 5. 记录日志 / 异常处理

    # 6. 返回最终结果
    return result
```

#### 类型安全严格标准
**🔴 严格禁止**：
- `Dict[str, Any]` - 严禁在任何场景使用
- `Any` 类型 - 严禁作为函数参数或返回值
- **替代方案**: 必须创建类型安全的专用类或使用 Pydantic models

#### Python 推荐库和工具
**核心依赖**:
- `fastmcp>=2.11.3` - MCP 服务器框架
- `pydantic>=2.0.0` - 数据验证和序列化
- `typing_extensions` - 类型提示增强
- `psutil>=6.0.0` - 系统信息获取

**开发工具**:
- `black` - 代码格式化
- `ruff` - 快速代码检查和修复
- `pytest` - 单元测试框架
- `pytest-asyncio` - 异步测试支持

#### 数据模型设计严格标准
**🔴 强制要求**：
- **Pydantic Models**: 所有数据模型必须使用 Pydantic BaseModel
- **严禁嵌套**: Model 内避免深度嵌套其他复杂对象
- **扁平化设计**: 优先使用扁平结构，必要时使用组合模式
- **类型注解**: 所有字段必须有明确的类型注解

#### FastMCP 工具开发标准
**🔴 强制要求**：
- **@mcp.tool 装饰器**: 所有 MCP 工具必须使用正确的装饰器
- **类型注解**: 工具函数必须有完整的类型注解
- **文档字符串**: 工具描述必须清晰，用于 AI 理解
- **错误处理**: 必须有适当的异常处理机制

```python
@mcp.tool
def example_tool(param: str) -> str:
    """
    工具功能描述，这个描述会被 AI 看到

    Args:
        param: 参数描述

    Returns:
        处理结果描述
    """
    # 1. 参数验证
    if not param:
        raise ValueError("参数不能为空")

    # 2. 执行逻辑
    result = process_param(param)

    # 3. 返回结果
    return result
```

### 编译和部署严格标准

#### 代码质量强制要求
**🔴 强制要求**：
- **类型检查**: 使用 `mypy` 进行类型检查，必须通过
- **代码格式**: 使用 `black` 格式化，必须符合标准
- **代码检查**: 使用 `ruff` 检查，必须通过所有检查
- **测试覆盖**: 核心功能必须有单元测试

#### 项目结构标准
```
src/
├── parallel_dev_mcp/
│   ├── __init__.py
│   ├── server.py          # FastMCP 服务器入口
│   ├── tmux/              # Tmux 层工具
│   ├── session/           # 会话层工具
│   ├── monitoring/        # 监控层工具
│   └── _internal/         # 内部工具
tests/
├── test_*.py              # 测试文件
pyproject.toml             # 项目配置
```

### 禁用功能清单
**❌ 明确禁止**：
- **过度复杂化**: 避免引入不必要的企业级特性
- `Dict[str, Any]`: 任何场景下都禁止使用
- `Any` 类型: 禁止作为函数参数或返回值
- **行尾注释**: 所有注释必须独立成行
- **深度嵌套**: 避免过度嵌套的数据结构
- **过度设计模式**: 避免为了模式而模式，保持简洁



### MCP工具集成
项目集成了以下MCP工具以提供增强功能：
- **sequential-thinking**: 复杂问题分析和决策支持
- **context7**: 技术文档和API查询
- **deepwiki**: 深度技术知识查询
- **git-config**: Git仓库配置管理
- **mcp-datetime**: 时间戳生成
- **yapi-auto-mcp**: API文档自动化
- **其他的 mcp 均按需使用**

## 常用命令

### 开发环境设置
```bash
# 同步依赖
uv sync

# 安装开发依赖
uv sync --dev

# 进入虚拟环境
source .venv/bin/activate
```

### 代码质量检查
```bash
# 代码格式化
uv run black src/ tests/

# 代码检查和修复
uv run ruff check src/ tests/ --fix

# 类型检查
uv run mypy src/

# 运行所有质量检查
uv run black src/ tests/ && uv run ruff check src/ tests/ --fix && uv run mypy src/
```

### 测试命令
```bash
# 运行所有测试
uv run pytest

# 运行特定测试文件
uv run pytest tests/test_session_coordinator.py

# 运行测试并生成覆盖率报告
uv run pytest --cov=src --cov-report=html

# 运行异步测试
uv run pytest -v --asyncio-mode=auto
```

### FastMCP 服务器操作
```bash
# 启动 FastMCP 服务器 (STDIO 模式)


# 启动开发服务器 (HTTP 模式)
uv run python -c "
from src.parallel_dev_mcp.server import mcp
mcp.run(transport='http', host='127.0.0.1', port=8000)
"

# 使用 fastmcp dev 命令启动开发服务器
uv run fastmcp dev src/parallel_dev_mcp/server.py

# 直接运行 MCP 工具测试
uv run python -c "
from src.parallel_dev_mcp.tmux.orchestrator import tmux_session_orchestrator
result = tmux_session_orchestrator('init', 'TEST_PROJECT', ['TASK1'])
print(result)
"
```

### 项目构建和分发
```bash
# 构建项目
uv build

# 安装本地构建
uv pip install dist/parallel_dev_mcp-*.whl

# 使用 uvx 直接从 Git 运行
uvx --from git+https://github.com/your-repo/parallel-dev-mcp.git parallel-dev-mcp
```

### 调试和诊断
```bash
# 检查 MCP 工具注册情况
uv run python -c "
from src.parallel_dev_mcp.server import mcp
print('注册的工具:', [tool.name for tool in mcp._tools])
"

# 系统健康检查
uv run python -c "
from src.parallel_dev_mcp.monitoring.health_monitor import check_system_health
print(check_system_health())
"

# 查看 tmux 会话状态
tmux list-sessions | grep parallel_
```


## 架构概览

### FastMCP 四层架构设计规范

本项目基于 FastMCP 2.11.3+ 框架，采用清晰的四层分层架构：

```
🎯 ORCHESTRATOR LAYER (编排层) - 3个工具
   └── 项目级编排和生命周期管理

📊 MONITORING LAYER (监控层) - 5个工具
   └── 系统监控、诊断和状态仪表板

📋 SESSION LAYER (会话层) - 7个工具
   └── 细粒度会话管理和消息通信

🔧 TMUX LAYER (基础层) - 1个工具
   └── 纯MCP tmux会话编排
```

#### 🔧 Tmux层 - 基础会话编排
**核心职责**：
- **会话编排**: 基础 tmux 会话创建和管理
- **统一入口**: 提供所有层级的统一访问入口
- **零脚本依赖**: 完全基于 FastMCP 实现

**开发规范**：
```python
@mcp.tool
def tmux_session_orchestrator(action: str, project_id: str, tasks: List[str]) -> Dict[str, Any]:
    """
    Tmux 会话编排工具

    Args:
        action: 操作类型 (start, stop, init)
        project_id: 项目标识
        tasks: 任务列表

    Returns:
        Dict[str, Any]: 操作结果
    """
    # 实现逻辑
```

#### 📋 Session层 - 会话管理设计
**核心职责**：
- **会话创建**: 精细化会话创建和终止
- **消息系统**: 会话间消息通信
- **关系管理**: 主子会话关系维护

**开发规范**：
- 必须使用 FastMCP @mcp.tool 装饰器
- 所有函数不得超过50行
- 使用 Pydantic 进行数据验证
- 完整的类型注解和文档字符串

```python
@mcp.tool
def create_development_session(
    project_id: str,
    session_type: str,
    task_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    创建开发会话

    Args:
        project_id: 项目ID
        session_type: 会话类型 (master/child)
        task_id: 任务ID (child会话必需)

    Returns:
        Dict[str, Any]: 创建结果
    """
    # 实现逻辑
```

#### 📊 Monitoring层 - 监控系统设计
**核心职责**：
- **健康检查**: 系统状态监控
- **性能诊断**: 会话性能分析
- **状态仪表板**: 全面的监控数据展示

**开发规范**：
- 使用 psutil 进行系统监控
- 返回结构化的监控数据
- 支持详细和简化两种模式

#### 🎯 Orchestrator层 - 项目编排设计
**核心职责**：
- **工作流编排**: 完整项目生命周期管理
- **并行协调**: 多任务并行执行协调
- **生命周期**: 项目启动、运行、结束管理

#### Python 项目结构规范
```
src/
├── parallel_dev_mcp/
│   ├── __init__.py              # 包初始化
│   ├── server.py                # FastMCP 服务器入口
│   ├── tmux/                    # Tmux 层
│   │   ├── __init__.py
│   │   └── orchestrator.py      # 基础编排工具
│   ├── session/                 # Session 层
│   │   ├── __init__.py
│   │   ├── session_manager.py   # 会话管理
│   │   ├── message_system.py    # 消息系统
│   │   └── relationship_manager.py # 关系管理
│   ├── monitoring/              # Monitoring 层
│   │   ├── __init__.py
│   │   └── health_monitor.py    # 健康监控
│   └── _internal/               # 内部工具
│       ├── __init__.py
│       ├── config_tools.py      # 配置工具
│       └── global_registry.py   # 全局注册表
tests/
├── test_session_coordinator.py  # 测试文件
pyproject.toml                   # 项目配置
```

#### 命名规范
- **MCP 工具**: 使用 snake_case 命名，如 `tmux_session_orchestrator`
- **函数命名**:
  - 创建：`create_*()`
  - 获取：`get_*()`
  - 查询：`query_*()`
  - 发送：`send_*()`
  - 注册：`register_*()`
  - 终止：`terminate_*()`
- **数据模型**: 使用 PascalCase + Model 后缀，如 `SessionInfoModel`
- **异常类**: 使用 PascalCase + Exception 后缀，如 `SessionNotFoundError`





## 🔧 系统健康检查和监控工具

本项目集成了完整的系统健康检查和监控工具集，提供全面的系统诊断和环境验证功能：

### 系统健康检查工具
- **system_health_check**: 全面的系统健康状态检查，包括Python环境、tmux可用性、项目结构、依赖包和文件权限
- **quick_system_status**: 快速系统状态检查，适用于频繁监控场景
- **diagnose_common_issues**: 自动检测和诊断常见问题，提供解决方案

### 环境变量测试工具
- **environment_variables_test**: 全面测试环境变量配置、继承、隔离和边界情况
- **check_critical_env_vars**: 检查关键环境变量的存在性和有效性
- **test_env_inheritance_isolation**: 测试环境变量在进程间的继承机制和隔离效果

### 项目依赖和兼容性检查
- **check_project_dependencies**: 检查项目依赖包的安装状态和版本兼容性
- **hooks_compatibility_check**: 检查examples/hooks/目录的兼容性和功能完整性

### 独立诊断脚本
项目还提供独立的诊断脚本，无需MCP依赖即可运行：
- `scripts/health_check.py` - 独立系统健康检查
- `scripts/env_test.py` - 独立环境变量测试
- `scripts/hooks_compatibility_check.py` - 独立Hooks兼容性检查

### 使用示例
```python
# 系统健康检查
system_health_check()
quick_system_status()

# 环境变量测试
environment_variables_test()
check_critical_env_vars()

# 兼容性检查
check_project_dependencies()
hooks_compatibility_check()
```

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
              
##### **标准 Python 代码模板**：

#### 🐍 普通类模板
```python
# -*- coding: utf-8 -*-
"""
${NAME} 模块

@author {{通过MCP Git自动获取}}
@date   {{通过MCP DateTime自动获取}}
@description ${NAME} 功能实现
"""

from typing import Optional, Dict, List
from pydantic import BaseModel


class ${NAME}:
    """
    ${NAME} 类

    Attributes:
        属性描述
    """

    def __init__(self) -> None:
        """
        初始化 ${NAME} 实例
        """
        # 1. 初始化基础属性

        # 2. 设置默认配置
        pass
```

#### 🔄 抽象基类模板
```python
# -*- coding: utf-8 -*-
"""
${NAME} 抽象基类

@author {{通过MCP Git自动获取}}
@date   {{通过MCP DateTime自动获取}}
@description ${NAME} 接口定义
"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class ${NAME}(ABC):
    """
    ${NAME} 抽象基类

    定义标准接口规范
    """

    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        """
        执行核心逻辑

        Args:
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            Any: 执行结果
        """
        pass
```

#### 📋 枚举类模板
```python
# -*- coding: utf-8 -*-
"""
${NAME} 枚举类

@author {{通过MCP Git自动获取}}
@date   {{通过MCP DateTime自动获取}}
@description ${NAME} 枚举定义
"""

from enum import Enum, unique


@unique
class ${NAME}(Enum):
    """
    ${NAME} 枚举

    定义系统中使用的常量值
    """
    OPTION_A = "option_a"
    OPTION_B = "option_b"
    OPTION_C = "option_c"

    def __str__(self) -> str:
        return self.value
```

#### ⚠️ 异常类模板
```python
# -*- coding: utf-8 -*-
"""
${NAME} 自定义异常

@author {{通过MCP Git自动获取}}
@date   {{通过MCP DateTime自动获取}}
@description ${NAME} 异常定义
"""


class ${NAME}(Exception):
    """
    ${NAME} 自定义异常

    用于处理特定的业务异常情况
    """

    def __init__(self, message: str, error_code: Optional[str] = None) -> None:
        """
        初始化异常

        Args:
            message: 错误消息
            error_code: 错误代码
        """
        # 1. 初始化基础异常信息
        super().__init__(message)

        # 2. 设置扩展属性
        self.error_code = error_code
        self.message = message
```

#### 🔧 FastMCP工具模板
```python
# -*- coding: utf-8 -*-
"""
${NAME} MCP工具

@author {{通过MCP Git自动获取}}
@date   {{通过MCP DateTime自动获取}}
@description ${NAME} MCP工具实现
"""

from fastmcp import FastMCP
from typing import Optional, Dict, Any

mcp = FastMCP("${NAME}_Server")


@mcp.tool
def ${name}_tool(param: str) -> Dict[str, Any]:
    """
    ${NAME} 工具功能描述

    Args:
        param: 输入参数描述

    Returns:
        Dict[str, Any]: 处理结果

    Raises:
        ValueError: 参数无效时抛出
    """
    # 1. 参数验证
    if not param:
        raise ValueError("参数不能为空")

    # 2. 执行核心逻辑
    result = process_logic(param)

    # 3. 返回结果
    return {"status": "success", "data": result}


def process_logic(param: str) -> str:
    """
    处理核心逻辑

    Args:
        param: 输入参数

    Returns:
        str: 处理结果
    """
    # 1. 数据处理

    # 2. 业务逻辑

    # 3. 返回结果
    return f"processed_{param}"
```

#### 📦 Pydantic Model模板
```python
# -*- coding: utf-8 -*-
"""
${NAME} 数据模型

@author {{通过MCP Git自动获取}}
@date   {{通过MCP DateTime自动获取}}
@description ${NAME} 数据模型定义
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict
from datetime import datetime


class ${NAME}Model(BaseModel):
    """
    ${NAME} 数据模型

    用于数据验证和序列化
    """
    id: Optional[str] = Field(None, description="唯一标识")
    name: str = Field(..., description="名称", min_length=1, max_length=100)
    status: str = Field("active", description="状态")
    created_at: Optional[datetime] = Field(None, description="创建时间")

    @validator('name')
    def validate_name(cls, v):
        """验证名称格式"""
        if not v or not v.strip():
            raise ValueError('名称不能为空')
        return v.strip()

    class Config:
        """模型配置"""
        # 1. 启用 JSON 编码器
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

        # 2. 示例数据
        schema_extra = {
            "example": {
                "name": "示例名称",
                "status": "active"
            }
        }
```

#### 🚀 主程序入口模板
```python
# -*- coding: utf-8 -*-
"""
${NAME} 主程序

@author {{通过MCP Git自动获取}}
@date   {{通过MCP DateTime自动获取}}
@description 程序入口
"""

import asyncio
import logging
from typing import Optional


def setup_logging() -> None:
    """
    配置日志系统
    """
    # 1. 配置日志格式
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


async def main() -> None:
    """
    主函数
    """
    # 1. 初始化日志
    setup_logging()
    logger = logging.getLogger(__name__)

    # 2. 执行主逻辑
    logger.info("程序启动")

    try:
        # 3. 业务逻辑
        await run_application()

    except Exception as e:
        # 4. 异常处理
        logger.error(f"程序执行失败: {e}")
        raise
    finally:
        # 5. 清理资源
        logger.info("程序结束")


async def run_application() -> None:
    """
    运行应用程序
    """
    # 1. 应用初始化

    # 2. 启动服务

    # 3. 等待完成
    pass


if __name__ == "__main__":
    asyncio.run(main())
```

## Task Master AI Instructions
**Import Task Master's development workflow commands and guidelines, treat as if import is in the main CLAUDE.md file.**
@./.taskmaster/CLAUDE.md