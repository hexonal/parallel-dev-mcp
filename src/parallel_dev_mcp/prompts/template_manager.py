# -*- coding: utf-8 -*-
"""
Prompt模板管理器

@description 管理Master/Child Prompt模板和继续执行Prompt系统
"""

import logging
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from .prompt_types import (
    PromptType, PromptContext, TemplateInfo, TemplateStatus, PromptResult
)
from .variable_processor import get_variable_processor

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PromptTemplateManager:
    """
    Prompt模板管理器

    提供模板加载、缓存和Prompt生成功能
    """

    def __init__(self, templates_dir: Optional[str] = None) -> None:
        """
        初始化Prompt模板管理器

        Args:
            templates_dir: 模板文件目录
        """
        # 1. 初始化配置
        self.templates_dir = Path(templates_dir) if templates_dir else Path.cwd() / "prompts"
        self.cache_ttl = timedelta(minutes=30)  # 缓存30分钟

        # 2. 初始化存储
        self._template_cache: Dict[str, TemplateInfo] = {}
        self._lock = threading.Lock()

        # 3. 初始化变量处理器
        self._variable_processor = get_variable_processor()

        # 4. 初始化模板映射
        self._template_mapping = {
            PromptType.MASTER_STOP: "master.txt",
            PromptType.MASTER_SESSION_END: "master.txt",
            PromptType.CHILD_DEFAULT: "child.txt",
            PromptType.CHILD_STARTUP: "child.txt",
            PromptType.CONTINUE_EXECUTION: "continue.txt",
            PromptType.RATE_LIMIT_RECOVERY: "rate_limit.txt"
        }

        # 5. 确保模板目录存在
        self.templates_dir.mkdir(parents=True, exist_ok=True)

        # 6. 创建默认模板文件
        self._create_default_templates()

        # 7. 记录初始化
        logger.info(f"Prompt模板管理器初始化完成，模板目录: {self.templates_dir}")

    def generate_prompt(
        self,
        prompt_type: PromptType,
        context: PromptContext,
        custom_variables: Optional[Dict[str, Any]] = None
    ) -> PromptResult:
        """
        生成Prompt

        Args:
            prompt_type: Prompt类型
            context: Prompt上下文
            custom_variables: 自定义变量

        Returns:
            PromptResult: Prompt生成结果
        """
        try:
            # 1. 获取模板
            template_info = self._get_template(prompt_type)

            if template_info.status != TemplateStatus.VALID:
                return PromptResult(
                    prompt_type=prompt_type,
                    content=self._get_fallback_prompt(prompt_type),
                    success=False,
                    context=context,
                    error_message=f"模板无效: {template_info.error_message}"
                )

            # 2. 处理变量替换
            processed_content = self._variable_processor.process_template(
                template_info.content,
                context,
                custom_variables
            )

            # 3. 根据类型调整内容
            final_content = self._adjust_content_by_type(prompt_type, processed_content)

            # 4. 返回成功结果
            return PromptResult(
                prompt_type=prompt_type,
                content=final_content,
                success=True,
                context=context,
                template_used=template_info.template_name,
                variables_applied=custom_variables or {}
            )

        except Exception as e:
            # 5. 异常处理
            logger.error(f"生成Prompt失败: {prompt_type.value}, 错误: {e}")
            return PromptResult(
                prompt_type=prompt_type,
                content=self._get_fallback_prompt(prompt_type),
                success=False,
                context=context,
                error_message=str(e)
            )

    def reload_template(self, template_name: str) -> bool:
        """
        重新加载模板

        Args:
            template_name: 模板名称

        Returns:
            bool: 是否重新加载成功
        """
        try:
            with self._lock:
                # 1. 从缓存中移除
                if template_name in self._template_cache:
                    del self._template_cache[template_name]

                # 2. 重新加载
                template_path = self.templates_dir / template_name
                template_info = self._load_template_file(template_name, template_path)

                # 3. 更新缓存
                self._template_cache[template_name] = template_info

                logger.info(f"模板重新加载成功: {template_name}")
                return template_info.status == TemplateStatus.VALID

        except Exception as e:
            logger.error(f"重新加载模板失败: {template_name}, 错误: {e}")
            return False

    def get_template_info(self, template_name: str) -> Optional[TemplateInfo]:
        """
        获取模板信息

        Args:
            template_name: 模板名称

        Returns:
            Optional[TemplateInfo]: 模板信息
        """
        with self._lock:
            return self._template_cache.get(template_name)

    def list_templates(self) -> Dict[str, TemplateInfo]:
        """
        列出所有模板

        Returns:
            Dict[str, TemplateInfo]: 模板信息字典
        """
        with self._lock:
            return self._template_cache.copy()

    def validate_all_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        验证所有模板

        Returns:
            Dict[str, Dict[str, Any]]: 验证结果
        """
        results = {}

        for template_name, template_info in self.list_templates().items():
            if template_info.content:
                validation_result = self._variable_processor.validate_template(
                    template_info.content
                )
                results[template_name] = validation_result
            else:
                results[template_name] = {
                    "valid": False,
                    "variables": [],
                    "unknown_functions": [],
                    "syntax_errors": ["模板内容为空"]
                }

        return results

    def _get_template(self, prompt_type: PromptType) -> TemplateInfo:
        """获取模板信息"""
        # 1. 获取模板文件名
        template_name = self._template_mapping.get(prompt_type, "default.txt")

        # 2. 检查缓存
        with self._lock:
            if template_name in self._template_cache:
                template_info = self._template_cache[template_name]

                # 3. 检查缓存是否过期
                if self._is_cache_valid(template_info):
                    return template_info

        # 4. 重新加载模板
        return self._load_and_cache_template(template_name)

    def _load_and_cache_template(self, template_name: str) -> TemplateInfo:
        """加载并缓存模板"""
        template_path = self.templates_dir / template_name

        # 1. 加载模板文件
        template_info = self._load_template_file(template_name, template_path)

        # 2. 更新缓存
        with self._lock:
            self._template_cache[template_name] = template_info

        return template_info

    def _load_template_file(self, template_name: str, template_path: Path) -> TemplateInfo:
        """加载模板文件"""
        try:
            # 1. 检查文件是否存在
            if not template_path.exists():
                return TemplateInfo(
                    template_name=template_name,
                    file_path=str(template_path),
                    status=TemplateStatus.NOT_FOUND,
                    error_message=f"模板文件不存在: {template_path}"
                )

            # 2. 读取文件内容
            content = template_path.read_text(encoding='utf-8')

            # 3. 获取文件修改时间
            stat_info = template_path.stat()
            last_modified = datetime.fromtimestamp(stat_info.st_mtime)

            # 4. 提取变量
            variables = list(self._variable_processor.extract_variables(content))

            # 5. 验证模板
            validation_result = self._variable_processor.validate_template(content)

            # 6. 创建模板信息
            return TemplateInfo(
                template_name=template_name,
                file_path=str(template_path),
                content=content,
                status=TemplateStatus.VALID if validation_result["valid"] else TemplateStatus.INVALID,
                last_loaded=datetime.now(),
                last_modified=last_modified,
                variables=variables,
                error_message=None if validation_result["valid"] else str(validation_result["syntax_errors"])
            )

        except Exception as e:
            # 7. 错误处理
            logger.error(f"加载模板文件失败: {template_path}, 错误: {e}")
            return TemplateInfo(
                template_name=template_name,
                file_path=str(template_path),
                status=TemplateStatus.ERROR,
                error_message=str(e)
            )

    def _is_cache_valid(self, template_info: TemplateInfo) -> bool:
        """检查缓存是否有效"""
        # 1. 检查加载时间
        if not template_info.last_loaded:
            return False

        # 2. 检查缓存TTL
        if datetime.now() - template_info.last_loaded > self.cache_ttl:
            return False

        # 3. 检查文件修改时间
        try:
            template_path = Path(template_info.file_path)
            if template_path.exists():
                stat_info = template_path.stat()
                file_modified = datetime.fromtimestamp(stat_info.st_mtime)

                if template_info.last_modified and file_modified > template_info.last_modified:
                    return False
        except Exception:
            # 文件访问失败，认为缓存无效
            return False

        return True

    def _adjust_content_by_type(self, prompt_type: PromptType, content: str) -> str:
        """根据类型调整内容"""
        if prompt_type == PromptType.CONTINUE_EXECUTION:
            # 继续执行类型，确保包含continue指令
            if 'continue' not in content.lower():
                return f"{content}\n\ncontinue"

        elif prompt_type == PromptType.RATE_LIMIT_RECOVERY:
            # 限流恢复类型，添加等待提示
            if '等待' not in content and 'wait' not in content.lower():
                return f"{content}\n\n请等待限流解除后继续执行。"

        return content

    def _get_fallback_prompt(self, prompt_type: PromptType) -> str:
        """获取fallback prompt"""
        fallback_prompts = {
            PromptType.MASTER_STOP: "会话已停止，感谢使用。",
            PromptType.MASTER_SESSION_END: "会话已结束，请保存重要信息。",
            PromptType.CHILD_DEFAULT: "子会话已启动，准备接受任务。",
            PromptType.CHILD_STARTUP: "子会话初始化完成。",
            PromptType.CONTINUE_EXECUTION: "continue",
            PromptType.RATE_LIMIT_RECOVERY: "检测到限流，请稍后继续。"
        }

        return fallback_prompts.get(prompt_type, "默认Prompt内容")

    def _create_default_templates(self) -> None:
        """创建默认模板文件"""
        default_templates = {
            "master.txt": """# Master Session Prompt

会话信息：
- 项目ID: {{project_id}}
- 会话名称: {{session_name}}
- 时间: {{now()}}

当前操作: {{prompt_type}}

请确保所有重要信息已保存。如需继续工作，请重新启动会话。""",

            "child.txt": """# Child Session Prompt

子会话已启动：
- 父项目: {{project("name")}}
- 任务ID: {{task_id}}
- 会话类型: {{session("type")}}
- 启动时间: {{now()}}

准备接受任务指令。请提供具体的实现要求。""",

            "continue.txt": """continue""",

            "rate_limit.txt": """检测到API限流，当前时间: {{now()}}

系统将自动重试，请稍候..."""
        }

        # 1. 创建默认模板文件
        for filename, content in default_templates.items():
            template_path = self.templates_dir / filename
            if not template_path.exists():
                try:
                    template_path.write_text(content, encoding='utf-8')
                    logger.info(f"创建默认模板文件: {filename}")
                except Exception as e:
                    logger.error(f"创建默认模板文件失败: {filename}, 错误: {e}")


# 全局模板管理器实例
_global_template_manager: Optional[PromptTemplateManager] = None


def get_template_manager() -> PromptTemplateManager:
    """
    获取全局模板管理器实例

    Returns:
        PromptTemplateManager: 模板管理器实例
    """
    global _global_template_manager

    # 1. 初始化全局实例（如果需要）
    if _global_template_manager is None:
        _global_template_manager = PromptTemplateManager()
        logger.info("初始化全局Prompt模板管理器实例")

    return _global_template_manager