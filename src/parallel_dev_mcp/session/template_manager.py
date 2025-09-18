# -*- coding: utf-8 -*-
"""
模板文件管理器

@description 管理和加载master.txt和child.txt模板文件，支持Claude Code启动
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TemplateManager:
    """
    模板文件管理器

    负责管理PRD要求的模板文件：
    - master.txt：Master启动时使用
    - child.txt：Child启动时使用
    支持模板变量替换和自动加载
    """

    def __init__(self, project_root: Optional[str] = None):
        """
        初始化模板管理器

        Args:
            project_root: 项目根目录
        """
        # 1. 设置项目根目录
        self.project_root = Path(project_root) if project_root else Path.cwd()

        # 2. 定义模板文件路径
        self.master_template_path = self.project_root / "master.txt"
        self.child_template_path = self.project_root / "child.txt"

        # 3. 定义默认模板目录
        self.templates_dir = self.project_root / ".parallel-dev-mcp" / "templates"

        # 4. 记录初始化
        logger.info(f"模板管理器初始化: 根目录={self.project_root}")

    def get_master_template(self, variables: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        获取Master模板内容

        Args:
            variables: 模板变量字典，用于替换

        Returns:
            Dict[str, Any]: 模板内容和元数据
        """
        try:
            # 1. 检查模板文件是否存在
            if not self.master_template_path.exists():
                # 尝试从默认模板目录加载
                default_path = self.templates_dir / "master.txt"
                if default_path.exists():
                    self.master_template_path = default_path
                else:
                    return {
                        "success": False,
                        "error": f"Master模板文件不存在: {self.master_template_path}",
                        "template_path": str(self.master_template_path)
                    }

            # 2. 读取模板内容
            content = self.master_template_path.read_text(encoding='utf-8')

            # 3. 替换变量
            if variables:
                content = self._replace_variables(content, variables)

            # 4. 返回成功结果
            logger.info(f"Master模板加载成功: {self.master_template_path}")
            return {
                "success": True,
                "content": content,
                "template_path": str(self.master_template_path),
                "file_size": self.master_template_path.stat().st_size,
                "last_modified": datetime.fromtimestamp(
                    self.master_template_path.stat().st_mtime
                ).isoformat()
            }

        except Exception as e:
            # 5. 异常处理
            logger.error(f"加载Master模板异常: {e}")
            return {
                "success": False,
                "error": f"加载失败: {str(e)}"
            }

    def get_child_template(
        self,
        task_id: Optional[str] = None,
        variables: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        获取Child模板内容

        Args:
            task_id: 任务ID，用于模板变量替换
            variables: 额外的模板变量字典

        Returns:
            Dict[str, Any]: 模板内容和元数据
        """
        try:
            # 1. 检查模板文件是否存在
            if not self.child_template_path.exists():
                # 尝试从默认模板目录加载
                default_path = self.templates_dir / "child.txt"
                if default_path.exists():
                    self.child_template_path = default_path
                else:
                    return {
                        "success": False,
                        "error": f"Child模板文件不存在: {self.child_template_path}",
                        "template_path": str(self.child_template_path)
                    }

            # 2. 读取模板内容
            content = self.child_template_path.read_text(encoding='utf-8')

            # 3. 构建默认变量
            default_vars = {}
            if task_id:
                default_vars['TASK_ID'] = task_id
                default_vars['TASK_BRANCH'] = f"task/{task_id}"
                default_vars['WORKTREE_PATH'] = f"./worktree/{task_id}"

            # 4. 合并变量
            if variables:
                default_vars.update(variables)

            # 5. 替换变量
            if default_vars:
                content = self._replace_variables(content, default_vars)

            # 6. 返回成功结果
            logger.info(f"Child模板加载成功: {self.child_template_path}")
            return {
                "success": True,
                "content": content,
                "template_path": str(self.child_template_path),
                "task_id": task_id,
                "variables_used": default_vars,
                "file_size": self.child_template_path.stat().st_size,
                "last_modified": datetime.fromtimestamp(
                    self.child_template_path.stat().st_mtime
                ).isoformat()
            }

        except Exception as e:
            # 7. 异常处理
            logger.error(f"加载Child模板异常: {e}")
            return {
                "success": False,
                "error": f"加载失败: {str(e)}"
            }

    def _replace_variables(self, content: str, variables: Dict[str, str]) -> str:
        """
        替换模板中的变量

        支持格式：
        - ${VARIABLE_NAME}
        - {{VARIABLE_NAME}}

        Args:
            content: 模板内容
            variables: 变量字典

        Returns:
            str: 替换后的内容
        """
        result = content

        for key, value in variables.items():
            # 替换 ${} 格式
            result = result.replace(f"${{{key}}}", str(value))
            # 替换 {{}} 格式
            result = result.replace(f"{{{{{key}}}}}", str(value))

        return result

    def create_default_templates(self, force: bool = False) -> Dict[str, Any]:
        """
        创建默认模板文件

        Args:
            force: 是否强制覆盖已存在的模板

        Returns:
            Dict[str, Any]: 创建结果
        """
        try:
            # 1. 确保模板目录存在
            self.templates_dir.mkdir(parents=True, exist_ok=True)

            results = {}

            # 2. 创建默认Master模板
            master_default = """# Master Session Template
# This template is used when starting a Master session
# Available variables: ${PROJECT_PREFIX}, ${SESSION_ID}

Welcome to the Master session for ${PROJECT_PREFIX}!

## Your responsibilities as Master:
1. Manage Flask web service (port: ${WEB_PORT})
2. Coordinate Child sessions
3. Monitor Git repository status
4. Maintain session_id.txt

## Quick Commands:
- Check system status: mcp tool get_parallel_dev_status
- Initialize system: mcp tool initialize_parallel_dev_system
- Monitor Child sessions: mcp tool child_session_monitoring_tool --action status

Ready to orchestrate parallel development!
"""

            master_path = self.templates_dir / "master_default.txt"
            if not master_path.exists() or force:
                master_path.write_text(master_default, encoding='utf-8')
                results["master"] = "created"
                logger.info(f"创建默认Master模板: {master_path}")
            else:
                results["master"] = "exists"

            # 3. 创建默认Child模板
            child_default = """# Child Session Template
# This template is used when starting a Child session
# Available variables: ${TASK_ID}, ${TASK_BRANCH}, ${WORKTREE_PATH}

Welcome to Child session for Task ${TASK_ID}!

## Working Information:
- Task ID: ${TASK_ID}
- Branch: ${TASK_BRANCH}
- Working Directory: ${WORKTREE_PATH}

## Your responsibilities:
1. Complete the assigned task
2. Commit changes to your branch
3. Report completion to Master

## Quick Commands:
- Check task status: git status
- Commit changes: git commit -am "Task ${TASK_ID}: Description"
- View task details: cat task_${TASK_ID}.md

Ready to work on your task!
"""

            child_path = self.templates_dir / "child_default.txt"
            if not child_path.exists() or force:
                child_path.write_text(child_default, encoding='utf-8')
                results["child"] = "created"
                logger.info(f"创建默认Child模板: {child_path}")
            else:
                results["child"] = "exists"

            # 4. 返回结果
            return {
                "success": True,
                "message": "默认模板创建完成",
                "templates_dir": str(self.templates_dir),
                "results": results,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            # 5. 异常处理
            logger.error(f"创建默认模板异常: {e}")
            return {
                "success": False,
                "error": f"创建失败: {str(e)}"
            }

    def list_templates(self) -> Dict[str, Any]:
        """
        列出所有可用的模板文件

        Returns:
            Dict[str, Any]: 模板列表
        """
        try:
            templates = []

            # 1. 检查主模板文件
            if self.master_template_path.exists():
                templates.append({
                    "name": "master.txt",
                    "type": "master",
                    "path": str(self.master_template_path),
                    "size": self.master_template_path.stat().st_size,
                    "modified": datetime.fromtimestamp(
                        self.master_template_path.stat().st_mtime
                    ).isoformat()
                })

            if self.child_template_path.exists():
                templates.append({
                    "name": "child.txt",
                    "type": "child",
                    "path": str(self.child_template_path),
                    "size": self.child_template_path.stat().st_size,
                    "modified": datetime.fromtimestamp(
                        self.child_template_path.stat().st_mtime
                    ).isoformat()
                })

            # 2. 检查模板目录中的文件
            if self.templates_dir.exists():
                for template_file in self.templates_dir.glob("*.txt"):
                    template_type = "master" if "master" in template_file.name.lower() else "child"
                    templates.append({
                        "name": template_file.name,
                        "type": template_type,
                        "path": str(template_file),
                        "size": template_file.stat().st_size,
                        "modified": datetime.fromtimestamp(
                            template_file.stat().st_mtime
                        ).isoformat()
                    })

            # 3. 返回结果
            return {
                "success": True,
                "templates": templates,
                "count": len(templates),
                "project_root": str(self.project_root),
                "templates_dir": str(self.templates_dir),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            # 4. 异常处理
            logger.error(f"列出模板文件异常: {e}")
            return {
                "success": False,
                "error": f"查询失败: {str(e)}"
            }

    def validate_template(self, template_type: str) -> Dict[str, Any]:
        """
        验证模板文件的有效性

        Args:
            template_type: 模板类型 (master/child)

        Returns:
            Dict[str, Any]: 验证结果
        """
        try:
            # 1. 选择模板路径
            if template_type == "master":
                template_path = self.master_template_path
            elif template_type == "child":
                template_path = self.child_template_path
            else:
                return {
                    "success": False,
                    "error": f"无效的模板类型: {template_type}"
                }

            # 2. 检查文件存在性
            if not template_path.exists():
                return {
                    "success": False,
                    "valid": False,
                    "error": f"模板文件不存在: {template_path}",
                    "template_type": template_type
                }

            # 3. 读取并验证内容
            try:
                content = template_path.read_text(encoding='utf-8')

                # 检查基本要求
                issues = []

                # 检查是否为空
                if not content.strip():
                    issues.append("模板内容为空")

                # 检查是否包含变量占位符
                has_variables = "${" in content or "{{" in content

                # 4. 返回验证结果
                return {
                    "success": True,
                    "valid": len(issues) == 0,
                    "template_type": template_type,
                    "path": str(template_path),
                    "size": template_path.stat().st_size,
                    "has_variables": has_variables,
                    "issues": issues,
                    "timestamp": datetime.now().isoformat()
                }

            except Exception as read_error:
                return {
                    "success": False,
                    "valid": False,
                    "error": f"读取模板失败: {str(read_error)}",
                    "template_type": template_type
                }

        except Exception as e:
            # 5. 异常处理
            logger.error(f"验证模板异常: {e}")
            return {
                "success": False,
                "error": f"验证失败: {str(e)}"
            }


# 全局模板管理器实例
_template_manager = None


def get_template_manager(project_root: Optional[str] = None) -> TemplateManager:
    """
    获取全局模板管理器实例

    Args:
        project_root: 项目根目录

    Returns:
        TemplateManager: 管理器实例
    """
    global _template_manager

    if _template_manager is None:
        _template_manager = TemplateManager(project_root)
        logger.info("创建全局模板管理器实例")

    return _template_manager