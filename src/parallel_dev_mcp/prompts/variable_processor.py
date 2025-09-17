# -*- coding: utf-8 -*-
"""
变量处理器

@description 处理模板变量替换和自定义配置
"""

import re
import logging
import os
from typing import Dict, Any, Optional, Set

from .prompt_types import PromptContext

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class VariableProcessor:
    """
    变量处理器

    处理模板变量替换和自定义配置
    """

    def __init__(self) -> None:
        """初始化变量处理器"""
        # 1. 初始化变量模式
        self.variable_pattern = re.compile(r'\{\{(\w+)\}\}')
        self.function_pattern = re.compile(r'\{\{(\w+)\((.*?)\)\}\}')

        # 2. 初始化内建变量函数
        self._builtin_functions = {
            'now': self._format_timestamp,
            'date': self._format_date,
            'time': self._format_time,
            'project': self._get_project_info,
            'session': self._get_session_info
        }

        # 3. 记录初始化
        logger.info("变量处理器初始化完成")

    def process_template(
        self,
        template_content: str,
        context: PromptContext,
        custom_variables: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        处理模板变量替换

        Args:
            template_content: 模板内容
            context: Prompt上下文
            custom_variables: 自定义变量

        Returns:
            str: 处理后的内容
        """
        try:
            # 1. 准备变量字典
            variables = self._prepare_variables(context, custom_variables)

            # 2. 处理函数调用
            content = self._process_functions(template_content, context)

            # 3. 处理简单变量替换
            content = self._process_variables(content, variables)

            return content

        except Exception as e:
            logger.error(f"模板变量处理失败: {e}")
            return template_content

    def extract_variables(self, template_content: str) -> Set[str]:
        """
        提取模板中的变量

        Args:
            template_content: 模板内容

        Returns:
            Set[str]: 变量名集合
        """
        # 1. 提取简单变量
        simple_vars = set(self.variable_pattern.findall(template_content))

        # 2. 提取函数变量
        function_vars = set(self.function_pattern.findall(template_content))
        function_names = {match[0] for match in function_vars}

        # 3. 合并变量
        return simple_vars.union(function_names)

    def validate_template(self, template_content: str) -> Dict[str, Any]:
        """
        验证模板语法

        Args:
            template_content: 模板内容

        Returns:
            Dict[str, Any]: 验证结果
        """
        try:
            # 1. 提取变量
            variables = self.extract_variables(template_content)

            # 2. 检查未知函数
            unknown_functions = []
            for func_match in self.function_pattern.finditer(template_content):
                func_name = func_match.group(1)
                if func_name not in self._builtin_functions:
                    unknown_functions.append(func_name)

            # 3. 检查语法错误
            syntax_errors = []
            try:
                # 尝试替换所有变量进行语法检查
                test_context = PromptContext(
                    prompt_type="master_stop",  # 使用有效的枚举值
                    variables={}
                )
                self.process_template(template_content, test_context, {})
            except Exception as e:
                syntax_errors.append(str(e))

            # 4. 返回验证结果
            is_valid = len(unknown_functions) == 0 and len(syntax_errors) == 0

            return {
                "valid": is_valid,
                "variables": list(variables),
                "unknown_functions": unknown_functions,
                "syntax_errors": syntax_errors
            }

        except Exception as e:
            logger.error(f"模板验证失败: {e}")
            return {
                "valid": False,
                "variables": [],
                "unknown_functions": [],
                "syntax_errors": [str(e)]
            }

    def _prepare_variables(
        self,
        context: PromptContext,
        custom_variables: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """准备变量字典"""
        # 1. 基础变量
        variables = {
            'session_name': context.session_name or '',
            'project_id': context.project_id or '',
            'task_id': context.task_id or '',
            'timestamp': context.timestamp.isoformat(),
            'prompt_type': context.prompt_type.value
        }

        # 2. 上下文变量
        variables.update(context.variables)

        # 3. 自定义变量
        if custom_variables:
            variables.update(custom_variables)

        # 4. 环境变量
        variables.update({
            'user': os.environ.get('USER', 'unknown'),
            'hostname': os.environ.get('HOSTNAME', 'localhost')
        })

        return variables

    def _process_variables(self, content: str, variables: Dict[str, Any]) -> str:
        """处理简单变量替换"""
        def replace_var(match):
            var_name = match.group(1)
            return str(variables.get(var_name, f'{{{{MISSING:{var_name}}}}}'))

        return self.variable_pattern.sub(replace_var, content)

    def _process_functions(self, content: str, context: PromptContext) -> str:
        """处理函数调用"""
        def replace_func(match):
            func_name = match.group(1)
            func_args = match.group(2) if len(match.groups()) > 1 else ''

            if func_name in self._builtin_functions:
                try:
                    return self._builtin_functions[func_name](context, func_args)
                except Exception as e:
                    logger.warning(f"函数调用失败: {func_name}({func_args}), 错误: {e}")
                    return f'{{{{ERROR:{func_name}}}}}'
            else:
                return f'{{{{UNKNOWN:{func_name}}}}}'

        return self.function_pattern.sub(replace_func, content)

    def _format_timestamp(self, context: PromptContext, args: str) -> str:
        """格式化时间戳函数"""
        format_str = args.strip('"\'') if args else '%Y-%m-%d %H:%M:%S'
        return context.timestamp.strftime(format_str)

    def _format_date(self, context: PromptContext, args: str) -> str:
        """格式化日期函数"""
        format_str = args.strip('"\'') if args else '%Y-%m-%d'
        return context.timestamp.strftime(format_str)

    def _format_time(self, context: PromptContext, args: str) -> str:
        """格式化时间函数"""
        format_str = args.strip('"\'') if args else '%H:%M:%S'
        return context.timestamp.strftime(format_str)

    def _get_project_info(self, context: PromptContext, args: str) -> str:
        """获取项目信息函数"""
        info_type = args.strip('"\'') if args else 'id'
        if info_type == 'id':
            return context.project_id or 'unknown'
        elif info_type == 'name':
            # 可以从项目ID推导项目名称
            return context.project_id or 'unknown'
        else:
            return f'unknown:{info_type}'

    def _get_session_info(self, context: PromptContext, args: str) -> str:
        """获取会话信息函数"""
        info_type = args.strip('"\'') if args else 'name'
        if info_type == 'name':
            return context.session_name or 'unknown'
        elif info_type == 'type':
            # 判断是master还是child会话
            if context.session_name and '_child_' in context.session_name:
                return 'child'
            else:
                return 'master'
        else:
            return f'unknown:{info_type}'


# 全局变量处理器实例
_global_variable_processor: Optional[VariableProcessor] = None


def get_variable_processor() -> VariableProcessor:
    """
    获取全局变量处理器实例

    Returns:
        VariableProcessor: 变量处理器实例
    """
    global _global_variable_processor

    # 1. 初始化全局实例（如果需要）
    if _global_variable_processor is None:
        _global_variable_processor = VariableProcessor()
        logger.info("初始化全局变量处理器实例")

    return _global_variable_processor