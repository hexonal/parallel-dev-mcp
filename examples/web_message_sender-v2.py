#!/usr/bin/env python3
"""
Web消息发送器 - Claude Code Hooks集成版
核心功能：通过Web服务向tmux发送消息，支持智能会话检测和hooks集成
"""
import os
import sys
import json
import subprocess
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple


class WebMessageSender:
    """Web消息发送器 - Claude Code Hooks集成版"""

    def __init__(self, web_service_url: str = None, project_prefix: str = None, web_port: int = None):
        # 1. 设置Web服务URL
        if web_service_url is None:
            web_port = web_port or int(os.environ.get('WEB_PORT', '5001'))
            web_service_url = f'http://localhost:{web_port}'
        self.web_service_url = web_service_url.rstrip('/')

        # 2. 设置项目前缀
        self.project_prefix = project_prefix or os.environ.get('PROJECT_PREFIX', 'PARALLEL')

        # 3. 初始化HTTP会话
        self.session = requests.Session()

        # 4. 获取当前tmux会话信息
        self.current_session_name = self._get_current_tmux_session()
        self.session_type = self._detect_session_type(self.current_session_name)

    def _get_current_tmux_session(self) -> Optional[str]:
        """获取当前tmux会话名称"""
        try:
            # 1. 尝试从TMUX环境变量获取
            tmux_env = os.environ.get('TMUX')
            if tmux_env:
                # TMUX格式：/tmp/tmux-uid/default,pid,session_number
                parts = tmux_env.split(',')
                if len(parts) >= 2:
                    # 使用tmux display-message获取会话名称
                    result = subprocess.run(
                        ['tmux', 'display-message', '-p', '#{session_name}'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        return result.stdout.strip()

            # 2. 备用方法：从tmux list-sessions中查找当前会话
            result = subprocess.run(
                ['tmux', 'list-sessions', '-F', '#{session_name}'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                sessions = result.stdout.strip().split('\n')
                # 返回第一个匹配项目前缀的会话
                for session in sessions:
                    if session.startswith(self.project_prefix.lower()) or session.startswith(self.project_prefix):
                        return session

            return None

        except Exception as e:
            print(f"获取tmux会话名称失败: {e}")
            return None

    def _detect_session_type(self, session_name: Optional[str]) -> str:
        """检测会话类型：master/child/unknown"""
        if not session_name:
            return "unknown"

        # 1. Child会话检测
        if "_child_" in session_name.lower():
            return "child"

        # 2. Master会话检测
        if ("_master_" in session_name.lower() or
            session_name.lower().startswith(self.project_prefix.lower()) or
            session_name.startswith(self.project_prefix)):
            return "master"

        # 3. 未知会话类型
        return "unknown"

    def _extract_task_id_from_session(self, session_name: Optional[str]) -> Optional[str]:
        """从Child会话名称中提取任务ID"""
        if not session_name or "_child_" not in session_name.lower():
            return None

        try:
            # 期望格式：{PROJECT_PREFIX}_child_{taskId}
            parts = session_name.split('_child_')
            if len(parts) == 2:
                return parts[1]
        except Exception:
            pass

        return None

    def _get_session_id_from_file(self) -> Optional[str]:
        """从session_id.txt文件读取会话ID"""
        try:
            session_file = Path("session_id.txt")
            if session_file.exists():
                session_id = session_file.read_text().strip()
                return session_id if session_id else None
        except Exception as e:
            print(f"读取session_id.txt失败: {e}")

        return None

    def _write_session_id_to_file(self, session_id: str) -> bool:
        """写入会话ID到session_id.txt（仅当文件为空时）"""
        try:
            session_file = Path("session_id.txt")

            # 1. 检查文件是否存在且非空
            if session_file.exists():
                existing_content = session_file.read_text().strip()
                if existing_content:
                    print(f"session_id.txt已存在内容，跳过写入: {existing_content[:8]}...")
                    return False

            # 2. 写入新的会话ID
            session_file.write_text(session_id)
            print(f"已写入session_id.txt: {session_id[:8]}...")
            return True

        except Exception as e:
            print(f"写入session_id.txt失败: {e}")
            return False


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

    def handle_stop_hook(self, hook_data: Dict) -> Dict:
        """处理Stop hook事件"""
        print(f"🛑 处理Stop hook: 会话类型={self.session_type}, 会话名称={self.current_session_name}")

        if self.session_type == "child":
            # Child Stop: 调用 /msg/send-child
            return self._handle_child_stop(hook_data)
        elif self.session_type == "master":
            # Master Stop: 调用 /msg/send
            return self._handle_master_stop(hook_data)
        else:
            return {'status': 'skipped', 'reason': f'未知会话类型: {self.session_type}'}

    def handle_session_start_hook(self, hook_data: Dict) -> Dict:
        """处理SessionStart hook事件"""
        print(f"🚀 处理SessionStart hook: 会话类型={self.session_type}, 会话名称={self.current_session_name}")

        if self.session_type == "master":
            # Master SessionStart: 写入session_id.txt
            return self._handle_master_session_start(hook_data)
        else:
            return {'status': 'skipped', 'reason': f'非Master会话，跳过SessionStart处理: {self.session_type}'}

    def _handle_child_stop(self, hook_data: Dict) -> Dict:
        """处理Child会话Stop事件"""
        try:
            # 1. 提取任务ID
            task_id = self._extract_task_id_from_session(self.current_session_name)
            if not task_id:
                return {'status': 'failed', 'reason': '无法从会话名称提取任务ID'}

            # 2. 构建Child Stop请求数据
            request_data = {
                'taskId': task_id,
                'sessionName': self.current_session_name,
                'status': 'success',  # 默认成功状态
                'exitTime': datetime.now().isoformat(),
                'projectPrefix': self.project_prefix,
                'hookData': hook_data
            }

            # 3. 发送到 /msg/send-child 端点
            result = self._send_http_request('/msg/send-child', request_data)

            # 4. 返回处理结果
            return {
                'status': 'success' if result['success'] else 'failed',
                'endpoint': '/msg/send-child',
                'task_id': task_id,
                'response': result
            }

        except Exception as e:
            return {'status': 'failed', 'reason': f'Child Stop处理异常: {e}'}

    def _handle_master_stop(self, hook_data: Dict) -> Dict:
        """处理Master会话Stop事件"""
        try:
            # 1. 获取会话ID
            session_id = self._get_session_id_from_file() or hook_data.get('session_id')
            if not session_id:
                return {'status': 'failed', 'reason': '无法获取session_id'}

            # 2. 构建Master Stop请求数据
            request_data = {
                'sessionId': session_id,
                'sessionName': self.current_session_name,
                'status': 'stop',
                'timestamp': datetime.now().isoformat(),
                'projectPrefix': self.project_prefix,
                'hookData': hook_data
            }

            # 3. 发送到 /msg/send 端点
            result = self._send_http_request('/msg/send', request_data)

            # 4. 返回处理结果
            return {
                'status': 'success' if result['success'] else 'failed',
                'endpoint': '/msg/send',
                'session_id': session_id[:8] + '...' if session_id else None,
                'response': result
            }

        except Exception as e:
            return {'status': 'failed', 'reason': f'Master Stop处理异常: {e}'}

    def _handle_master_session_start(self, hook_data: Dict) -> Dict:
        """处理Master会话SessionStart事件"""
        try:
            # 1. 获取会话ID
            session_id = hook_data.get('session_id')
            if not session_id:
                return {'status': 'failed', 'reason': '缺少session_id'}

            # 2. 尝试写入session_id.txt
            write_success = self._write_session_id_to_file(session_id)

            # 3. 返回处理结果
            return {
                'status': 'success',
                'action': 'session_id_write',
                'write_success': write_success,
                'session_id': session_id[:8] + '...' if session_id else None,
                'session_name': self.current_session_name
            }

        except Exception as e:
            return {'status': 'failed', 'reason': f'Master SessionStart处理异常: {e}'}


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
        # 没有命令行参数且有stdin输入，处理hooks数据
        try:
            input_data = json.load(sys.stdin)

            print("成功读取hooks输入数据:", input_data)

            # 提取hook事件信息
            hook_event_name = input_data.get('hook_event_name', 'unknown')
            session_id = input_data.get('session_id')

            session_display = session_id[:8] + '...' if session_id else 'None'
            print(f"📝 处理Hook事件: {hook_event_name} (Session ID: {session_display})")
            print(f"🔍 会话检测: 类型={sender.session_type}, 名称={sender.current_session_name}")

            # 根据hook事件类型分发处理
            if hook_event_name == 'Stop':
                # 处理Stop hook事件
                result = sender.handle_stop_hook(input_data)
                print(f"🛑 Stop事件处理结果: {result}")

            elif hook_event_name == 'SessionStart':
                # 处理SessionStart hook事件
                result = sender.handle_session_start_hook(input_data)
                print(f"🚀 SessionStart事件处理结果: {result}")

            else:
                # 其他事件：发送到通用消息端点
                print(f"ℹ️ 其他事件类型，发送到通用端点: {hook_event_name}")
                message = json.dumps(input_data, ensure_ascii=False, indent=2)
                result = sender.send_text_message(message, session_id=session_id)
                print(f"📤 消息发送结果: {result['status']}")

            # 输出最终结果
            final_result = {
                'hook_event': hook_event_name,
                'session_type': sender.session_type,
                'session_name': sender.current_session_name,
                'processing_result': result,
                'timestamp': datetime.now().isoformat()
            }
            print(f"✅ Hook处理完成: {json.dumps(final_result, ensure_ascii=False, indent=2)}")

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

    elif operation == 'session-info':
        # 会话信息检查 (新功能)
        print("🔍 检查当前会话信息...")
        result = {
            'status': 'success',
            'session_name': sender.current_session_name,
            'session_type': sender.session_type,
            'project_prefix': sender.project_prefix,
            'web_service_url': sender.web_service_url
        }

        print(f"会话名称: {sender.current_session_name or '未检测到'}")
        print(f"会话类型: {sender.session_type}")
        print(f"项目前缀: {sender.project_prefix}")

        # 如果是Child会话，显示任务ID
        if sender.session_type == "child":
            task_id = sender._extract_task_id_from_session(sender.current_session_name)
            result['task_id'] = task_id
            print(f"任务ID: {task_id or '未提取到'}")

        # 如果是Master会话，显示session_id.txt状态
        if sender.session_type == "master":
            session_id = sender._get_session_id_from_file()
            result['session_id_file'] = session_id[:8] + '...' if session_id else None
            print(f"session_id.txt: {'存在' if session_id else '不存在或为空'}")

    elif operation == 'test-hooks':
        # 测试hooks处理 (新功能)
        hook_type = sys.argv[2] if len(sys.argv) > 2 else 'Stop'
        print(f"🧪 测试Hook处理: {hook_type}")

        # 模拟hook数据
        mock_hook_data = {
            'hook_event_name': hook_type,
            'session_id': 'test-session-id-12345',
            'timestamp': datetime.now().isoformat(),
            'test_mode': True
        }

        if hook_type == 'Stop':
            result = sender.handle_stop_hook(mock_hook_data)
        elif hook_type == 'SessionStart':
            result = sender.handle_session_start_hook(mock_hook_data)
        else:
            result = {'status': 'error', 'reason': f'不支持的hook类型: {hook_type}'}

        print(f"测试结果: {json.dumps(result, ensure_ascii=False, indent=2)}")

    else:
        result = {
            'status': 'error',
            'message': f'未知操作类型: {operation}',
            'supported_operations': ['send', 'health', 'session-info', 'test-hooks'],
            'usage': [
                'python web_message_sender.py send "Hello World" [target_session]',
                'python web_message_sender.py health',
                'python web_message_sender.py session-info',
                'python web_message_sender.py test-hooks [Stop|SessionStart]',
                'echo \'{"hook_event_name": "Stop", "session_id": "..."}\' | python web_message_sender.py  # hooks'
            ]
        }

    # 简化：删除复杂的verbose输出处理


if __name__ == "__main__":
    main()