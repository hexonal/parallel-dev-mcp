"""
Relationship Manager - 会话关系管理
从coordinator的关系处理能力完美融合而来，提供会话父子关系管理。
每个函数都是独立的MCP工具，Claude可以直接调用。
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

# 复用已重构的注册中心组件
from .._internal.session_registry import SessionRegistry

# MCP工具装饰器
def mcp_tool(name: str = None, description: str = None):
    """MCP工具装饰器"""
    def decorator(func):
        func.mcp_tool_name = name or func.__name__
        func.mcp_tool_description = description or func.__doc__
        return func
    return decorator

# 全局会话注册中心
_session_registry = SessionRegistry()

@mcp_tool(
    name="register_session_relationship",
    description="注册会话父子关系，建立会话层级结构"
)
def register_session_relationship(
    parent_session: str,
    child_session: str,
    relationship_type: str = "parent-child",
    metadata: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    注册会话关系 - 建立会话层级结构
    
    Args:
        parent_session: 父会话名称
        child_session: 子会话名称  
        relationship_type: 关系类型 (parent-child/sibling/dependency)
        metadata: 关系元数据
    """
    try:
        # 检查父会话是否存在
        parent_info = _session_registry.get_session_info(parent_session)
        if not parent_info:
            return {
                "success": False,
                "error": f"父会话不存在: {parent_session}"
            }
        
        # 检查子会话是否存在
        child_info = _session_registry.get_session_info(child_session)
        if not child_info:
            return {
                "success": False,
                "error": f"子会话不存在: {child_session}"
            }
        
        # 检查是否会形成循环关系
        if _would_create_cycle(parent_session, child_session):
            return {
                "success": False,
                "error": f"关系注册会形成循环依赖: {parent_session} -> {child_session}"
            }
        
        # 注册关系
        relationship_registered = _session_registry.register_relationship(parent_session, child_session)
        
        if not relationship_registered:
            return {
                "success": False,
                "error": f"关系已存在: {parent_session} -> {child_session}"
            }
        
        # 构建响应
        result = {
            "success": True,
            "relationship": {
                "parent": parent_session,
                "child": child_session,
                "type": relationship_type,
                "registered_at": datetime.now().isoformat(),
                "metadata": metadata or {}
            },
            "parent_info": parent_info.to_dict(),
            "child_info": child_info.to_dict()
        }
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": f"注册会话关系失败: {str(e)}"
        }

@mcp_tool(
    name="query_child_sessions",
    description="查询指定会话的所有子会话"
)
def query_child_sessions(
    parent_session: str,
    include_details: bool = True,
    recursive: bool = False
) -> Dict[str, Any]:
    """
    查询子会话 - 获取会话的子级列表
    
    Args:
        parent_session: 父会话名称
        include_details: 是否包含子会话详细信息
        recursive: 是否递归查询所有后代会话
    """
    try:
        # 检查父会话是否存在
        parent_info = _session_registry.get_session_info(parent_session)
        if not parent_info:
            return {
                "success": False,
                "error": f"父会话不存在: {parent_session}"
            }
        
        # 获取直接子会话
        direct_children = _session_registry.get_child_sessions(parent_session)
        
        if recursive:
            # 递归获取所有后代会话
            all_descendants = _get_all_descendants(parent_session)
            children_data = _build_hierarchical_data(parent_session, all_descendants, include_details)
        else:
            # 只获取直接子会话数据
            children_data = []
            for child_name in direct_children:
                child_info = _session_registry.get_session_info(child_name)
                if child_info:
                    child_data = {
                        "name": child_name,
                        "direct_child": True
                    }
                    
                    if include_details:
                        child_data.update(child_info.to_dict())
                        child_data["child_count"] = len(_session_registry.get_child_sessions(child_name))
                    
                    children_data.append(child_data)
        
        # 构建响应
        result = {
            "success": True,
            "parent_session": parent_session,
            "query_params": {
                "include_details": include_details,
                "recursive": recursive
            },
            "children": {
                "direct_count": len(direct_children),
                "total_count": len(children_data),
                "sessions": children_data
            }
        }
        
        if include_details:
            result["parent_details"] = parent_info.to_dict()
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": f"查询子会话失败: {str(e)}"
        }

@mcp_tool(
    name="get_session_hierarchy",
    description="获取完整的会话层级结构树"
)
def get_session_hierarchy(
    root_session: str = None,
    max_depth: int = None,
    include_siblings: bool = False
) -> Dict[str, Any]:
    """
    获取会话层级结构 - 完整的会话树视图
    
    Args:
        root_session: 根会话名称（为空时显示所有根会话）
        max_depth: 最大深度限制
        include_siblings: 是否包含兄弟会话信息
    """
    try:
        if root_session:
            # 指定根会话的层级结构
            root_info = _session_registry.get_session_info(root_session)
            if not root_info:
                return {
                    "success": False,
                    "error": f"根会话不存在: {root_session}"
                }
            
            hierarchy = _build_session_tree(root_session, max_depth or 10, 0)
            
            result = {
                "success": True,
                "hierarchy_type": "single_root",
                "root_session": root_session,
                "tree": hierarchy
            }
        
        else:
            # 所有会话的完整层级结构
            all_sessions = _session_registry.list_all_sessions()
            root_sessions = _find_root_sessions(list(all_sessions.keys()))
            
            trees = {}
            for root in root_sessions:
                trees[root] = _build_session_tree(root, max_depth or 10, 0)
            
            result = {
                "success": True,
                "hierarchy_type": "full_forest",
                "root_sessions": root_sessions,
                "trees": trees,
                "total_sessions": len(all_sessions),
                "orphaned_sessions": _find_orphaned_sessions(list(all_sessions.keys()))
            }
        
        # 添加层级统计
        result["hierarchy_stats"] = _calculate_hierarchy_stats(result)
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": f"获取会话层级结构失败: {str(e)}"
        }

@mcp_tool(
    name="find_session_path",
    description="查找两个会话之间的路径关系"
)
def find_session_path(
    source_session: str,
    target_session: str,
    max_hops: int = 10
) -> Dict[str, Any]:
    """
    查找会话路径 - 分析会话间的关系路径
    
    Args:
        source_session: 源会话
        target_session: 目标会话
        max_hops: 最大跳数限制
    """
    try:
        # 检查会话是否存在
        source_info = _session_registry.get_session_info(source_session)
        target_info = _session_registry.get_session_info(target_session)
        
        if not source_info:
            return {
                "success": False,
                "error": f"源会话不存在: {source_session}"
            }
        
        if not target_info:
            return {
                "success": False,
                "error": f"目标会话不存在: {target_session}"
            }
        
        # 查找路径
        path_result = _find_path_between_sessions(source_session, target_session, max_hops)
        
        if path_result["found"]:
            result = {
                "success": True,
                "path_found": True,
                "source_session": source_session,
                "target_session": target_session,
                "path": path_result["path"],
                "distance": len(path_result["path"]) - 1,
                "relationship_type": _determine_relationship_type(path_result["path"])
            }
        else:
            result = {
                "success": True,
                "path_found": False,
                "source_session": source_session,
                "target_session": target_session,
                "reason": path_result.get("reason", "No path found within max hops")
            }
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": f"查找会话路径失败: {str(e)}"
        }

# === 内部辅助函数 ===

def _would_create_cycle(parent: str, child: str) -> bool:
    """检查是否会创建循环依赖"""
    # 从child开始，向上查找所有祖先
    current = child
    visited = set()
    
    while current and current not in visited:
        visited.add(current)
        parent_of_current = _session_registry.get_parent_session(current)
        
        if parent_of_current == parent:
            return True  # 会形成循环
        
        current = parent_of_current
    
    return False

def _get_all_descendants(session_name: str) -> List[str]:
    """递归获取所有后代会话"""
    descendants = []
    direct_children = _session_registry.get_child_sessions(session_name)
    
    for child in direct_children:
        descendants.append(child)
        descendants.extend(_get_all_descendants(child))
    
    return descendants

def _build_hierarchical_data(parent: str, descendants: List[str], include_details: bool) -> List[Dict]:
    """构建层级化的会话数据"""
    data = []
    direct_children = _session_registry.get_child_sessions(parent)
    
    for child in direct_children:
        child_info = _session_registry.get_session_info(child)
        if child_info:
            child_data = {
                "name": child,
                "direct_child": True,
                "depth": 1
            }
            
            if include_details:
                child_data.update(child_info.to_dict())
            
            # 递归处理子会话的子会话
            grandchildren = _build_hierarchical_data(child, descendants, include_details)
            if grandchildren:
                child_data["children"] = grandchildren
                for grandchild in grandchildren:
                    grandchild["depth"] = grandchild.get("depth", 1) + 1
            
            data.append(child_data)
    
    return data

def _build_session_tree(session_name: str, max_depth: int, current_depth: int) -> Dict:
    """构建会话树结构"""
    session_info = _session_registry.get_session_info(session_name)
    
    tree_node = {
        "name": session_name,
        "depth": current_depth
    }
    
    if session_info:
        tree_node.update(session_info.to_dict())
    
    # 如果还没达到最大深度，继续构建子树
    if current_depth < max_depth:
        children = _session_registry.get_child_sessions(session_name)
        if children:
            tree_node["children"] = []
            for child in children:
                child_tree = _build_session_tree(child, max_depth, current_depth + 1)
                tree_node["children"].append(child_tree)
            
            tree_node["child_count"] = len(children)
        else:
            tree_node["child_count"] = 0
    
    return tree_node

def _find_root_sessions(session_names: List[str]) -> List[str]:
    """查找根会话（没有父会话的会话）"""
    roots = []
    for session_name in session_names:
        parent = _session_registry.get_parent_session(session_name)
        if not parent:
            roots.append(session_name)
    return roots

def _find_orphaned_sessions(session_names: List[str]) -> List[str]:
    """查找孤儿会话（既不是根也没有子会话的独立会话）"""
    orphans = []
    for session_name in session_names:
        parent = _session_registry.get_parent_session(session_name)
        children = _session_registry.get_child_sessions(session_name)
        
        if not parent and not children:
            orphans.append(session_name)
    
    return orphans

def _calculate_hierarchy_stats(hierarchy_data: Dict) -> Dict:
    """计算层级统计信息"""
    def count_nodes_and_depth(tree_data):
        if isinstance(tree_data, dict):
            if "children" in tree_data:
                total_nodes = 1
                max_depth = tree_data.get("depth", 0)
                
                for child in tree_data["children"]:
                    child_stats = count_nodes_and_depth(child)
                    total_nodes += child_stats["nodes"]
                    max_depth = max(max_depth, child_stats["max_depth"])
                
                return {"nodes": total_nodes, "max_depth": max_depth}
            else:
                return {"nodes": 1, "max_depth": tree_data.get("depth", 0)}
        return {"nodes": 0, "max_depth": 0}
    
    stats = {"total_nodes": 0, "max_depth": 0, "tree_count": 0}
    
    if hierarchy_data["hierarchy_type"] == "single_root":
        tree_stats = count_nodes_and_depth(hierarchy_data["tree"])
        stats.update(tree_stats)
        stats["tree_count"] = 1
    else:
        for root, tree in hierarchy_data.get("trees", {}.items():
            tree_stats = count_nodes_and_depth(tree)
            stats["total_nodes"] += tree_stats["nodes"]
            stats["max_depth"] = max(stats["max_depth"], tree_stats["max_depth"])
        
        stats["tree_count"] = len(hierarchy_data.get("trees", {})
    
    return stats

def _find_path_between_sessions(source: str, target: str, max_hops: int) -> Dict:
    """使用BFS查找两个会话之间的路径"""
    from collections import deque
    
    if source == target:
        return {"found": True, "path": [source]}
    
    # BFS搜索
    queue = deque([(source, [source])])
    visited = {source}
    
    while queue and len(queue) < max_hops * 10:  # 避免无限循环
        current, path = queue.popleft()
        
        if len(path) > max_hops:
            continue
        
        # 获取当前会话的相关会话（父会话和子会话）
        related_sessions = set()
        
        # 添加父会话
        parent = _session_registry.get_parent_session(current)
        if parent:
            related_sessions.add(parent)
        
        # 添加子会话
        children = _session_registry.get_child_sessions(current)
        related_sessions.update(children)
        
        for related in related_sessions:
            if related == target:
                return {"found": True, "path": path + [related]}
            
            if related not in visited:
                visited.add(related)
                queue.append((related, path + [related]))
    
    return {"found": False, "reason": f"No path found within {max_hops} hops"}

def _determine_relationship_type(path: List[str]) -> Dict[str, Any]:
    """根据路径确定关系类型"""
    if len(path) == 2:
        # 直接关系
        source, target = path
        parent = _session_registry.get_parent_session(target)
        if parent == source:
            return "parent-child"
        
        children = _session_registry.get_child_sessions(source)
        if target in children:
            return "child-parent"
        
        # 检查是否为兄弟关系
        source_parent = _session_registry.get_parent_session(source)
        target_parent = _session_registry.get_parent_session(target)
        if source_parent and source_parent == target_parent:
            return "sibling"
    
    elif len(path) > 2:
        return f"indirect-{len(path)-1}-hops"
    
    return "unknown"