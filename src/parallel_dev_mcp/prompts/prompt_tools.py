# -*- coding: utf-8 -*-
"""
Prompt MCP工具

@description 提供Prompt模板管理的FastMCP工具接口
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

# 获取FastMCP实例
from ..mcp_instance import mcp
from .template_manager import get_template_manager
from .prompt_types import PromptType, PromptContext

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@mcp.tool
def generate_prompt_tool(
    prompt_type: str,
    session_name: Optional[str] = None,
    project_id: Optional[str] = None,
    task_id: Optional[str] = None,
    custom_variables: Optional[str] = None
) -> Dict[str, Any]:
    """
    生成Prompt工具

    根据指定类型和上下文生成Prompt内容。

    Args:
        prompt_type: Prompt类型 (master_stop/master_session_end/child_default/child_startup/continue_execution/rate_limit_recovery)
        session_name: 会话名称
        project_id: 项目ID
        task_id: 任务ID
        custom_variables: 自定义变量（JSON字符串格式）

    Returns:
        Dict[str, Any]: 生成的Prompt结果
    """
    try:
        # 1. 参数验证
        try:
            prompt_type_enum = PromptType(prompt_type)
        except ValueError:
            return {
                "success": False,
                "error": f"无效的Prompt类型: {prompt_type}，支持的类型: {[t.value for t in PromptType]}"
            }

        # 2. 解析自定义变量
        variables = {}
        if custom_variables:
            try:
                import json
                variables = json.loads(custom_variables)
            except Exception as e:
                return {
                    "success": False,
                    "error": f"自定义变量JSON解析失败: {str(e)}"
                }

        # 3. 创建上下文
        context = PromptContext(
            prompt_type=prompt_type_enum,
            session_name=session_name,
            project_id=project_id,
            task_id=task_id,
            variables=variables
        )

        # 4. 生成Prompt
        template_manager = get_template_manager()
        result = template_manager.generate_prompt(
            prompt_type=prompt_type_enum,
            context=context,
            custom_variables=variables
        )

        # 5. 记录操作
        logger.info(f"生成Prompt: {prompt_type}, 会话: {session_name}")

        # 6. 返回结果
        return {
            "success": result.success,
            "prompt_type": result.prompt_type.value,
            "content": result.content,
            "template_used": result.template_used,
            "variables_applied": result.variables_applied,
            "generated_at": result.generated_at.isoformat(),
            "error_message": result.error_message
        }

    except Exception as e:
        # 7. 异常处理
        logger.error(f"生成Prompt工具异常: {e}")
        return {
            "success": False,
            "error": f"生成Prompt失败: {str(e)}"
        }


@mcp.tool
def list_templates_tool() -> Dict[str, Any]:
    """
    列出模板工具

    获取所有可用的Prompt模板信息。

    Returns:
        Dict[str, Any]: 模板列表和状态信息
    """
    try:
        # 1. 获取模板管理器
        template_manager = get_template_manager()

        # 2. 获取模板列表
        templates = template_manager.list_templates()

        # 3. 构建结果
        template_list = []
        for name, info in templates.items():
            template_list.append({
                "name": info.template_name,
                "file_path": info.file_path,
                "status": info.status.value,
                "last_loaded": info.last_loaded.isoformat() if info.last_loaded else None,
                "last_modified": info.last_modified.isoformat() if info.last_modified else None,
                "variables": info.variables,
                "error_message": info.error_message
            })

        # 4. 记录操作
        logger.info("查询模板列表")

        # 5. 返回结果
        return {
            "success": True,
            "total_templates": len(template_list),
            "templates": template_list
        }

    except Exception as e:
        # 6. 异常处理
        logger.error(f"列出模板工具异常: {e}")
        return {
            "success": False,
            "error": f"获取模板列表失败: {str(e)}"
        }


@mcp.tool
def reload_template_tool(template_name: str) -> Dict[str, Any]:
    """
    重新加载模板工具

    强制重新加载指定的模板文件。

    Args:
        template_name: 模板名称

    Returns:
        Dict[str, Any]: 重新加载结果
    """
    try:
        # 1. 参数验证
        if not template_name or not template_name.strip():
            return {
                "success": False,
                "error": "模板名称不能为空"
            }

        # 2. 重新加载模板
        template_manager = get_template_manager()
        success = template_manager.reload_template(template_name.strip())

        # 3. 获取重新加载后的模板信息
        template_info = template_manager.get_template_info(template_name.strip())

        # 4. 记录操作
        logger.info(f"重新加载模板: {template_name}, 成功: {success}")

        # 5. 返回结果
        result = {
            "success": success,
            "template_name": template_name.strip(),
            "message": "模板重新加载成功" if success else "模板重新加载失败"
        }

        if template_info:
            result.update({
                "status": template_info.status.value,
                "last_loaded": template_info.last_loaded.isoformat() if template_info.last_loaded else None,
                "variables": template_info.variables,
                "error_message": template_info.error_message
            })

        return result

    except Exception as e:
        # 6. 异常处理
        logger.error(f"重新加载模板工具异常: {e}")
        return {
            "success": False,
            "error": f"重新加载模板失败: {str(e)}"
        }


@mcp.tool
def validate_templates_tool() -> Dict[str, Any]:
    """
    验证模板工具

    验证所有模板的语法和变量使用。

    Returns:
        Dict[str, Any]: 验证结果
    """
    try:
        # 1. 获取模板管理器
        template_manager = get_template_manager()

        # 2. 执行验证
        validation_results = template_manager.validate_all_templates()

        # 3. 统计验证结果
        total_templates = len(validation_results)
        valid_templates = sum(1 for result in validation_results.values() if result["valid"])
        invalid_templates = total_templates - valid_templates

        # 4. 记录操作
        logger.info(f"验证所有模板: 总数={total_templates}, 有效={valid_templates}, 无效={invalid_templates}")

        # 5. 返回结果
        return {
            "success": True,
            "summary": {
                "total_templates": total_templates,
                "valid_templates": valid_templates,
                "invalid_templates": invalid_templates,
                "validation_timestamp": datetime.now().isoformat()
            },
            "validation_results": validation_results
        }

    except Exception as e:
        # 6. 异常处理
        logger.error(f"验证模板工具异常: {e}")
        return {
            "success": False,
            "error": f"验证模板失败: {str(e)}"
        }


@mcp.tool
def get_template_info_tool(template_name: str) -> Dict[str, Any]:
    """
    获取模板信息工具

    获取指定模板的详细信息。

    Args:
        template_name: 模板名称

    Returns:
        Dict[str, Any]: 模板详细信息
    """
    try:
        # 1. 参数验证
        if not template_name or not template_name.strip():
            return {
                "success": False,
                "error": "模板名称不能为空"
            }

        # 2. 获取模板信息
        template_manager = get_template_manager()
        template_info = template_manager.get_template_info(template_name.strip())

        if not template_info:
            return {
                "success": False,
                "error": f"模板不存在: {template_name}"
            }

        # 3. 记录操作
        logger.info(f"查询模板信息: {template_name}")

        # 4. 返回详细信息
        return {
            "success": True,
            "template_name": template_info.template_name,
            "file_path": template_info.file_path,
            "status": template_info.status.value,
            "content": template_info.content,
            "last_loaded": template_info.last_loaded.isoformat() if template_info.last_loaded else None,
            "last_modified": template_info.last_modified.isoformat() if template_info.last_modified else None,
            "variables": template_info.variables,
            "error_message": template_info.error_message
        }

    except Exception as e:
        # 5. 异常处理
        logger.error(f"获取模板信息工具异常: {e}")
        return {
            "success": False,
            "error": f"获取模板信息失败: {str(e)}"
        }


@mcp.tool
def generate_continue_prompt_tool(
    session_name: Optional[str] = None,
    context_message: Optional[str] = None
) -> Dict[str, Any]:
    """
    生成继续执行Prompt工具

    专门用于生成继续执行的Prompt，通常在触发限流时使用。

    Args:
        session_name: 会话名称
        context_message: 上下文消息

    Returns:
        Dict[str, Any]: 继续执行Prompt结果
    """
    try:
        # 1. 创建上下文
        context = PromptContext(
            prompt_type=PromptType.CONTINUE_EXECUTION,
            session_name=session_name,
            variables={"context_message": context_message} if context_message else {}
        )

        # 2. 生成继续执行Prompt
        template_manager = get_template_manager()
        result = template_manager.generate_prompt(
            prompt_type=PromptType.CONTINUE_EXECUTION,
            context=context
        )

        # 3. 记录操作
        logger.info(f"生成继续执行Prompt: 会话={session_name}")

        # 4. 返回结果
        return {
            "success": result.success,
            "content": result.content,
            "session_name": session_name,
            "context_message": context_message,
            "generated_at": result.generated_at.isoformat(),
            "error_message": result.error_message
        }

    except Exception as e:
        # 5. 异常处理
        logger.error(f"生成继续执行Prompt工具异常: {e}")
        return {
            "success": False,
            "error": f"生成继续执行Prompt失败: {str(e)}"
        }