/**
 * 任务 AI 服务
 * 提供 PRD 解析、任务展开等 AI 功能
 * @module tm-core/services/task-ai.service
 */

import * as fs from 'fs';
import * as path from 'path';
import { AIService, getAIService } from '../ai';
import type { AIConfig, AIResponse } from '../ai/types';
import { getLogger } from '../common/logger';
import type { Task, Subtask } from '../common/types';
import {
  parsePrdPrompt,
  expandTaskPrompt,
  type ParsePrdParams,
  type ExpandTaskParams
} from '../prompts';
import {
  ParsePRDResponseSchema,
  ExpandTaskResponseSchema
} from '../schemas';
import { FileStorage } from '../storage';

const logger = getLogger('TaskAIService');

/**
 * PRD 解析选项
 */
export interface ParsePRDOptions {
  /** 目标任务数量 */
  numTasks?: number;
  /** 是否使用研究模式 */
  research?: boolean;
  /** 默认任务优先级 */
  defaultPriority?: 'high' | 'medium' | 'low';
  /** 是否追加到现有任务 */
  append?: boolean;
  /** 是否强制覆盖 */
  force?: boolean;
  /** 标签 */
  tag?: string;
}

/**
 * 任务展开选项
 */
export interface ExpandTaskOptions {
  /** 子任务数量 */
  numSubtasks?: number;
  /** 是否使用研究模式 */
  research?: boolean;
  /** 附加上下文 */
  additionalContext?: string;
  /** 是否强制覆盖现有子任务 */
  force?: boolean;
  /** 标签 */
  tag?: string;
}

/**
 * 任务 AI 服务类
 */
export class TaskAIService {
  private projectRoot: string;
  private aiService: AIService;
  private storage: FileStorage;

  constructor(projectRoot: string, aiConfig?: Partial<AIConfig>) {
    this.projectRoot = projectRoot;
    this.aiService = getAIService(aiConfig);
    this.storage = new FileStorage(projectRoot);
  }

  /**
   * 检查 AI 服务是否可用
   */
  isAvailable(): boolean {
    return this.aiService.isAvailable();
  }

  /**
   * 解析 PRD 文件生成任务
   * @param prdPath PRD 文件路径
   * @param options 选项
   * @returns 生成的任务数组
   */
  async parsePRD(
    prdPath: string,
    options: ParsePRDOptions = {}
  ): Promise<AIResponse<Task[]>> {
    const {
      numTasks = 10,
      research = false,
      defaultPriority = 'medium',
      append = false,
      force = false,
      tag
    } = options;

    logger.info(`Parsing PRD: ${prdPath}`);

    // 读取 PRD 内容
    const fullPath = path.isAbsolute(prdPath)
      ? prdPath
      : path.join(this.projectRoot, prdPath);

    if (!fs.existsSync(fullPath)) {
      throw new Error(`PRD file not found: ${fullPath}`);
    }

    const prdContent = fs.readFileSync(fullPath, 'utf-8');

    // 获取现有任务以确定起始 ID
    let existingTasks: Task[] = [];
    let nextId = 1;

    try {
      existingTasks = await this.storage.loadTasks(tag);
      if (existingTasks.length > 0) {
        const maxId = Math.max(...existingTasks.map((t) => Number(t.id)));
        nextId = maxId + 1;
      }
    } catch {
      // 如果没有现有任务，从 1 开始
    }

    // 检查是否需要强制覆盖
    if (existingTasks.length > 0 && !append && !force) {
      throw new Error(
        'Tasks already exist. Use --append to add to existing tasks, or --force to overwrite.'
      );
    }

    // 如果是覆盖模式，重置 nextId
    if (force && !append) {
      nextId = 1;
      existingTasks = [];
    }

    // 构建 prompt 参数
    const promptParams: ParsePrdParams = {
      numTasks,
      nextId,
      prdContent,
      prdPath,
      research,
      defaultTaskPriority: defaultPriority,
      projectRoot: this.projectRoot
    };

    // 生成 prompts
    const systemPrompt = parsePrdPrompt.getSystemPrompt(promptParams);
    const userPrompt = parsePrdPrompt.getUserPrompt(promptParams);

    // 调用 AI 生成任务
    const response = await this.aiService.generateObject({
      systemPrompt,
      userPrompt,
      schema: ParsePRDResponseSchema,
      options: {
        temperature: 0.7,
        maxTokens: 8192
      }
    });

    // 处理生成的任务
    const generatedTasks = response.result.tasks.map((task) => ({
      id: String(task.id),
      title: task.title,
      description: task.description,
      status: (task.status || 'pending') as Task['status'],
      priority: (task.priority || defaultPriority) as Task['priority'],
      dependencies: (task.dependencies || []).map(String),
      subtasks: [],
      details: task.details || '',
      testStrategy: task.testStrategy || '',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    }));

    // 合并任务
    const finalTasks = append
      ? [...existingTasks, ...generatedTasks]
      : generatedTasks;

    // 保存到文件
    await this.storage.saveTasks(finalTasks, tag);

    logger.info(`Generated ${generatedTasks.length} tasks`);

    return {
      result: generatedTasks,
      usage: response.usage,
      model: response.model,
      provider: response.provider,
      duration: response.duration
    };
  }

  /**
   * 展开任务为子任务
   * @param taskId 任务 ID
   * @param options 选项
   * @returns 展开后的任务
   */
  async expandTask(
    taskId: string,
    options: ExpandTaskOptions = {}
  ): Promise<AIResponse<Task>> {
    const {
      numSubtasks = 5,
      research = false,
      additionalContext = '',
      force = false,
      tag
    } = options;

    logger.info(`Expanding task: ${taskId}`);

    // 加载任务
    const tasks = await this.storage.loadTasks(tag);
    const task = tasks.find((t) => t.id === taskId);

    if (!task) {
      throw new Error(`Task not found: ${taskId}`);
    }

    // 检查是否已有子任务
    if (task.subtasks && task.subtasks.length > 0 && !force) {
      throw new Error(
        `Task ${taskId} already has ${task.subtasks.length} subtasks. Use --force to replace.`
      );
    }

    // 如果强制覆盖，清空现有子任务
    if (force) {
      task.subtasks = [];
    }

    // 计算下一个子任务 ID
    const nextSubtaskId = (task.subtasks?.length || 0) + 1;

    // 构建 prompt 参数
    const promptParams: ExpandTaskParams = {
      task,
      subtaskCount: numSubtasks,
      nextSubtaskId,
      additionalContext,
      useResearch: research,
      projectRoot: this.projectRoot
    };

    // 生成 prompts
    const systemPrompt = expandTaskPrompt.getSystemPrompt(promptParams);
    const userPrompt = expandTaskPrompt.getUserPrompt(promptParams);

    // 调用 AI 生成子任务
    const response = await this.aiService.generateObject({
      systemPrompt,
      userPrompt,
      schema: ExpandTaskResponseSchema,
      options: {
        temperature: 0.7,
        maxTokens: 4096
      }
    });

    // 处理生成的子任务
    const generatedSubtasks: Subtask[] = response.result.subtasks.map((st) => ({
      id: st.id,
      parentId: taskId,
      title: st.title,
      description: st.description,
      status: (st.status || 'pending') as Subtask['status'],
      priority: task.priority,
      dependencies: (st.dependencies || []).map(String),
      details: '',
      testStrategy: ''
    }));

    // 添加子任务到任务
    task.subtasks = [...(task.subtasks || []), ...generatedSubtasks];
    task.updatedAt = new Date().toISOString();

    // 更新任务
    await this.storage.updateTask(taskId, task, tag);

    logger.info(`Generated ${generatedSubtasks.length} subtasks for task ${taskId}`);

    return {
      result: task,
      usage: response.usage,
      model: response.model,
      provider: response.provider,
      duration: response.duration
    };
  }

  /**
   * 使用 AI 更新任务
   * @param taskId 任务 ID
   * @param prompt 更新提示
   * @param options 选项
   */
  async updateTaskWithAI(
    taskId: string,
    prompt: string,
    options: { tag?: string } = {}
  ): Promise<AIResponse<Task>> {
    const { tag } = options;

    logger.info(`Updating task with AI: ${taskId}`);

    // 加载任务
    const tasks = await this.storage.loadTasks(tag);
    const task = tasks.find((t) => t.id === taskId);

    if (!task) {
      throw new Error(`Task not found: ${taskId}`);
    }

    const systemPrompt = `You are an AI assistant that helps update development tasks based on user feedback or new information.

Given a task and an update instruction, modify the task appropriately. You may update:
- title: if the scope or focus changes
- description: if more detail is needed
- details: implementation guidance
- testStrategy: testing approach
- priority: if urgency changes
- status: if progress is made

Return a JSON object with the updated fields only (do not include unchanged fields).`;

    const userPrompt = `## CURRENT TASK

ID: ${task.id}
Title: ${task.title}
Description: ${task.description}
Details: ${task.details || 'None'}
Test Strategy: ${task.testStrategy || 'None'}
Priority: ${task.priority}
Status: ${task.status}

## UPDATE INSTRUCTION

${prompt}

Return a JSON object with only the fields that need to be updated.`;

    // 调用 AI
    const response = await this.aiService.generateText({
      systemPrompt,
      userPrompt,
      options: {
        temperature: 0.5,
        maxTokens: 2048
      }
    });

    // 解析更新
    const jsonMatch = response.result.match(/\{[\s\S]*\}/);
    if (!jsonMatch) {
      throw new Error('No valid update found in AI response');
    }

    const updates = JSON.parse(jsonMatch[0]);

    // 应用更新
    const updatedTask: Task = {
      ...task,
      ...updates,
      updatedAt: new Date().toISOString()
    };

    // 保存更新
    await this.storage.updateTask(taskId, updatedTask, tag);

    logger.info(`Updated task ${taskId}`);

    return {
      result: updatedTask,
      usage: response.usage,
      model: response.model,
      provider: response.provider,
      duration: response.duration
    };
  }

  /**
   * 获取 AI 配置
   */
  getAIConfig(): AIConfig {
    return this.aiService.getConfig();
  }

  /**
   * 更新 AI 配置
   */
  updateAIConfig(config: Partial<AIConfig>): void {
    this.aiService.updateConfig(config);
  }
}
