# -*- coding: utf-8 -*-
"""
日志管理MCP工具

@description 提供结构化日志管理的MCP工具接口
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

# 导入FastMCP实例
from ..mcp_instance import mcp

# 导入结构化日志管理器
from .structured_logger import (
    get_structured_logger,
    LogLevel,
    LogCategory,
    log_info,
    log_warning,
    log_error
)

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def _structured_log_internal(
    action: str,
    level: Optional[str] = None,
    category: Optional[str] = None,
    message: Optional[str] = None,
    context: Optional[str] = None
) -> Dict[str, Any]:
    """
    结构化日志管理工具

    提供日志记录、查询和管理功能。

    Args:
        action: 操作类型 (log/query/stats/rotate)
        level: 日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
        category: 日志分类 (SYSTEM/SESSION/MASTER/CHILD/GIT/TMUX/WEB/MESSAGE/TEMPLATE/MONITORING)
        message: 日志消息 (log操作必需)
        context: JSON格式的上下文信息

    Returns:
        Dict[str, Any]: 操作结果
    """
    try:
        # 1. 参数验证
        if action not in ['log', 'query', 'stats', 'rotate']:
            return {
                "success": False,
                "error": "无效的操作类型，必须是: log, query, stats, rotate"
            }

        # 2. 获取日志管理器
        logger_mgr = get_structured_logger()

        # 3. 执行对应操作
        if action == 'log':
            if not message:
                return {
                    "success": False,
                    "error": "log操作需要提供message参数"
                }

            # 解析级别和分类
            try:
                log_level = LogLevel[level.upper()] if level else LogLevel.INFO
                log_category = LogCategory[category.upper()] if category else LogCategory.SYSTEM
            except KeyError as e:
                return {
                    "success": False,
                    "error": f"无效的级别或分类: {e}"
                }

            # 解析上下文
            context_dict = {}
            if context:
                try:
                    import json
                    context_dict = json.loads(context)
                except:
                    context_dict = {"raw_context": context}

            # 记录日志
            return logger_mgr.log(log_level, log_category, message, context_dict)

        elif action == 'query':
            # 构建查询参数
            query_params = {}

            if category:
                try:
                    query_params['category'] = LogCategory[category.upper()]
                except KeyError:
                    return {
                        "success": False,
                        "error": f"无效的日志分类: {category}"
                    }

            if level:
                try:
                    query_params['level'] = LogLevel[level.upper()]
                except KeyError:
                    return {
                        "success": False,
                        "error": f"无效的日志级别: {level}"
                    }

            # 执行查询
            return logger_mgr.query_logs(**query_params)

        elif action == 'stats':
            return logger_mgr.get_log_stats()

        elif action == 'rotate':
            return logger_mgr.rotate_logs()

    except Exception as e:
        # 4. 异常处理
        logger.error(f"结构化日志工具异常: {e}")
        return {
            "success": False,
            "error": f"操作失败: {str(e)}"
        }


def _log_query_advanced_internal(
    category: Optional[str] = None,
    level: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: Optional[int] = 100,
    keywords: Optional[str] = None
) -> Dict[str, Any]:
    """
    高级日志查询工具

    提供更灵活的日志查询功能，支持时间范围和关键词过滤。

    Args:
        category: 日志分类过滤
        level: 日志级别过滤
        start_time: 开始时间 (ISO格式)
        end_time: 结束时间 (ISO格式)
        limit: 返回记录限制 (默认100)
        keywords: 关键词过滤 (逗号分隔)

    Returns:
        Dict[str, Any]: 查询结果
    """
    try:
        # 1. 获取日志管理器
        logger_mgr = get_structured_logger()

        # 2. 构建查询参数
        query_params = {'limit': limit or 100}

        if category:
            try:
                query_params['category'] = LogCategory[category.upper()]
            except KeyError:
                return {
                    "success": False,
                    "error": f"无效的日志分类: {category}"
                }

        if level:
            try:
                query_params['level'] = LogLevel[level.upper()]
            except KeyError:
                return {
                    "success": False,
                    "error": f"无效的日志级别: {level}"
                }

        if start_time:
            try:
                query_params['start_time'] = datetime.fromisoformat(start_time)
            except ValueError:
                return {
                    "success": False,
                    "error": f"无效的开始时间格式: {start_time}"
                }

        if end_time:
            try:
                query_params['end_time'] = datetime.fromisoformat(end_time)
            except ValueError:
                return {
                    "success": False,
                    "error": f"无效的结束时间格式: {end_time}"
                }

        # 3. 执行查询
        result = logger_mgr.query_logs(**query_params)

        # 4. 关键词过滤
        if keywords and result.get("success"):
            keyword_list = [k.strip() for k in keywords.split(',')]
            filtered_logs = []

            for log_entry in result.get("logs", []):
                message = log_entry.get("message", "")
                if any(kw.lower() in message.lower() for kw in keyword_list):
                    filtered_logs.append(log_entry)

            result["logs"] = filtered_logs
            result["count"] = len(filtered_logs)

        return result

    except Exception as e:
        # 5. 异常处理
        logger.error(f"高级日志查询异常: {e}")
        return {
            "success": False,
            "error": f"查询失败: {str(e)}"
        }


def _log_cleanup_internal(
    days: Optional[int] = 7,
    categories: Optional[str] = None,
    dry_run: Optional[bool] = False
) -> Dict[str, Any]:
    """
    日志清理工具

    清理旧的日志文件和归档文件。

    Args:
        days: 保留最近N天的日志 (默认7天)
        categories: 要清理的分类 (逗号分隔，默认所有)
        dry_run: 是否仅预览不实际删除

    Returns:
        Dict[str, Any]: 清理结果
    """
    try:
        from pathlib import Path

        # 1. 获取日志目录
        logger_mgr = get_structured_logger()
        logs_dir = logger_mgr.logs_dir
        archive_dir = logs_dir / "archive"

        # 2. 计算截止时间
        cutoff_time = datetime.now() - timedelta(days=days)
        files_to_delete = []
        total_size = 0

        # 3. 扫描归档文件
        if archive_dir.exists():
            for file_path in archive_dir.iterdir():
                if file_path.is_file():
                    # 检查文件修改时间
                    file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_time < cutoff_time:
                        files_to_delete.append(file_path)
                        total_size += file_path.stat().st_size

        # 4. 执行清理
        deleted_files = []
        if not dry_run:
            for file_path in files_to_delete:
                try:
                    file_path.unlink()
                    deleted_files.append(str(file_path))
                except Exception as e:
                    logger.warning(f"删除文件失败 {file_path}: {e}")

        # 5. 返回结果
        return {
            "success": True,
            "dry_run": dry_run,
            "cutoff_date": cutoff_time.isoformat(),
            "files_found": len(files_to_delete),
            "files_deleted": len(deleted_files),
            "total_size": total_size,
            "deleted_files": deleted_files if not dry_run else [str(f) for f in files_to_delete],
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        # 6. 异常处理
        logger.error(f"日志清理工具异常: {e}")
        return {
            "success": False,
            "error": f"清理失败: {str(e)}"
        }


def _log_monitor_internal(
    categories: Optional[str] = None,
    tail_lines: Optional[int] = 20
) -> Dict[str, Any]:
    """
    日志监控工具

    实时监控最新的日志记录。

    Args:
        categories: 要监控的分类 (逗号分隔)
        tail_lines: 显示最后N行日志 (默认20)

    Returns:
        Dict[str, Any]: 监控结果
    """
    try:
        # 1. 获取日志管理器
        logger_mgr = get_structured_logger()

        # 2. 解析分类
        category_list = []
        if categories:
            for cat in categories.split(','):
                try:
                    category_list.append(LogCategory[cat.strip().upper()])
                except KeyError:
                    logger.warning(f"忽略无效分类: {cat}")

        # 3. 获取最新日志
        recent_logs = {}
        for category in (category_list or list(LogCategory)):
            result = logger_mgr.query_logs(category=category, limit=tail_lines)
            if result.get("success") and result.get("logs"):
                recent_logs[category.value] = result["logs"]

        # 4. 返回监控结果
        total_logs = sum(len(logs) for logs in recent_logs.values())
        return {
            "success": True,
            "recent_logs": recent_logs,
            "total_entries": total_logs,
            "categories_monitored": [cat.value for cat in (category_list or list(LogCategory))],
            "tail_lines": tail_lines,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        # 5. 异常处理
        logger.error(f"日志监控工具异常: {e}")
        return {
            "success": False,
            "error": f"监控失败: {str(e)}"
        }