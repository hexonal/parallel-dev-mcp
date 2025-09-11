"""
Status Monitor - Clean system health monitoring

Focused on health checks and system diagnostics.
No mixing with operational concerns.
"""

import subprocess
import json
from typing import Dict, Any, List
from datetime import datetime
from .session_registry import SessionRegistry


def calculate_session_health_score(session_dict: Dict[str, Any]) -> float:
    """计算会话健康分数"""
    score = 1.0
    
    # 检查活动时间
    try:
        last_activity = datetime.fromisoformat(session_dict.get("last_activity", ""))
        hours_since_activity = (datetime.now() - last_activity).total_seconds() / 3600
        if hours_since_activity > 24:
            score -= 0.3
        elif hours_since_activity > 6:
            score -= 0.1
    except:
        score -= 0.2
    
    # 检查消息数量
    message_count = session_dict.get("message_count", 0)
    if message_count == 0:
        score -= 0.1
    
    return max(0.0, score)


class StatusMonitor:
    """状态监控器 - 纯监控逻辑"""
    
    def __init__(self, registry: SessionRegistry):
        self.registry = registry
    
    def get_system_health(self) -> Dict[str, Any]:
        """获取系统整体健康状态"""
        try:
            session_health = self._check_session_health()
            tmux_health = self._check_tmux_health()
            registry_health = self._check_registry_health()
            
            overall_score = self._calculate_overall_health(session_health, tmux_health, registry_health)
            
            return {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "overall_health_score": overall_score,
                "overall_status": self._get_status_from_score(overall_score),
                "components": {
                    "sessions": session_health,
                    "tmux": tmux_health,
                    "registry": registry_health
                },
                "recommendations": self._generate_health_recommendations(overall_score, session_health, tmux_health, registry_health)
            }
            
        except Exception as e:
            return {"success": False, "error": f"Health check failed: {str(e)}"}
    
    def get_detailed_session_status(self, session_name: str = None) -> Dict[str, Any]:
        """获取详细会话状态"""
        try:
            if session_name:
                # 单个会话状态
                session_info = self.registry.get_session_info(session_name)
                if not session_info:
                    return {"success": False, "error": f"会话不存在: {session_name}"}
                
                session_dict = session_info.to_dict()
                session_dict["health_score"] = calculate_session_health_score(session_dict)
                session_dict["tmux_info"] = self._get_tmux_session_info(session_name)
                
                return {"success": True, "session": session_dict}
            else:
                # 所有会话状态
                all_sessions = self.registry.list_all_sessions()
                session_statuses = {}
                
                for name, info in all_sessions.items():
                    session_dict = info.to_dict()
                    session_dict["health_score"] = calculate_session_health_score(session_dict)
                    session_dict["tmux_info"] = self._get_tmux_session_info(name)
                    session_statuses[name] = session_dict
                
                return {
                    "success": True,
                    "total_sessions": len(session_statuses),
                    "sessions": session_statuses,
                    "summary": self._generate_session_summary(session_statuses)
                }
                
        except Exception as e:
            return {"success": False, "error": f"Get session status failed: {str(e)}"}
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        try:
            registry_stats = self.registry.get_registry_stats()
            tmux_stats = self._get_tmux_performance_stats()
            
            return {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "registry_metrics": registry_stats,
                "tmux_metrics": tmux_stats,
                "system_metrics": self._get_system_performance_metrics()
            }
            
        except Exception as e:
            return {"success": False, "error": f"Performance metrics failed: {str(e)}"}
    
    def run_diagnostic_checks(self) -> Dict[str, Any]:
        """运行诊断检查"""
        try:
            checks = []
            
            # 检查1: tmux可用性
            checks.append(self._check_tmux_availability())
            
            # 检查2: 会话一致性
            checks.append(self._check_session_consistency())
            
            # 检查3: 消息队列健康
            checks.append(self._check_message_queue_health())
            
            # 检查4: 文件系统权限
            checks.append(self._check_filesystem_permissions())
            
            # 检查5: 内存使用
            checks.append(self._check_memory_usage())
            
            passed_checks = sum(1 for check in checks if check["status"] == "pass")
            total_checks = len(checks)
            
            return {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "checks_passed": passed_checks,
                "total_checks": total_checks,
                "pass_rate": passed_checks / total_checks if total_checks > 0 else 0,
                "overall_status": "healthy" if passed_checks == total_checks else "issues_detected",
                "diagnostic_results": checks
            }
            
        except Exception as e:
            return {"success": False, "error": f"Diagnostic checks failed: {str(e)}"}
    
    # === 私有辅助方法 ===
    
    def _check_session_health(self) -> Dict[str, Any]:
        """检查会话健康状态"""
        all_sessions = self.registry.list_all_sessions()
        
        if not all_sessions:
            return {"status": "no_sessions", "score": 1.0, "session_count": 0}
        
        health_scores = []
        for session_info in all_sessions.values():
            session_dict = session_info.to_dict()
            score = calculate_session_health_score(session_dict)
            health_scores.append(score)
        
        avg_health = sum(health_scores) / len(health_scores)
        
        return {
            "status": "healthy" if avg_health > 0.8 else "degraded" if avg_health > 0.5 else "unhealthy",
            "score": avg_health,
            "session_count": len(all_sessions),
            "healthy_sessions": sum(1 for score in health_scores if score > 0.8)
        }
    
    def _check_tmux_health(self) -> Dict[str, Any]:
        """检查tmux健康状态"""
        try:
            # 检查tmux是否运行
            result = subprocess.run(['tmux', 'list-sessions'], capture_output=True, text=True)
            tmux_available = result.returncode == 0
            
            if not tmux_available:
                return {"status": "unavailable", "score": 0.0, "error": "tmux not running"}
            
            # 统计会话数量
            session_count = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
            
            return {
                "status": "healthy",
                "score": 1.0,
                "session_count": session_count,
                "tmux_version": self._get_tmux_version()
            }
            
        except Exception as e:
            return {"status": "error", "score": 0.0, "error": str(e)}
    
    def _check_registry_health(self) -> Dict[str, Any]:
        """检查注册中心健康状态"""
        try:
            stats = self.registry.get_registry_stats()
            
            # 检查数据一致性
            total_sessions = stats["total_sessions"]
            total_relationships = stats["total_relationships"]
            
            # 简单的健康评分
            if total_sessions == 0:
                score = 1.0  # 无会话是正常状态
            else:
                # 评估关系数据的合理性
                relationship_ratio = total_relationships / total_sessions
                score = min(1.0, 0.5 + relationship_ratio * 0.5)
            
            return {
                "status": "healthy" if score > 0.8 else "degraded",
                "score": score,
                "registry_stats": stats
            }
            
        except Exception as e:
            return {"status": "error", "score": 0.0, "error": str(e)}
    
    def _calculate_overall_health(self, session_health, tmux_health, registry_health) -> float:
        """计算整体健康分数"""
        weights = {"sessions": 0.4, "tmux": 0.4, "registry": 0.2}
        
        total_score = (
            session_health["score"] * weights["sessions"] +
            tmux_health["score"] * weights["tmux"] +
            registry_health["score"] * weights["registry"]
        )
        
        return total_score
    
    def _get_status_from_score(self, score: float) -> str:
        """从分数获取状态描述"""
        if score > 0.9:
            return "excellent"
        elif score > 0.8:
            return "healthy"
        elif score > 0.6:
            return "degraded"
        elif score > 0.3:
            return "unhealthy"
        else:
            return "critical"
    
    def _generate_health_recommendations(self, overall_score, session_health, tmux_health, registry_health) -> List[str]:
        """生成健康建议"""
        recommendations = []
        
        if overall_score < 0.8:
            if session_health["score"] < 0.7:
                recommendations.append("检查会话活动状态，清理非活跃会话")
            
            if tmux_health["score"] < 0.7:
                recommendations.append("检查tmux服务状态，确保正常运行")
            
            if registry_health["score"] < 0.7:
                recommendations.append("检查注册中心数据一致性")
        
        if not recommendations:
            recommendations.append("系统运行正常，无需特殊关注")
        
        return recommendations
    
    def _get_tmux_session_info(self, session_name: str) -> Dict[str, Any]:
        """获取tmux会话信息"""
        try:
            result = subprocess.run(
                ['tmux', 'display-message', '-t', session_name, '-p', '#{session_windows}:#{session_attached}'],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                parts = result.stdout.strip().split(':')
                return {
                    "exists": True,
                    "windows": int(parts[0]) if parts[0] else 0,
                    "attached": parts[1] == '1' if len(parts) > 1 else False
                }
            else:
                return {"exists": False}
                
        except Exception:
            return {"exists": False, "error": "Check failed"}
    
    def _generate_session_summary(self, session_statuses: Dict[str, Dict]) -> Dict[str, Any]:
        """生成会话摘要"""
        if not session_statuses:
            return {"healthy_count": 0, "total_count": 0, "avg_health_score": 0.0}
        
        health_scores = [s["health_score"] for s in session_statuses.values()]
        healthy_count = sum(1 for score in health_scores if score > 0.8)
        
        return {
            "healthy_count": healthy_count,
            "total_count": len(session_statuses),
            "avg_health_score": sum(health_scores) / len(health_scores),
            "health_ratio": healthy_count / len(session_statuses)
        }
    
    def _get_tmux_performance_stats(self) -> Dict[str, Any]:
        """获取tmux性能统计"""
        try:
            result = subprocess.run(['tmux', 'list-sessions', '-F', '#{session_name}'], 
                                  capture_output=True, text=True)
            
            session_count = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
            
            return {
                "active_sessions": session_count,
                "tmux_responsive": result.returncode == 0
            }
            
        except Exception:
            return {"active_sessions": 0, "tmux_responsive": False}
    
    def _get_system_performance_metrics(self) -> Dict[str, Any]:
        """获取系统性能指标"""
        try:
            import psutil
            
            return {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage_percent": psutil.disk_usage('/').percent
            }
        except ImportError:
            return {"note": "psutil not available for system metrics"}
        except Exception as e:
            return {"error": f"System metrics failed: {str(e)}"}
    
    def _get_tmux_version(self) -> str:
        """获取tmux版本"""
        try:
            result = subprocess.run(['tmux', '-V'], capture_output=True, text=True)
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except Exception:
            return "unknown"
    
    # === 诊断检查方法 ===
    
    def _check_tmux_availability(self) -> Dict[str, Any]:
        """诊断检查: tmux可用性"""
        try:
            result = subprocess.run(['tmux', '-V'], capture_output=True, text=True)
            return {
                "name": "tmux_availability",
                "status": "pass" if result.returncode == 0 else "fail",
                "message": f"tmux version: {result.stdout.strip()}" if result.returncode == 0 else "tmux not available",
                "details": {"returncode": result.returncode}
            }
        except Exception as e:
            return {
                "name": "tmux_availability",
                "status": "fail",
                "message": f"tmux check failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    def _check_session_consistency(self) -> Dict[str, Any]:
        """诊断检查: 会话一致性"""
        try:
            registry_sessions = set(self.registry.list_all_sessions().keys())
            
            # 获取tmux会话
            result = subprocess.run(['tmux', 'list-sessions', '-F', '#{session_name}'], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                tmux_sessions = set(result.stdout.strip().split('\n')) if result.stdout.strip() else set()
            else:
                tmux_sessions = set()
            
            # 检查一致性
            only_in_registry = registry_sessions - tmux_sessions
            only_in_tmux = tmux_sessions - registry_sessions
            
            consistent = len(only_in_registry) == 0 and len(only_in_tmux) == 0
            
            return {
                "name": "session_consistency",
                "status": "pass" if consistent else "fail",
                "message": "Sessions consistent" if consistent else f"Inconsistencies found: {len(only_in_registry)} registry-only, {len(only_in_tmux)} tmux-only",
                "details": {
                    "registry_sessions": len(registry_sessions),
                    "tmux_sessions": len(tmux_sessions),
                    "only_in_registry": list(only_in_registry),
                    "only_in_tmux": list(only_in_tmux)
                }
            }
            
        except Exception as e:
            return {
                "name": "session_consistency",
                "status": "fail",
                "message": f"Consistency check failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    def _check_message_queue_health(self) -> Dict[str, Any]:
        """诊断检查: 消息队列健康"""
        try:
            stats = self.registry.get_registry_stats()
            total_messages = stats["total_messages"]
            
            # 简单的健康检查
            if total_messages > 10000:
                status = "fail"
                message = f"Too many messages ({total_messages}), consider cleanup"
            else:
                status = "pass"
                message = f"Message queue healthy ({total_messages} messages)"
            
            return {
                "name": "message_queue_health",
                "status": status,
                "message": message,
                "details": stats
            }
            
        except Exception as e:
            return {
                "name": "message_queue_health",
                "status": "fail",
                "message": f"Message queue check failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    def _check_filesystem_permissions(self) -> Dict[str, Any]:
        """诊断检查: 文件系统权限"""
        try:
            from pathlib import Path
            
            # 检查关键目录的读写权限
            test_paths = [Path("projects"), Path("projects/.test_write")]
            
            issues = []
            
            for path in test_paths:
                if path.name == ".test_write":
                    # 测试写权限
                    try:
                        path.parent.mkdir(exist_ok=True)
                        path.write_text("test")
                        path.unlink()
                    except Exception as e:
                        issues.append(f"Write permission issue in {path.parent}: {str(e)}")
                else:
                    # 检查目录存在和读权限
                    if not path.exists():
                        try:
                            path.mkdir(exist_ok=True)
                        except Exception as e:
                            issues.append(f"Cannot create directory {path}: {str(e)}")
            
            return {
                "name": "filesystem_permissions",
                "status": "pass" if not issues else "fail",
                "message": "Filesystem permissions OK" if not issues else f"Permission issues: {'; '.join(issues)}",
                "details": {"checked_paths": [str(p) for p in test_paths], "issues": issues}
            }
            
        except Exception as e:
            return {
                "name": "filesystem_permissions",
                "status": "fail",
                "message": f"Filesystem check failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    def _check_memory_usage(self) -> Dict[str, Any]:
        """诊断检查: 内存使用"""
        try:
            import sys
            
            # 获取当前进程内存使用
            try:
                import psutil
                process = psutil.Process()
                memory_mb = process.memory_info().rss / 1024 / 1024
                
                status = "pass" if memory_mb < 500 else "fail"  # 500MB阈值
                message = f"Memory usage: {memory_mb:.1f}MB"
                
                details = {
                    "memory_mb": memory_mb,
                    "threshold_mb": 500,
                    "within_limit": memory_mb < 500
                }
                
            except ImportError:
                # psutil不可用，使用基本检查
                status = "pass"
                message = "Memory check skipped (psutil not available)"
                details = {"psutil_available": False}
            
            return {
                "name": "memory_usage",
                "status": status,
                "message": message,
                "details": details
            }
            
        except Exception as e:
            return {
                "name": "memory_usage",
                "status": "fail",
                "message": f"Memory check failed: {str(e)}",
                "details": {"error": str(e)}
            }