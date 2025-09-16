#!/usr/bin/env python3
"""
智能会话识别脚本 - 基于tmux会话名称的自动识别系统
支持统一命名规范: parallel_{PROJECT_ID}_task_*

核心优势:
1. 零环境变量依赖 - 完全基于tmux会话名称
2. 自动会话发现 - 动态识别主会话和子会话
3. 智能通信路由 - 自动建立主子会话通信
4. 配置简化 - 单一脚本处理所有会话类型
"""
import os
import subprocess
import json
import re
import sys
from datetime import datetime
from typing import Optional, Dict, List, Tuple


class SmartSessionDetector:
    """智能会话检测器"""
    
    def __init__(self):
        self.current_session = self._get_current_session_name()
        self.session_info = self._parse_session_name(self.current_session) if self.current_session else None
    
    def _get_current_session_name(self) -> Optional[str]:
        """获取当前tmux会话名称"""
        try:
            # 从TMUX环境变量获取会话信息
            tmux_info = os.environ.get('TMUX', '')
            if not tmux_info:
                return None
            
            # TMUX格式: /tmp/tmux-xxx/default,xxx,x
            session_info = tmux_info.split(',')[1] if ',' in tmux_info else None
            if not session_info:
                return None
            
            # 获取实际会话名称
            result = subprocess.run([
                'tmux', 'display-message', '-p', '#{session_name}'
            ], capture_output=True, text=True)
            
            return result.stdout.strip() if result.returncode == 0 else None
            
        except Exception:
            return None
    
    def _parse_session_name(self, session_name: str) -> Optional[Dict[str, str]]:
        """解析会话名称，提取项目信息"""
        if not session_name:
            return None
        
        # 匹配主会话: parallel_{PROJECT_ID}_task_master
        master_pattern = r'^parallel_(.+)_task_master$'
        master_match = re.match(master_pattern, session_name)
        if master_match:
            return {
                'session_name': session_name,
                'session_type': 'master',
                'project_id': master_match.group(1),
                'task_id': None
            }
        
        # 匹配子会话: parallel_{PROJECT_ID}_task_child_{TASK_ID}
        child_pattern = r'^parallel_(.+)_task_child_(.+)$'
        child_match = re.match(child_pattern, session_name)
        if child_match:
            return {
                'session_name': session_name,
                'session_type': 'child',
                'project_id': child_match.group(1),
                'task_id': child_match.group(2)
            }
        
        return None
    
    def _find_master_session(self, project_id: str) -> Optional[str]:
        """查找指定项目的主会话"""
        try:
            result = subprocess.run([
                'tmux', 'list-sessions', '-F', '#{session_name}'
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                return None
            
            expected_master = f"parallel_{project_id}_task_master"
            for session in result.stdout.strip().split('\n'):
                if session.strip() == expected_master:
                    return session.strip()
            
            return None
            
        except Exception:
            return None
    
    def _find_child_sessions(self, project_id: str) -> List[Dict[str, str]]:
        """查找指定项目的所有子会话"""
        try:
            result = subprocess.run([
                'tmux', 'list-sessions', '-F', '#{session_name}'
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                return []
            
            child_prefix = f"parallel_{project_id}_task_child_"
            child_sessions = []
            
            for session in result.stdout.strip().split('\n'):
                session = session.strip()
                if session.startswith(child_prefix):
                    task_id = session.replace(child_prefix, '')
                    child_sessions.append({
                        'session_name': session,
                        'task_id': task_id,
                        'project_id': project_id
                    })
            
            return child_sessions
            
        except Exception:
            return []
    
    def _send_message_to_session(self, target_session: str, message: str) -> bool:
        """发送消息到指定会话"""
        try:
            # 发送显示消息
            subprocess.run([
                'tmux', 'send-keys', '-t', target_session,
                f'echo "{message}"', 'Enter'
            ], check=False)
            return True
        except Exception:
            return False
    
    def _session_exists(self, session_name: str) -> bool:
        """检查tmux会话是否存在"""
        try:
            result = subprocess.run([
                'tmux', 'list-sessions', '-F', '#{session_name}'
            ], capture_output=True, text=True)

            if result.returncode != 0:
                return False

            sessions = result.stdout.strip().split('\n')
            return session_name in [s.strip() for s in sessions if s.strip()]

        except Exception:
            return False

    def _send_claude_notification(self, target_session: str, notification_type: str, data: dict) -> bool:
        """发送Claude Code可识别的通知消息"""
        try:
            # Claude Code会话中的通知格式
            # 这些消息会被Claude Code识别并处理
            notification_message = f"""
🔔 MCP通知 [{notification_type}]
📋 会话: {target_session}
📊 数据: {json.dumps(data, ensure_ascii=False, indent=2)}
⏰ 时间: {datetime.now().strftime('%H:%M:%S')}
"""
            
            subprocess.run([
                'tmux', 'send-keys', '-t', target_session,
                f'echo "{notification_message.strip()}"', 'Enter'
            ], check=False)
            
            return True
        except Exception:
            return False
    
    def handle_session_start(self) -> Dict[str, any]:
        """处理会话启动事件"""
        if not self.session_info:
            return {
                'status': 'ignored',
                'reason': '非parallel-dev-mcp会话'
            }
        
        session_type = self.session_info['session_type']
        project_id = self.session_info['project_id']
        
        if session_type == 'master':
            return self._handle_master_start(project_id)
        elif session_type == 'child':
            return self._handle_child_start(project_id, self.session_info['task_id'])
    
    def _handle_master_start(self, project_id: str) -> Dict[str, any]:
        """处理主会话启动"""
        print(f"🎯 Master会话启动: 项目 {project_id}")
        
        # 查找所有子会话
        child_sessions = self._find_child_sessions(project_id)
        
        if child_sessions:
            print(f"📋 发现 {len(child_sessions)} 个子会话:")
            for child in child_sessions:
                print(f"  - {child['task_id']}: {child['session_name']}")
        else:
            print(f"📋 暂无子会话，等待任务会话启动")
        
        return {
            'status': 'success',
            'session_type': 'master',
            'project_id': project_id,
            'child_sessions_found': len(child_sessions)
        }
    
    def _handle_child_start(self, project_id: str, task_id: str) -> Dict[str, any]:
        """处理子会话启动"""
        print(f"🔧 Child会话启动: 项目 {project_id} - 任务 {task_id}")
        
        # 查找主会话并注册
        master_session = self._find_master_session(project_id)
        if master_session:
            # 发送结构化通知到主会话
            notification_data = {
                'session_name': self.current_session,
                'task_id': task_id,
                'project_id': project_id,
                'action': 'child_session_started',
                'timestamp': datetime.now().isoformat()
            }
            
            success = self._send_claude_notification(
                master_session,
                'SESSION_REGISTERED',
                notification_data
            )
            
            if success:
                print(f"✅ 已注册到主会话: {master_session}")
            else:
                print(f"❌ 向主会话注册失败")
                
            return {
                'status': 'success',
                'session_type': 'child',
                'project_id': project_id,
                'task_id': task_id,
                'master_session': master_session,
                'registered': success
            }
        else:
            print(f"⚠️  未找到主会话: parallel_{project_id}_task_master")
            return {
                'status': 'warning',
                'session_type': 'child',
                'project_id': project_id,
                'task_id': task_id,
                'master_session': None,
                'registered': False
            }
    
    def handle_task_progress(self) -> Dict[str, any]:
        """处理任务进度汇报（Stop事件）"""
        if not self.session_info or self.session_info['session_type'] != 'child':
            return {'status': 'ignored', 'reason': '仅子会话汇报进度'}
        
        project_id = self.session_info['project_id']
        task_id = self.session_info['task_id']
        
        master_session = self._find_master_session(project_id)
        if not master_session:
            return {
                'status': 'failed',
                'reason': f'未找到主会话: parallel_{project_id}_task_master'
            }
        
        # 构建进度消息
        progress_message = json.dumps({
            'type': 'task_progress',
            'session': self.current_session,
            'task': task_id,
            'project': project_id,
            'timestamp': datetime.now().isoformat()
        })
        
        success = self._send_message_to_session(
            master_session,
            f"📈 任务进度: {progress_message}"
        )
        
        return {
            'status': 'success' if success else 'failed',
            'session_type': 'child',
            'project_id': project_id,
            'task_id': task_id,
            'master_session': master_session,
            'message_sent': success
        }
    
    def handle_post_tool_use(self, tool_name: str = "unknown") -> Dict[str, any]:
        """处理工具使用后的事件 - 子会话向主会话汇报进度"""
        if not self.session_info:
            return {'status': 'skip', 'reason': '未能识别会话信息'}
        
        session_type = self.session_info.get('session_type')
        project_id = self.session_info.get('project_id')
        task_id = self.session_info.get('task_id')
        
        # 只有子会话才需要汇报进度
        if session_type != 'child':
            return {
                'status': 'skip', 
                'reason': f'{session_type}会话无需汇报工具使用进度'
            }
        
        # 构建进度消息
        progress_message = f"🔧 Task {task_id}: 完成 {tool_name} 操作"
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # 查找主会话
        master_session_name = f"parallel_{project_id}_task_master"
        if not self._session_exists(master_session_name):
            return {
                'status': 'warning',
                'message': f'主会话不存在: {master_session_name}',
                'tool_name': tool_name
            }
        
        # 发送进度消息到主会话
        message_result = self._send_message_to_session(
            master_session_name, 
            f"[{timestamp}] {progress_message}"
        )
        
        return {
            'status': 'success',
            'action': 'post_tool_use_report',
            'session_type': session_type,
            'project_id': project_id,
            'task_id': task_id,
            'tool_name': tool_name,
            'progress_message': progress_message,
            'master_session': master_session_name,
            'message_sent': message_result
        }

    def handle_session_complete(self) -> Dict[str, any]:
        """处理会话完成（SessionEnd事件）"""
        if not self.session_info:
            return {'status': 'ignored', 'reason': '非parallel-dev-mcp会话'}
        
        session_type = self.session_info['session_type']
        project_id = self.session_info['project_id']
        
        if session_type == 'master':
            print(f"🎯 Master会话结束: 项目 {project_id}")
            return {
                'status': 'success',
                'session_type': 'master',
                'project_id': project_id
            }
        
        # 子会话完成，通知主会话
        task_id = self.session_info['task_id']
        master_session = self._find_master_session(project_id)
        
        if master_session:
            completion_message = json.dumps({
                'type': 'session_completed',
                'session': self.current_session,
                'task': task_id,
                'project': project_id,
                'status': 'completed',
                'timestamp': datetime.now().isoformat()
            })
            
            success = self._send_message_to_session(
                master_session,
                f"✅ 会话完成: {completion_message}"
            )
            
            print(f"✅ 已向主会话汇报完成: {master_session}" if success else "❌ 汇报完成失败")
            
            return {
                'status': 'success',
                'session_type': 'child',
                'project_id': project_id,
                'task_id': task_id,
                'master_session': master_session,
                'completion_reported': success
            }
        else:
            print(f"⚠️  未找到主会话进行完成汇报")
            return {
                'status': 'warning',
                'session_type': 'child',
                'project_id': project_id,
                'task_id': task_id,
                'master_session': None,
                'completion_reported': False
            }
    
    def handle_user_prompt(self, prompt: str = "") -> Dict[str, any]:
        """处理用户提示事件"""
        if not self.session_info:
            return {'status': 'ignored', 'reason': '非parallel-dev-mcp会话'}
        
        session_type = self.session_info['session_type']
        project_id = self.session_info['project_id']
        prompt_length = len(prompt) if prompt else 0
        
        if session_type == 'master':
            print(f"🎯 Master会话 [{project_id}]: 处理提示 - {prompt_length}字符")
        else:
            task_id = self.session_info['task_id']
            print(f"⚡ Child会话 [{project_id}:{task_id}]: 处理提示 - {prompt_length}字符")
        
        return {
            'status': 'success',
            'session_type': session_type,
            'project_id': project_id,
            'task_id': self.session_info.get('task_id'),
            'prompt_length': prompt_length
        }
    
    def get_session_info(self) -> Dict[str, any]:
        """获取当前会话信息"""
        if not self.session_info:
            return {
                'detected': False,
                'current_session': self.current_session,
                'reason': '未检测到parallel-dev-mcp会话格式'
            }
        
        info = {
            'detected': True,
            'current_session': self.current_session,
            **self.session_info
        }
        
        # 添加相关会话信息
        project_id = self.session_info['project_id']
        
        if self.session_info['session_type'] == 'master':
            info['child_sessions'] = self._find_child_sessions(project_id)
        else:
            info['master_session'] = self._find_master_session(project_id)
        
        return info


def main():
    """主执行函数 - 支持多种事件类型"""
    detector = SmartSessionDetector()
    
    # 从命令行参数获取事件类型
    event_type = sys.argv[1] if len(sys.argv) > 1 else 'info'
    
    if event_type == 'session-start':
        result = detector.handle_session_start()
    elif event_type == 'post-tool-use':
        tool_name = sys.argv[2] if len(sys.argv) > 2 else "unknown"
        result = detector.handle_post_tool_use(tool_name)
    elif event_type == 'stop':
        result = detector.handle_task_progress()
    elif event_type == 'session-end':
        result = detector.handle_session_complete()
    elif event_type == 'user-prompt':
        prompt = sys.argv[2] if len(sys.argv) > 2 else ""
        result = detector.handle_user_prompt(prompt)
    elif event_type == 'info':
        result = detector.get_session_info()
    else:
        result = {
            'status': 'error',
            'message': f'未知事件类型: {event_type}',
            'supported_events': ['session-start', 'post-tool-use', 'stop', 'session-end', 'user-prompt', 'info']
        }
    
    # 输出结果（可选）
    if '-v' in sys.argv or '--verbose' in sys.argv:
        print(f"\n[DEBUG] 事件处理结果:")
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()