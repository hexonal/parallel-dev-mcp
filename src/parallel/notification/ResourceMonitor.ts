/**
 * ResourceMonitor - 资源监控器
 *
 * Layer 6: 通知层组件
 * 满足需求：
 * - R6.3: 资源使用监控（CPU/内存/磁盘）
 * - R6.4: 实时日志捕获
 */

import * as os from 'os';
import * as fs from 'fs';
import { execSync } from 'child_process';
import { EventEmitter } from 'events';

/**
 * 资源报告
 */
export interface ResourceReport {
  cpu: number;
  memory: {
    used: number;
    total: number;
    percent: number;
  };
  disk: {
    used: number;
    total: number;
    percent: number;
  };
  timestamp: string;
}

/**
 * 日志条目
 */
export interface LogEntry {
  timestamp: string;
  workerId: string;
  level: 'info' | 'warn' | 'error';
  message: string;
}

/**
 * 资源监控配置
 */
export interface ResourceMonitorConfig {
  logBufferSize?: number;
  captureIntervalMs?: number;
}

/**
 * ResourceMonitor 类
 *
 * 提供 CPU/内存/磁盘监控和实时日志捕获
 */
export class ResourceMonitor extends EventEmitter {
  private logBuffers: Map<string, string[]> = new Map();
  private logBufferSize: number;
  private captureIntervalMs: number;
  private captureTimers: Map<string, NodeJS.Timeout> = new Map();
  private logHandlers: Set<(entry: LogEntry) => void> = new Set();
  private lastCpuInfo: os.CpuInfo[] | null = null;

  constructor(config: ResourceMonitorConfig = {}) {
    super();
    this.logBufferSize = config.logBufferSize || 1000;
    this.captureIntervalMs = config.captureIntervalMs || 5000;
  }

  // ============================================================
  // R6.3: 资源使用监控
  // ============================================================

  /**
   * 获取 CPU 使用率
   *
   * @returns CPU 使用率百分比
   */
  async getCpuUsage(): Promise<number> {
    const cpus = os.cpus();

    if (!this.lastCpuInfo) {
      this.lastCpuInfo = cpus;
      // 第一次调用，等待 100ms 再测量
      await this.delay(100);
      return this.getCpuUsage();
    }

    let totalIdle = 0;
    let totalTick = 0;

    for (let i = 0; i < cpus.length; i++) {
      const cpu = cpus[i];
      const lastCpu = this.lastCpuInfo[i];

      const idle = cpu.times.idle - lastCpu.times.idle;
      const total =
        cpu.times.user -
        lastCpu.times.user +
        (cpu.times.nice - lastCpu.times.nice) +
        (cpu.times.sys - lastCpu.times.sys) +
        (cpu.times.idle - lastCpu.times.idle) +
        (cpu.times.irq - lastCpu.times.irq);

      totalIdle += idle;
      totalTick += total;
    }

    this.lastCpuInfo = cpus;

    const usage = totalTick > 0 ? ((totalTick - totalIdle) / totalTick) * 100 : 0;
    return Math.round(usage * 100) / 100;
  }

  /**
   * 获取内存使用情况
   *
   * @returns 内存使用信息
   */
  async getMemoryUsage(): Promise<{
    used: number;
    total: number;
    percent: number;
  }> {
    const total = os.totalmem();
    const free = os.freemem();
    const used = total - free;
    const percent = (used / total) * 100;

    return {
      used,
      total,
      percent: Math.round(percent * 100) / 100,
    };
  }

  /**
   * 获取磁盘使用情况
   *
   * @param path 检查的路径，默认为当前工作目录
   * @returns 磁盘使用信息
   */
  async getDiskUsage(path?: string): Promise<{
    used: number;
    total: number;
    percent: number;
  }> {
    const targetPath = path || process.cwd();

    try {
      // macOS/Linux: 使用 df 命令
      const output = execSync(`df -k "${targetPath}"`, {
        encoding: 'utf-8',
      });

      const lines = output.trim().split('\n');
      if (lines.length < 2) {
        throw new Error('Failed to parse df output');
      }

      // 解析 df 输出（第二行）
      const parts = lines[1].split(/\s+/);
      const total = parseInt(parts[1], 10) * 1024;
      const used = parseInt(parts[2], 10) * 1024;
      const percent = (used / total) * 100;

      return {
        used,
        total,
        percent: Math.round(percent * 100) / 100,
      };
    } catch {
      // 无法获取磁盘信息时返回默认值
      return {
        used: 0,
        total: 0,
        percent: 0,
      };
    }
  }

  /**
   * 获取综合资源报告
   *
   * @returns 完整的资源报告
   */
  async getResourceReport(): Promise<ResourceReport> {
    const [cpu, memory, disk] = await Promise.all([
      this.getCpuUsage(),
      this.getMemoryUsage(),
      this.getDiskUsage(),
    ]);

    const report: ResourceReport = {
      cpu,
      memory,
      disk,
      timestamp: new Date().toISOString(),
    };

    this.emit('resource_report', report);
    return report;
  }

  // ============================================================
  // R6.4: 实时日志捕获
  // ============================================================

  /**
   * 开始捕获 Worker 日志
   *
   * @param workerId Worker ID
   */
  startLogCapture(workerId: string): void {
    // 初始化日志缓冲区
    if (!this.logBuffers.has(workerId)) {
      this.logBuffers.set(workerId, []);
    }

    // 如果已经在捕获，先停止
    this.stopLogCapture(workerId);

    // 开始定期捕获
    const timer = setInterval(() => {
      this.captureWorkerLogs(workerId);
    }, this.captureIntervalMs);

    this.captureTimers.set(workerId, timer);
    this.emit('log_capture_started', { workerId });
  }

  /**
   * 停止捕获 Worker 日志
   *
   * @param workerId Worker ID
   */
  stopLogCapture(workerId: string): void {
    const timer = this.captureTimers.get(workerId);
    if (timer) {
      clearInterval(timer);
      this.captureTimers.delete(workerId);
      this.emit('log_capture_stopped', { workerId });
    }
  }

  /**
   * 获取最近的日志条目
   *
   * @param workerId Worker ID
   * @param lines 获取的行数
   * @returns 日志行列表
   */
  getRecentLogs(workerId: string, lines: number = 50): string[] {
    const buffer = this.logBuffers.get(workerId) || [];
    return buffer.slice(-lines);
  }

  /**
   * 聚合所有 Worker 的日志
   *
   * @param since 起始时间
   * @returns 日志条目列表
   */
  aggregateLogs(since?: Date): LogEntry[] {
    const entries: LogEntry[] = [];
    const sinceTime = since?.getTime() || 0;

    for (const [workerId, buffer] of this.logBuffers.entries()) {
      for (const line of buffer) {
        const entry = this.parseLogLine(workerId, line);
        if (entry) {
          const entryTime = new Date(entry.timestamp).getTime();
          if (entryTime >= sinceTime) {
            entries.push(entry);
          }
        }
      }
    }

    // 按时间排序
    return entries.sort((a, b) => {
      return new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime();
    });
  }

  /**
   * 注册日志处理器
   *
   * @param handler 日志处理回调
   */
  onLog(handler: (entry: LogEntry) => void): void {
    this.logHandlers.add(handler);
  }

  /**
   * 移除日志处理器
   *
   * @param handler 日志处理回调
   */
  offLog(handler: (entry: LogEntry) => void): void {
    this.logHandlers.delete(handler);
  }

  /**
   * 清理所有日志捕获
   */
  cleanup(): void {
    for (const timer of this.captureTimers.values()) {
      clearInterval(timer);
    }
    this.captureTimers.clear();
    this.logBuffers.clear();
    this.logHandlers.clear();
  }

  // ============================================================
  // 私有方法
  // ============================================================

  /**
   * 从 Tmux 会话捕获 Worker 日志
   */
  private captureWorkerLogs(workerId: string): void {
    try {
      const sessionName = `parallel-dev-${workerId}`;

      // 使用 tmux capture-pane 获取会话输出
      const output = execSync(
        `tmux capture-pane -t ${sessionName} -p -S -100 2>/dev/null || echo ""`,
        { encoding: 'utf-8' }
      );

      if (output.trim()) {
        const lines = output.trim().split('\n');
        this.appendLogs(workerId, lines);
      }
    } catch {
      // Tmux 会话不存在或其他错误，忽略
    }
  }

  /**
   * 追加日志到缓冲区
   */
  private appendLogs(workerId: string, lines: string[]): void {
    let buffer = this.logBuffers.get(workerId);
    if (!buffer) {
      buffer = [];
      this.logBuffers.set(workerId, buffer);
    }

    for (const line of lines) {
      if (!line.trim()) continue;

      buffer.push(line);

      // 环形缓冲区：超出大小时移除旧条目
      while (buffer.length > this.logBufferSize) {
        buffer.shift();
      }

      // 通知日志处理器
      const entry = this.parseLogLine(workerId, line);
      if (entry) {
        this.notifyLogHandlers(entry);
      }
    }
  }

  /**
   * 解析日志行
   */
  private parseLogLine(workerId: string, line: string): LogEntry | null {
    // 尝试提取时间戳和级别
    const timestampMatch = line.match(/\[(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})/);
    const levelMatch = line.match(/\[(info|warn|error)\]/i);

    let level: 'info' | 'warn' | 'error' = 'info';
    if (levelMatch) {
      level = levelMatch[1].toLowerCase() as 'info' | 'warn' | 'error';
    } else if (line.includes('error') || line.includes('Error') || line.includes('ERROR')) {
      level = 'error';
    } else if (line.includes('warn') || line.includes('Warn') || line.includes('WARN')) {
      level = 'warn';
    }

    return {
      timestamp: timestampMatch ? timestampMatch[1] : new Date().toISOString(),
      workerId,
      level,
      message: line,
    };
  }

  /**
   * 通知所有日志处理器
   */
  private notifyLogHandlers(entry: LogEntry): void {
    for (const handler of this.logHandlers) {
      try {
        handler(entry);
      } catch {
        // 忽略处理器错误
      }
    }
    this.emit('log', entry);
  }

  /**
   * 延迟辅助函数
   */
  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}
