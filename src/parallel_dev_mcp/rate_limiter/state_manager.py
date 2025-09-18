# -*- coding: utf-8 -*-
"""
限流状态管理器

@description 统一管理限流、重试任务、检测结果等状态数据的存储和管理
"""

import json
import logging
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any, Union
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum, unique
import threading
import shutil

# 配置日志系统
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@unique
class StateType(Enum):
    """状态数据类型枚举"""
    RATE_LIMIT = "rate_limit"
    RETRY_TASKS = "retry_tasks"
    DETECTION_HISTORY = "detection_history"
    MESSAGE_QUEUE = "message_queue"
    SYSTEM_CONFIG = "system_config"


class StateConfig(BaseModel):
    """状态管理配置数据模型"""

    storage_directory: str = Field(".rate_limiter_state", description="状态存储目录")
    backup_enabled: bool = Field(True, description="是否启用备份")
    backup_interval_hours: int = Field(6, description="备份间隔小时数", ge=1, le=24)
    max_backup_files: int = Field(10, description="最大备份文件数", ge=1, le=50)
    auto_cleanup_days: int = Field(7, description="自动清理天数", ge=1, le=30)
    compression_enabled: bool = Field(False, description="是否启用压缩")
    encryption_enabled: bool = Field(False, description="是否启用加密")
    sync_enabled: bool = Field(True, description="是否启用同步写入")

    model_config = ConfigDict()


class StateSnapshot(BaseModel):
    """状态快照数据模型"""

    snapshot_id: str = Field(..., description="快照ID")
    state_type: StateType = Field(..., description="状态类型")
    data: Dict[str, Any] = Field(..., description="状态数据")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    size_bytes: int = Field(0, description="数据大小（字节）")
    checksum: Optional[str] = Field(None, description="数据校验和")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")

    model_config = ConfigDict(
        # json_encoders deprecated in V2 - datetime fields will use default serialization
    )


class StateManager:
    """
    统一状态管理器

    负责所有限流相关状态的持久化存储和管理
    """

    def __init__(self, config: Optional[StateConfig] = None) -> None:
        """
        初始化状态管理器

        Args:
            config: 状态管理配置
        """
        # 1. 设置配置
        self.config = config or StateConfig()

        # 2. 初始化存储目录
        self.storage_dir = Path(self.config.storage_directory)
        self.storage_dir.mkdir(exist_ok=True)

        # 3. 初始化文件路径
        self._init_file_paths()

        # 4. 初始化内存缓存
        self.memory_cache: Dict[StateType, Dict[str, Any]] = {}
        self._cache_lock = threading.RLock()

        # 5. 初始化备份管理
        self.backup_enabled = self.config.backup_enabled
        self.last_backup_time: Optional[datetime] = None

        # 6. 记录初始化信息
        logger.info(f"状态管理器初始化: 存储目录={self.storage_dir}")

    def _init_file_paths(self) -> None:
        """初始化文件路径"""
        # 1. 主要状态文件
        self.state_files = {
            StateType.RATE_LIMIT: self.storage_dir / "rate_limit.json",
            StateType.RETRY_TASKS: self.storage_dir / "retry_tasks.json",
            StateType.DETECTION_HISTORY: self.storage_dir / "detection_history.json",
            StateType.MESSAGE_QUEUE: self.storage_dir / "message_queue.json",
            StateType.SYSTEM_CONFIG: self.storage_dir / "system_config.json",
        }

        # 2. 备份目录
        self.backup_dir = self.storage_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)

    def save_state(self, state_type: StateType, data: Dict[str, Any],
                   sync: Optional[bool] = None) -> bool:
        """
        保存状态数据

        Args:
            state_type: 状态类型
            data: 状态数据
            sync: 是否同步写入，None使用配置默认值

        Returns:
            bool: 是否保存成功
        """
        try:
            # 1. 准备数据
            state_data = {
                "state_type": state_type.value,
                "data": data,
                "updated_at": datetime.now().isoformat(),
                "version": "1.0"
            }

            # 2. 更新内存缓存
            with self._cache_lock:
                self.memory_cache[state_type] = data

            # 3. 写入文件
            file_path = self.state_files[state_type]
            content = json.dumps(state_data, ensure_ascii=False, indent=2)

            if sync if sync is not None else self.config.sync_enabled:
                # 同步写入
                file_path.write_text(content, encoding='utf-8')
            else:
                # 异步写入
                self._async_write_file(file_path, content)

            # 4. 检查是否需要备份
            self._check_backup_needed()

            # 5. 记录保存信息
            logger.debug(f"保存状态: {state_type.value}, 大小: {len(content)} 字节")

            return True

        except Exception as e:
            # 6. 处理保存异常
            logger.error(f"保存状态失败: {state_type.value}, 错误: {e}")
            return False

    def load_state(self, state_type: StateType, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """
        加载状态数据

        Args:
            state_type: 状态类型
            use_cache: 是否使用缓存

        Returns:
            Optional[Dict[str, Any]]: 状态数据，失败返回None
        """
        try:
            # 1. 检查内存缓存
            if use_cache:
                with self._cache_lock:
                    if state_type in self.memory_cache:
                        return self.memory_cache[state_type].copy()

            # 2. 从文件加载
            file_path = self.state_files[state_type]
            if not file_path.exists():
                return None

            # 3. 读取文件内容
            content = file_path.read_text(encoding='utf-8')
            state_data = json.loads(content)

            # 4. 提取数据
            data = state_data.get("data", {})

            # 5. 更新缓存
            if use_cache:
                with self._cache_lock:
                    self.memory_cache[state_type] = data.copy()

            # 6. 记录加载信息
            logger.debug(f"加载状态: {state_type.value}, 大小: {len(content)} 字节")

            return data

        except Exception as e:
            # 7. 处理加载异常
            logger.error(f"加载状态失败: {state_type.value}, 错误: {e}")
            return None

    def delete_state(self, state_type: StateType) -> bool:
        """
        删除状态数据

        Args:
            state_type: 状态类型

        Returns:
            bool: 是否删除成功
        """
        try:
            # 1. 从内存缓存删除
            with self._cache_lock:
                if state_type in self.memory_cache:
                    del self.memory_cache[state_type]

            # 2. 删除文件
            file_path = self.state_files[state_type]
            if file_path.exists():
                file_path.unlink()

            # 3. 记录删除信息
            logger.info(f"删除状态: {state_type.value}")

            return True

        except Exception as e:
            # 4. 处理删除异常
            logger.error(f"删除状态失败: {state_type.value}, 错误: {e}")
            return False

    def clear_all_states(self, confirm: bool = False) -> bool:
        """
        清空所有状态数据

        Args:
            confirm: 确认清空操作

        Returns:
            bool: 是否清空成功
        """
        if not confirm:
            logger.warning("清空所有状态需要确认参数")
            return False

        try:
            # 1. 清空内存缓存
            with self._cache_lock:
                self.memory_cache.clear()

            # 2. 删除所有状态文件
            for state_type in StateType:
                file_path = self.state_files[state_type]
                if file_path.exists():
                    file_path.unlink()

            # 3. 记录清空信息
            logger.info("清空所有状态数据")

            return True

        except Exception as e:
            # 4. 处理清空异常
            logger.error(f"清空状态失败: {e}")
            return False

    def create_backup(self, backup_name: Optional[str] = None) -> Optional[str]:
        """
        创建状态备份

        Args:
            backup_name: 备份名称，None则自动生成

        Returns:
            Optional[str]: 备份文件路径，失败返回None
        """
        try:
            # 1. 生成备份名称
            if not backup_name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"backup_{timestamp}"

            # 2. 创建备份目录
            backup_path = self.backup_dir / backup_name
            backup_path.mkdir(exist_ok=True)

            # 3. 复制状态文件
            copied_files = 0
            for state_type, file_path in self.state_files.items():
                if file_path.exists():
                    backup_file = backup_path / file_path.name
                    shutil.copy2(file_path, backup_file)
                    copied_files += 1

            # 4. 创建备份元数据
            metadata = {
                "backup_name": backup_name,
                "created_at": datetime.now().isoformat(),
                "files_count": copied_files,
                "total_size": self._calculate_directory_size(backup_path)
            }

            metadata_file = backup_path / "backup_metadata.json"
            metadata_file.write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )

            # 5. 更新备份时间
            self.last_backup_time = datetime.now()

            # 6. 清理旧备份
            self._cleanup_old_backups()

            # 7. 记录备份信息
            logger.info(f"创建状态备份: {backup_name}, 文件数: {copied_files}")

            return str(backup_path)

        except Exception as e:
            # 8. 处理备份异常
            logger.error(f"创建备份失败: {e}")
            return None

    def restore_backup(self, backup_name: str, confirm: bool = False) -> bool:
        """
        恢复状态备份

        Args:
            backup_name: 备份名称
            confirm: 确认恢复操作

        Returns:
            bool: 是否恢复成功
        """
        if not confirm:
            logger.warning("恢复备份需要确认参数")
            return False

        try:
            # 1. 检查备份是否存在
            backup_path = self.backup_dir / backup_name
            if not backup_path.exists():
                logger.error(f"备份不存在: {backup_name}")
                return False

            # 2. 清空当前状态
            self.clear_all_states(confirm=True)

            # 3. 恢复备份文件
            restored_files = 0
            for state_file in backup_path.glob("*.json"):
                if state_file.name != "backup_metadata.json":
                    target_file = self.storage_dir / state_file.name
                    shutil.copy2(state_file, target_file)
                    restored_files += 1

            # 4. 重新加载状态到缓存
            for state_type in StateType:
                self.load_state(state_type, use_cache=True)

            # 5. 记录恢复信息
            logger.info(f"恢复状态备份: {backup_name}, 文件数: {restored_files}")

            return True

        except Exception as e:
            # 6. 处理恢复异常
            logger.error(f"恢复备份失败: {backup_name}, 错误: {e}")
            return False

    def list_backups(self) -> List[Dict[str, Any]]:
        """
        列出所有备份

        Returns:
            List[Dict[str, Any]]: 备份信息列表
        """
        # 1. 初始化备份列表
        backups = []

        try:
            # 2. 扫描备份目录
            for backup_dir in self.backup_dir.iterdir():
                if backup_dir.is_dir():
                    # 3. 读取备份元数据
                    metadata_file = backup_dir / "backup_metadata.json"
                    if metadata_file.exists():
                        try:
                            metadata = json.loads(metadata_file.read_text(encoding='utf-8'))
                            metadata["backup_path"] = str(backup_dir)
                            backups.append(metadata)
                        except Exception as e:
                            logger.warning(f"读取备份元数据失败: {backup_dir.name}, 错误: {e}")

            # 4. 按创建时间排序
            backups.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        except Exception as e:
            # 5. 处理列表异常
            logger.error(f"列出备份失败: {e}")

        return backups

    def get_state_summary(self) -> Dict[str, Any]:
        """
        获取状态摘要信息

        Returns:
            Dict[str, Any]: 状态摘要
        """
        # 1. 统计文件信息
        file_info = {}
        total_size = 0

        for state_type, file_path in self.state_files.items():
            if file_path.exists():
                file_size = file_path.stat().st_size
                file_info[state_type.value] = {
                    "exists": True,
                    "size_bytes": file_size,
                    "modified_at": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                }
                total_size += file_size
            else:
                file_info[state_type.value] = {"exists": False}

        # 2. 统计缓存信息
        cache_info = {}
        with self._cache_lock:
            for state_type, data in self.memory_cache.items():
                cache_info[state_type.value] = {
                    "cached": True,
                    "items_count": len(data) if isinstance(data, (dict, list)) else 1
                }

        # 3. 统计备份信息
        backup_count = len(self.list_backups())

        # 4. 返回摘要信息
        return {
            "storage_directory": str(self.storage_dir),
            "total_size_bytes": total_size,
            "files": file_info,
            "cache": cache_info,
            "backup_count": backup_count,
            "last_backup": self.last_backup_time.isoformat() if self.last_backup_time else None,
            "config": self.config.model_dump()
        }

    def _async_write_file(self, file_path: Path, content: str) -> None:
        """
        异步写入文件

        Args:
            file_path: 文件路径
            content: 文件内容
        """
        def write_file():
            try:
                file_path.write_text(content, encoding='utf-8')
            except Exception as e:
                logger.error(f"异步写入文件失败: {file_path}, 错误: {e}")

        # 1. 在新线程中执行写入
        threading.Thread(target=write_file, daemon=True).start()

    def _check_backup_needed(self) -> None:
        """检查是否需要创建备份"""
        # 1. 检查是否启用备份
        if not self.backup_enabled:
            return

        # 2. 检查备份间隔
        if self.last_backup_time:
            time_since_backup = datetime.now() - self.last_backup_time
            if time_since_backup.total_seconds() < self.config.backup_interval_hours * 3600:
                return

        # 3. 创建自动备份
        self.create_backup()

    def _cleanup_old_backups(self) -> None:
        """清理旧备份文件"""
        try:
            # 1. 获取所有备份
            backups = self.list_backups()

            # 2. 按时间排序（最新的在前）
            backups.sort(key=lambda x: x.get("created_at", ""), reverse=True)

            # 3. 删除超出限制的备份
            if len(backups) > self.config.max_backup_files:
                for backup in backups[self.config.max_backup_files:]:
                    backup_path = Path(backup["backup_path"])
                    if backup_path.exists():
                        shutil.rmtree(backup_path)
                        logger.info(f"删除旧备份: {backup_path.name}")

        except Exception as e:
            # 4. 处理清理异常
            logger.warning(f"清理旧备份失败: {e}")

    def _calculate_directory_size(self, directory: Path) -> int:
        """
        计算目录大小

        Args:
            directory: 目录路径

        Returns:
            int: 目录大小（字节）
        """
        total_size = 0
        try:
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except Exception as e:
            logger.warning(f"计算目录大小失败: {directory}, 错误: {e}")

        return total_size