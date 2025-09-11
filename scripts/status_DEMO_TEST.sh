#!/bin/bash
# 查询项目状态: DEMO_TEST

PROJECT_ROOT="/Users/flink/parallel-dev-mcp"
PROJECT_ID="DEMO_TEST"
MASTER_SESSION="master_project_DEMO_TEST"

echo "=== DEMO_TEST 项目状态 ==="
echo ""

# 检查tmux会话
echo "活跃会话:"
tmux list-sessions 2>/dev/null | grep "DEMO_TEST" || echo "  无相关会话运行"
echo ""

# 查询MCP系统状态
echo "MCP系统状态:"
cd "$PROJECT_ROOT"
python3 -c "
from src.mcp_server.session_coordinator import SessionCoordinatorMCP
import json
coordinator = SessionCoordinatorMCP('status-check')
result = coordinator.get_child_sessions('$MASTER_SESSION')
data = json.loads(result)
print(f'  子会话数量: {data[\"child_count\"]}')
if data['children']:
    print('  子会话详情:')
    for child in data['children']:
        print(f'    - {child[\"session_name\"]}: {child[\"status\"]} ({child[\"progress\"]}%)')
else:
    print('  暂无活跃子会话')
"
