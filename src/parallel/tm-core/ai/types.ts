/**
 * AI 服务类型定义
 * @module tm-core/ai/types
 */

import { z } from 'zod';

/**
 * AI 提供商类型
 */
export type AIProvider = 'anthropic' | 'openai' | 'google' | 'local';

/**
 * AI 请求选项
 */
export interface AIRequestOptions {
  /** 温度参数 (0.0 - 1.0) */
  temperature?: number;
  /** 最大输出 token 数 */
  maxTokens?: number;
  /** Top-p 采样参数 */
  topP?: number;
  /** 请求超时 (ms) */
  timeout?: number;
  /** 重试次数 */
  retries?: number;
}

/**
 * AI 响应
 */
export interface AIResponse<T = unknown> {
  /** 解析后的结果 */
  result: T;
  /** 使用的 token 数 */
  usage: {
    inputTokens: number;
    outputTokens: number;
    totalTokens: number;
  };
  /** 使用的模型 */
  model: string;
  /** 提供商名称 */
  provider: string;
  /** 响应耗时 (ms) */
  duration: number;
}

/**
 * AI 配置
 */
export interface AIConfig {
  /** 主要提供商 */
  provider: AIProvider;
  /** API 密钥 (用于 x-api-key header) */
  apiKey: string;
  /** Auth Token (用于 Bearer 认证，代理服务器常用) */
  authToken?: string;
  /** 模型 ID */
  model: string;
  /** 基础 URL (可选) */
  baseUrl?: string;
  /** 自定义 HTTP headers (代理服务器可能需要) */
  defaultHeaders?: Record<string, string>;
  /** 默认请求选项 */
  defaultOptions?: AIRequestOptions;
}

/**
 * 生成结构化对象的参数
 */
export interface GenerateObjectParams<T extends z.ZodType> {
  /** 系统提示词 */
  systemPrompt: string;
  /** 用户提示词 */
  userPrompt: string;
  /** Zod schema */
  schema: T;
  /** 请求选项 */
  options?: AIRequestOptions;
}

/**
 * 生成文本的参数
 */
export interface GenerateTextParams {
  /** 系统提示词 */
  systemPrompt: string;
  /** 用户提示词 */
  userPrompt: string;
  /** 请求选项 */
  options?: AIRequestOptions;
}
