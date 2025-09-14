"""
Session Naming Service - 会话命名标准化服务

统一管理所有会话命名逻辑，消除硬编码，提升可维护性。
替代项目中21处硬编码的会话命名模式。
"""

import re
from typing import Dict, Optional, Tuple


class SessionNaming:
    """会话命名服务 - 统一管理会话命名规范"""
    
    # 命名常量
    PREFIX = "parallel"
    MASTER_SUFFIX = "task_master" 
    CHILD_SUFFIX = "task_child"
    SEPARATOR = "_"
    
    # 正则表达式模式
    MASTER_PATTERN = re.compile(r'^parallel_(.+)_task_master$')
    CHILD_PATTERN = re.compile(r'^parallel_(.+)_task_child_(.+)$')
    
    @classmethod
    def master_session(cls, project_id: str) -> str:
        """生成主会话名称
        
        Args:
            project_id: 项目ID
            
        Returns:
            str: 格式化的主会话名称 (parallel_{project_id}_task_master)
        """
        if not project_id or not project_id.strip():
            raise ValueError("project_id cannot be empty")
        
        return f"{cls.PREFIX}{cls.SEPARATOR}{project_id.strip()}{cls.SEPARATOR}{cls.MASTER_SUFFIX}"
    
    @classmethod  
    def child_session(cls, project_id: str, task_id: str) -> str:
        """生成子会话名称
        
        Args:
            project_id: 项目ID
            task_id: 任务ID
            
        Returns:
            str: 格式化的子会话名称 (parallel_{project_id}_task_child_{task_id})
        """
        if not project_id or not project_id.strip():
            raise ValueError("project_id cannot be empty")
        if not task_id or not task_id.strip():
            raise ValueError("task_id cannot be empty")
            
        return f"{cls.PREFIX}{cls.SEPARATOR}{project_id.strip()}{cls.SEPARATOR}{cls.CHILD_SUFFIX}{cls.SEPARATOR}{task_id.strip()}"
    
    @classmethod
    def parse_session_name(cls, session_name: str) -> Dict[str, Optional[str]]:
        """解析会话名称，提取项目ID和任务ID
        
        Args:
            session_name: 会话名称
            
        Returns:
            Dict: 包含session_type, project_id, task_id的字典
        """
        if not session_name:
            return {"session_type": "unknown", "project_id": None, "task_id": None}
        
        # 尝试匹配主会话
        master_match = cls.MASTER_PATTERN.match(session_name)
        if master_match:
            return {
                "session_type": "master",
                "project_id": master_match.group(1),
                "task_id": None
            }
        
        # 尝试匹配子会话
        child_match = cls.CHILD_PATTERN.match(session_name)
        if child_match:
            return {
                "session_type": "child", 
                "project_id": child_match.group(1),
                "task_id": child_match.group(2)
            }
        
        # 无法识别的会话名称
        return {"session_type": "unknown", "project_id": None, "task_id": None}
    
    @classmethod
    def is_project_session(cls, session_name: str, project_id: str) -> bool:
        """检查会话是否属于指定项目
        
        Args:
            session_name: 会话名称
            project_id: 项目ID
            
        Returns:
            bool: 是否属于指定项目
        """
        parsed = cls.parse_session_name(session_name)
        return parsed["project_id"] == project_id
    
    @classmethod
    def get_session_type(cls, session_name: str) -> str:
        """获取会话类型
        
        Args:
            session_name: 会话名称
            
        Returns:
            str: 会话类型 (master/child/unknown)
        """
        return cls.parse_session_name(session_name)["session_type"]
    
    @classmethod
    def extract_project_id(cls, session_name: str) -> Optional[str]:
        """从会话名称提取项目ID
        
        Args:
            session_name: 会话名称
            
        Returns:
            Optional[str]: 项目ID，如果无法提取则返回None
        """
        return cls.parse_session_name(session_name)["project_id"]
    
    @classmethod
    def extract_task_id(cls, session_name: str) -> Optional[str]:
        """从子会话名称提取任务ID
        
        Args:
            session_name: 子会话名称
            
        Returns:
            Optional[str]: 任务ID，如果是主会话或无法提取则返回None
        """
        return cls.parse_session_name(session_name)["task_id"]
    
    @classmethod
    def list_project_sessions(cls, all_sessions: list, project_id: str) -> Tuple[Optional[str], list]:
        """从会话列表中筛选项目相关会话
        
        Args:
            all_sessions: 所有会话名称列表
            project_id: 项目ID
            
        Returns:
            Tuple[Optional[str], list]: (master_session, child_sessions_list)
        """
        master_session = None
        child_sessions = []
        
        for session_name in all_sessions:
            if cls.is_project_session(session_name, project_id):
                session_type = cls.get_session_type(session_name)
                if session_type == "master":
                    master_session = session_name
                elif session_type == "child":
                    child_sessions.append(session_name)
        
        return master_session, child_sessions