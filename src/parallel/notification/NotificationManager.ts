/**
 * NotificationManager - 通知管理器
 *
 * Layer 6: 通知层核心组件
 * 负责任务状态通知和多渠道消息发送
 */

import { execSync } from 'child_process';
import { EventEmitter } from 'events';
import { Task, SchedulerStats } from '../types';

/**
 * 通知渠道类型
 */
export type NotificationChannel = 'terminal' | 'sound' | 'webhook';

/**
 * 通知级别
 */
export type NotificationLevel = 'info' | 'success' | 'warning' | 'error';

/**
 * 通知选项
 */
export interface NotificationOptions {
  title: string;
  message: string;
  level: NotificationLevel;
  channels?: NotificationChannel[];
}

/**
 * Webhook 配置
 */
export interface WebhookConfig {
  url: string;
  headers?: Record<string, string>;
}

/**
 * NotificationManager 类
 *
 * 多渠道通知管理器
 */
export class NotificationManager extends EventEmitter {
  private activeChannels: Set<NotificationChannel>;
  private webhookConfig?: WebhookConfig;

  constructor() {
    super();
    this.activeChannels = new Set(['terminal']);
  }

  /**
   * 发送通知
   *
   * @param options 通知选项
   */
  async notify(options: NotificationOptions): Promise<void> {
    const channels = options.channels || Array.from(this.activeChannels);

    for (const channel of channels) {
      try {
        await this.sendToChannel(channel, options);
      } catch (error) {
        this.emit('error', { channel, error });
      }
    }

    this.emit('notified', { options, channels });
  }

  /**
   * 设置活动通知渠道
   *
   * @param channels 通知渠道列表
   */
  setChannels(channels: NotificationChannel[]): void {
    this.activeChannels = new Set(channels);
    this.emit('channels_changed', { channels });
  }

  /**
   * 配置 Webhook
   *
   * @param config Webhook 配置
   */
  setWebhookConfig(config: WebhookConfig): void {
    this.webhookConfig = config;
  }

  /**
   * 通知任务完成
   *
   * @param task 已完成的任务
   */
  async notifyTaskCompleted(task: Task): Promise<void> {
    await this.notify({
      title: '✅ 任务完成',
      message: `任务 "${task.title}" (${task.id}) 已完成`,
      level: 'success',
    });
  }

  /**
   * 通知任务失败
   *
   * @param task 失败的任务
   * @param error 错误信息
   */
  async notifyTaskFailed(task: Task, error: string): Promise<void> {
    await this.notify({
      title: '❌ 任务失败',
      message: `任务 "${task.title}" (${task.id}) 失败: ${error}`,
      level: 'error',
    });
  }

  /**
   * 通知所有任务完成
   *
   * @param stats 调度器统计信息
   */
  async notifyAllCompleted(stats: SchedulerStats): Promise<void> {
    const hasFailures = stats.failedTasks > 0;
    const level: NotificationLevel = hasFailures ? 'warning' : 'success';
    const icon = hasFailures ? '⚠️' : '🎉';

    await this.notify({
      title: `${icon} 所有任务完成`,
      message: this.formatStatsMessage(stats),
      level,
    });

    // 播放完成提示音
    if (this.activeChannels.has('sound')) {
      this.playSound(hasFailures ? 'error' : 'success');
    }
  }

  /**
   * 发送到指定渠道
   */
  private async sendToChannel(
    channel: NotificationChannel,
    options: NotificationOptions
  ): Promise<void> {
    switch (channel) {
      case 'terminal':
        this.printToTerminal(options);
        break;
      case 'sound':
        this.playSound(options.level === 'error' ? 'error' : 'success');
        break;
      case 'webhook':
        if (this.webhookConfig) {
          await this.sendWebhook(this.webhookConfig.url, options);
        }
        break;
    }
  }

  /**
   * 打印到终端
   */
  private printToTerminal(options: NotificationOptions): void {
    const { title, message, level } = options;
    const prefix = this.getLevelPrefix(level);
    const timestamp = new Date().toLocaleTimeString();

    console.log(`\n${prefix} [${timestamp}] ${title}`);
    console.log(`   ${message}\n`);
  }

  /**
   * 获取级别前缀
   */
  private getLevelPrefix(level: NotificationLevel): string {
    const prefixes: Record<NotificationLevel, string> = {
      info: '📢',
      success: '✅',
      warning: '⚠️',
      error: '❌',
    };
    return prefixes[level];
  }

  /**
   * 播放声音提示
   */
  private playSound(type: 'success' | 'error'): void {
    try {
      // macOS 系统声音
      const sound = type === 'success' ? 'Glass' : 'Basso';
      execSync(`afplay /System/Library/Sounds/${sound}.aiff &`, {
        stdio: 'ignore',
      });
    } catch {
      // 声音播放失败时忽略
    }
  }

  /**
   * 发送 Webhook
   */
  private async sendWebhook(
    url: string,
    payload: NotificationOptions
  ): Promise<void> {
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...this.webhookConfig?.headers,
        },
        body: JSON.stringify({
          ...payload,
          timestamp: new Date().toISOString(),
        }),
      });

      if (!response.ok) {
        throw new Error(`Webhook failed: ${response.status}`);
      }
    } catch (error) {
      this.emit('webhook_error', { url, error });
      throw error;
    }
  }

  /**
   * 格式化统计信息消息
   */
  private formatStatsMessage(stats: SchedulerStats): string {
    const parts: string[] = [];

    parts.push(`总任务: ${stats.totalTasks}`);
    parts.push(`完成: ${stats.completedTasks}`);

    if (stats.failedTasks > 0) {
      parts.push(`失败: ${stats.failedTasks}`);
    }

    return parts.join(' | ');
  }
}
