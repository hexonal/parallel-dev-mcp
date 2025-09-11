#!/usr/bin/env python3
"""
Tmux会话编排器测试和演示脚本
完整验证纯MCP方案的功能
"""

import json
import time
import sys
from pathlib import Path

# 导入我们的MCP工具
from tmux_session_orchestrator import tmux_session_orchestrator

def print_separator(title: str):
    """打印分隔符"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def print_result(result: dict, action: str):
    """打印结果"""
    print(f"\n📊 {action} 结果:")
    if "error" in result:
        print(f"❌ 错误: {result['error']}")
    else:
        print("✅ 成功!")
        
    print(json.dumps(result, indent=2, ensure_ascii=False))

def test_complete_workflow():
    """测试完整的工作流程"""
    
    project_id = "TMUX_DEMO_TEST"
    tasks = ["AUTH", "PAYMENT", "UI"]
    
    print_separator("🚀 Tmux会话编排器完整测试")
    
    print(f"""
🎯 测试场景:
   项目ID: {project_id}
   任务列表: {tasks}
   
📋 测试步骤:
   1. 初始化项目配置
   2. 启动所有会话 
   3. 检查项目状态
   4. 测试会话间通信
   5. 获取连接说明
   6. 列出所有会话
   7. 清理项目环境
    """)
    
    input("按Enter开始测试...")
    
    # 1. 初始化项目
    print_separator("1️⃣ 初始化项目配置")
    init_result = tmux_session_orchestrator("init", project_id, tasks)
    print_result(init_result, "项目初始化")
    
    if "error" in init_result:
        print("❌ 初始化失败，终止测试")
        return False
    
    # 2. 启动会话
    print_separator("2️⃣ 启动所有会话")
    start_result = tmux_session_orchestrator("start", project_id, tasks)
    print_result(start_result, "会话启动")
    
    if "error" in start_result:
        print("❌ 会话启动失败")
        return False
    
    # 等待会话稳定
    print("\n⏳ 等待会话稳定...")
    time.sleep(3)
    
    # 3. 检查项目状态
    print_separator("3️⃣ 检查项目状态") 
    status_result = tmux_session_orchestrator("status", project_id)
    print_result(status_result, "状态检查")
    
    # 4. 测试会话间通信
    print_separator("4️⃣ 测试会话间通信")
    
    # 发送消息从主会话到AUTH子会话
    message_result = tmux_session_orchestrator(
        "message", project_id,
        from_session=f"master_project_{project_id}",
        to_session=f"child_{project_id}_task_AUTH", 
        message="请报告AUTH任务的开发进度"
    )
    print_result(message_result, "消息发送 (Master -> AUTH)")
    
    # 发送消息从AUTH子会话到主会话
    message_result2 = tmux_session_orchestrator(
        "message", project_id,
        from_session=f"child_{project_id}_task_AUTH",
        to_session=f"master_project_{project_id}",
        message="AUTH任务进度: 已完成用户模型设计，正在实现登录接口"
    )
    print_result(message_result2, "消息发送 (AUTH -> Master)")
    
    # 5. 获取连接说明
    print_separator("5️⃣ 获取会话连接说明")
    
    # 主会话连接说明
    attach_master = tmux_session_orchestrator("attach", project_id, session_type="master")
    print_result(attach_master, "主会话连接说明")
    
    # 子会话列表
    attach_list = tmux_session_orchestrator("attach", project_id, session_type="list") 
    print_result(attach_list, "子会话列表")
    
    # 6. 列出所有会话
    print_separator("6️⃣ 列出所有会话")
    list_result = tmux_session_orchestrator("list", project_id)
    print_result(list_result, "会话列表")
    
    # 7. 用户交互演示
    print_separator("7️⃣ 用户交互演示")
    
    if status_result.get("all_healthy", False):
        print("✅ 所有会话运行正常!")
        print("\n🎯 您现在可以:")
        
        if "attach_commands" in status_result:
            print("\n📱 连接到会话:")
            for name, command in status_result["attach_commands"].items():
                print(f"   {name}: {command}")
        
        print(f"\n📁 项目文件位置:")
        print(f"   配置目录: ./projects/{project_id}/config/")
        print(f"   消息目录: ./projects/{project_id}/messages/")
        
        choice = input("\n是否现在清理测试环境? (y/N): ").lower()
        if choice == 'y':
            cleanup_now = True
        else:
            cleanup_now = False
            print("💡 稍后可以手动清理:")
            print(f"   tmux_session_orchestrator('cleanup', '{project_id}')")
    else:
        print("⚠️ 部分会话可能有问题，建议检查")
        cleanup_now = True
    
    # 8. 清理环境
    if cleanup_now:
        print_separator("8️⃣ 清理项目环境")
        cleanup_result = tmux_session_orchestrator("cleanup", project_id)
        print_result(cleanup_result, "环境清理")
    
    return True

def test_individual_functions():
    """测试单个功能"""
    
    print_separator("🧪 单功能测试")
    
    project_id = "UNIT_TEST"
    
    # 测试项目初始化
    print("\n1. 测试项目初始化...")
    init_result = tmux_session_orchestrator("init", project_id, ["TEST_TASK"])
    print(f"   结果: {'✅ 成功' if 'error' not in init_result else '❌ 失败'}")
    
    # 测试会话列表
    print("\n2. 测试会话列表功能...")
    list_result = tmux_session_orchestrator("list", project_id)
    print(f"   结果: {'✅ 成功' if 'error' not in list_result else '❌ 失败'}")
    
    # 测试错误处理
    print("\n3. 测试错误处理...")
    error_result = tmux_session_orchestrator("invalid_action", project_id)
    print(f"   结果: {'✅ 正确处理错误' if 'error' in error_result else '❌ 错误处理失败'}")
    
    # 清理
    cleanup_result = tmux_session_orchestrator("cleanup", project_id)
    print(f"   清理: {'✅ 成功' if 'error' not in cleanup_result else '❌ 失败'}")

def interactive_demo():
    """交互式演示"""
    
    print_separator("🎮 交互式演示模式")
    
    print("""
欢迎使用Tmux会话编排器交互式演示!

可用命令:
  1. init <project_id> <task1,task2...>  - 初始化项目
  2. start <project_id> <task1,task2...> - 启动会话  
  3. status <project_id>                 - 查看状态
  4. message <project_id>                - 发送消息 (交互式)
  5. attach <project_id>                 - 获取连接说明
  6. list <project_id>                   - 列出会话
  7. cleanup <project_id>                - 清理项目
  8. help                                - 显示帮助
  9. exit                                - 退出
  
示例:
  init DEMO_PROJECT AUTH,PAYMENT,UI
  start DEMO_PROJECT AUTH,PAYMENT,UI
  status DEMO_PROJECT
    """)
    
    while True:
        try:
            command = input("\n🎯 请输入命令: ").strip()
            
            if not command:
                continue
                
            if command == "exit":
                print("👋 再见!")
                break
                
            if command == "help":
                print("📖 命令格式请参考上面的说明")
                continue
            
            parts = command.split()
            if len(parts) < 2:
                print("❌ 命令格式错误")
                continue
            
            action = parts[0]
            project_id = parts[1]
            
            if action == "init" or action == "start":
                if len(parts) < 3:
                    print("❌ 需要指定任务列表")
                    continue
                tasks = parts[2].split(',')
                result = tmux_session_orchestrator(action, project_id, tasks)
            
            elif action == "message":
                print(f"发送消息 - 项目: {project_id}")
                from_session = input("  从会话: ").strip()
                to_session = input("  到会话: ").strip() 
                message = input("  消息内容: ").strip()
                
                if all([from_session, to_session, message]):
                    result = tmux_session_orchestrator(
                        "message", project_id,
                        from_session=from_session,
                        to_session=to_session,
                        message=message
                    )
                else:
                    print("❌ 消息信息不完整")
                    continue
            
            elif action in ["status", "list", "cleanup"]:
                result = tmux_session_orchestrator(action, project_id)
            
            elif action == "attach":
                session_type = input("  会话类型 (master/list): ").strip() or "master"
                result = tmux_session_orchestrator("attach", project_id, session_type=session_type)
            
            else:
                print(f"❌ 未知命令: {action}")
                continue
            
            # 显示结果
            print(f"\n📊 执行结果:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
        except KeyboardInterrupt:
            print("\n\n👋 用户中断，退出演示")
            break
        except Exception as e:
            print(f"❌ 执行错误: {str(e)}")

def main():
    """主函数"""
    
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        
        if mode == "full":
            test_complete_workflow()
        elif mode == "unit":
            test_individual_functions()
        elif mode == "demo":
            interactive_demo()
        else:
            print(f"未知模式: {mode}")
            print("可用模式: full, unit, demo")
    else:
        print("🚀 Tmux会话编排器测试脚本")
        print("\n使用方法:")
        print("  python test_tmux_orchestrator.py full   # 完整工作流测试")
        print("  python test_tmux_orchestrator.py unit   # 单功能测试") 
        print("  python test_tmux_orchestrator.py demo   # 交互式演示")
        print("\n选择测试模式:")
        
        choice = input("输入模式 (full/unit/demo) 或直接按Enter使用完整测试: ").strip()
        
        if choice == "unit":
            test_individual_functions()
        elif choice == "demo":
            interactive_demo()
        else:
            test_complete_workflow()

if __name__ == "__main__":
    main()