#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Web消息发送脚本

@description Claude Code SessionEnd Hook调用的简单脚本
用于向Flask服务报告会话结束事件
"""

import sys
import os
import subprocess
import requests
from datetime import datetime


def get_tmux_session_name():
    """
    获取当前tmux会话名称

    Returns:
        str: 会话名称，如果不在tmux中返回None
    """
    # 检查是否在tmux环境中
    tmux_env = os.environ.get('TMUX')
    if not tmux_env:
        return None

    try:
        # 使用tmux命令获取当前会话名称
        result = subprocess.run(
            ['tmux', 'display-message', '-p', '#{session_name}'],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass

    return None


def send_session_end_message(web_port, project_prefix):
    """
    发送会话结束消息到Flask服务

    Args:
        web_port: Flask服务端口
        project_prefix: 项目前缀
    """
    # 1. 获取tmux会话名称
    session_name = get_tmux_session_name()

    if not session_name:
        # 不在tmux中，不做任何操作
        return

    # 2. 判断是master还是child
    master_session = f"{project_prefix}_master"
    is_master = (session_name == master_session)
    is_child = session_name.startswith(f"{project_prefix}_child_")

    if not (is_master or is_child):
        # 不是我们管理的会话，不做操作
        return

    # 3. 构建请求数据
    url = f"http://localhost:{web_port}"
    payload = {
        "session_name": session_name,
        "timestamp": datetime.now().isoformat(),
        "event": "SessionEnd"
    }

    # 4. 发送到对应端点
    try:
        if is_master:
            # Master会话结束，调用 /msg/send
            endpoint = f"{url}/msg/send"
            payload["type"] = "master"

            # 如果session_id.txt为空，写入session_id
            session_id_file = "session_id.txt"
            if os.path.exists(session_id_file):
                with open(session_id_file, 'r') as f:
                    content = f.read().strip()
                if not content:
                    # 写入新的session_id
                    session_id = f"master_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    with open(session_id_file, 'w') as f:
                        f.write(session_id)
                    payload["session_id"] = session_id
        else:
            # Child会话结束，调用 /msg/send-child
            endpoint = f"{url}/msg/send-child"
            payload["type"] = "child"
            # 提取task_id
            task_id = session_name.replace(f"{project_prefix}_child_", "")
            payload["task_id"] = task_id

        # 5. 发送POST请求
        response = requests.post(
            endpoint,
            json=payload,
            timeout=5
        )

        if response.status_code != 200:
            print(f"Warning: Flask returned {response.status_code}", file=sys.stderr)

    except requests.exceptions.ConnectionError:
        # Flask服务未运行，静默失败
        pass
    except Exception as e:
        # 其他错误，静默失败
        print(f"Error: {e}", file=sys.stderr)


def main():
    """
    主函数

    使用方式: python web_message_sender.py {WEB_PORT} {PROJECT_PREFIX}
    """
    if len(sys.argv) != 3:
        print("Usage: python web_message_sender.py {WEB_PORT} {PROJECT_PREFIX}", file=sys.stderr)
        sys.exit(1)

    try:
        web_port = int(sys.argv[1])
        project_prefix = sys.argv[2]

        send_session_end_message(web_port, project_prefix)

    except ValueError:
        print("Error: WEB_PORT must be a number", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()