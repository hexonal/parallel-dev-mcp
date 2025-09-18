# -*- coding: utf-8 -*-
"""
模板管理MCP工具

@description 提供模板文件管理的MCP工具接口
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

# 导入FastMCP实例
from ..mcp_instance import mcp

# 导入模板管理器
from .template_manager import get_template_manager

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def _template_manager_internal(
    action: str,
    template_type: Optional[str] = None,
    task_id: Optional[str] = None,
    variables: Optional[str] = None,
    force: Optional[bool] = False
) -> Dict[str, Any]:
    """
    模板文件管理内部函数

    内部使用，不暴露为MCP工具。
    管理master.txt和child.txt模板文件，支持创建、加载、验证等操作。

    Args:
        action: 操作类型 (get/create_defaults/list/validate)
        template_type: 模板类型 (master/child)
        task_id: 任务ID (获取child模板时使用)
        variables: JSON格式的变量字典字符串，用于模板替换
        force: 是否强制覆盖已存在的模板

    Returns:
        Dict[str, Any]: 操作结果
    """
    try:
        # 1. 参数验证
        if action not in ['get', 'create_defaults', 'list', 'validate']:
            return {
                "success": False,
                "error": "无效的操作类型，必须是: get, create_defaults, list, validate"
            }

        # 2. 获取模板管理器
        manager = get_template_manager()

        # 3. 执行对应操作
        if action == 'get':
            if not template_type:
                return {
                    "success": False,
                    "error": "get操作需要提供template_type参数 (master/child)"
                }

            # 解析变量
            vars_dict = {}
            if variables:
                try:
                    import json
                    vars_dict = json.loads(variables)
                except:
                    logger.warning(f"无法解析变量JSON: {variables}")

            # 获取模板
            if template_type == 'master':
                return manager.get_master_template(vars_dict)
            elif template_type == 'child':
                return manager.get_child_template(task_id, vars_dict)
            else:
                return {
                    "success": False,
                    "error": f"无效的模板类型: {template_type}"
                }

        elif action == 'create_defaults':
            return manager.create_default_templates(force)

        elif action == 'list':
            return manager.list_templates()

        elif action == 'validate':
            if not template_type:
                # 验证所有模板
                results = {}
                for ttype in ['master', 'child']:
                    results[ttype] = manager.validate_template(ttype)

                return {
                    "success": True,
                    "validation_results": results,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return manager.validate_template(template_type)

    except Exception as e:
        # 4. 异常处理
        logger.error(f"模板管理工具异常: {e}")
        return {
            "success": False,
            "error": f"操作失败: {str(e)}"
        }


def _apply_template_to_session_internal(
    session_type: str,
    task_id: Optional[str] = None,
    session_name: Optional[str] = None,
    variables: Optional[str] = None
) -> Dict[str, Any]:
    """
    应用模板到会话内部函数

    内部使用，不暴露为MCP工具。
    将模板内容发送到指定的tmux会话。

    Args:
        session_type: 会话类型 (master/child)
        task_id: 任务ID (child会话需要)
        session_name: tmux会话名称 (可选，默认自动生成)
        variables: JSON格式的变量字典字符串

    Returns:
        Dict[str, Any]: 应用结果
    """
    try:
        import subprocess
        import os

        # 1. 获取模板管理器
        manager = get_template_manager()

        # 2. 解析变量
        vars_dict = {}
        if variables:
            try:
                import json
                vars_dict = json.loads(variables)
            except:
                logger.warning(f"无法解析变量JSON: {variables}")

        # 3. 添加环境变量到变量字典
        project_prefix = os.environ.get('PROJECT_PREFIX', '')
        if project_prefix:
            vars_dict['PROJECT_PREFIX'] = project_prefix

        web_port = os.environ.get('WEB_PORT', '')
        if web_port:
            vars_dict['WEB_PORT'] = web_port

        # 4. 获取模板内容
        if session_type == 'master':
            template_result = manager.get_master_template(vars_dict)
            if not session_name:
                session_name = f"{project_prefix}_master"
        elif session_type == 'child':
            if not task_id:
                return {
                    "success": False,
                    "error": "Child会话需要提供task_id"
                }
            template_result = manager.get_child_template(task_id, vars_dict)
            if not session_name:
                session_name = f"{project_prefix}_child_{task_id}"
        else:
            return {
                "success": False,
                "error": f"无效的会话类型: {session_type}"
            }

        # 5. 检查模板获取结果
        if not template_result.get("success"):
            return template_result

        # 6. 检查tmux会话是否存在
        try:
            result = subprocess.run(
                ['tmux', 'has-session', '-t', session_name],
                capture_output=True,
                timeout=5
            )

            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"Tmux会话 {session_name} 不存在"
                }
        except Exception as tmux_error:
            return {
                "success": False,
                "error": f"无法检查tmux会话: {str(tmux_error)}"
            }

        # 7. 将模板内容写入临时文件
        from pathlib import Path
        import tempfile

        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.txt',
            delete=False,
            encoding='utf-8'
        ) as tmp_file:
            tmp_file.write(template_result['content'])
            tmp_path = tmp_file.name

        try:
            # 8. 使用tmux send-keys发送模板内容
            # 先发送清屏命令
            subprocess.run(
                ['tmux', 'send-keys', '-t', session_name, 'C-l'],
                timeout=5
            )

            # 发送cat命令显示模板
            cat_cmd = f"cat {tmp_path}"
            subprocess.run(
                ['tmux', 'send-keys', '-t', session_name, cat_cmd, 'Enter'],
                timeout=5
            )

            # 9. 清理临时文件
            Path(tmp_path).unlink(missing_ok=True)

            # 10. 返回成功结果
            logger.info(f"模板已应用到会话: {session_name}")
            return {
                "success": True,
                "message": f"模板已应用到会话 {session_name}",
                "session_name": session_name,
                "session_type": session_type,
                "template_size": len(template_result['content']),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as send_error:
            # 清理临时文件
            Path(tmp_path).unlink(missing_ok=True)
            raise send_error

    except Exception as e:
        # 11. 异常处理
        logger.error(f"应用模板到会话异常: {e}")
        return {
            "success": False,
            "error": f"应用失败: {str(e)}"
        }


def _create_custom_template_internal(
    template_type: str,
    content: str,
    backup: Optional[bool] = True
) -> Dict[str, Any]:
    """
    创建自定义模板内部函数

    内部使用，不暴露为MCP工具。
    创建或更新master.txt或child.txt模板文件。

    Args:
        template_type: 模板类型 (master/child)
        content: 模板内容
        backup: 是否备份现有模板

    Returns:
        Dict[str, Any]: 创建结果
    """
    try:
        from pathlib import Path

        # 1. 参数验证
        if template_type not in ['master', 'child']:
            return {
                "success": False,
                "error": "模板类型必须是: master 或 child"
            }

        if not content or not content.strip():
            return {
                "success": False,
                "error": "模板内容不能为空"
            }

        # 2. 确定文件路径
        project_root = Path.cwd()
        if template_type == 'master':
            template_path = project_root / 'master.txt'
        else:
            template_path = project_root / 'child.txt'

        # 3. 备份现有模板
        if backup and template_path.exists():
            backup_path = template_path.with_suffix('.txt.bak')
            counter = 1
            while backup_path.exists():
                backup_path = template_path.with_suffix(f'.txt.bak{counter}')
                counter += 1

            template_path.rename(backup_path)
            logger.info(f"备份现有模板到: {backup_path}")
            backup_created = str(backup_path)
        else:
            backup_created = None

        # 4. 写入新模板
        template_path.write_text(content, encoding='utf-8')

        # 5. 验证写入
        if template_path.exists() and template_path.read_text(encoding='utf-8') == content:
            logger.info(f"自定义模板创建成功: {template_path}")
            return {
                "success": True,
                "message": f"{template_type.capitalize()}模板创建成功",
                "path": str(template_path),
                "size": len(content),
                "backup_path": backup_created,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "error": "模板写入验证失败"
            }

    except Exception as e:
        # 6. 异常处理
        logger.error(f"创建自定义模板异常: {e}")
        return {
            "success": False,
            "error": f"创建失败: {str(e)}"
        }