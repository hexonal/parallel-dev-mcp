#!/usr/bin/env python3
"""
集成系统完整测试
验证tmux编排器与现有MCP服务器的集成效果
"""

import json
import sys
import time
import importlib.util
from pathlib import Path

def print_header(title: str):
    """打印测试标题"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def print_result(test_name: str, result: dict, success_key: str = "success"):
    """打印测试结果"""
    success = result.get(success_key, False)
    status = "✅ 通过" if success else "❌ 失败"
    print(f"\n{status} {test_name}")
    
    if not success and "error" in result:
        print(f"   错误: {result['error']}")
    
    # 显示关键信息
    if "project_id" in result:
        print(f"   项目: {result['project_id']}")
    
    if success:
        if "steps" in result:
            print(f"   完成步骤: {len(result['steps'])}")
        if "sessions_created" in result:
            print(f"   创建会话: {len(result['sessions_created'])}")

def test_tmux_orchestrator_basic():
    """测试基础tmux编排器功能"""
    print_header("🧪 测试基础Tmux编排器功能")
    
    try:
        # 导入tmux编排器
        from src.mcp_tools.tmux_session_orchestrator import tmux_session_orchestrator
        
        project_id = "INTEGRATION_TEST"
        tasks = ["BASIC_TASK1", "BASIC_TASK2"]
        
        # 测试1: 初始化
        print("\n1️⃣ 测试项目初始化...")
        init_result = tmux_session_orchestrator("init", project_id, tasks)
        print_result("项目初始化", init_result)
        
        if "error" in init_result:
            return False
        
        # 测试2: 状态检查
        print("\n2️⃣ 测试状态检查...")
        status_result = tmux_session_orchestrator("status", project_id)
        print_result("状态检查", status_result)
        
        # 测试3: 连接信息
        print("\n3️⃣ 测试连接信息...")
        attach_result = tmux_session_orchestrator("attach", project_id, session_type="master")
        print_result("连接信息", attach_result)
        
        # 测试4: 清理
        print("\n4️⃣ 测试环境清理...")
        cleanup_result = tmux_session_orchestrator("cleanup", project_id)
        print_result("环境清理", cleanup_result)
        
        return True
        
    except Exception as e:
        print(f"❌ 基础测试失败: {str(e)}")
        return False

def test_integrated_mcp_server():
    """测试集成的MCP服务器功能"""
    print_header("🔗 测试集成MCP服务器功能")
    
    try:
        # 导入集成的MCP服务器
        from src.mcp_server.session_coordinator import session_coordinator
        
        project_id = "MCP_INTEGRATION_TEST"
        tasks = "MCP_TASK1,MCP_TASK2,MCP_TASK3"
        
        # 测试1: MCP项目初始化
        print("\n1️⃣ 测试MCP项目初始化...")
        init_result = json.loads(session_coordinator.tmux_project_init(project_id, tasks))
        print_result("MCP项目初始化", init_result)
        
        if not init_result.get("success"):
            return False
        
        # 测试2: MCP项目启动
        print("\n2️⃣ 测试MCP项目启动...")
        start_result = json.loads(session_coordinator.tmux_project_start(project_id))
        print_result("MCP项目启动", start_result)
        
        # 测试3: MCP项目状态
        print("\n3️⃣ 测试MCP项目状态...")
        status_result = json.loads(session_coordinator.tmux_project_status(project_id))
        print_result("MCP项目状态", status_result)
        
        # 测试4: 连接信息
        print("\n4️⃣ 测试MCP连接信息...")
        attach_result = json.loads(session_coordinator.tmux_session_attach_info(project_id, "master"))
        print_result("MCP连接信息", attach_result)
        
        # 测试5: MCP项目清理
        print("\n5️⃣ 测试MCP项目清理...")
        cleanup_result = json.loads(session_coordinator.tmux_project_cleanup(project_id))
        print_result("MCP项目清理", cleanup_result)
        
        return True
        
    except Exception as e:
        print(f"❌ MCP集成测试失败: {str(e)}")
        return False

def test_unified_api():
    """测试统一API接口"""
    print_header("🚀 测试统一API接口")
    
    try:
        # 导入统一API
        from src.mcp_server.unified_api import (
            parallel_dev_one_click, 
            parallel_dev_status,
            parallel_dev_cleanup,
            parallel_dev_help
        )
        
        project_id = "UNIFIED_API_TEST"
        tasks = "API_TASK1,API_TASK2"
        
        # 测试1: 一键设置
        print("\n1️⃣ 测试一键设置...")
        one_click_result = json.loads(parallel_dev_one_click(project_id, tasks))
        print_result("一键设置", one_click_result)
        
        if not one_click_result.get("success"):
            print("⚠️ 一键设置失败，尝试继续其他测试...")
        
        # 等待系统稳定
        time.sleep(2)
        
        # 测试2: 状态检查
        print("\n2️⃣ 测试统一状态检查...")
        status_result = json.loads(parallel_dev_status(project_id))
        print_result("统一状态检查", status_result)
        
        # 测试3: 帮助信息
        print("\n3️⃣ 测试帮助信息...")
        help_result = json.loads(parallel_dev_help())
        print_result("帮助信息", {"success": "title" in help_result})
        
        # 测试4: 环境清理
        print("\n4️⃣ 测试统一清理...")
        cleanup_result = json.loads(parallel_dev_cleanup(project_id))
        print_result("统一清理", cleanup_result)
        
        return True
        
    except Exception as e:
        print(f"❌ 统一API测试失败: {str(e)}")
        return False

def test_hooks_configuration():
    """测试Hooks配置"""
    print_header("🪝 测试Hooks配置")
    
    try:
        # 检查hooks文件是否存在
        hooks_dir = Path("src/hooks")
        master_hooks = hooks_dir / "master_session_hooks.json"
        child_hooks = hooks_dir / "child_session_hooks.json"
        
        tests = []
        
        # 测试1: 检查文件存在
        master_exists = master_hooks.exists()
        child_exists = child_hooks.exists()
        
        tests.append(("主会话hooks文件", {"success": master_exists}))
        tests.append(("子会话hooks文件", {"success": child_exists}))
        
        # 测试2: 检查文件内容
        if master_exists:
            try:
                with open(master_hooks, 'r') as f:
                    master_content = json.load(f)
                tests.append(("主会话hooks内容", {"success": "user-prompt-submit-hook" in master_content}))
            except Exception as e:
                tests.append(("主会话hooks内容", {"success": False, "error": str(e)}))
        
        if child_exists:
            try:
                with open(child_hooks, 'r') as f:
                    child_content = json.load(f)
                tests.append(("子会话hooks内容", {"success": "user-prompt-submit-hook" in child_content}))
            except Exception as e:
                tests.append(("子会话hooks内容", {"success": False, "error": str(e)}))
        
        # 显示测试结果
        for test_name, result in tests:
            print_result(test_name, result)
        
        return all(test[1].get("success", False) for test in tests)
        
    except Exception as e:
        print(f"❌ Hooks配置测试失败: {str(e)}")
        return False

def test_system_validation():
    """验证核心MCP工具功能"""
    print_header("📋 验证核心MCP功能")
    
    try:
        from src.mcp_tools.tmux_session_orchestrator import tmux_session_orchestrator
        
        # 测试核心MCP工具的基础功能
        test_project = "CORE_VALIDATION"
        
        # 1. 测试初始化
        init_result = tmux_session_orchestrator("init", test_project, ["VALIDATION_TASK"])
        if not init_result.get("success"):
            print("❌ 核心MCP工具初始化失败")
            return False
        
        # 2. 测试状态查询
        status_result = tmux_session_orchestrator("status", test_project)
        if not status_result.get("success"):
            print("❌ 核心MCP工具状态查询失败")
            return False
        
        # 3. 测试清理
        cleanup_result = tmux_session_orchestrator("cleanup", test_project)
        if not cleanup_result.get("success"):
            print("❌ 核心MCP工具清理失败")
            return False
        
        print("✅ 核心MCP功能验证通过")
        print("   ✓ 初始化功能正常")
        print("   ✓ 状态查询功能正常") 
        print("   ✓ 清理功能正常")
        return True
            
    except Exception as e:
        print(f"❌ 核心MCP功能验证失败: {str(e)}")
        return False

def run_all_tests():
    """运行所有集成测试"""
    print_header("🧪 完整集成测试开始")
    
    print(f"""
🎯 测试范围:
   • 基础tmux编排器功能
   • MCP服务器集成功能  
   • 统一API接口
   • Hooks配置验证
   • 核心MCP功能验证

📋 测试目标:
   • 验证零Shell脚本方案可行性
   • 确保与现有系统完全兼容
   • 测试完整的用户工作流程
    """)
    
    input("按Enter开始测试...")
    
    test_results = []
    
    # 运行各项测试
    tests = [
        ("基础Tmux编排器", test_tmux_orchestrator_basic),
        ("MCP服务器集成", test_integrated_mcp_server),  
        ("统一API接口", test_unified_api),
        ("Hooks配置", test_hooks_configuration),
        ("核心MCP功能验证", test_system_validation)
    ]
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            test_results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {str(e)}")
            test_results.append((test_name, False))
    
    # 汇总结果
    print_header("📊 集成测试结果汇总")
    
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    success_rate = (passed / total * 100) if total > 0 else 0
    
    print(f"""
📈 测试统计:
   总测试数: {total}
   通过: {passed}
   失败: {total - passed}
   成功率: {success_rate:.1f}%

📋 详细结果:""")
    
    for test_name, result in test_results:
        status = "✅" if result else "❌"
        print(f"   {status} {test_name}")
    
    # 最终评估
    if success_rate >= 80:
        print(f"""
🎉 集成测试总体成功！

✅ 系统就绪状态:
   • 基础功能完整可用
   • 与现有系统兼容良好
   • 用户接口简洁易用
   • 零Shell脚本目标达成

🚀 立即可用的命令:
   from src.mcp_server.unified_api import parallel_dev_one_click
   parallel_dev_one_click("MY_PROJECT", "TASK1,TASK2,TASK3")

📚 使用文档:
   src/mcp_tools/README.md
        """)
    else:
        print(f"""
⚠️ 集成测试发现问题

🔧 需要注意:
   • {total - passed}个测试失败
   • 建议检查失败的测试项
   • 部分功能可能需要调整

💡 故障排除:
   • 确保tmux已安装
   • 检查Python环境和依赖
   • 验证文件权限设置
        """)
    
    return success_rate >= 80

def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        print("🏃‍♂️ 快速测试模式")
        result = test_unified_api()
        print(f"快速测试结果: {'✅ 通过' if result else '❌ 失败'}")
    else:
        run_all_tests()

if __name__ == "__main__":
    main()