/**
 * ReportGenerator - 报告生成器
 *
 * Layer 6: 通知层组件
 * 负责生成执行报告（Markdown/JSON 格式）
 */

import * as fs from 'fs/promises';
import * as path from 'path';
import { Task, TaskStatus, Worker } from '../types';
import { SystemState } from '../master/StateManager';

/**
 * 执行报告接口
 */
export interface ExecutionReport {
  summary: {
    totalTasks: number;
    completedTasks: number;
    failedTasks: number;
    duration: string;
    startedAt: string;
    completedAt: string;
  };
  tasks: Array<{
    id: string;
    title: string;
    status: TaskStatus;
    duration?: string;
    worker?: string;
    error?: string;
  }>;
  workers: Array<{
    id: string;
    completedTasks: number;
    failedTasks: number;
  }>;
}

/**
 * 报告格式类型
 */
export type ReportFormat = 'markdown' | 'json';

/**
 * ReportGenerator 类
 *
 * 生成和格式化执行报告
 */
export class ReportGenerator {
  private projectRoot: string;
  private reportsDir: string;

  constructor(projectRoot: string) {
    this.projectRoot = projectRoot;
    this.reportsDir = path.join(projectRoot, '.paralleldev', 'reports');
  }

  /**
   * 生成执行报告
   *
   * @param state 系统状态
   */
  generateReport(state: SystemState): ExecutionReport {
    const completedAt = state.updatedAt || new Date().toISOString();
    const startedAt = state.startedAt || completedAt;

    return {
      summary: this.generateSummary(state, startedAt, completedAt),
      tasks: this.generateTasksReport(state.tasks),
      workers: this.generateWorkersReport(state.workers),
    };
  }

  /**
   * 格式化为 Markdown
   *
   * @param report 执行报告
   */
  formatMarkdown(report: ExecutionReport): string {
    const sections: string[] = [
      this.formatMarkdownHeader(),
      this.formatMarkdownSummary(report.summary),
      this.formatMarkdownTasks(report.tasks),
      this.formatMarkdownFailures(report.tasks),
      this.formatMarkdownWorkers(report.workers),
      this.formatMarkdownFooter(),
    ];

    return sections.filter(Boolean).join('\n');
  }

  /**
   * 格式化 Markdown 标题
   */
  private formatMarkdownHeader(): string {
    return '# ParallelDev 执行报告\n';
  }

  /**
   * 格式化 Markdown 摘要
   */
  private formatMarkdownSummary(summary: ExecutionReport['summary']): string {
    const lines = [
      '## 执行摘要',
      '',
      '| 指标 | 值 |',
      '|------|-----|',
      `| 总任务数 | ${summary.totalTasks} |`,
      `| 完成任务 | ${summary.completedTasks} |`,
      `| 失败任务 | ${summary.failedTasks} |`,
      `| 执行时长 | ${summary.duration} |`,
      `| 开始时间 | ${summary.startedAt} |`,
      `| 完成时间 | ${summary.completedAt} |`,
      '',
    ];
    return lines.join('\n');
  }

  /**
   * 格式化 Markdown 任务列表
   */
  private formatMarkdownTasks(tasks: ExecutionReport['tasks']): string {
    const lines = [
      '## 任务详情',
      '',
      '| ID | 标题 | 状态 | Worker | 耗时 |',
      '|----|------|------|--------|------|',
    ];

    for (const task of tasks) {
      const status = this.getStatusEmoji(task.status);
      const worker = task.worker || '-';
      const duration = task.duration || '-';
      lines.push(`| ${task.id} | ${task.title} | ${status} | ${worker} | ${duration} |`);
    }

    lines.push('');
    return lines.join('\n');
  }

  /**
   * 格式化 Markdown 失败任务详情
   */
  private formatMarkdownFailures(tasks: ExecutionReport['tasks']): string {
    const failedTasks = tasks.filter((t) => t.status === 'failed');

    if (failedTasks.length === 0) {
      return '';
    }

    const lines = ['## 失败任务详情', ''];

    for (const task of failedTasks) {
      lines.push(`### ${task.id}: ${task.title}`, '', '```');
      lines.push(task.error || 'Unknown error');
      lines.push('```', '');
    }

    return lines.join('\n');
  }

  /**
   * 格式化 Markdown Worker 统计
   */
  private formatMarkdownWorkers(workers: ExecutionReport['workers']): string {
    const lines = [
      '## Worker 统计',
      '',
      '| Worker | 完成任务 | 失败任务 |',
      '|--------|----------|----------|',
    ];

    for (const worker of workers) {
      lines.push(`| ${worker.id} | ${worker.completedTasks} | ${worker.failedTasks} |`);
    }

    lines.push('');
    return lines.join('\n');
  }

  /**
   * 格式化 Markdown 页脚
   */
  private formatMarkdownFooter(): string {
    return `---\n*生成时间: ${new Date().toISOString()}*`;
  }

  /**
   * 格式化为 JSON
   *
   * @param report 执行报告
   */
  formatJson(report: ExecutionReport): string {
    return JSON.stringify(report, null, 2);
  }

  /**
   * 保存报告到文件
   *
   * @param report 执行报告
   * @param format 报告格式
   * @returns 保存的文件路径
   */
  async saveReport(
    report: ExecutionReport,
    format: ReportFormat
  ): Promise<string> {
    // 确保目录存在
    await fs.mkdir(this.reportsDir, { recursive: true });

    // 生成文件名
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const extension = format === 'markdown' ? 'md' : 'json';
    const filename = `report-${timestamp}.${extension}`;
    const filePath = path.join(this.reportsDir, filename);

    // 格式化内容
    const content =
      format === 'markdown'
        ? this.formatMarkdown(report)
        : this.formatJson(report);

    // 写入文件
    await fs.writeFile(filePath, content, 'utf-8');

    return filePath;
  }

  /**
   * 生成摘要
   */
  private generateSummary(
    state: SystemState,
    startedAt: string,
    completedAt: string
  ): ExecutionReport['summary'] {
    const tasks = state.tasks;
    const completedTasks = tasks.filter((t) => t.status === 'completed').length;
    const failedTasks = tasks.filter((t) => t.status === 'failed').length;

    return {
      totalTasks: tasks.length,
      completedTasks,
      failedTasks,
      duration: this.calculateDuration(startedAt, completedAt),
      startedAt: this.formatDateTime(startedAt),
      completedAt: this.formatDateTime(completedAt),
    };
  }

  /**
   * 生成任务报告
   */
  private generateTasksReport(tasks: Task[]): ExecutionReport['tasks'] {
    return tasks.map((task) => ({
      id: task.id,
      title: task.title,
      status: task.status,
      duration: this.getTaskDuration(task),
      worker: task.assignedWorker,
      error: task.error,
    }));
  }

  /**
   * 生成 Worker 报告
   */
  private generateWorkersReport(workers: Worker[]): ExecutionReport['workers'] {
    return workers.map((worker) => ({
      id: worker.id,
      completedTasks: worker.completedTasks,
      failedTasks: worker.failedTasks,
    }));
  }

  /**
   * 获取状态 Emoji
   */
  private getStatusEmoji(status: TaskStatus): string {
    const emojis: Record<TaskStatus, string> = {
      pending: '⏳',
      ready: '🔜',
      running: '🔄',
      completed: '✅',
      failed: '❌',
      cancelled: '🚫',
    };
    return emojis[status] || status;
  }

  /**
   * 计算执行时长
   */
  private calculateDuration(startedAt: string, completedAt: string): string {
    const start = new Date(startedAt).getTime();
    const end = new Date(completedAt).getTime();
    const durationMs = end - start;

    if (durationMs < 1000) {
      return `${durationMs}ms`;
    }

    const seconds = Math.floor(durationMs / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);

    if (hours > 0) {
      return `${hours}h ${minutes % 60}m ${seconds % 60}s`;
    }

    if (minutes > 0) {
      return `${minutes}m ${seconds % 60}s`;
    }

    return `${seconds}s`;
  }

  /**
   * 格式化日期时间
   */
  private formatDateTime(isoString: string): string {
    return new Date(isoString).toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  }

  /**
   * 获取任务执行时长
   */
  private getTaskDuration(task: Task): string | undefined {
    if (!task.startedAt || !task.completedAt) {
      return undefined;
    }
    return this.calculateDuration(task.startedAt, task.completedAt);
  }
}
