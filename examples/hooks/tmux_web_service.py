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
import re
import threading
from datetime import timedelta

# 独立实现tmux消息发送，不依赖其他服务
import subprocess

app = Flask(__name__)

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 全局调用频率跟踪器
class CallFrequencyTracker:
    """SessionEnd事件频率跟踪器 - 检测compact阶段的高频调用问题

    注意：只记录SessionEnd事件的频率，不记录自动消息或其他事件类型
    目的是检测Claude Code compact阶段可能导致的短时间内重复SessionEnd调用
    """

    def __init__(self, window_seconds=30, threshold=1):
        self.window_seconds = window_seconds  # 时间窗口（秒）
        self.threshold = threshold            # 阈值（次数）
        self.call_times = deque()            # 调用时间戳队列

    def record_call(self):
        """记录一次调用 - 仅用于SessionEnd事件的频率检测"""
        current_time = time.time()
        self.call_times.append(current_time)

        # 清理超出时间窗口的记录
        cutoff_time = current_time - self.window_seconds
        expired_count = 0
        while self.call_times and self.call_times[0] < cutoff_time:
            self.call_times.popleft()
            expired_count += 1

        if expired_count > 0:
            logger.debug(f"🧹 清理了 {expired_count} 个过期的频率记录")

        logger.info(f"📊 SessionEnd频率记录: {len(self.call_times)} 次调用在过去 {self.window_seconds} 秒内 (阈值: {self.threshold}, 考虑10秒消息延迟)")

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
# 消息发送时间成本分析：
# - 每次消息发送：~12秒（发送内容 + 10秒等待 + 发送回车）
# - SessionEnd + 自动hi：~24秒（两次完整发送）
#
# 参数设计合理性：
# - window_seconds=30: 覆盖完整的SessionEnd+自动hi周期(~24秒)
# - threshold=1: 30秒内2次SessionEnd = 异常高频，触发自动hi
# - 自动hi使用custom_message参数，不会再次触发频率统计
# - 发送hi后重置跟踪器，避免循环触发
frequency_tracker = CallFrequencyTracker(window_seconds=30, threshold=1)

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
    def send_message(session_name, custom_message=None, skip_limit_check: bool = False):
        """发送消息到指定tmux会话

        Args:
            session_name: 目标tmux会话名称
            custom_message: 自定义消息内容，如果为None则从send.txt读取
        """
        try:
            # 发送消息前检查是否命中速率限制
            if not skip_limit_check:
                try:
                    pane_text = DemoTmuxSender.capture_pane(session_name)
                    reset_dt = DemoTmuxSender.parse_reset_time(pane_text) if pane_text else None
                    if reset_dt:
                        # 命中限制：计划一个定时任务，届时发送“继续执行”的命令
                        DemoTmuxSender.schedule_continue_message(session_name, reset_dt)
                        logger.warning(
                            f"⛔ 检测到 5-hour limit，已计划在 {reset_dt.isoformat()} 发送继续命令，当前消息不立即发送"
                        )
                        return True
                except Exception as _e:
                    logger.warning(f"检查速率限制时出现问题，忽略并继续发送: {_e}")

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
            logger.info(f"🔧 执行步骤1: 发送消息内容到 {session_name}")
            cmd1 = ['tmux', 'send-keys', '-t', session_name, message_content]
            logger.info(f"🔧 命令1: {' '.join(cmd1)}")
            try:
                result1 = subprocess.run(cmd1, capture_output=True, text=True, check=True)
                logger.info(f"✅ 步骤1完成: 消息内容已发送")
                if result1.stderr:
                    logger.warning(f"⚠️ 步骤1 stderr: {result1.stderr}")
            except subprocess.CalledProcessError as e:
                logger.error(f"❌ 步骤1失败: {e}")
                logger.error(f"❌ 步骤1 stdout: {e.stdout}")
                logger.error(f"❌ 步骤1 stderr: {e.stderr}")
                return False

            # 等待10秒后再发送回车键 - tmux需要处理时间
            logger.info(f"⏳ 等待10秒后发送回车键 - tmux需要处理时间")
            for i in range(10, 0, -1):
                logger.info(f"⏳ 倒计时 {i} 秒...")
                time.sleep(1)
            logger.info(f"✅ 等待完成，准备发送回车键")

            # 步骤2：发送回车 (不记录频率)
            logger.info(f"🔧 执行步骤2: 发送回车键到 {session_name}")
            cmd2 = ['tmux', 'send-keys', '-t', session_name, 'Enter']
            logger.info(f"🔧 命令2: {' '.join(cmd2)}")
            try:
                result2 = subprocess.run(cmd2, capture_output=True, text=True, check=True)
                logger.info(f"✅ 步骤2完成: 回车键已发送")
                if result2.stderr:
                    logger.warning(f"⚠️ 步骤2 stderr: {result2.stderr}")
            except subprocess.CalledProcessError as e:
                logger.error(f"❌ 步骤2失败: {e}")
                logger.error(f"❌ 步骤2 stdout: {e.stdout}")
                logger.error(f"❌ 步骤2 stderr: {e.stderr}")
                return False

            logger.info(f"✅ 完整消息发送完成到 '{session_name}': {message_content[:50]}...")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to send message to session '{session_name}': {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False

    @staticmethod
    def send_auto_hi_message(session_name):
        """发送自动 'hi' 消息到指定会话

        注意：这是自动消息，不应该触发频率统计
        """
        return DemoTmuxSender.send_message(session_name, custom_message="hi")

    # =============== Limit Handling Utilities ===============
    @staticmethod
    def capture_pane(session_name: str) -> str:
        """获取指定会话当前活动窗格文本内容"""
        try:
            result = subprocess.run(
                ['tmux', 'capture-pane', '-p', '-t', session_name],
                capture_output=True, text=True, check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            logger.warning(f"capture-pane 失败: {e}")
            return ""

    @staticmethod
    def parse_reset_time(pane_text: str):
        """从pane文本中解析 '5-hour limit reached ∙ resets <time>' 的时间

        返回本地时区的下一次可发送的 datetime，如果未找到返回None
        """
        if not pane_text:
            return None

        # 匹配例如: 5-hour limit reached ∙ resets 1pm / 12:30am / 9:05PM 等
        m = re.search(r"5-hour\s+limit\s+reached.*?resets\s+([0-9]{1,2}(?::[0-9]{2})?\s*[ap]m)",
                      pane_text, flags=re.IGNORECASE | re.DOTALL)
        if not m:
            return None

        time_str = m.group(1).strip().lower().replace(" ", "")
        # 尝试解析时间
        parsed = None
        for fmt in ("%I%p", "%I:%M%p"):
            try:
                parsed = datetime.strptime(time_str, fmt)
                break
            except ValueError:
                continue
        if not parsed:
            return None

        now = datetime.now()
        candidate = now.replace(hour=parsed.hour, minute=parsed.minute, second=0, microsecond=0)
        if candidate <= now:
            candidate = candidate + timedelta(days=1)
        return candidate

    @staticmethod
    def schedule_continue_message(session_name: str, when_dt: datetime):
        """在指定时间发送继续执行的命令（读取 send-v2.txt）"""
        delay = max(0.0, (when_dt - datetime.now()).total_seconds())

        def _job():
            try:
                # 读取 send-v2.txt 作为继续命令
                send2_path = os.path.join(os.path.dirname(__file__), 'send.txt')
                if os.path.exists(send2_path):
                    with open(send2_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                else:
                    content = "continue"
                logger.info(f"⏰ 触发继续命令发送 -> {session_name}")
                DemoTmuxSender.send_message(session_name, custom_message=content, skip_limit_check=True)
            except Exception as e:
                logger.error(f"计划的继续命令发送失败: {e}")

        logger.info(f"🗓️ 计划在 {when_dt.isoformat()} 发送继续命令 (延迟 {int(delay)}s)")
        timer = threading.Timer(delay, _job)
        timer.daemon = True
        timer.start()

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
        data = request.get_json()
        # 正确打印完整JSON内容（支持中文、不截断）
        try:
            logger.info("json信息是：\n%s", json.dumps(data, ensure_ascii=False, indent=2))
        except Exception:
            logger.info(f"json信息是：{data}")
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
            logger.info(f"📊 非Stop事件不记录频率 - 只有SessionEnd事件才可能触发高频调用检测")
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

        # SessionEnd事件：在发送前检查是否命中限流
        target_session = data.get('target_session', 'test-v2')

        try:
            pane_text = DemoTmuxSender.capture_pane(target_session)
            reset_dt = DemoTmuxSender.parse_reset_time(pane_text) if pane_text else None
            if reset_dt:
                DemoTmuxSender.schedule_continue_message(target_session, reset_dt)
                logger.info(f"⛔ 命中速率限制，已计划在 {reset_dt.isoformat()} 发送继续命令，当前请求不立即发送")
                return jsonify({
                    'success': True,
                    'scheduled': True,
                    'scheduled_time': reset_dt.isoformat(),
                    'reason': '5-hour limit reached; will send continue command at reset time',
                    'target_session': target_session,
                    'session_id': current_session_id
                }), 200
        except Exception as _e:
            logger.warning(f"发送前的速率限制检查失败，忽略并继续尝试发送: {_e}")

        # 发送消息 - 只有真实的SessionEnd消息内容才记录频率
        logger.info("📊 SessionEnd事件：发送真实消息内容（从send.txt读取）")
        success = DemoTmuxSender.send_message(target_session)

        # 记录频率 - 只对真实消息内容记录，排除自动hi和回车键
        if success:
            logger.info("📊 记录真实消息内容发送频率（排除自动hi和回车键）")
            frequency_tracker.record_call()

        # 检查是否需要发送自动 'hi' 消息（由于compact阶段问题的优化）
        auto_hi_sent = False
        if frequency_tracker.should_trigger_auto_message():
            logger.info(f"🤖 触发自动 'hi' 消息发送 - 由于compact阶段出现的问题")
            logger.info(f"📝 自动'hi'消息使用custom_message参数，完全跳过频率统计")
            logger.info(f"⏳ 注意：hi消息也需要10秒延迟发送回车，总耗时~12秒")
            auto_hi_success = DemoTmuxSender.send_auto_hi_message(target_session)
            if auto_hi_success:
                logger.info(f"✅ 自动 'hi' 消息已发送到 {target_session} (耗时~12秒，未记录频率)")
                auto_hi_sent = True
                # 重置频率跟踪器以避免重复触发
                frequency_tracker.reset()
                logger.info(f"🔄 频率跟踪器已重置")
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
    parser.add_argument('--port', type=int, default=5501, help='服务器端口')
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
