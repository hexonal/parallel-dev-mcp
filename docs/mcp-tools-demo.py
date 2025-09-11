#!/usr/bin/env python3
"""
MCP Session Coordinator 工具调用演示
演示如何在Claude Code中使用MCP工具进行会话管理
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.mcp_server.session_coordinator import SessionCoordinatorMCP
import json

def demo_mcp_tools():
    """演示所有MCP工具的使用方法"""
    
    print("="*60)
    print("MCP Session Coordinator 工具调用演示")
    print("="*60)
    
    # 创建MCP协调器实例
    coordinator = SessionCoordinatorMCP("demo-session")
    
    # 项目配置
    project_id = "ECOMMERCE_DEMO"
    master_session = f"master_project_{project_id}"
    
    # 任务配置
    tasks = [
        {"id": "AUTH", "name": "用户认证系统"},
        {"id": "PAYMENT", "name": "支付处理系统"},
        {"id": "CART", "name": "购物车功能"}
    ]
    
    print(f"\n🚀 项目启动: {project_id}")
    print(f"主会话: {master_session}")
    
    # ===== 第1步：注册会话关系 =====
    print(f"\n📋 第1步：注册会话关系")
    child_sessions = []
    
    for task in tasks:
        child_session = f"child_{project_id}_task_{task['id']}"
        child_sessions.append(child_session)
        
        print(f"\n  ➤ 注册任务: {task['name']} ({task['id']})")
        result = coordinator.register_session_relationship(
            parent_session=master_session,
            child_session=child_session,
            task_id=task['id'],
            project_id=project_id
        )
        print(f"    结果: {result}")
    
    # ===== 第2步：子会话状态上报 =====
    print(f"\n📊 第2步：子会话状态上报")
    
    # 模拟开发过程中的状态变化
    development_phases = [
        {"status": "STARTED", "progress": 0, "phase": "任务启动"},
        {"status": "WORKING", "progress": 25, "phase": "需求分析"},
        {"status": "WORKING", "progress": 50, "phase": "核心开发"},
        {"status": "WORKING", "progress": 75, "phase": "测试编写"},
        {"status": "COMPLETED", "progress": 100, "phase": "任务完成"}
    ]
    
    for i, child_session in enumerate(child_sessions):
        task_name = tasks[i]['name']
        print(f"\n  ➤ {task_name} 开发进度:")
        
        for phase in development_phases[:3]:  # 只演示前3个阶段
            result = coordinator.report_session_status(
                session_name=child_session,
                status=phase['status'],
                progress=phase['progress'],
                details=f"{task_name} - {phase['phase']}"
            )
            print(f"    {phase['phase']}: {phase['progress']}% - {phase['status']}")
    
    # ===== 第3步：主会话监控子会话 =====
    print(f"\n👀 第3步：主会话监控子会话")
    
    result = coordinator.get_child_sessions(master_session)
    child_data = json.loads(result)
    
    print(f"  📈 子会话总数: {child_data['child_count']}")
    print(f"  📋 子会话详情:")
    
    for child in child_data['children']:
        print(f"    • {child['session_name']}: {child['status']} ({child['progress']}%)")
        print(f"      任务: {child['task_id']}")
    
    # ===== 第4步：主会话发送指令 =====
    print(f"\n📤 第4步：主会话发送指令")
    
    instructions = [
        "请报告当前开发进度和遇到的问题",
        "准备进行代码review，请确保代码已提交",
        "开始准备与其他模块的集成测试"
    ]
    
    for i, child_session in enumerate(child_sessions):
        instruction = instructions[i % len(instructions)]
        
        print(f"\n  ➤ 向 {tasks[i]['name']} 发送指令:")
        print(f"    指令内容: {instruction}")
        
        result = coordinator.send_message_to_session(
            from_session=master_session,
            to_session=child_session,
            message=instruction,
            message_type="INSTRUCTION"
        )
        print(f"    发送结果: {result}")
    
    # ===== 第5步：子会话接收消息 =====
    print(f"\n📥 第5步：子会话接收消息")
    
    for i, child_session in enumerate(child_sessions):
        print(f"\n  ➤ {tasks[i]['name']} 检查消息:")
        
        result = coordinator.get_session_messages(child_session)
        messages_data = json.loads(result)
        
        print(f"    未读消息数: {messages_data['unread_count']}")
        
        if messages_data['messages']:
            for msg in messages_data['messages']:
                print(f"    📩 消息: {msg['content']}")
                print(f"       发送者: {msg['from_session']}")
    
    # ===== 第6步：系统状态总览 =====
    print(f"\n🔍 第6步：系统状态总览")
    
    result = coordinator.query_session_status()
    status_data = json.loads(result)
    
    print(f"  🖥️  系统状态:")
    print(f"    活跃会话总数: {status_data['total_sessions']}")
    
    # ===== 第7步：模拟任务完成 =====
    print(f"\n✅ 第7步：模拟任务完成")
    
    for i, child_session in enumerate(child_sessions):
        task_name = tasks[i]['name']
        
        print(f"\n  ➤ {task_name} 任务完成:")
        
        result = coordinator.report_session_status(
            session_name=child_session,
            status="COMPLETED",
            progress=100,
            details=f"{task_name} - 开发完成，代码已提交，测试通过"
        )
        print(f"    完成状态: {result}")
    
    # 最终状态检查
    print(f"\n🎯 最终状态检查:")
    result = coordinator.get_child_sessions(master_session)
    final_data = json.loads(result)
    
    completed_count = sum(1 for child in final_data['children'] if child['status'] == 'COMPLETED')
    total_count = final_data['child_count']
    
    print(f"  📊 项目进度: {completed_count}/{total_count} 任务已完成")
    
    if completed_count == total_count:
        print(f"  🎉 {project_id} 项目开发完成！准备合并和部署。")
    else:
        print(f"  ⏳ 还有 {total_count - completed_count} 个任务进行中...")
    
    print("\n" + "="*60)
    print("✅ MCP工具演示完成！")
    print("="*60)

def demo_error_handling():
    """演示错误处理机制"""
    
    print("\n" + "="*60)
    print("错误处理演示")
    print("="*60)
    
    coordinator = SessionCoordinatorMCP("error-demo")
    
    # 1. 无效会话名称
    print("\n🚫 测试1: 无效会话名称")
    result = coordinator.register_session_relationship(
        parent_session="invalid_name",
        child_session="also_invalid",
        task_id="TEST",
        project_id="TEST"
    )
    print(f"  结果: {result}")
    
    # 2. 无效状态值
    print("\n🚫 测试2: 无效状态值")
    result = coordinator.report_session_status(
        session_name="child_TEST_task_DEMO",
        status="INVALID_STATUS",
        progress=50
    )
    print(f"  结果: {result}")
    
    # 3. 查询不存在的会话
    print("\n🚫 测试3: 查询不存在的会话")
    result = coordinator.get_session_messages("nonexistent_session")
    print(f"  结果: {result}")
    
    print("\n✅ 错误处理演示完成")

if __name__ == "__main__":
    try:
        demo_mcp_tools()
        demo_error_handling()
        
        print(f"\n💡 提示:")
        print(f"  1. 在实际使用中，这些工具会通过Claude Code的MCP集成自动调用")
        print(f"  2. 可以通过hooks配置实现自动化的状态上报和消息处理")
        print(f"  3. 详细使用方法请参考: docs/usage-guide.md")
        
    except Exception as e:
        print(f"\n❌ 演示过程中出现错误: {e}")
        sys.exit(1)