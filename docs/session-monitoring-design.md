# 会话监控与状态检测机制设计

## 核心问题解决方案

### 问题1: 如何判断子会话是否完成开发？

#### 多层状态检测机制

**1. 心跳检测 (Heartbeat Detection)**
```bash
# 每个子会话必须定期发送心跳
echo "HEARTBEAT:$(date +%s):${session_name}:${task_id}" > /tmp/session-heartbeat/${session_name}.beat

# 主会话监控心跳超时 (超过 10 分钟无心跳视为异常)
./scripts/check-session-heartbeat.sh --timeout=600
```

**2. 状态文件监控**
```python
# 状态文件结构
session_status = {
    "task_id": "AUTH_001",
    "session_name": "dev_session_auth",
    "status": "WORKING|COMPLETED|BLOCKED|ERROR",
    "last_activity": "2025-01-09T10:30:00Z",
    "completion_percentage": 75,
    "current_action": "implementing login endpoint",
    "files_modified": ["auth.py", "models.py"],
    "tests_status": "PASSING|FAILING|NOT_RUN",
    "ready_for_merge": false
}
```

**3. Git 活动监控**
```bash
# 监控 worktree 中的 Git 活动
git -C worktrees/task-${task_id} log --oneline --since="10 minutes ago" --count
git -C worktrees/task-${task_id} status --porcelain | wc -l
```

**4. 进程活动检测**
```bash
# 检测会话中是否有活跃的开发进程
tmux list-panes -t ${session_name} -F "#{pane_current_command}" | grep -E "(vim|code|python|npm|git)"
```

#### 智能状态判断算法

```python
def determine_session_status(session_name: str) -> SessionStatus:
    """
    综合多个指标判断会话状态
    """
    # 1. 检查心跳 (权重: 40%)
    heartbeat_fresh = check_heartbeat_freshness(session_name)
    
    # 2. 检查状态文件 (权重: 30%)
    status_file = read_status_file(session_name)
    
    # 3. 检查Git活动 (权重: 20%)
    git_activity = check_git_activity(session_name)
    
    # 4. 检查进程活动 (权重: 10%)
    process_activity = check_process_activity(session_name)
    
    # 综合判断
    if not heartbeat_fresh:
        return SessionStatus.TIMEOUT
    
    if status_file.status == "COMPLETED" and status_file.ready_for_merge:
        return SessionStatus.READY_FOR_MERGE
    
    if git_activity > 0 or process_activity:
        return SessionStatus.ACTIVE_DEVELOPMENT
    
    if status_file.status == "BLOCKED":
        return SessionStatus.BLOCKED
    
    return SessionStatus.IDLE
```

### 问题2: 如何避免嵌套子会话问题？

#### 权限控制机制

**1. 环境变量控制**
```bash
# 在子会话中设置限制环境变量
export SPLITMIND_SESSION_LEVEL=1
export SPLITMIND_PARENT_SESSION=${parent_session_name}
export SPLITMIND_MAX_NESTING=1

# 检查嵌套级别
if [ "${SPLITMIND_SESSION_LEVEL:-0}" -ge "${SPLITMIND_MAX_NESTING}" ]; then
    echo "错误: 不允许创建嵌套子会话"
    exit 1
fi
```

**2. 会话权限配置文件**
```json
{
    "session_permissions": {
        "master_coordinator": {
            "can_create_sessions": true,
            "can_manage_worktrees": true,
            "can_merge_branches": true,
            "max_child_sessions": 8
        },
        "dev_session": {
            "can_create_sessions": false,
            "can_manage_worktrees": false,
            "can_merge_branches": false,
            "restricted_to_task": true
        }
    }
}
```

**3. 会话创建拦截器**
```python
def create_session_with_permission_check(session_name: str, session_type: str):
    """
    带权限检查的会话创建
    """
    current_level = int(os.environ.get('SPLITMIND_SESSION_LEVEL', 0))
    max_nesting = int(os.environ.get('SPLITMIND_MAX_NESTING', 1))
    
    if current_level >= max_nesting:
        raise PermissionError(f"会话嵌套级别超过限制: {current_level} >= {max_nesting}")
    
    if session_type == "dev_session" and current_level > 0:
        raise PermissionError("开发会话不能创建子会话")
    
    # 创建会话并设置新的环境变量
    new_env = os.environ.copy()
    new_env['SPLITMIND_SESSION_LEVEL'] = str(current_level + 1)
    new_env['SPLITMIND_PARENT_SESSION'] = get_current_session_name()
    
    return create_tmux_session(session_name, env=new_env)
```

### 问题3: 5分钟自动回复与跟踪机制

#### 定时监控系统

**1. 主会话调度器**
```python
import asyncio
from datetime import datetime, timedelta

class SessionMonitor:
    def __init__(self, check_interval=300):  # 5分钟
        self.check_interval = check_interval
        self.sessions = {}
        
    async def start_monitoring(self):
        """开始监控循环"""
        while True:
            await self.check_all_sessions()
            await asyncio.sleep(self.check_interval)
    
    async def check_all_sessions(self):
        """检查所有会话状态"""
        active_sessions = self.get_active_sessions()
        
        for session in active_sessions:
            status = self.determine_session_status(session.name)
            await self.process_session_status(session, status)
    
    async def process_session_status(self, session, status):
        """处理会话状态变化"""
        if status == SessionStatus.READY_FOR_MERGE:
            await self.initiate_merge_process(session)
        elif status == SessionStatus.TIMEOUT:
            await self.handle_session_timeout(session)
        elif status == SessionStatus.BLOCKED:
            await self.escalate_blocked_session(session)
        
        # 记录状态变化日志
        self.log_session_status(session, status)
```

**2. 自动回复机制**
```python
async def send_status_request(session_name: str):
    """向会话发送状态请求"""
    message = {
        "type": "STATUS_REQUEST",
        "timestamp": datetime.now().isoformat(),
        "request_id": generate_request_id(),
        "required_fields": [
            "current_task_progress",
            "blocking_issues", 
            "estimated_completion",
            "files_modified",
            "tests_status"
        ]
    }
    
    # 通过tmux发送消息到指定会话
    await send_tmux_message(session_name, json.dumps(message))
    
    # 等待回复，超时处理
    response = await wait_for_response(session_name, timeout=60)
    return response

async def handle_status_response(session_name: str, response: dict):
    """处理会话的状态回复"""
    # 更新会话状态
    update_session_status(session_name, response)
    
    # 同步到 TaskMaster-AI
    await sync_to_taskmaster(response["task_id"], response)
    
    # 检查是否需要干预
    if response.get("blocking_issues"):
        await escalate_blocking_issues(session_name, response["blocking_issues"])
```

## 集成实现方案

### 状态同步到 TaskMaster-AI

```python
async def sync_session_status_to_taskmaster(session_name: str, status: dict):
    """将会话状态同步到 TaskMaster-AI"""
    taskmaster_api = TaskMasterAPI()
    
    # 转换状态格式
    taskmaster_update = {
        "task_id": status["task_id"],
        "progress_percentage": status["completion_percentage"],
        "status": map_session_status_to_taskmaster(status["status"]),
        "last_update": status["last_activity"],
        "blocking_issues": status.get("blocking_issues", []),
        "estimated_completion": status.get("estimated_completion"),
        "metadata": {
            "session_name": session_name,
            "files_modified": status.get("files_modified", []),
            "tests_status": status.get("tests_status")
        }
    }
    
    await taskmaster_api.update_task_status(taskmaster_update)
```

### 监控仪表板集成

```python
class MonitoringDashboard:
    """实时监控仪表板"""
    
    def __init__(self):
        self.websocket_clients = set()
        
    async def broadcast_session_update(self, session_name: str, status: dict):
        """广播会话状态更新"""
        update_message = {
            "type": "SESSION_UPDATE",
            "session_name": session_name,
            "status": status,
            "timestamp": datetime.now().isoformat()
        }
        
        # 广播到所有连接的客户端
        if self.websocket_clients:
            await asyncio.gather(
                *[client.send(json.dumps(update_message)) 
                  for client in self.websocket_clients]
            )
    
    def get_dashboard_data(self) -> dict:
        """获取仪表板数据"""
        return {
            "active_sessions": len(self.get_active_sessions()),
            "completed_tasks": self.get_completed_tasks_count(),
            "blocked_sessions": self.get_blocked_sessions(),
            "average_completion_time": self.calculate_avg_completion_time(),
            "session_details": [
                self.get_session_summary(session) 
                for session in self.get_all_sessions()
            ]
        }
```

## 安全和容错考虑

### 会话崩溃恢复

```python
async def recover_crashed_sessions():
    """恢复崩溃的会话"""
    # 检查状态文件中标记为活跃但实际不存在的会话
    active_status_files = glob("/tmp/session-status/*.json")
    
    for status_file in active_status_files:
        status = json.load(open(status_file))
        session_name = status["session_name"]
        
        if not tmux_session_exists(session_name):
            # 会话不存在但状态文件显示活跃，需要恢复
            await recover_session(session_name, status)

async def recover_session(session_name: str, last_status: dict):
    """恢复特定会话"""
    task_id = last_status["task_id"]
    worktree_path = f"worktrees/task-{task_id}"
    
    if os.path.exists(worktree_path):
        # Worktree 存在，重新创建会话
        await create_recovery_session(session_name, task_id, worktree_path)
    else:
        # Worktree 不存在，标记任务为需要重新开始
        await mark_task_for_restart(task_id)
```

这个设计解决了您提出的所有核心问题，提供了可靠的会话监控、状态检测和权限控制机制。