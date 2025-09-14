"""
Response Builder - 响应格式标准化服务

统一管理所有MCP工具的响应格式，消除重复代码，提升一致性。
替代项目中15+处重复的响应格式构建逻辑。
"""

from typing import Any, Dict, Optional, List
from datetime import datetime


class ResponseBuilder:
    """响应构建器 - 标准化所有MCP工具的响应格式"""
    
    @staticmethod
    def success(data: Any = None, **kwargs) -> Dict[str, Any]:
        """构建成功响应
        
        Args:
            data: 响应数据，可以是dict、list或其他类型
            **kwargs: 额外的响应字段
            
        Returns:
            Dict[str, Any]: 标准化的成功响应
        """
        result = {"success": True}
        
        # 处理数据字段
        if data is not None:
            if isinstance(data, dict):
                # 如果data是dict，直接合并到结果中
                result.update(data)
            else:
                # 如果data不是dict，作为data字段
                result["data"] = data
        
        # 添加额外字段
        result.update(kwargs)
        
        return result
    
    @staticmethod
    def error(message: str, **kwargs) -> Dict[str, Any]:
        """构建错误响应
        
        Args:
            message: 错误消息
            **kwargs: 额外的错误详情字段
            
        Returns:
            Dict[str, Any]: 标准化的错误响应
        """
        result = {
            "success": False,
            "error": message
        }
        result.update(kwargs)
        return result
    
    @staticmethod
    def validation_error(field: str, value: Any, expected: str) -> Dict[str, Any]:
        """构建参数验证错误响应
        
        Args:
            field: 验证失败的字段名
            value: 实际值
            expected: 期望值描述
            
        Returns:
            Dict[str, Any]: 参数验证错误响应
        """
        return ResponseBuilder.error(
            f"Invalid {field}: {value}. Expected: {expected}",
            validation_error=True,
            field=field,
            actual_value=value,
            expected_value=expected
        )
    
    @staticmethod
    def not_found_error(resource_type: str, identifier: str) -> Dict[str, Any]:
        """构建资源未找到错误响应
        
        Args:
            resource_type: 资源类型 (如: session, project, file)
            identifier: 资源标识符
            
        Returns:
            Dict[str, Any]: 资源未找到错误响应
        """
        return ResponseBuilder.error(
            f"{resource_type.title()} not found: {identifier}",
            not_found=True,
            resource_type=resource_type,
            resource_id=identifier
        )
    
    @staticmethod
    def already_exists_error(resource_type: str, identifier: str) -> Dict[str, Any]:
        """构建资源已存在错误响应
        
        Args:
            resource_type: 资源类型
            identifier: 资源标识符
            
        Returns:
            Dict[str, Any]: 资源已存在错误响应
        """
        return ResponseBuilder.error(
            f"{resource_type.title()} already exists: {identifier}",
            already_exists=True,
            resource_type=resource_type,
            resource_id=identifier
        )
    
    @staticmethod
    def permission_error(action: str, resource: str) -> Dict[str, Any]:
        """构建权限错误响应
        
        Args:
            action: 尝试执行的动作
            resource: 相关资源
            
        Returns:
            Dict[str, Any]: 权限错误响应
        """
        return ResponseBuilder.error(
            f"Permission denied: cannot {action} {resource}",
            permission_denied=True,
            action=action,
            resource=resource
        )
    
    @staticmethod
    def operation_result(operation: str, success: bool, message: str = None, **kwargs) -> Dict[str, Any]:
        """构建操作结果响应
        
        Args:
            operation: 操作名称
            success: 操作是否成功
            message: 自定义消息
            **kwargs: 额外的结果数据
            
        Returns:
            Dict[str, Any]: 操作结果响应
        """
        if success:
            result = ResponseBuilder.success(
                operation=operation,
                message=message or f"{operation} completed successfully",
                **kwargs
            )
        else:
            result = ResponseBuilder.error(
                message or f"{operation} failed",
                operation=operation,
                **kwargs
            )
        
        return result
    
    @staticmethod
    def list_result(items: List[Any], total_count: int = None, 
                   filtered: bool = False, **kwargs) -> Dict[str, Any]:
        """构建列表结果响应
        
        Args:
            items: 列表项目
            total_count: 总数量（如果与返回数量不同）
            filtered: 是否经过筛选
            **kwargs: 额外的元数据
            
        Returns:
            Dict[str, Any]: 列表结果响应
        """
        result = ResponseBuilder.success(
            items=items,
            count=len(items),
            **kwargs
        )
        
        if total_count is not None and total_count != len(items):
            result["total_count"] = total_count
            result["filtered"] = True
        elif filtered:
            result["filtered"] = True
            
        return result
    
    @staticmethod
    def status_result(status: str, details: Dict[str, Any] = None, 
                     healthy: bool = None, **kwargs) -> Dict[str, Any]:
        """构建状态结果响应
        
        Args:
            status: 状态值 (healthy/warning/error/unknown等)
            details: 状态详情
            healthy: 是否健康（布尔值）
            **kwargs: 额外的状态数据
            
        Returns:
            Dict[str, Any]: 状态结果响应
        """
        result = ResponseBuilder.success(
            status=status,
            timestamp=datetime.now().isoformat(),
            **kwargs
        )
        
        if details:
            result["details"] = details
            
        if healthy is not None:
            result["healthy"] = healthy
        elif status == "healthy":
            result["healthy"] = True
        elif status in ["error", "critical", "failed"]:
            result["healthy"] = False
            
        return result
    
    @staticmethod
    def session_result(session_name: str, session_type: str = None, 
                      project_id: str = None, task_id: str = None,
                      **kwargs) -> Dict[str, Any]:
        """构建会话相关结果响应
        
        Args:
            session_name: 会话名称
            session_type: 会话类型
            project_id: 项目ID
            task_id: 任务ID
            **kwargs: 额外的会话数据
            
        Returns:
            Dict[str, Any]: 会话结果响应
        """
        result = ResponseBuilder.success(
            session_name=session_name,
            **kwargs
        )
        
        if session_type:
            result["session_type"] = session_type
        if project_id:
            result["project_id"] = project_id
        if task_id:
            result["task_id"] = task_id
            
        return result
    
    @staticmethod
    def with_recommendations(base_response: Dict[str, Any], 
                           recommendations: List[str]) -> Dict[str, Any]:
        """为响应添加建议信息
        
        Args:
            base_response: 基础响应
            recommendations: 建议列表
            
        Returns:
            Dict[str, Any]: 包含建议的响应
        """
        if recommendations:
            base_response["recommendations"] = recommendations
        return base_response