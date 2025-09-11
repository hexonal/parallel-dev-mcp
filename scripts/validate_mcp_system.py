#!/usr/bin/env python3
"""MCP Session Coordinator系统实际验证脚本

在真实环境中测试MCP服务器的运行和功能。
"""

import asyncio
import json
import os
import sys
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, List

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.mcp_server.session_coordinator import SessionCoordinatorMCP
from src.hooks.hooks_manager import HooksManager


class MCPSystemValidator:
    """MCP系统验证器"""
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root or os.getcwd())
        self.coordinator = SessionCoordinatorMCP("validation-test")
        self.hooks_manager = HooksManager(str(self.project_root))
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """记录测试结果"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"    {details}")
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details
        })
    
    async def validate_mcp_server_core(self):
        """验证MCP服务器核心功能"""
        print("\n=== 验证MCP服务器核心功能 ===")
        
        # 测试1: 服务器初始化
        try:
            stats = self.coordinator.get_server_stats()
            self.log_test(
                "MCP服务器初始化",
                True,
                f"活跃关系: {stats['active_relationships']}, 活跃会话: {stats['active_sessions']}"
            )
        except Exception as e:
            self.log_test("MCP服务器初始化", False, str(e))
        
        # 测试2: 会话关系注册
        try:
            project_id = "VALIDATION_TEST"
            master_session = f"master_project_{project_id}"
            child_session = f"child_{project_id}_task_CORE_TEST"
            task_id = "CORE_TEST"
            
            result = self.coordinator.register_session_relationship(
                parent_session=master_session,
                child_session=child_session,
                task_id=task_id,
                project_id=project_id
            )
            
            success = "注册成功" in result
            self.log_test("会话关系注册", success, result)
            
        except Exception as e:
            self.log_test("会话关系注册", False, str(e))
        
        # 测试3: 状态上报和查询
        try:
            # 上报状态
            status_result = self.coordinator.report_session_status(
                session_name=child_session,
                status="WORKING",
                progress=75,
                details="验证测试进行中"
            )
            
            # 查询状态
            query_result = self.coordinator.query_session_status(child_session)
            query_data = json.loads(query_result)
            
            success = (
                "状态已更新" in status_result and
                query_data.get("status") == "WORKING" and
                query_data.get("progress") == 75
            )
            
            self.log_test(
                "状态上报和查询",
                success,
                f"状态: {query_data.get('status')}, 进度: {query_data.get('progress')}%"
            )
            
        except Exception as e:
            self.log_test("状态上报和查询", False, str(e))
        
        # 测试4: 子会话查询
        try:
            children_result = self.coordinator.get_child_sessions(master_session)
            children_data = json.loads(children_result)
            
            success = children_data.get("child_count", 0) > 0
            self.log_test(
                "子会话查询",
                success,
                f"发现 {children_data.get('child_count', 0)} 个子会话"
            )
            
        except Exception as e:
            self.log_test("子会话查询", False, str(e))
        
        # 测试5: 消息传递
        try:
            # 发送消息
            send_result = self.coordinator.send_message_to_session(
                from_session=master_session,
                to_session=child_session,
                message="验证测试消息",
                message_type="INSTRUCTION"
            )
            
            # 接收消息
            receive_result = self.coordinator.get_session_messages(child_session)
            receive_data = json.loads(receive_result)
            
            success = (
                "消息已发送" in send_result and
                receive_data.get("unread_count", 0) > 0
            )
            
            self.log_test(
                "消息传递",
                success,
                f"发送结果: {'成功' if '消息已发送' in send_result else '失败'}, "
                f"未读消息: {receive_data.get('unread_count', 0)}条"
            )
            
        except Exception as e:
            self.log_test("消息传递", False, str(e))
    
    def validate_hooks_generation(self):
        """验证hooks配置生成"""
        print("\n=== 验证Hooks配置生成 ===")
        
        # 测试1: 生成主会话hooks
        try:
            master_hooks_path = self.hooks_manager.generate_master_session_hooks(
                session_name="validation_master_project_TEST",
                project_id="TEST"
            )
            
            success = Path(master_hooks_path).exists()
            self.log_test(
                "主会话hooks生成",
                success,
                f"文件: {master_hooks_path}" if success else "文件未生成"
            )
            
            # 验证hooks内容
            if success:
                with open(master_hooks_path, 'r', encoding='utf-8') as f:
                    hooks_data = json.load(f)
                
                required_hooks = ["session-start", "periodic-monitoring", "send-instructions"]
                missing_hooks = [h for h in required_hooks if h not in hooks_data.get("hooks", {})]
                
                content_valid = len(missing_hooks) == 0
                self.log_test(
                    "主会话hooks内容验证",
                    content_valid,
                    f"缺失hooks: {missing_hooks}" if missing_hooks else "所有必需hooks存在"
                )
            
        except Exception as e:
            self.log_test("主会话hooks生成", False, str(e))
        
        # 测试2: 生成子会话hooks
        try:
            child_hooks_path = self.hooks_manager.generate_child_session_hooks(
                session_name="validation_child_TEST_task_HOOKS",
                master_session_id="validation_master_project_TEST",
                task_id="HOOKS",
                project_id="TEST"
            )
            
            success = Path(child_hooks_path).exists()
            self.log_test(
                "子会话hooks生成",
                success,
                f"文件: {child_hooks_path}" if success else "文件未生成"
            )
            
            # 验证hooks内容
            if success:
                with open(child_hooks_path, 'r', encoding='utf-8') as f:
                    hooks_data = json.load(f)
                
                required_hooks = ["session-start", "after-tool-call", "task-completion", "periodic-check"]
                missing_hooks = [h for h in required_hooks if h not in hooks_data.get("hooks", {})]
                
                content_valid = len(missing_hooks) == 0
                self.log_test(
                    "子会话hooks内容验证",
                    content_valid,
                    f"缺失hooks: {missing_hooks}" if missing_hooks else "所有必需hooks存在"
                )
            
        except Exception as e:
            self.log_test("子会话hooks生成", False, str(e))
    
    def validate_tmux_integration(self):
        """验证tmux集成"""
        print("\n=== 验证tmux集成 ===")
        
        # 测试1: 检查tmux可用性
        try:
            result = subprocess.run(["tmux", "-V"], capture_output=True, text=True)
            success = result.returncode == 0
            version = result.stdout.strip() if success else "未知"
            
            self.log_test(
                "tmux可用性检查",
                success,
                f"版本: {version}" if success else "tmux未安装或不可用"
            )
            
        except Exception as e:
            self.log_test("tmux可用性检查", False, str(e))
        
        # 测试2: 创建测试会话
        try:
            test_session_name = "validation_test_session"
            
            # 创建会话，使用 sleep 命令保持会话活跃
            create_result = subprocess.run([
                "tmux", "new-session", "-d", "-s", test_session_name,
                "-e", "TEST_VAR=validation_test",
                "sleep 5"
            ], capture_output=True, text=True)
            
            if create_result.returncode == 0:
                # 短暂等待确保会话启动
                time.sleep(1)
                
                # 验证会话存在
                list_result = subprocess.run([
                    "tmux", "list-sessions", "-F", "#{session_name}"
                ], capture_output=True, text=True)
                
                session_exists = test_session_name in list_result.stdout
                
                # 清理会话（如果存在的话）
                if session_exists:
                    subprocess.run([
                        "tmux", "kill-session", "-t", test_session_name
                    ], capture_output=True, text=True)
                
                self.log_test(
                    "tmux会话创建和管理",
                    session_exists,
                    "会话创建、验证、清理成功" if session_exists else "会话创建失败"
                )
            else:
                self.log_test("tmux会话创建和管理", False, f"创建失败: {create_result.stderr}")
                
        except Exception as e:
            self.log_test("tmux会话创建和管理", False, str(e))
        
        # 测试3: 环境变量传递
        try:
            env_test_session = "validation_env_test"
            test_env_var = "VALIDATION_TEST_123"
            test_env_value = "test_value_456"
            
            # 创建带环境变量的会话
            create_result = subprocess.run([
                "tmux", "new-session", "-d", "-s", env_test_session,
                "-e", f"{test_env_var}={test_env_value}",
                "sleep 2"
            ], capture_output=True, text=True)
            
            if create_result.returncode == 0:
                time.sleep(1)  # 等待会话启动
                
                # 获取环境变量
                env_result = subprocess.run([
                    "tmux", "show-environment", "-t", env_test_session
                ], capture_output=True, text=True)
                
                env_found = f"{test_env_var}={test_env_value}" in env_result.stdout
                
                # 清理
                subprocess.run([
                    "tmux", "kill-session", "-t", env_test_session
                ], capture_output=True, text=True)
                
                self.log_test(
                    "环境变量传递",
                    env_found,
                    f"环境变量 {test_env_var}={'找到' if env_found else '未找到'}"
                )
            else:
                self.log_test("环境变量传递", False, create_result.stderr)
                
        except Exception as e:
            self.log_test("环境变量传递", False, str(e))
    
    def validate_error_handling(self):
        """验证错误处理"""
        print("\n=== 验证错误处理 ===")
        
        # 测试1: 无效会话名称
        try:
            result = self.coordinator.register_session_relationship(
                parent_session="invalid_session_name",
                child_session="also_invalid",
                task_id="TEST",
                project_id="TEST"
            )
            
            success = "无效" in result or "错误" in result
            self.log_test(
                "无效会话名称处理",
                success,
                "正确拒绝无效会话名称" if success else "未正确处理无效输入"
            )
            
        except Exception as e:
            self.log_test("无效会话名称处理", False, str(e))
        
        # 测试2: 无效状态值
        try:
            result = self.coordinator.report_session_status(
                session_name="child_TEST_task_ERROR",
                status="INVALID_STATUS",
                progress=0
            )
            
            success = "无效" in result
            self.log_test(
                "无效状态值处理",
                success,
                "正确拒绝无效状态" if success else "未正确处理无效状态"
            )
            
        except Exception as e:
            self.log_test("无效状态值处理", False, str(e))
        
        # 测试3: 不存在的会话查询
        try:
            result = self.coordinator.query_session_status("nonexistent_session_12345")
            result_data = json.loads(result)
            
            success = "error" in result_data
            self.log_test(
                "不存在会话查询处理",
                success,
                "正确返回错误信息" if success else "未正确处理不存在的会话"
            )
            
        except Exception as e:
            self.log_test("不存在会话查询处理", False, str(e))
    
    def validate_performance(self):
        """验证性能"""
        print("\n=== 验证性能 ===")
        
        # 测试1: 批量会话操作
        try:
            start_time = time.time()
            
            # 创建多个会话关系
            project_id = "PERF_TEST"
            master_session = f"master_project_{project_id}"
            
            for i in range(10):
                task_id = f"TASK_{i:03d}"
                child_session = f"child_{project_id}_task_{task_id}"
                
                self.coordinator.register_session_relationship(
                    parent_session=master_session,
                    child_session=child_session,
                    task_id=task_id,
                    project_id=project_id
                )
                
                self.coordinator.report_session_status(
                    session_name=child_session,
                    status="WORKING",
                    progress=50,
                    details=f"性能测试任务 {i+1}"
                )
            
            # 查询所有子会话
            children_result = self.coordinator.get_child_sessions(master_session)
            children_data = json.loads(children_result)
            
            end_time = time.time()
            duration = end_time - start_time
            
            success = (
                children_data.get("child_count") == 10 and
                duration < 5.0  # 应该在5秒内完成
            )
            
            self.log_test(
                "批量操作性能",
                success,
                f"10个会话操作耗时: {duration:.2f}秒, 创建会话: {children_data.get('child_count', 0)}个"
            )
            
        except Exception as e:
            self.log_test("批量操作性能", False, str(e))
        
        # 测试2: 消息队列性能
        try:
            start_time = time.time()
            
            test_session = "perf_test_messages"
            
            # 发送大量消息
            for i in range(50):
                self.coordinator.send_message_to_session(
                    from_session="perf_sender",
                    to_session=test_session,
                    message=f"性能测试消息 {i+1}",
                    message_type="INSTRUCTION"
                )
            
            # 获取所有消息
            messages_result = self.coordinator.get_session_messages(test_session)
            messages_data = json.loads(messages_result)
            
            end_time = time.time()
            duration = end_time - start_time
            
            success = (
                messages_data.get("unread_count") == 50 and
                duration < 3.0  # 应该在3秒内完成
            )
            
            self.log_test(
                "消息队列性能",
                success,
                f"50条消息处理耗时: {duration:.2f}秒, 接收消息: {messages_data.get('unread_count', 0)}条"
            )
            
        except Exception as e:
            self.log_test("消息队列性能", False, str(e))
    
    def generate_validation_report(self):
        """生成验证报告"""
        print("\n" + "="*60)
        print("MCP Session Coordinator系统验证报告")
        print("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\n📊 测试统计:")
        print(f"  总测试数: {total_tests}")
        print(f"  通过: {passed_tests}")
        print(f"  失败: {failed_tests}")
        print(f"  成功率: {success_rate:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ 失败的测试:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['details']}")
        
        print(f"\n{'✅ 系统验证通过!' if failed_tests == 0 else '⚠️  系统存在问题，需要修复'}")
        
        # 保存报告到文件
        report_data = {
            "validation_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": success_rate,
            "test_results": self.test_results
        }
        
        report_path = self.project_root / "logs" / "validation_report.json"
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 详细报告已保存到: {report_path}")
        
        return failed_tests == 0


async def main():
    """主验证流程"""
    print("MCP Session Coordinator系统实际验证")
    print("="*50)
    
    validator = MCPSystemValidator()
    
    # 运行所有验证测试
    await validator.validate_mcp_server_core()
    validator.validate_hooks_generation()
    validator.validate_tmux_integration()
    validator.validate_error_handling()
    validator.validate_performance()
    
    # 生成验证报告
    success = validator.generate_validation_report()
    
    return success


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n验证被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n验证过程发生错误: {e}")
        sys.exit(1)