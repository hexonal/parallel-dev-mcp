# -*- coding: utf-8 -*-
"""
Prompt类型定义

@description 定义不同类型的Prompt和上下文信息
"""

from enum import Enum, unique
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


@unique
class PromptType(Enum):
    """Prompt类型枚举"""
    MASTER_STOP = "master_stop"
    MASTER_SESSION_END = "master_session_end"
    CHILD_DEFAULT = "child_default"
    CHILD_STARTUP = "child_startup"
    CONTINUE_EXECUTION = "continue_execution"
    RATE_LIMIT_RECOVERY = "rate_limit_recovery"


@unique
class TemplateStatus(Enum):
    """模板状态枚举"""
    VALID = "valid"
    INVALID = "invalid"
    NOT_FOUND = "not_found"
    LOADING = "loading"
    ERROR = "error"


class PromptContext(BaseModel):
    """Prompt上下文数据模型"""

    prompt_type: PromptType = Field(..., description="Prompt类型")
    session_name: Optional[str] = Field(None, description="会话名称")
    project_id: Optional[str] = Field(None, description="项目ID")
    task_id: Optional[str] = Field(None, description="任务ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
    variables: Dict[str, Any] = Field(default_factory=dict, description="模板变量")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="附加元数据")


class TemplateInfo(BaseModel):
    """模板信息数据模型"""

    template_name: str = Field(..., description="模板名称")
    file_path: str = Field(..., description="文件路径")
    content: Optional[str] = Field(None, description="模板内容")
    status: TemplateStatus = Field(..., description="模板状态")
    last_loaded: Optional[datetime] = Field(None, description="最后加载时间")
    last_modified: Optional[datetime] = Field(None, description="文件最后修改时间")
    variables: list[str] = Field(default_factory=list, description="模板中的变量")
    error_message: Optional[str] = Field(None, description="错误信息")


class PromptResult(BaseModel):
    """Prompt生成结果数据模型"""

    prompt_type: PromptType = Field(..., description="Prompt类型")
    content: str = Field(..., description="生成的Prompt内容")
    success: bool = Field(..., description="是否生成成功")
    context: PromptContext = Field(..., description="生成上下文")
    template_used: Optional[str] = Field(None, description="使用的模板名称")
    variables_applied: Dict[str, Any] = Field(default_factory=dict, description="应用的变量")
    error_message: Optional[str] = Field(None, description="错误信息")
    generated_at: datetime = Field(default_factory=datetime.now, description="生成时间")