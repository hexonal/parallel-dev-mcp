# -*- coding: utf-8 -*-
"""
结构化日志管理器

@description 提供结构化的日志记录和管理功能，支持PRD要求的日志系统
"""

import os
import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
import threading
from queue import Queue
import traceback

# 配置基础日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class LogLevel(Enum):
    """
    日志级别枚举

    定义系统支持的日志级别
    """
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(Enum):
    """
    日志分类枚举

    定义系统日志分类
    """
    SYSTEM = "SYSTEM"          # 系统级别日志
    SESSION = "SESSION"        # 会话管理日志
    MASTER = "MASTER"          # Master职责日志
    CHILD = "CHILD"            # Child会话日志
    GIT = "GIT"                # Git操作日志
    TMUX = "TMUX"              # Tmux操作日志
    WEB = "WEB"                # Web服务日志
    MESSAGE = "MESSAGE"        # 消息系统日志
    TEMPLATE = "TEMPLATE"      # 模板系统日志
    MONITORING = "MONITORING"  # 监控系统日志


class StructuredLogger:
    """
    结构化日志管理器

    提供结构化日志记录、文件管理和查询功能
    """

    def __init__(self, project_root: Optional[str] = None):
        """
        初始化结构化日志管理器

        Args:
            project_root: 项目根目录
        """
        # 1. 设置项目根目录
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.logs_dir = self.project_root / ".parallel-dev-mcp" / "logs"

        # 2. 创建日志目录结构
        self._create_log_directories()

        # 3. 初始化日志队列和线程
        self.log_queue = Queue()
        self.running = True
        self.worker_thread = threading.Thread(target=self._log_worker, daemon=True)
        self.worker_thread.start()

        # 4. 设置日志文件路径
        self.log_files = {
            LogCategory.SYSTEM: self.logs_dir / "system.log",
            LogCategory.SESSION: self.logs_dir / "session.log",
            LogCategory.MASTER: self.logs_dir / "master.log",
            LogCategory.CHILD: self.logs_dir / "child.log",
            LogCategory.GIT: self.logs_dir / "git.log",
            LogCategory.TMUX: self.logs_dir / "tmux.log",
            LogCategory.WEB: self.logs_dir / "web.log",
            LogCategory.MESSAGE: self.logs_dir / "message.log",
            LogCategory.TEMPLATE: self.logs_dir / "template.log",
            LogCategory.MONITORING: self.logs_dir / "monitoring.log"
        }

        # 5. 统一日志文件
        self.unified_log = self.logs_dir / "unified.log"

        logger.info(f"结构化日志管理器初始化: 日志目录={self.logs_dir}")

    def _create_log_directories(self) -> None:
        """
        创建日志目录结构
        """
        try:
            # 1. 创建主日志目录
            self.logs_dir.mkdir(parents=True, exist_ok=True)

            # 2. 创建归档目录
            archive_dir = self.logs_dir / "archive"
            archive_dir.mkdir(exist_ok=True)

            # 3. 创建临时目录
            temp_dir = self.logs_dir / "temp"
            temp_dir.mkdir(exist_ok=True)

        except Exception as e:
            logger.error(f"创建日志目录失败: {e}")

    def log(
        self,
        level: LogLevel,
        category: LogCategory,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        记录结构化日志

        Args:
            level: 日志级别
            category: 日志分类
            message: 日志消息
            context: 上下文信息

        Returns:
            Dict[str, Any]: 日志记录结果
        """
        try:
            # 1. 构建日志条目
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "level": level.value,
                "category": category.value,
                "message": message,
                "context": context or {},
                "thread_id": threading.current_thread().ident,
                "process_id": os.getpid()
            }

            # 2. 添加到队列
            self.log_queue.put(log_entry)

            # 3. 同时使用标准logger
            log_func = getattr(logger, level.value.lower())
            log_func(f"[{category.value}] {message}")

            return {
                "success": True,
                "log_id": f"{log_entry['timestamp']}_{category.value}",
                "entry": log_entry
            }

        except Exception as e:
            # 4. 异常处理
            logger.error(f"记录日志失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _log_worker(self) -> None:
        """
        日志写入工作线程

        从队列读取日志并写入文件
        """
        while self.running:
            try:
                # 1. 从队列获取日志
                if not self.log_queue.empty():
                    log_entry = self.log_queue.get(timeout=1)

                    # 2. 写入分类日志文件
                    category = LogCategory[log_entry["category"]]
                    if category in self.log_files:
                        self._write_to_file(self.log_files[category], log_entry)

                    # 3. 写入统一日志文件
                    self._write_to_file(self.unified_log, log_entry)

            except Exception as e:
                # 4. 忽略超时和其他错误
                pass

    def _write_to_file(self, file_path: Path, log_entry: Dict[str, Any]) -> None:
        """
        将日志写入文件

        Args:
            file_path: 日志文件路径
            log_entry: 日志条目
        """
        try:
            # 1. 格式化为JSON行
            json_line = json.dumps(log_entry, ensure_ascii=False) + "\n"

            # 2. 追加写入文件
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(json_line)

        except Exception as e:
            # 3. 写入失败时使用标准错误输出
            logger.error(f"写入日志文件失败: {e}")

    def query_logs(
        self,
        category: Optional[LogCategory] = None,
        level: Optional[LogLevel] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        查询日志记录

        Args:
            category: 日志分类过滤
            level: 日志级别过滤
            start_time: 开始时间
            end_time: 结束时间
            limit: 返回记录限制

        Returns:
            Dict[str, Any]: 查询结果
        """
        try:
            # 1. 确定查询文件
            if category and category in self.log_files:
                log_file = self.log_files[category]
            else:
                log_file = self.unified_log

            # 2. 读取日志文件
            if not log_file.exists():
                return {
                    "success": True,
                    "logs": [],
                    "count": 0
                }

            logs = []
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())

                        # 3. 应用过滤条件
                        if level and entry.get("level") != level.value:
                            continue

                        if start_time:
                            entry_time = datetime.fromisoformat(entry["timestamp"])
                            if entry_time < start_time:
                                continue

                        if end_time:
                            entry_time = datetime.fromisoformat(entry["timestamp"])
                            if entry_time > end_time:
                                continue

                        logs.append(entry)

                    except:
                        continue

            # 4. 限制返回数量
            logs = logs[-limit:] if len(logs) > limit else logs

            return {
                "success": True,
                "logs": logs,
                "count": len(logs),
                "total": len(logs),
                "query_time": datetime.now().isoformat()
            }

        except Exception as e:
            # 5. 异常处理
            logger.error(f"查询日志失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def rotate_logs(self) -> Dict[str, Any]:
        """
        轮转日志文件

        将当前日志文件归档并创建新文件

        Returns:
            Dict[str, Any]: 轮转结果
        """
        try:
            # 1. 获取归档目录
            archive_dir = self.logs_dir / "archive"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            archived_files = []

            # 2. 轮转各个日志文件
            for category, log_file in self.log_files.items():
                if log_file.exists() and log_file.stat().st_size > 0:
                    archive_name = f"{category.value.lower()}_{timestamp}.log"
                    archive_path = archive_dir / archive_name

                    # 移动文件到归档目录
                    log_file.rename(archive_path)
                    archived_files.append(str(archive_path))

            # 3. 轮转统一日志文件
            if self.unified_log.exists() and self.unified_log.stat().st_size > 0:
                archive_path = archive_dir / f"unified_{timestamp}.log"
                self.unified_log.rename(archive_path)
                archived_files.append(str(archive_path))

            # 4. 返回结果
            logger.info(f"日志文件轮转完成: 归档{len(archived_files)}个文件")
            return {
                "success": True,
                "archived_files": archived_files,
                "archive_dir": str(archive_dir),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            # 5. 异常处理
            logger.error(f"日志轮转失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_log_stats(self) -> Dict[str, Any]:
        """
        获取日志统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            stats = {}
            total_size = 0
            total_lines = 0

            # 1. 统计各分类日志
            for category, log_file in self.log_files.items():
                if log_file.exists():
                    size = log_file.stat().st_size
                    lines = sum(1 for _ in open(log_file, 'r', encoding='utf-8'))

                    stats[category.value] = {
                        "file": str(log_file),
                        "size": size,
                        "lines": lines
                    }
                    total_size += size
                    total_lines += lines

            # 2. 统计统一日志
            if self.unified_log.exists():
                size = self.unified_log.stat().st_size
                lines = sum(1 for _ in open(self.unified_log, 'r', encoding='utf-8'))

                stats["UNIFIED"] = {
                    "file": str(self.unified_log),
                    "size": size,
                    "lines": lines
                }

            # 3. 返回统计结果
            return {
                "success": True,
                "stats": stats,
                "total_size": total_size,
                "total_lines": total_lines,
                "logs_dir": str(self.logs_dir),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            # 4. 异常处理
            logger.error(f"获取日志统计失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def cleanup(self) -> None:
        """
        清理日志管理器

        停止工作线程并保存未写入的日志
        """
        try:
            # 1. 停止工作线程
            self.running = False

            # 2. 处理剩余日志
            while not self.log_queue.empty():
                log_entry = self.log_queue.get()
                category = LogCategory[log_entry["category"]]
                if category in self.log_files:
                    self._write_to_file(self.log_files[category], log_entry)
                self._write_to_file(self.unified_log, log_entry)

            # 3. 等待线程结束
            if self.worker_thread.is_alive():
                self.worker_thread.join(timeout=2)

            logger.info("结构化日志管理器已清理")

        except Exception as e:
            logger.error(f"清理日志管理器失败: {e}")


# 全局日志管理器实例
_structured_logger = None


def get_structured_logger(project_root: Optional[str] = None) -> StructuredLogger:
    """
    获取全局结构化日志管理器实例

    Args:
        project_root: 项目根目录

    Returns:
        StructuredLogger: 管理器实例
    """
    global _structured_logger

    if _structured_logger is None:
        _structured_logger = StructuredLogger(project_root)
        logger.info("创建全局结构化日志管理器实例")

    return _structured_logger


# 便捷日志函数
def log_info(category: LogCategory, message: str, **context) -> Dict[str, Any]:
    """记录INFO级别日志"""
    return get_structured_logger().log(LogLevel.INFO, category, message, context)


def log_warning(category: LogCategory, message: str, **context) -> Dict[str, Any]:
    """记录WARNING级别日志"""
    return get_structured_logger().log(LogLevel.WARNING, category, message, context)


def log_error(category: LogCategory, message: str, **context) -> Dict[str, Any]:
    """记录ERROR级别日志"""
    return get_structured_logger().log(LogLevel.ERROR, category, message, context)


def log_debug(category: LogCategory, message: str, **context) -> Dict[str, Any]:
    """记录DEBUG级别日志"""
    return get_structured_logger().log(LogLevel.DEBUG, category, message, context)