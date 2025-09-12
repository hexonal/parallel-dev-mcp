#!/usr/bin/env python3
"""Session Coordinator MCP服务器单元测试

验证MCP服务器的核心功能：会话注册、状态管理、消息传递等。
"""

import json
import unittest
from datetime import datetime
import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.mcp_server.session_coordinator import SessionCoordinatorMCP
from src.mcp_server.session_models import SessionStatusEnum, MessageType
from src.mcp_server.session_utils import (
    parse_session_name, validate_session_name, generate_session_name,
    SessionRole
)


class TestSessionCoordinator(unittest.TestCase):
    """Session Coordinator MCP服务器测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.coordinator = SessionCoordinatorMCP("test-coordinator")
        
        # 测试数据
        self.project_id = "TEST_PROJECT"
        self.task_id = "AUTH_001" 
        self.master_session = f"parallel_{self.project_id}_task_master"
        self.child_session = f"parallel_{self.project_id}_task_child_{self.task_id}"
    
    def test_session_name_parsing(self):
        """测试会话名称解析"""
        print("\\n=== 测试会话名称解析 ===")
        
        # 测试主会话解析
        master_result = parse_session_name(self.master_session)
        self.assertIsNotNone(master_result)
        self.assertEqual(master_result["role"], "master")
        self.assertEqual(master_result["project_id"], self.project_id)
        print(f"✓ 主会话解析: {master_result}")
        
        # 测试子会话解析
        child_result = parse_session_name(self.child_session)
        self.assertIsNotNone(child_result)
        self.assertEqual(child_result["role"], "child")
        self.assertEqual(child_result["project_id"], self.project_id)
        self.assertEqual(child_result["task_id"], self.task_id)
        self.assertEqual(child_result["parent_session"], self.master_session)
        print(f"✓ 子会话解析: {child_result}")
        
        # 测试无效会话名称
        invalid_result = parse_session_name("invalid_session_name")
        self.assertIsNone(invalid_result)
        print("✓ 无效会话名称正确拒绝")
    
    def test_session_name_validation(self):
        """测试会话名称验证"""
        print("\\n=== 测试会话名称验证 ===")
        
        # 有效名称
        valid, error = validate_session_name(self.master_session)
        self.assertTrue(valid)
        print(f"✓ 有效主会话名称: {self.master_session}")
        
        valid, error = validate_session_name(self.child_session)
        self.assertTrue(valid)
        print(f"✓ 有效子会话名称: {self.child_session}")
        
        # 无效名称
        invalid_names = ["", "too_short", "invalid_format_name", "x" * 101]
        for invalid_name in invalid_names:
            valid, error = validate_session_name(invalid_name)
            self.assertFalse(valid)
            print(f"✓ 无效名称被拒绝: {invalid_name} ({error})")
    
    def test_session_name_generation(self):
        """测试会话名称生成"""
        print("\\n=== 测试会话名称生成 ===")
        
        # 生成主会话名称
        generated_master = generate_session_name(SessionRole.MASTER, self.project_id)
        self.assertEqual(generated_master, self.master_session)
        print(f"✓ 生成主会话名称: {generated_master}")
        
        # 生成子会话名称
        generated_child = generate_session_name(
            SessionRole.CHILD, self.project_id, self.task_id
        )
        self.assertEqual(generated_child, self.child_session)
        print(f"✓ 生成子会话名称: {generated_child}")
        
        # 测试缺少task_id的错误
        with self.assertRaises(ValueError):
            generate_session_name(SessionRole.CHILD, self.project_id)
        print("✓ 子会话缺少task_id正确抛出错误")
    
    def test_register_session_relationship(self):
        """测试会话关系注册"""
        print("\\n=== 测试会话关系注册 ===")
        
        # 注册会话关系
        result = self.coordinator.register_session_relationship(
            parent_session=self.master_session,
            child_session=self.child_session,
            task_id=self.task_id,
            project_id=self.project_id
        )
        
        self.assertIn("注册成功", result)
        print(f"✓ 注册结果: {result}")
        
        # 验证关系是否正确存储
        relationship = self.coordinator.state.session_relationships.get(self.child_session)
        self.assertIsNotNone(relationship)
        self.assertEqual(relationship.parent_session, self.master_session)
        self.assertEqual(relationship.task_id, self.task_id)
        print("✓ 关系数据正确存储")
        
        # 测试无效会话名称注册
        invalid_result = self.coordinator.register_session_relationship(
            parent_session="invalid_name",
            child_session=self.child_session,
            task_id=self.task_id
        )
        self.assertIn("无效", invalid_result)
        print(f"✓ 无效会话注册被拒绝: {invalid_result}")
    
    def test_report_session_status(self):
        """测试会话状态上报"""
        print("\\n=== 测试会话状态上报 ===")
        
        # 先注册会话关系
        self.coordinator.register_session_relationship(
            parent_session=self.master_session,
            child_session=self.child_session,
            task_id=self.task_id,
            project_id=self.project_id
        )
        
        # 上报子会话状态
        result = self.coordinator.report_session_status(
            session_name=self.child_session,
            status="WORKING",
            progress=50,
            details="正在实现登录功能"
        )
        
        self.assertIn("状态已更新", result)
        print(f"✓ 状态上报结果: {result}")
        
        # 验证状态是否正确存储
        session_status = self.coordinator.state.active_sessions.get(self.child_session)
        self.assertIsNotNone(session_status)
        self.assertEqual(session_status.status, SessionStatusEnum.WORKING)
        self.assertEqual(session_status.progress, 50)
        print("✓ 状态数据正确存储")
        
        # 测试完成状态上报（应该自动通知父会话）
        completion_result = self.coordinator.report_session_status(
            session_name=self.child_session,
            status="COMPLETED",
            progress=100,
            details="任务已完成"
        )
        
        self.assertIn("状态已更新", completion_result)
        print(f"✓ 完成状态上报: {completion_result}")
        
        # 验证父会话是否收到通知
        parent_messages = self.coordinator.state.session_messages.get(self.master_session, [])
        self.assertTrue(len(parent_messages) > 0)
        completion_message = parent_messages[-1]
        self.assertEqual(completion_message.message_type, MessageType.STATUS_UPDATE)
        print("✓ 父会话收到完成通知")
        
        # 测试无效状态值
        invalid_result = self.coordinator.report_session_status(
            session_name=self.child_session,
            status="INVALID_STATUS",
            progress=0
        )
        self.assertIn("无效的状态值", invalid_result)
        print(f"✓ 无效状态被拒绝: {invalid_result}")
    
    def test_get_child_sessions(self):
        """测试获取子会话列表"""
        print("\\n=== 测试获取子会话列表 ===")
        
        # 注册多个子会话
        child_sessions = [
            (f"parallel_{self.project_id}_task_child_AUTH", "AUTH"),
            (f"parallel_{self.project_id}_task_child_DB", "DB"),
            (f"parallel_{self.project_id}_task_child_API", "API")
        ]
        
        for child_session, task_id in child_sessions:
            self.coordinator.register_session_relationship(
                parent_session=self.master_session,
                child_session=child_session,
                task_id=task_id,
                project_id=self.project_id
            )
            
            # 为每个子会话设置状态
            self.coordinator.report_session_status(
                session_name=child_session,
                status="WORKING",
                progress=30,
                details=f"正在执行{task_id}任务"
            )
        
        # 获取子会话列表
        result = self.coordinator.get_child_sessions(self.master_session)
        result_data = json.loads(result)
        
        self.assertEqual(result_data["child_count"], 3)
        self.assertEqual(len(result_data["children"]), 3)
        print(f"✓ 子会话列表: {result_data['child_count']}个子会话")
        
        # 验证每个子会话的信息
        for child_info in result_data["children"]:
            self.assertIn("session_name", child_info)
            self.assertIn("task_id", child_info)
            self.assertIn("status", child_info)
            self.assertIn("health_score", child_info)
            print(f"  - {child_info['session_name']}: {child_info['status']} ({child_info['progress']}%)")
    
    def test_message_passing(self):
        """测试消息传递功能"""
        print("\\n=== 测试消息传递功能 ===")
        
        # 注册会话关系
        self.coordinator.register_session_relationship(
            parent_session=self.master_session,
            child_session=self.child_session,
            task_id=self.task_id,
            project_id=self.project_id
        )
        
        # 主会话向子会话发送指令
        send_result = self.coordinator.send_message_to_session(
            from_session=self.master_session,
            to_session=self.child_session,
            message="请报告当前进度并准备合并",
            message_type="INSTRUCTION"
        )
        
        self.assertIn("消息已发送", send_result)
        print(f"✓ 发送消息结果: {send_result}")
        
        # 子会话获取消息
        get_result = self.coordinator.get_session_messages(self.child_session)
        messages_data = json.loads(get_result)
        
        self.assertEqual(messages_data["unread_count"], 1)
        self.assertTrue(len(messages_data["messages"]) > 0)
        
        message = messages_data["messages"][0]
        self.assertEqual(message["from_session"], self.master_session)
        self.assertEqual(message["message_type"], "INSTRUCTION")
        self.assertEqual(message["content"], "请报告当前进度并准备合并")
        print(f"✓ 接收消息: {message['content']}")
        
        # 再次获取消息（应该为空，因为已读）
        empty_result = self.coordinator.get_session_messages(self.child_session)
        empty_data = json.loads(empty_result)
        self.assertEqual(empty_data["unread_count"], 0)
        print("✓ 消息标记为已读")
    
    def test_query_session_status(self):
        """测试会话状态查询"""
        print("\\n=== 测试会话状态查询 ===")
        
        # 创建测试会话状态
        self.coordinator.report_session_status(
            session_name=self.child_session,
            status="WORKING",
            progress=75,
            details="即将完成"
        )
        
        # 查询单个会话状态
        single_result = self.coordinator.query_session_status(self.child_session)
        single_data = json.loads(single_result)
        
        self.assertEqual(single_data["session_name"], self.child_session)
        self.assertEqual(single_data["status"], "WORKING")
        self.assertEqual(single_data["progress"], 75)
        self.assertIn("health_score", single_data)
        print(f"✓ 单会话查询: {single_data['session_name']} - {single_data['status']}")
        
        # 查询所有会话状态
        all_result = self.coordinator.query_session_status()
        all_data = json.loads(all_result)
        
        self.assertIn("total_sessions", all_data)
        self.assertIn("sessions", all_data)
        self.assertTrue(all_data["total_sessions"] > 0)
        print(f"✓ 所有会话查询: {all_data['total_sessions']}个会话")
        
        # 查询不存在的会话
        nonexistent_result = self.coordinator.query_session_status("nonexistent_session")
        nonexistent_data = json.loads(nonexistent_result)
        self.assertIn("error", nonexistent_data)
        print("✓ 不存在的会话正确返回错误")


class TestIntegrationScenarios(unittest.TestCase):
    """集成场景测试"""
    
    def setUp(self):
        """测试前准备"""
        self.coordinator = SessionCoordinatorMCP("integration-test")
    
    def test_complete_development_workflow(self):
        """测试完整的开发工作流"""
        print("\\n=== 集成测试：完整开发工作流 ===")
        
        project_id = "DEMO_PROJECT"
        master_session = f"parallel_{project_id}_task_master"
        
        # 创建3个开发任务
        tasks = [
            ("AUTH", "用户认证系统"),
            ("API", "REST API接口"),
            ("UI", "前端界面")
        ]
        
        child_sessions = []
        for task_id, description in tasks:
            child_session = f"parallel_{project_id}_task_child_{task_id}"
            child_sessions.append((child_session, task_id, description))
            
            # 1. 注册会话关系
            self.coordinator.register_session_relationship(
                parent_session=master_session,
                child_session=child_session,
                task_id=task_id,
                project_id=project_id
            )
            
            # 2. 开始任务
            self.coordinator.report_session_status(
                session_name=child_session,
                status="STARTED",
                progress=0,
                details=f"开始{description}"
            )
            
            print(f"✓ 任务启动: {task_id} - {description}")
        
        # 3. 模拟开发过程
        for i, (child_session, task_id, description) in enumerate(child_sessions):
            # 工作中状态
            self.coordinator.report_session_status(
                session_name=child_session,
                status="WORKING", 
                progress=50,
                details=f"{description}开发进行中"
            )
            
            # 主会话发送指令
            self.coordinator.send_message_to_session(
                from_session=master_session,
                to_session=child_session,
                message=f"请加快{task_id}任务进度",
                message_type="INSTRUCTION"
            )
            
            print(f"✓ 任务进行中: {task_id} (50%)")
        
        # 4. 查看全局状态
        children_result = self.coordinator.get_child_sessions(master_session)
        children_data = json.loads(children_result)
        
        self.assertEqual(children_data["child_count"], 3)
        print(f"✓ 主会话监控: {children_data['child_count']}个子任务")
        
        # 5. 完成任务
        completed_count = 0
        for child_session, task_id, description in child_sessions:
            self.coordinator.report_session_status(
                session_name=child_session,
                status="COMPLETED",
                progress=100,
                details=f"{description}开发完成"
            )
            completed_count += 1
            print(f"✓ 任务完成: {task_id} ({completed_count}/3)")
        
        # 6. 验证完成通知
        parent_messages = self.coordinator.state.session_messages.get(master_session, [])
        completion_notifications = [
            msg for msg in parent_messages 
            if msg.message_type == MessageType.STATUS_UPDATE
        ]
        
        self.assertEqual(len(completion_notifications), 3)
        print(f"✓ 完成通知: 主会话收到{len(completion_notifications)}个完成通知")
        
        # 7. 最终状态检查
        final_status = self.coordinator.query_session_status()
        final_data = json.loads(final_status)
        
        completed_sessions = [
            name for name, status in final_data["sessions"].items()
            if status["status"] == "COMPLETED"
        ]
        
        self.assertEqual(len(completed_sessions), 3)
        print(f"✓ 最终状态: {len(completed_sessions)}个任务已完成")
        print("✅ 完整工作流测试通过")


def run_tests():
    """运行所有测试"""
    print("Session Coordinator MCP服务器测试套件")
    print("=" * 60)
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestSessionCoordinator))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegrationScenarios))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 测试结果总结
    print("\\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ 所有测试通过!")
        print(f"运行了 {result.testsRun} 个测试")
    else:
        print("❌ 部分测试失败!")
        print(f"运行了 {result.testsRun} 个测试")
        print(f"失败: {len(result.failures)} 个")
        print(f"错误: {len(result.errors)} 个")
        
        if result.failures:
            print("\\n失败的测试:")
            for test, traceback in result.failures:
                print(f"  - {test}: {traceback}")
        
        if result.errors:
            print("\\n错误的测试:")
            for test, traceback in result.errors:
                print(f"  - {test}: {traceback}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)