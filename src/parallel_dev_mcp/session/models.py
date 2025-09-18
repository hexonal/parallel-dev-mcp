# -*- coding: utf-8 -*-
"""
MCP资源数据模型

@description 定义Master和Child资源的数据结构和验证规则
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator
from enum import Enum, unique


@unique
class ChildStatus(Enum):
    """Child会话状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@unique
class MasterStatus(Enum):
    """Master会话状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class RepoInfo(BaseModel):
    """仓库信息数据模型"""

    remote: str = Field(..., description="远程仓库地址", min_length=1, max_length=500)
    branch: str = Field(..., description="分支名称", min_length=1, max_length=100)
    commit_hash: Optional[str] = Field(None, description="提交哈希", max_length=40)
    last_sync: Optional[datetime] = Field(None, description="最后同步时间")

    @field_validator('remote')
    @classmethod
    def validate_remote(cls, v: str) -> str:
        """验证远程仓库地址格式"""
        # 1. 基本格式检查
        if not v or not v.strip():
            raise ValueError('远程仓库地址不能为空')

        # 2. 移除首尾空格
        remote = v.strip()

        # 3. 简单的URL格式验证
        valid_prefixes = ['https://', 'http://', 'git@', 'ssh://']
        if not any(remote.startswith(prefix) for prefix in valid_prefixes):
            raise ValueError('远程仓库地址格式无效')

        return remote

    @field_validator('branch')
    @classmethod
    def validate_branch(cls, v: str) -> str:
        """验证分支名称格式"""
        # 1. 基本检查
        if not v or not v.strip():
            raise ValueError('分支名称不能为空')

        # 2. 移除首尾空格
        branch = v.strip()

        # 3. 检查无效字符
        invalid_chars = [' ', '\t', '\n', '\r', '..', '~', '^', ':', '?', '*', '[', '\\']
        for char in invalid_chars:
            if char in branch:
                raise ValueError(f'分支名称包含无效字符: {char}')

        return branch

    model_config = ConfigDict(
        # datetime fields use default ISO format serialization in Pydantic V2
    )


class ChildResourceModel(BaseModel):
    """Child资源数据模型"""

    session_name: str = Field(..., description="会话名称", min_length=1, max_length=200)
    task_id: str = Field(..., description="任务ID", min_length=1, max_length=100)
    status: ChildStatus = Field(ChildStatus.PENDING, description="会话状态")
    reason: Optional[str] = Field(None, description="状态原因或说明", max_length=500)
    transcript: Optional[str] = Field(None, description="会话记录", max_length=10000)
    last_update: datetime = Field(default_factory=datetime.now, description="最后更新时间")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    project_id: Optional[str] = Field(None, description="项目ID", max_length=100)
    worktree_path: Optional[str] = Field(None, description="工作树路径", max_length=500)
    exit_code: Optional[int] = Field(None, description="退出码")
    duration_seconds: Optional[float] = Field(None, description="运行时长（秒）", ge=0)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="附加元数据")

    @field_validator('session_name')
    @classmethod
    def validate_session_name(cls, v: str) -> str:
        """验证会话名称格式"""
        # 1. 基本检查
        if not v or not v.strip():
            raise ValueError('会话名称不能为空')

        # 2. 移除首尾空格
        session_name = v.strip()

        # 3. 检查长度
        if len(session_name) < 1 or len(session_name) > 200:
            raise ValueError('会话名称长度必须在1-200字符之间')

        return session_name

    @field_validator('task_id')
    @classmethod
    def validate_task_id(cls, v: str) -> str:
        """验证任务ID格式"""
        # 1. 基本检查
        if not v or not v.strip():
            raise ValueError('任务ID不能为空')

        # 2. 移除首尾空格
        task_id = v.strip()

        # 3. 简单格式检查
        if not task_id.replace('_', '').replace('-', '').replace('.', '').isalnum():
            raise ValueError('任务ID只能包含字母、数字、下划线、连字符和点')

        return task_id

    @field_validator('transcript')
    @classmethod
    def validate_transcript(cls, v: Optional[str]) -> Optional[str]:
        """验证会话记录长度"""
        # 1. 空值检查
        if v is None:
            return v

        # 2. 长度检查
        if len(v) > 10000:
            # 截断过长的记录
            return v[:10000] + "...[truncated]"

        return v

    model_config = ConfigDict(
        # datetime fields use default ISO format serialization in Pydantic V2
    )


class MasterResourceModel(BaseModel):
    """Master资源数据模型"""

    session_id: Optional[str] = Field(None, description="会话ID", max_length=100)
    repo: RepoInfo = Field(..., description="仓库信息")
    children: List[ChildResourceModel] = Field(default_factory=list, description="子会话列表")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    status: MasterStatus = Field(MasterStatus.ACTIVE, description="Master状态")
    project_id: str = Field(..., description="项目ID", min_length=1, max_length=100)
    project_name: Optional[str] = Field(None, description="项目名称", max_length=200)
    total_children: int = Field(0, description="子会话总数", ge=0)
    active_children: int = Field(0, description="活跃子会话数", ge=0)
    worktree_base_path: Optional[str] = Field(None, description="工作树基础路径", max_length=500)
    auto_refresh_enabled: bool = Field(True, description="是否启用自动刷新")
    last_refresh: Optional[datetime] = Field(None, description="最后刷新时间")
    configuration: Dict[str, Any] = Field(default_factory=dict, description="配置信息")

    @field_validator('session_id')
    @classmethod
    def validate_session_id(cls, v: Optional[str]) -> Optional[str]:
        """验证会话ID格式"""
        # 1. 空值检查
        if v is None or v == "":
            return None

        # 2. 移除首尾空格
        session_id = v.strip()

        # 3. 空字符串处理
        if not session_id:
            return None

        # 4. 长度检查
        if len(session_id) > 100:
            raise ValueError('会话ID长度不能超过100字符')

        return session_id

    @field_validator('project_id')
    @classmethod
    def validate_project_id(cls, v: str) -> str:
        """验证项目ID格式"""
        # 1. 基本检查
        if not v or not v.strip():
            raise ValueError('项目ID不能为空')

        # 2. 移除首尾空格
        project_id = v.strip()

        # 3. 格式检查
        if not project_id.replace('_', '').replace('-', '').isalnum():
            raise ValueError('项目ID只能包含字母、数字、下划线和连字符')

        return project_id

    @field_validator('children')
    @classmethod
    def validate_children(cls, v: List[ChildResourceModel]) -> List[ChildResourceModel]:
        """验证子会话列表"""
        # 1. 检查重复的任务ID
        task_ids = [child.task_id for child in v]
        if len(task_ids) != len(set(task_ids)):
            raise ValueError('子会话中存在重复的任务ID')

        # 2. 检查重复的会话名称
        session_names = [child.session_name for child in v]
        if len(session_names) != len(set(session_names)):
            raise ValueError('子会话中存在重复的会话名称')

        return v

    @field_validator('total_children')
    @classmethod
    def validate_total_children(cls, v: int, values: Dict[str, Any]) -> int:
        """验证子会话总数"""
        # 1. 获取children列表
        children = values.get('children', [])

        # 2. 如果指定了total_children，验证是否与实际数量一致
        if v != len(children):
            # 自动调整为实际数量
            return len(children)

        return v

    @field_validator('active_children')
    @classmethod
    def validate_active_children(cls, v: int, values: Dict[str, Any]) -> int:
        """验证活跃子会话数"""
        # 1. 获取children列表
        children = values.get('children', [])

        # 2. 计算实际的活跃会话数
        active_statuses = [ChildStatus.RUNNING, ChildStatus.PENDING]
        actual_active = sum(1 for child in children if child.status in active_statuses)

        # 3. 如果指定值与实际不符，自动调整
        if v != actual_active:
            return actual_active

        return v

    def add_child(self, child: ChildResourceModel) -> None:
        """
        添加子会话

        Args:
            child: 子会话模型
        """
        # 1. 检查任务ID是否重复
        existing_task_ids = [c.task_id for c in self.children]
        if child.task_id in existing_task_ids:
            raise ValueError(f'任务ID已存在: {child.task_id}')

        # 2. 检查会话名称是否重复
        existing_session_names = [c.session_name for c in self.children]
        if child.session_name in existing_session_names:
            raise ValueError(f'会话名称已存在: {child.session_name}')

        # 3. 添加子会话
        self.children.append(child)

        # 4. 更新计数
        self.total_children = len(self.children)
        self._update_active_children_count()

        # 5. 更新时间
        self.updated_at = datetime.now()

    def remove_child(self, task_id: str) -> bool:
        """
        移除子会话

        Args:
            task_id: 任务ID

        Returns:
            bool: 是否移除成功
        """
        # 1. 查找要移除的子会话
        for i, child in enumerate(self.children):
            if child.task_id == task_id:
                # 2. 移除子会话
                self.children.pop(i)

                # 3. 更新计数
                self.total_children = len(self.children)
                self._update_active_children_count()

                # 4. 更新时间
                self.updated_at = datetime.now()

                return True

        # 5. 未找到指定的子会话
        return False

    def update_child_status(self, task_id: str, status: ChildStatus, reason: Optional[str] = None) -> bool:
        """
        更新子会话状态

        Args:
            task_id: 任务ID
            status: 新状态
            reason: 状态原因

        Returns:
            bool: 是否更新成功
        """
        # 1. 查找子会话
        for child in self.children:
            if child.task_id == task_id:
                # 2. 更新状态
                child.status = status
                if reason:
                    child.reason = reason
                child.last_update = datetime.now()

                # 3. 更新计数
                self._update_active_children_count()

                # 4. 更新时间
                self.updated_at = datetime.now()

                return True

        # 5. 未找到指定的子会话
        return False

    def get_child(self, task_id: str) -> Optional[ChildResourceModel]:
        """
        获取子会话

        Args:
            task_id: 任务ID

        Returns:
            Optional[ChildResourceModel]: 子会话模型
        """
        # 1. 查找子会话
        for child in self.children:
            if child.task_id == task_id:
                return child

        # 2. 未找到
        return None

    def _update_active_children_count(self) -> None:
        """更新活跃子会话数"""
        # 1. 计算活跃会话数
        active_statuses = [ChildStatus.RUNNING, ChildStatus.PENDING]
        self.active_children = sum(1 for child in self.children if child.status in active_statuses)

    model_config = ConfigDict(
        # datetime fields use default ISO format serialization in Pydantic V2
    )