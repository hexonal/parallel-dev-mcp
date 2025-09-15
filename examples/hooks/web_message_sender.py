#!/usr/bin/env python3
"""
Web消息发送器 - 简化版
核心功能：通过Web服务向tmux发送消息
"""
import os
import sys
import json
import requests
from datetime import datetime
from typing import Dict


class WebMessageSender:
    """Web消息发送器 - 核心功能"""

    def __init__(self, web_service_url: str = None):
        if web_service_url is None:
            web_service_url = os.environ.get('WEB_SERVICE_URL', 'http://localhost:5500')
        self.web_service_url = web_service_url.rstrip('/')
        self.session = requests.Session()


    def _check_web_service(self) -> bool:
        """检查 Web 服务是否可用"""
        try:
            response = self.session.get(f"{self.web_service_url}/health", timeout=3)
            return response.status_code == 200
        except Exception:
            return False

    def _send_http_request(self, endpoint: str, data: dict, method: str = "POST") -> Dict:
        """发送 HTTP 请求到 Web 服务"""
        try:
            url = f"{self.web_service_url}{endpoint}"

            if method.upper() == "POST":
                response = self.session.post(url, json=data, timeout=10)
            else:
                response = self.session.get(url, timeout=10)

            return {
                'success': response.status_code == 200,
                'status_code': response.status_code,
                'data': response.json() if response.content else {},
                'error': None
            }

        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'status_code': 0,
                'data': {},
                'error': str(e)
            }


    def send_text_message(self, message: str, target_session: str = None, session_id: str = None) -> Dict[str, any]:
        """发送文本消息（核心功能）"""
        if not self._check_web_service():
            return {'status': 'failed', 'reason': 'Web服务不可用'}

        # 构造请求数据，匹配tmux_web_service.py的期望格式
        request_data = {
            'message': message,
        }

        if target_session:
            request_data['target_session'] = target_session

        if session_id:
            request_data['session_id'] = session_id

        # 发送请求到正确的端点
        result = self._send_http_request('/message/send', request_data)

        # 简化返回结构
        return {
            'status': 'success' if result['success'] else 'failed',
            'target_session': target_session or 'default'
        }

    # 简化：删除send_structured_notification，通过send_text_message实现

    # 简化：删除get_available_sessions，非核心功能

    # 简化：删除handle_session_communication，复杂业务逻辑

    # 简化：删除handle_task_progress，项目管理逻辑

    # 简化：删除handle_tool_usage_report，特定业务逻辑


# 简化：删除_log_debug调试功能



def main():
    """主执行函数 - 简化版"""
    # 初始化发送器
    try:
        sender = WebMessageSender()
    except Exception as e:
        error_result = {
            'status': 'error',
            'reason': 'initialization_error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }
        print(json.dumps(error_result, ensure_ascii=False))
        return

    # 检查是否有命令行参数，如果有则跳过stdin模式
    if len(sys.argv) > 1:
        # 有命令行参数，直接进入命令行模式
        pass
    elif not sys.stdin.isatty():
        # 没有命令行参数且有stdin输入，处理hooks数据并发送消息
        try:
            input_data = json.load(sys.stdin)
            print("成功读取输入数据:", input_data)

            # 提取session信息（简化处理）
            session_id = input_data.get('session_id')  # 直接从input_data获取session_id
            hook_event_name = input_data.get('hook_event_name', 'unknown')

            # 简化处理 - 修复session_id显示问题
            session_display = session_id[:8] + '...' if session_id else 'None'
            print(f"📝 处理事件: {hook_event_name} (Session ID: {session_display})")

            # 正常处理消息
            # 发送完整的input_data到tmux
            message = json.dumps(input_data, ensure_ascii=False, indent=2)

            # 发送消息到tmux（传递session_id用于绑定验证）
            result = sender.send_text_message(message, session_id=session_id)
            print(f"消息发送结果: {result['status']}")

        except json.JSONDecodeError as e:
            print(f"JSON解析错误，跳过: {e}")
            print(f"错误详情: {str(e)}")
            print(f"错误类型: {type(e).__name__}")
        except Exception as e:
            print(f"读取stdin时发生错误，跳过: {e}")
            print(f"错误详情: {str(e)}")
            print(f"错误类型: {type(e).__name__}")
            # 输出更多调试信息
            import traceback
            print(f"完整错误堆栈:\n{traceback.format_exc()}")
        return

    # 命令行模式（向后兼容）
    operation = sys.argv[1] if len(sys.argv) > 1 else 'info'
    # 简化：删除调试日志

    # 核心操作：只保留send和health
    if operation == 'send':
        # 发送文本消息 (核心功能)
        message = sys.argv[2] if len(sys.argv) > 2 else "Test message"
        target_session = sys.argv[3] if len(sys.argv) > 3 else None

        print(f"📤 发送消息: '{message[:50]}...' → {target_session or 'default'}")
        result = sender.send_text_message(message, target_session)
        print(f"结果: {'成功' if result['status'] == 'success' else '失败'}")

    elif operation == 'health':
        # 健康检查 (基础功能)
        print("🔍 检查 Web 服务状态...")
        is_healthy = sender._check_web_service()
        result = {
            'status': 'success' if is_healthy else 'failed',
            'web_service_healthy': is_healthy,
            'web_service_url': sender.web_service_url
        }
        print(f"服务状态: {'✅ 正常' if is_healthy else '❌ 异常'}")

    # 简化：删除所有其他复杂操作

    else:
        result = {
            'status': 'error',
            'message': f'未知操作类型: {operation}',
            'supported_operations': ['send', 'health'],
            'usage': [
                'python web_message_sender.py send "Hello World" [target_session]',
                'python web_message_sender.py health',
                'echo \'{"event": "data"}\' | python web_message_sender.py  # hooks'
            ]
        }

    # 简化：删除复杂的verbose输出处理


if __name__ == "__main__":
    main()