#!/usr/bin/env python3
"""
Tmux Web服务 - 简化版
核心功能：为web_message_sender.py提供HTTP接口
"""

import os
import sys
import json
import logging
from flask import Flask, request, jsonify
from datetime import datetime
from typing import Dict, Any
from collections import deque
import time

# 独立实现tmux消息发送，不依赖其他服务
import subprocess

app = Flask(__name__)

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 全局调用频率跟踪器
class CallFrequencyTracker:
    """调用频率跟踪器 - 检测短时间内的高频调用"""

    def __init__(self, window_seconds=20, threshold=2):
        self.window_seconds = window_seconds  # 时间窗口（秒）
        self.threshold = threshold            # 阈值（次数）
        self.call_times = deque()            # 调用时间戳队列

    def record_call(self):
        """记录一次调用"""
        current_time = time.time()
        self.call_times.append(current_time)

        # 清理超出时间窗口的记录
        cutoff_time = current_time - self.window_seconds
        while self.call_times and self.call_times[0] < cutoff_time:
            self.call_times.popleft()

        logger.debug(f"📊 调用频率记录: {len(self.call_times)} 次调用在过去 {self.window_seconds} 秒内")

    def should_trigger_auto_message(self):
        """检查是否应该触发自动消息"""
        result = len(self.call_times) > self.threshold
        if result:
            logger.info(f"🚨 检测到高频调用: {len(self.call_times)} 次在 {self.window_seconds} 秒内 (阈值: {self.threshold})")
        return result

    def reset(self):
        """重置跟踪器"""
        self.call_times.clear()
        logger.debug("🔄 调用频率跟踪器已重置")

# 全局频率跟踪器实例
frequency_tracker = CallFrequencyTracker(window_seconds=20, threshold=2)

# 会话绑定管理
class SessionManager:
    """会话绑定管理器"""

    @staticmethod
    def get_binding_file():
        """获取绑定文件路径"""
        return os.path.join(os.path.dirname(__file__), 'session_binding.txt')

    @staticmethod
    def get_bound_session():
        """获取已绑定的session_id"""
        try:
            binding_file = SessionManager.get_binding_file()
            logger.debug(f"🔍 检查绑定文件: {binding_file}")

            if os.path.exists(binding_file):
                with open(binding_file, 'r') as f:
                    content = f.read().strip()
                    if content:
                        logger.debug(f"📖 读取到绑定会话: {content}")
                        return content
                    else:
                        logger.debug(f"📄 绑定文件为空")
                        return None
            else:
                logger.debug(f"❌ 绑定文件不存在")
                return None
        except Exception as e:
            logger.error(f"Error reading session binding: {e}")
            return None

    @staticmethod
    def bind_session(session_id):
        """绑定session_id到文件"""
        try:
            binding_file = SessionManager.get_binding_file()
            with open(binding_file, 'w') as f:
                f.write(session_id)
            logger.info(f"Session bound: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error binding session: {e}")
            return False

    @staticmethod
    def is_session_bound():
        """检查是否已有绑定的会话"""
        bound_session = SessionManager.get_bound_session()
        is_bound = bound_session is not None and bound_session != ""
        logger.info(f"🔗 会话绑定状态检查: {'已绑定' if is_bound else '未绑定'} (session: {bound_session})")
        return is_bound

# 核心tmux操作类
class DemoTmuxSender:
    """简化的tmux操作类"""

    # 简化：删除list_sessions，非核心功能

    @staticmethod
    def session_exists(session_name):
        """检查会话是否存在"""
        # 简化：直接尝试发送消息检测会话存在性
        try:
            result = subprocess.run(['tmux', 'has-session', '-t', session_name],
                                  capture_output=True, text=True)
            return result.returncode == 0
        except Exception:
            return False

    @staticmethod
    def send_message(session_name, custom_message=None):
        """发送消息到指定tmux会话

        Args:
            session_name: 目标tmux会话名称
            custom_message: 自定义消息内容，如果为None则从send.txt读取
        """
        try:
            # 检查会话是否存在
            if not DemoTmuxSender.session_exists(session_name):
                logger.warning(f"Session '{session_name}' does not exist")
                return False

            # 获取消息内容
            if custom_message:
                message_content = custom_message
                logger.info(f"📤 使用自定义消息: {message_content}")
            else:
                # 读取send.txt文件内容
                send_file_path = os.path.join(os.path.dirname(__file__), 'send.txt')
                if not os.path.exists(send_file_path):
                    logger.error(f"Send file not found: {send_file_path}")
                    return False

                with open(send_file_path, 'r', encoding='utf-8') as f:
                    message_content = f.read().strip()
                logger.info(f"📄 从文件读取消息: {message_content[:50]}...")

            # 分两步发送：1. 发送消息内容，2. 发送回车
            # 步骤1：发送消息内容
            cmd1 = ['tmux', 'send-keys', '-t', session_name, message_content]
            result1 = subprocess.run(cmd1, capture_output=True, text=True, check=True)

            # 步骤2：发送回车
            cmd2 = ['tmux', 'send-keys', '-t', session_name, 'Enter']
            result2 = subprocess.run(cmd2, capture_output=True, text=True, check=True)

            logger.info(f"Message sent to session '{session_name}': {message_content[:50]}...")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to send message to session '{session_name}': {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False

    @staticmethod
    def send_auto_hi_message(session_name):
        """发送自动 'hi' 消息到指定会话"""
        return DemoTmuxSender.send_message(session_name, custom_message="hi")

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    return jsonify({
        'status': 'healthy',
        'service': 'tmux-web-service',
        'timestamp': datetime.now().isoformat()
    }), 200

# Demo简化：移除复杂的会话绑定功能，只保留核心消息发送

@app.route('/message/send', methods=['POST'])
def send_message():
    """发送消息端点"""
    try:
        # 记录调用频率
        frequency_tracker.record_call()

        data = request.get_json()
        logger.info("json信息是：",data)
        if not data:
            return jsonify({
                'success': False,
                'error': 'Missing request body'
            }), 400

        # 提取消息内容
        message = data.get('message', '')
        if not message:
            return jsonify({
                'success': False,
                'error': 'Missing message content'
            }), 400

        # 尝试解析消息中的JSON数据，获取session_id和hook_event_name
        current_session_id = None
        hook_event_name = None
        try:
            # 如果消息是JSON格式，尝试解析
            if message.strip().startswith('{'):
                parsed_msg = json.loads(message)
                current_session_id = parsed_msg.get('session_id')
                hook_event_name = parsed_msg.get('hook_event_name')
        except:
            # 如果不是JSON，使用传统方式获取session_id
            current_session_id = data.get('session_id')

        # 详细的会话信息日志
        logger.info(f"📨 收到消息 - 事件: {hook_event_name}, 会话ID: {current_session_id}")

        # SessionStart自动注册逻辑
        if hook_event_name == 'SessionStart':
            logger.info(f"🚀 检测到SessionStart事件")
            if not SessionManager.is_session_bound() and current_session_id:
                # 第一次SessionStart且session_binding.txt为空，自动注册
                logger.info(f"🔄 开始自动注册会话: {current_session_id}")
                SessionManager.bind_session(current_session_id)
                logger.info(f"🔗 自动注册会话成功: {current_session_id}")
            elif SessionManager.is_session_bound():
                logger.info(f"⚠️ 已有绑定会话，跳过注册")
            elif not current_session_id:
                logger.warning(f"⚠️ SessionStart事件缺少session_id")

        # 只有SessionEnd事件才发送消息
        if hook_event_name != 'Stop':
            logger.info(f"📋 非Stop事件 ({hook_event_name})，跳过发送消息")
            return jsonify({
                'success': True,
                'message': f'Event {hook_event_name} received but not processed (only SessionEnd triggers message sending)',
                'hook_event_name': hook_event_name
            }), 200

        # 会话过滤和日志输出
        bound_session = SessionManager.get_bound_session()
        logger.info(f"🔍 会话匹配检查 - 绑定: {bound_session}, 当前: {current_session_id}")

        if bound_session:
            if current_session_id == bound_session:
                logger.info(f"✅ 本会话 SessionEnd {current_session_id} -> 准备发送消息")
            else:
                logger.info(f"❌ 非本会话 (期望: {bound_session}, 实际: {current_session_id}) -> 跳过发送")
                # 非本会话的消息直接返回成功但不处理
                return jsonify({
                    'success': True,
                    'message': 'Message from different session, ignored',
                    'session_filter': f'Expected: {bound_session}, Got: {current_session_id}'
                }), 200
        else:
            logger.info(f"ℹ️ 无绑定会话，处理SessionEnd事件")

        # SessionEnd事件：读取send.txt并发送到指定会话
        target_session = data.get('target_session', 'test-v1')
        success = DemoTmuxSender.send_message(target_session)

        # 检查是否需要发送自动 'hi' 消息（由于compact阶段问题的优化）
        auto_hi_sent = False
        if frequency_tracker.should_trigger_auto_message():
            logger.info(f"🤖 触发自动 'hi' 消息发送 - 由于compact阶段出现的问题")
            auto_hi_success = DemoTmuxSender.send_auto_hi_message(target_session)
            if auto_hi_success:
                logger.info(f"✅ 自动 'hi' 消息已发送到 {target_session}")
                auto_hi_sent = True
                # 重置频率跟踪器以避免重复触发
                frequency_tracker.reset()
            else:
                logger.error(f"❌ 自动 'hi' 消息发送失败到 {target_session}")

        if success:
            response_data = {
                'success': True,
                'message': f'Successfully sent message to {target_session}',
                'target_session': target_session,
                'session_id': current_session_id
            }

            # 如果发送了自动hi消息，在响应中标记
            if auto_hi_sent:
                response_data['auto_hi_sent'] = True
                response_data['auto_hi_reason'] = 'High frequency calls detected - compact phase optimization'

            return jsonify(response_data), 200
        else:
            return jsonify({
                'success': False,
                'error': f'Failed to send message to {target_session}'
            }), 500

    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Demo简化：移除notify端点，通知功能通过message/send实现

# 简化：删除/session/list端点，非核心功能

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500

def main():
    """主函数 - 启动Flask web服务"""
    import argparse

    parser = argparse.ArgumentParser(description='Tmux消息发送Web服务')
    parser.add_argument('--host', default='localhost', help='服务器主机地址')
    parser.add_argument('--port', type=int, default=5500, help='服务器端口')
    parser.add_argument('--debug', action='store_true', help='开启调试模式')

    args = parser.parse_args()

    logger.info(f"启动Tmux Web服务，地址: http://{args.host}:{args.port}")
    logger.info("核心端点:")
    logger.info("  GET  /health - 健康检查")
    logger.info("  POST /message/send - 发送消息")

    try:
        app.run(host=args.host, port=args.port, debug=args.debug)
    except KeyboardInterrupt:
        logger.info("服务已停止")
    except Exception as e:
        logger.error(f"服务启动失败: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()