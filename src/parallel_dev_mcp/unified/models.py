# -*- coding: utf-8 -*-
"""
统一工具数据模型

@description 符合CLAUDE.md规范的类型安全模型，禁止使用Dict[str, Any]
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class SessionInfo(BaseModel):
    """
    会话信息模型

    描述单个并行开发会话的完整信息。
    """
    session_id: str = Field(..., description="会话唯一标识（格式：project_id/task_id）")
    session_name: str = Field(..., description="Tmux会话名称")
    task_id: str = Field(..., description="任务ID")
    project_id: str = Field(..., description="项目ID")
    status: str = Field("active", description="会话状态（active/terminated）")
    worktree_path: str = Field("", description="Git worktree路径")
    tmux_session_id: str = Field("", description="Tmux内部会话ID")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")

    @field_validator('session_id')
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        """验证会话ID格式"""
        # 1. 检查会话ID不为空
        if not v or not v.strip():
            raise ValueError('会话ID不能为空')

        # 2. 返回验证后的值
        return v.strip()

    @field_validator('session_name')
    @classmethod
    def validate_session_name(cls, v: str) -> str:
        """验证会话名称格式"""
        # 1. 检查会话名称不为空
        if not v or not v.strip():
            raise ValueError('会话名称不能为空')

        # 2. 返回验证后的值
        return v.strip()


class SessionResult(BaseModel):
    """
    会话操作结果模型

    所有会话操作的统一返回类型，符合CLAUDE.md规范。
    """
    success: bool = Field(..., description="操作是否成功")
    message: str = Field("", description="操作结果消息")
    action: str = Field("", description="执行的操作类型")
    session: Optional[SessionInfo] = Field(None, description="单个会话信息（create/info操作）")
    sessions: List[SessionInfo] = Field(default_factory=list, description="会话列表（list操作）")
    count: int = Field(0, description="会话数量", ge=0)
    timestamp: datetime = Field(default_factory=datetime.now, description="操作时间")
    error: Optional[str] = Field(None, description="错误信息（失败时）")

    @field_validator('action')
    @classmethod
    def validate_action(cls, v: str) -> str:
        """验证操作类型"""
        # 1. 定义有效的操作类型
        valid_actions = ['create', 'list', 'terminate', 'info', '']

        # 2. 检查操作类型有效性
        if v and v not in valid_actions:
            raise ValueError(f'操作类型必须是以下之一: {valid_actions}')

        # 3. 返回验证后的值
        return v


class MessageResult(BaseModel):
    """
    消息发送结果模型

    消息发送操作的统一返回类型，符合CLAUDE.md规范。
    """
    success: bool = Field(..., description="发送是否成功")
    message: str = Field("", description="操作结果消息")
    session_name: str = Field("", description="目标会话名称")
    content: str = Field("", description="发送的消息内容")
    delivered: bool = Field(False, description="消息是否已送达")
    delay_seconds: int = Field(0, description="延时秒数", ge=0, le=300)
    timestamp: datetime = Field(default_factory=datetime.now, description="发送时间")
    error: Optional[str] = Field(None, description="错误信息（失败时）")

    @field_validator('session_name')
    @classmethod
    def validate_session_name(cls, v: str) -> str:
        """验证会话名称"""
        # 1. 检查会话名称不为空
        if not v or not v.strip():
            raise ValueError('会话名称不能为空')

        # 2. 返回验证后的值
        return v.strip()

    @field_validator('delay_seconds')
    @classmethod
    def validate_delay(cls, v: int) -> int:
        """验证延时参数"""
        # 1. 限制延时范围
        if v < 0:
            return 0
        if v > 300:
            return 300

        # 2. 返回验证后的值
        return v


class ChildResourceUpdateResult(BaseModel):
    """
    Child资源更新结果模型

    更新Child资源操作的统一返回类型，符合CLAUDE.md规范。
    替代 Dict[str, Any] 返回值。
    """
    success: bool = Field(..., description="更新是否成功")
    message: str = Field("", description="操作结果消息")
    project_id: str = Field("", description="项目ID")
    task_id: str = Field("", description="任务ID")
    updated_fields: List[str] = Field(default_factory=list, description="已更新的字段列表")
    timestamp: datetime = Field(default_factory=datetime.now, description="更新时间")
    error: Optional[str] = Field(None, description="错误信息（失败时）")

    @field_validator('project_id')
    @classmethod
    def validate_project_id(cls, v: str) -> str:
        """验证项目ID"""
        # 1. 检查项目ID不为空
        if v and not v.strip():
            raise ValueError('项目ID不能为空字符串')

        # 2. 返回验证后的值
        return v.strip() if v else ""

    @field_validator('task_id')
    @classmethod
    def validate_task_id(cls, v: str) -> str:
        """验证任务ID"""
        # 1. 检查任务ID不为空
        if v and not v.strip():
            raise ValueError('任务ID不能为空字符串')

        # 2. 返回验证后的值
        return v.strip() if v else ""
