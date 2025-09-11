#!/usr/bin/env python3
"""标准MCP协议服务器实现

为Claude Code提供标准MCP协议兼容的Session Coordinator服务器
"""

import asyncio
import json
import sys
from typing import Any, Dict, List, Optional
import logging

from .session_coordinator import SessionCoordinatorMCP

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MCPServer:
    """标准MCP协议服务器"""
    
    def __init__(self):
        self.coordinator = SessionCoordinatorMCP("session-coordinator-mcp")
        
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理MCP请求"""
        try:
            method = request.get("method")
            params = request.get("params", {})
            request_id = request.get("id")
            
            logger.info(f"处理MCP请求: {method}")
            
            if method == "initialize":
                return await self.handle_initialize(request_id, params)
            elif method == "tools/list":
                return await self.handle_tools_list(request_id)
            elif method == "tools/call":
                return await self.handle_tools_call(request_id, params)
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
                
        except Exception as e:
            logger.error(f"处理请求时出错: {e}", exc_info=True)
            return {
                "jsonrpc": "2.0", 
                "id": request.get("id"),
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def handle_initialize(self, request_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理初始化请求"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {
                        "listChanged": True
                    }
                },
                "serverInfo": {
                    "name": "session-coordinator",
                    "version": "1.0.0"
                }
            }
        }
    
    async def handle_tools_list(self, request_id: str) -> Dict[str, Any]:
        """处理工具列表请求"""
        tools = [
            {
                "name": "register_session_relationship",
                "description": "注册主子会话关系",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "parent_session": {"type": "string", "description": "主会话名称"},
                        "child_session": {"type": "string", "description": "子会话名称"},
                        "task_id": {"type": "string", "description": "任务ID"},
                        "project_id": {"type": "string", "description": "项目ID"}
                    },
                    "required": ["parent_session", "child_session", "task_id", "project_id"]
                }
            },
            {
                "name": "report_session_status",
                "description": "子会话状态上报",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "session_name": {"type": "string", "description": "会话名称"},
                        "status": {"type": "string", "description": "状态"},
                        "progress": {"type": "number", "description": "进度(0-100)"},
                        "details": {"type": "string", "description": "详细信息", "default": ""}
                    },
                    "required": ["session_name", "status", "progress"]
                }
            },
            {
                "name": "get_child_sessions", 
                "description": "获取子会话列表",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "parent_session": {"type": "string", "description": "主会话名称"}
                    },
                    "required": ["parent_session"]
                }
            },
            {
                "name": "query_session_status",
                "description": "查询会话状态",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "session_name": {"type": "string", "description": "会话名称", "default": ""}
                    }
                }
            },
            {
                "name": "send_message_to_session",
                "description": "发送会话消息",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "from_session": {"type": "string", "description": "发送方会话"},
                        "to_session": {"type": "string", "description": "接收方会话"},
                        "message": {"type": "string", "description": "消息内容"},
                        "message_type": {"type": "string", "description": "消息类型", "default": "INSTRUCTION"}
                    },
                    "required": ["from_session", "to_session", "message"]
                }
            },
            {
                "name": "get_session_messages",
                "description": "获取会话消息",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "session_name": {"type": "string", "description": "会话名称"}
                    },
                    "required": ["session_name"]
                }
            }
        ]
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": tools
            }
        }
    
    async def handle_tools_call(self, request_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理工具调用请求"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        logger.info(f"调用工具: {tool_name}, 参数: {arguments}")
        
        try:
            if tool_name == "register_session_relationship":
                result = self.coordinator.register_session_relationship(
                    parent_session=arguments["parent_session"],
                    child_session=arguments["child_session"],
                    task_id=arguments["task_id"],
                    project_id=arguments["project_id"]
                )
            elif tool_name == "report_session_status":
                result = self.coordinator.report_session_status(
                    session_name=arguments["session_name"],
                    status=arguments["status"],
                    progress=arguments["progress"],
                    details=arguments.get("details", "")
                )
            elif tool_name == "get_child_sessions":
                result = self.coordinator.get_child_sessions(
                    parent_session=arguments["parent_session"]
                )
            elif tool_name == "query_session_status":
                session_name = arguments.get("session_name", "")
                result = self.coordinator.query_session_status(session_name if session_name else None)
            elif tool_name == "send_message_to_session":
                result = self.coordinator.send_message_to_session(
                    from_session=arguments["from_session"],
                    to_session=arguments["to_session"],
                    message=arguments["message"],
                    message_type=arguments.get("message_type", "INSTRUCTION")
                )
            elif tool_name == "get_session_messages":
                result = self.coordinator.get_session_messages(
                    session_name=arguments["session_name"]
                )
            else:
                raise ValueError(f"Unknown tool: {tool_name}")
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": str(result)
                        }
                    ]
                }
            }
            
        except Exception as e:
            logger.error(f"工具调用出错 {tool_name}: {e}", exc_info=True)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": f"Tool execution error: {str(e)}"
                }
            }


async def main():
    """主函数"""
    server = MCPServer()
    
    logger.info("Session Coordinator MCP服务器启动")
    logger.info("等待来自Claude Code的MCP请求...")
    
    try:
        while True:
            # 读取来自stdin的JSON-RPC请求
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            
            if not line:
                break
                
            line = line.strip()
            if not line:
                continue
                
            try:
                request = json.loads(line)
                response = await server.handle_request(request)
                
                # 输出JSON-RPC响应到stdout
                print(json.dumps(response), flush=True)
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析错误: {e}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": "Parse error"
                    }
                }
                print(json.dumps(error_response), flush=True)
                
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭服务器...")
    except Exception as e:
        logger.error(f"服务器运行出错: {e}", exc_info=True)
    finally:
        logger.info("Session Coordinator MCP服务器已关闭")


if __name__ == "__main__":
    asyncio.run(main())