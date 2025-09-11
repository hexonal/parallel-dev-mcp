#!/usr/bin/env python3
"""Session Coordinator MCP服务器启动脚本

启动并运行Session Coordinator MCP服务器，提供会话协调服务。
"""

import asyncio
import signal
import sys
import json
import logging
from pathlib import Path
from typing import Any, Dict

from .session_coordinator import SessionCoordinatorMCP


class SessionCoordinatorServer:
    """Session Coordinator服务器管理器"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or "config/session_coordinator_config.json"
        self.config = self._load_config()
        self.coordinator = SessionCoordinatorMCP("session-coordinator")
        self.running = False
        self.cleanup_task = None
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        default_config = {
            "server": {
                "name": "session-coordinator",
                "host": "localhost", 
                "port": 8080,
                "log_level": "INFO"
            },
            "session": {
                "max_message_age_hours": 24,
                "max_messages_per_session": 100,
                "cleanup_interval_minutes": 60,
                "health_check_interval_seconds": 30
            },
            "storage": {
                "state_file": "config/session_state.json",
                "backup_interval_minutes": 60,
                "max_backups": 24
            }
        }
        
        try:
            config_file = Path(self.config_path)
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                
                # 合并配置
                default_config.update(user_config)
                
                print(f"配置已加载: {config_file}")
            else:
                print(f"使用默认配置 (配置文件不存在: {config_file})")
                
                # 创建默认配置文件
                config_file.parent.mkdir(parents=True, exist_ok=True)
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=2, ensure_ascii=False)
                print(f"默认配置已保存到: {config_file}")
                
        except Exception as e:
            print(f"加载配置失败，使用默认配置: {e}")
        
        return default_config
    
    def _setup_logging(self):
        """设置日志"""
        log_level = getattr(logging, self.config["server"]["log_level"], logging.INFO)
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('logs/session_coordinator.log', encoding='utf-8')
            ]
        )
        
        # 创建日志目录
        Path('logs').mkdir(exist_ok=True)
    
    def _setup_signal_handlers(self):
        """设置信号处理"""
        def signal_handler(signum, frame):
            print(f"\\n接收到信号 {signum}，正在关闭服务器...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def _periodic_cleanup(self):
        """定期清理任务"""
        cleanup_interval = self.config["session"]["cleanup_interval_minutes"] * 60
        
        while self.running:
            try:
                await asyncio.sleep(cleanup_interval)
                if self.running:
                    self.coordinator.cleanup_old_data()
                    await self._save_state()
            except Exception as e:
                logging.error(f"定期清理失败: {e}")
    
    async def _save_state(self):
        """保存服务器状态"""
        try:
            state_file = Path(self.config["storage"]["state_file"])
            state_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 创建备份
            if state_file.exists():
                backup_file = state_file.with_suffix(f'.backup.{int(asyncio.get_event_loop().time())}.json')
                state_file.rename(backup_file)
                
                # 清理旧备份
                backup_files = sorted(state_file.parent.glob(f'{state_file.stem}.backup.*.json'))
                max_backups = self.config["storage"]["max_backups"]
                for old_backup in backup_files[:-max_backups]:
                    old_backup.unlink()
            
            # 保存当前状态
            state_data = {
                "relationships": {
                    name: {
                        "parent_session": rel.parent_session,
                        "child_session": rel.child_session,
                        "task_id": rel.task_id,
                        "project_id": rel.project_id,
                        "created_at": rel.created_at.isoformat(),
                        "is_active": rel.is_active
                    }
                    for name, rel in self.coordinator.state.session_relationships.items()
                },
                "active_sessions": {
                    name: status.to_dict()
                    for name, status in self.coordinator.state.active_sessions.items()
                },
                "server_stats": self.coordinator.get_server_stats(),
                "saved_at": asyncio.get_event_loop().time()
            }
            
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
            
            logging.info(f"状态已保存到: {state_file}")
            
        except Exception as e:
            logging.error(f"保存状态失败: {e}")
    
    async def _load_state(self):
        """加载服务器状态"""
        try:
            state_file = Path(self.config["storage"]["state_file"])
            if not state_file.exists():
                logging.info("状态文件不存在，从空状态开始")
                return
            
            with open(state_file, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
            
            # 恢复会话关系 (消息不恢复，避免过多历史数据)
            relationships_count = len(state_data.get("relationships", {}))
            sessions_count = len(state_data.get("active_sessions", {}))
            
            logging.info(f"状态已加载: {relationships_count}个关系, {sessions_count}个会话")
            
        except Exception as e:
            logging.error(f"加载状态失败: {e}")
    
    async def start(self):
        """启动服务器"""
        self._setup_logging()
        self._setup_signal_handlers()
        
        logging.info("正在启动Session Coordinator MCP服务器...")
        
        # 加载历史状态
        await self._load_state()
        
        # 配置协调器参数
        session_config = self.config["session"]
        self.coordinator.max_message_age_hours = session_config["max_message_age_hours"]
        self.coordinator.max_messages_per_session = session_config["max_messages_per_session"]
        
        self.running = True
        
        # 启动定期清理任务
        self.cleanup_task = asyncio.create_task(self._periodic_cleanup())
        
        logging.info("Session Coordinator MCP服务器已启动")
        logging.info(f"配置: {json.dumps(self.config, indent=2, ensure_ascii=False)}")
        
        # 显示MCP工具列表
        tools = [
            "register_session_relationship",
            "report_session_status", 
            "get_child_sessions",
            "query_session_status",
            "send_message_to_session",
            "get_session_messages"
        ]
        logging.info(f"可用MCP工具: {', '.join(tools)}")
        
        try:
            # 主服务循环 (实际的MCP服务器会在这里运行)
            while self.running:
                await asyncio.sleep(1)
                
                # TODO: 这里需要集成实际的MCP服务器运行逻辑
                # 目前只是模拟运行状态
                
        except Exception as e:
            logging.error(f"服务器运行错误: {e}")
        
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """关闭服务器"""
        logging.info("正在关闭Session Coordinator MCP服务器...")
        
        self.running = False
        
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        # 最后一次保存状态
        await self._save_state()
        
        logging.info("Session Coordinator MCP服务器已关闭")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Session Coordinator MCP服务器")
    parser.add_argument(
        "--config", 
        default="config/session_coordinator_config.json",
        help="配置文件路径"
    )
    parser.add_argument(
        "--test-mode",
        action="store_true", 
        help="测试模式，显示工具信息后退出"
    )
    
    args = parser.parse_args()
    
    if args.test_mode:
        # 测试模式：显示服务器信息
        print("Session Coordinator MCP服务器")
        print("=" * 50)
        
        coordinator = SessionCoordinatorMCP()
        print(f"服务器名称: {coordinator.server.name}")
        
        tools = [
            ("register_session_relationship", "注册主子会话关系"),
            ("report_session_status", "子会话状态上报"),
            ("get_child_sessions", "获取子会话列表"),
            ("query_session_status", "查询会话状态"),
            ("send_message_to_session", "发送会话消息"),
            ("get_session_messages", "获取会话消息")
        ]
        
        print("\\n可用MCP工具:")
        for tool_name, description in tools:
            print(f"  - {tool_name}: {description}")
        
        return
    
    # 正常启动模式
    server = SessionCoordinatorServer(args.config)
    
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\\n服务器已停止")
    except Exception as e:
        print(f"服务器启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()