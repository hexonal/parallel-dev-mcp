/**
 * 任务相关的 Zod Schema 定义
 * @module tm-core/schemas/task.schema
 */

import { z } from 'zod';

/**
 * 子任务 Schema
 */
export const SubtaskSchema = z.object({
  id: z.number().int().positive(),
  title: z.string().min(1),
  description: z.string().min(1),
  status: z.string().default('pending'),
  dependencies: z.array(z.number().int().positive()).nullable().default([])
});

/**
 * PRD 解析生成的单个任务 Schema
 */
export const ParsedTaskSchema = z.object({
  id: z.number().int().positive(),
  title: z.string().min(1),
  description: z.string().min(1),
  details: z.string().nullable().default(''),
  testStrategy: z.string().nullable().default(''),
  priority: z.enum(['high', 'medium', 'low']).nullable().default('medium'),
  dependencies: z.array(z.number().int().positive()).nullable().default([]),
  status: z.string().nullable().default('pending')
});

/**
 * PRD 解析响应 Schema
 */
export const ParsePRDResponseSchema = z.object({
  tasks: z.array(ParsedTaskSchema)
});

/**
 * 任务展开响应 Schema
 */
export const ExpandTaskResponseSchema = z.object({
  subtasks: z.array(SubtaskSchema)
});

/**
 * 任务更新响应 Schema
 */
export const UpdateTaskResponseSchema = z.object({
  id: z.number().int().positive(),
  title: z.string().optional(),
  description: z.string().optional(),
  details: z.string().optional(),
  testStrategy: z.string().optional(),
  priority: z.enum(['high', 'medium', 'low']).optional(),
  status: z.string().optional()
});

// 类型导出
export type Subtask = z.infer<typeof SubtaskSchema>;
export type ParsedTask = z.infer<typeof ParsedTaskSchema>;
export type ParsePRDResponse = z.infer<typeof ParsePRDResponseSchema>;
export type ExpandTaskResponse = z.infer<typeof ExpandTaskResponseSchema>;
export type UpdateTaskResponse = z.infer<typeof UpdateTaskResponseSchema>;
