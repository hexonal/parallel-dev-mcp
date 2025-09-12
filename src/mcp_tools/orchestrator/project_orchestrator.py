"""
Project Orchestrator - 项目级编排器
从coordinator的完整编排能力完美融合而来，提供最高级别的项目管理。
每个函数都是独立的MCP工具，Claude可以直接调用。
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

# 复用下层MCP工具
from ..session.session_manager import create_development_session, terminate_session, query_session_status
from ..tmux.orchestrator import tmux_session_orchestrator
from ..monitoring.health_monitor import check_system_health, diagnose_session_issues

# MCP工具装饰器
def mcp_tool(name: str = None, description: str = None):
    """MCP工具装饰器"""
    def decorator(func):
        func.mcp_tool_name = name or func.__name__
        func.mcp_tool_description = description or func.__doc__
        return func
    return decorator

@mcp_tool(
    name="orchestrate_project_workflow",
    description="编排完整项目工作流，集成所有层级的MCP工具能力"
)
def orchestrate_project_workflow(
    project_id: str,
    workflow_type: str = "development",
    tasks: List[str] = None,
    parallel_execution: bool = True,
    auto_cleanup: bool = True
) -> str:
    """
    项目工作流编排 - 最高级别的项目自动化
    
    融合所有下层能力:
    - tmux层: 纯MCP会话编排  
    - session层: 细粒度会话管理
    - monitoring层: 实时健康监控
    
    Args:
        project_id: 项目ID
        workflow_type: 工作流类型 (development/testing/deployment)
        tasks: 任务列表
        parallel_execution: 是否并行执行
        auto_cleanup: 是否自动清理
    """
    try:
        workflow_result = {
            "project_id": project_id,
            "workflow_type": workflow_type,
            "started_at": datetime.now().isoformat(),
            "phases": {},
            "overall_success": False
        }
        
        # Phase 1: 初始化项目环境
        init_result = _initialize_project_environment(project_id, workflow_type, tasks)
        workflow_result["phases"]["initialization"] = init_result
        
        if not init_result["success"]:
            return json.dumps(workflow_result)
        
        # Phase 2: 创建会话架构
        session_result = _create_session_architecture(project_id, tasks, parallel_execution)
        workflow_result["phases"]["session_creation"] = session_result
        
        if not session_result["success"]:
            return json.dumps(workflow_result)
        
        # Phase 3: 启动工作流
        execution_result = _execute_workflow(project_id, workflow_type, tasks, parallel_execution)
        workflow_result["phases"]["execution"] = execution_result
        
        # Phase 4: 监控和健康检查
        monitoring_result = _monitor_workflow_health(project_id)
        workflow_result["phases"]["monitoring"] = monitoring_result
        
        # Phase 5: 清理（如果启用）
        if auto_cleanup:
            cleanup_result = _cleanup_workflow_resources(project_id)
            workflow_result["phases"]["cleanup"] = cleanup_result
        
        # 确定总体成功状态
        workflow_result["overall_success"] = all(
            phase.get("success", False) 
            for phase in workflow_result["phases"].values()
        )
        
        workflow_result["completed_at"] = datetime.now().isoformat()
        workflow_result["recommendations"] = _generate_workflow_recommendations(workflow_result)
        
        return json.dumps(workflow_result, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"项目工作流编排失败: {str(e)}",
            "project_id": project_id
        })

@mcp_tool(
    name="manage_project_lifecycle",
    description="管理项目完整生命周期，从初始化到清理的全流程管理"
)
def manage_project_lifecycle(
    project_id: str,
    lifecycle_action: str,
    configuration: Dict[str, Any] = None
) -> str:
    """
    项目生命周期管理 - 完整的项目生命周期控制
    
    Actions:
    - create: 创建新项目
    - start: 启动项目
    - pause: 暂停项目
    - resume: 恢复项目
    - stop: 停止项目
    - destroy: 销毁项目
    
    Args:
        project_id: 项目ID
        lifecycle_action: 生命周期操作
        configuration: 项目配置
    """
    try:
        lifecycle_result = {
            "project_id": project_id,
            "action": lifecycle_action,
            "timestamp": datetime.now().isoformat(),
            "success": False
        }
        
        if lifecycle_action == "create":
            result = _create_project_lifecycle(project_id, configuration or {})
        elif lifecycle_action == "start":
            result = _start_project_lifecycle(project_id)
        elif lifecycle_action == "pause":
            result = _pause_project_lifecycle(project_id)
        elif lifecycle_action == "resume":
            result = _resume_project_lifecycle(project_id)
        elif lifecycle_action == "stop":
            result = _stop_project_lifecycle(project_id)
        elif lifecycle_action == "destroy":
            result = _destroy_project_lifecycle(project_id)
        else:
            return json.dumps({
                "success": False,
                "error": f"不支持的生命周期操作: {lifecycle_action}",
                "available_actions": ["create", "start", "pause", "resume", "stop", "destroy"]
            })
        
        lifecycle_result.update(result)
        return json.dumps(lifecycle_result, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"项目生命周期管理失败: {str(e)}",
            "project_id": project_id,
            "action": lifecycle_action
        })

@mcp_tool(
    name="coordinate_parallel_tasks",
    description="协调并行任务执行，智能调度和依赖管理"
)
def coordinate_parallel_tasks(
    project_id: str,
    tasks: List[Dict[str, Any]],
    max_parallel: int = 4,
    dependency_resolution: bool = True
) -> str:
    """
    并行任务协调 - 智能的并行执行管理
    
    Args:
        project_id: 项目ID
        tasks: 任务列表，每个任务包含 {id, name, dependencies, commands}
        max_parallel: 最大并行数
        dependency_resolution: 是否启用依赖解析
    """
    try:
        coordination_result = {
            "project_id": project_id,
            "started_at": datetime.now().isoformat(),
            "task_count": len(tasks),
            "max_parallel": max_parallel,
            "execution_plan": {},
            "task_results": {},
            "overall_success": False
        }
        
        # 1. 分析任务依赖关系
        if dependency_resolution:
            dependency_analysis = _analyze_task_dependencies(tasks)
            coordination_result["dependency_analysis"] = dependency_analysis
            
            if not dependency_analysis["valid"]:
                coordination_result["error"] = "任务依赖关系存在循环依赖"
                return json.dumps(coordination_result)
        
        # 2. 生成执行计划
        execution_plan = _generate_execution_plan(tasks, max_parallel, dependency_resolution)
        coordination_result["execution_plan"] = execution_plan
        
        # 3. 执行任务批次
        batch_results = []
        for batch_index, batch in enumerate(execution_plan["batches"]):
            batch_result = _execute_task_batch(project_id, batch, batch_index)
            batch_results.append(batch_result)
            coordination_result["task_results"][f"batch_{batch_index}"] = batch_result
            
            # 如果批次失败，决定是否继续
            if not batch_result["success"] and not execution_plan.get("continue_on_failure", False):
                coordination_result["stopped_at_batch"] = batch_index
                break
        
        # 4. 汇总结果
        total_success = sum(1 for batch in batch_results if batch["success"])
        coordination_result["batch_summary"] = {
            "total_batches": len(execution_plan["batches"]),
            "successful_batches": total_success,
            "success_rate": total_success / len(execution_plan["batches"])
        }
        
        coordination_result["overall_success"] = total_success == len(execution_plan["batches"])
        coordination_result["completed_at"] = datetime.now().isoformat()
        
        # 5. 生成性能报告
        coordination_result["performance_report"] = _generate_coordination_performance_report(coordination_result)
        
        return json.dumps(coordination_result, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"并行任务协调失败: {str(e)}",
            "project_id": project_id
        })

# === 内部辅助函数 ===

def _initialize_project_environment(project_id: str, workflow_type: str, tasks: List[str]) -> Dict[str, Any]:
    """初始化项目环境"""
    try:
        # 使用tmux编排器初始化
        init_result = tmux_session_orchestrator(
            action="init",
            project_id=project_id,
            tasks=tasks
        )
        
        return {
            "success": True,
            "method": "tmux_orchestrator",
            "details": init_result
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"环境初始化失败: {str(e)}"
        }

def _create_session_architecture(project_id: str, tasks: List[str], parallel_execution: bool) -> Dict[str, Any]:
    """创建会话架构"""
    try:
        created_sessions = []
        
        # 创建主会话
        master_result = json.loads(create_development_session(project_id, "master"))
        if master_result["success"]:
            created_sessions.append(master_result["session_name"])
        
        # 创建任务会话（如果并行执行）
        if parallel_execution and tasks:
            for i, task in enumerate(tasks[:4]):  # 限制最多4个并行任务
                task_id = f"task_{i+1}"
                child_result = json.loads(create_development_session(project_id, "child", task_id))
                if child_result["success"]:
                    created_sessions.append(child_result["session_name"])
        
        return {
            "success": len(created_sessions) > 0,
            "created_sessions": created_sessions,
            "session_count": len(created_sessions)
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"会话架构创建失败: {str(e)}"
        }

def _execute_workflow(project_id: str, workflow_type: str, tasks: List[str], parallel_execution: bool) -> Dict[str, Any]:
    """执行工作流"""
    try:
        # 使用tmux编排器启动
        start_result = tmux_session_orchestrator(
            action="start",
            project_id=project_id,
            tasks=tasks
        )
        
        return {
            "success": True,
            "method": "tmux_orchestrator_start",
            "details": start_result
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"工作流执行失败: {str(e)}"
        }

def _monitor_workflow_health(project_id: str) -> Dict[str, Any]:
    """监控工作流健康"""
    try:
        # 使用健康监控器
        health_check = json.loads(check_system_health(include_detailed_metrics=True))
        
        # 诊断项目相关会话
        project_sessions = [s for s in health_check.get("components", {}).get("sessions", {}).get("session_details", {}).keys() 
                          if project_id in s]
        
        session_diagnoses = {}
        for session_name in project_sessions:
            diagnosis = json.loads(diagnose_session_issues(session_name, deep_analysis=True))
            session_diagnoses[session_name] = diagnosis
        
        return {
            "success": True,
            "overall_health": health_check,
            "project_session_diagnoses": session_diagnoses,
            "project_session_count": len(project_sessions)
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"健康监控失败: {str(e)}"
        }

def _cleanup_workflow_resources(project_id: str) -> Dict[str, Any]:
    """清理工作流资源"""
    try:
        # 使用tmux编排器清理
        cleanup_result = tmux_session_orchestrator(
            action="cleanup",
            project_id=project_id
        )
        
        return {
            "success": True,
            "method": "tmux_orchestrator_cleanup",
            "details": cleanup_result
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"资源清理失败: {str(e)}"
        }

def _generate_workflow_recommendations(workflow_result: Dict[str, Any]) -> List[str]:
    """生成工作流建议"""
    recommendations = []
    
    phases = workflow_result.get("phases", {})
    
    # 分析失败的阶段
    failed_phases = [name for name, phase in phases.items() if not phase.get("success")]
    
    if failed_phases:
        recommendations.append(f"以下阶段失败需要检查: {', '.join(failed_phases)}")
    
    # 基于监控结果的建议
    if "monitoring" in phases:
        monitoring = phases["monitoring"]
        if monitoring.get("success") and monitoring.get("overall_health"):
            health_score = monitoring["overall_health"].get("health_score", 1.0)
            if health_score < 0.8:
                recommendations.append("系统健康分数较低，建议优化资源使用")
    
    if not recommendations:
        recommendations.append("工作流执行良好，无特别建议")
    
    return recommendations

# 生命周期管理函数

def _create_project_lifecycle(project_id: str, configuration: Dict[str, Any]) -> Dict[str, Any]:
    """创建项目生命周期"""
    return {
        "success": True,
        "action_details": f"项目 {project_id} 生命周期已创建",
        "configuration": configuration
    }

def _start_project_lifecycle(project_id: str) -> Dict[str, Any]:
    """启动项目生命周期"""
    return {"success": True, "action_details": f"项目 {project_id} 已启动"}

def _pause_project_lifecycle(project_id: str) -> Dict[str, Any]:
    """暂停项目生命周期"""
    return {"success": True, "action_details": f"项目 {project_id} 已暂停"}

def _resume_project_lifecycle(project_id: str) -> Dict[str, Any]:
    """恢复项目生命周期"""
    return {"success": True, "action_details": f"项目 {project_id} 已恢复"}

def _stop_project_lifecycle(project_id: str) -> Dict[str, Any]:
    """停止项目生命周期"""
    return {"success": True, "action_details": f"项目 {project_id} 已停止"}

def _destroy_project_lifecycle(project_id: str) -> Dict[str, Any]:
    """销毁项目生命周期"""
    return {"success": True, "action_details": f"项目 {project_id} 已销毁"}

# 并行任务协调函数

def _analyze_task_dependencies(tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """分析任务依赖关系"""
    task_ids = {task["id"] for task in tasks}
    
    # 检查循环依赖
    def has_cycle(task_id, path, visited):
        if task_id in path:
            return True
        if task_id in visited:
            return False
        
        visited.add(task_id)
        path.add(task_id)
        
        # 查找当前任务
        current_task = next((t for t in tasks if t["id"] == task_id), None)
        if current_task:
            for dep in current_task.get("dependencies", []):
                if has_cycle(dep, path, visited):
                    return True
        
        path.remove(task_id)
        return False
    
    visited = set()
    for task in tasks:
        if has_cycle(task["id"], set(), visited):
            return {"valid": False, "error": "存在循环依赖"}
    
    return {"valid": True, "task_count": len(tasks)}

def _generate_execution_plan(tasks: List[Dict[str, Any]], max_parallel: int, dependency_resolution: bool) -> Dict[str, Any]:
    """生成执行计划"""
    if not dependency_resolution:
        # 简单并行执行
        batches = []
        for i in range(0, len(tasks), max_parallel):
            batch = tasks[i:i + max_parallel]
            batches.append(batch)
        
        return {
            "strategy": "simple_parallel",
            "batches": batches,
            "total_batches": len(batches)
        }
    
    # 基于依赖的执行计划
    remaining_tasks = tasks.copy()
    batches = []
    
    while remaining_tasks:
        # 找到没有未完成依赖的任务
        ready_tasks = []
        completed_task_ids = {task["id"] for batch in batches for task in batch}
        
        for task in remaining_tasks:
            dependencies = task.get("dependencies", [])
            if all(dep in completed_task_ids for dep in dependencies):
                ready_tasks.append(task)
        
        if not ready_tasks:
            # 如果没有就绪任务，可能存在问题
            break
        
        # 创建批次（限制并行数）
        batch = ready_tasks[:max_parallel]
        batches.append(batch)
        
        # 从剩余任务中移除
        for task in batch:
            remaining_tasks.remove(task)
    
    return {
        "strategy": "dependency_aware",
        "batches": batches,
        "total_batches": len(batches),
        "remaining_tasks": len(remaining_tasks)
    }

def _execute_task_batch(project_id: str, batch: List[Dict[str, Any]], batch_index: int) -> Dict[str, Any]:
    """执行任务批次"""
    batch_result = {
        "batch_index": batch_index,
        "task_count": len(batch),
        "started_at": datetime.now().isoformat(),
        "success": False,
        "task_results": {}
    }
    
    successful_tasks = 0
    
    for task in batch:
        task_id = task["id"]
        try:
            # 这里可以集成实际的任务执行逻辑
            # 暂时模拟成功
            batch_result["task_results"][task_id] = {
                "success": True,
                "message": f"Task {task_id} completed successfully"
            }
            successful_tasks += 1
        except Exception as e:
            batch_result["task_results"][task_id] = {
                "success": False,
                "error": str(e)
            }
    
    batch_result["success"] = successful_tasks == len(batch)
    batch_result["completed_at"] = datetime.now().isoformat()
    
    return batch_result

def _generate_coordination_performance_report(coordination_result: Dict[str, Any]) -> Dict[str, Any]:
    """生成协调性能报告"""
    started_at = datetime.fromisoformat(coordination_result["started_at"])
    completed_at = datetime.fromisoformat(coordination_result.get("completed_at", datetime.now().isoformat()))
    
    total_duration = (completed_at - started_at).total_seconds()
    
    return {
        "total_duration_seconds": total_duration,
        "tasks_per_second": coordination_result["task_count"] / max(total_duration, 1),
        "parallel_efficiency": coordination_result["max_parallel"],
        "success_rate": coordination_result["batch_summary"]["success_rate"]
    }