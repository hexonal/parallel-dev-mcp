/**
 * AI 服务 - 调用 AI API 生成结构化输出
 * @module tm-core/ai/ai-service
 */

import Anthropic from '@anthropic-ai/sdk';
import { z } from 'zod';
import { getLogger } from '../common/logger';
import type {
  AIConfig,
  AIRequestOptions,
  AIResponse,
  GenerateObjectParams,
  GenerateTextParams
} from './types';

const logger = getLogger('AIService');

/**
 * 默认配置
 */
const DEFAULT_OPTIONS: AIRequestOptions = {
  temperature: 0.7,
  maxTokens: 4096,
  topP: 1.0,
  timeout: 60000,
  retries: 2
};

/**
 * AI 服务类
 * 封装 AI API 调用，支持结构化输出
 */
export class AIService {
  private config: AIConfig;
  private anthropic: Anthropic | null = null;

  constructor(config: Partial<AIConfig> = {}) {
    // 从环境变量读取配置
    // 支持两种认证方式：apiKey (x-api-key) 和 authToken (Bearer)
    const baseUrl = config.baseUrl ?? process.env.ANTHROPIC_BASE_URL;

    // 代理服务器可能阻止 SDK 默认 User-Agent，使用兼容的 User-Agent
    const proxyHeaders: Record<string, string> = baseUrl
      ? { 'User-Agent': 'curl/8.4.0' }
      : {};

    this.config = {
      provider: config.provider ?? 'anthropic',
      apiKey: config.apiKey ?? process.env.ANTHROPIC_API_KEY ?? '',
      authToken: config.authToken ?? process.env.ANTHROPIC_AUTH_TOKEN,
      model: config.model ?? 'claude-sonnet-4-20250514',
      baseUrl,
      defaultHeaders: { ...proxyHeaders, ...config.defaultHeaders },
      defaultOptions: { ...DEFAULT_OPTIONS, ...config.defaultOptions }
    };

    this.initializeClient();
  }

  /**
   * 初始化 API 客户端
   * 支持两种认证方式：
   * - authToken: Bearer Token (代理服务器常用)
   * - apiKey: x-api-key header (官方 API)
   */
  private initializeClient(): void {
    if (this.config.provider === 'anthropic') {
      const commonOptions = {
        baseURL: this.config.baseUrl,
        defaultHeaders: this.config.defaultHeaders
      };

      // 优先使用 authToken (Bearer 认证)
      if (this.config.authToken) {
        this.anthropic = new Anthropic({
          authToken: this.config.authToken,
          ...commonOptions
        });
      } else if (this.config.apiKey) {
        this.anthropic = new Anthropic({
          apiKey: this.config.apiKey,
          ...commonOptions
        });
      }
    }
  }

  /**
   * 检查服务是否可用
   */
  isAvailable(): boolean {
    return this.anthropic !== null;
  }

  /**
   * 生成结构化对象
   * 使用 AI 生成符合 schema 的 JSON 对象
   */
  async generateObject<T extends z.ZodType>(
    params: GenerateObjectParams<T>
  ): Promise<AIResponse<z.infer<T>>> {
    const { systemPrompt, userPrompt, schema, options } = params;
    const mergedOptions = { ...this.config.defaultOptions, ...options };

    if (!this.anthropic) {
      throw new Error('AI service not available: missing API key');
    }

    const startTime = Date.now();
    let lastError: Error | null = null;
    const retries = mergedOptions.retries ?? DEFAULT_OPTIONS.retries ?? 2;

    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        logger.debug(`Attempt ${attempt + 1}/${retries + 1} generating object`);

        const response = await this.anthropic.messages.create({
          model: this.config.model,
          max_tokens: mergedOptions.maxTokens ?? DEFAULT_OPTIONS.maxTokens ?? 4096,
          temperature: mergedOptions.temperature ?? DEFAULT_OPTIONS.temperature ?? 0.7,
          system: systemPrompt,
          messages: [
            {
              role: 'user',
              content: userPrompt
            }
          ]
        });

        // 提取文本内容
        const textContent = response.content.find((c) => c.type === 'text');
        if (!textContent || textContent.type !== 'text') {
          throw new Error('No text content in response');
        }

        // 解析 JSON
        const jsonMatch = textContent.text.match(/\{[\s\S]*\}/);
        if (!jsonMatch) {
          throw new Error('No JSON object found in response');
        }

        const parsed = JSON.parse(jsonMatch[0]);

        // 使用 schema 验证
        const validated = schema.parse(parsed);

        const duration = Date.now() - startTime;

        return {
          result: validated,
          usage: {
            inputTokens: response.usage.input_tokens,
            outputTokens: response.usage.output_tokens,
            totalTokens: response.usage.input_tokens + response.usage.output_tokens
          },
          model: this.config.model,
          provider: this.config.provider,
          duration
        };
      } catch (error) {
        lastError = error as Error;
        logger.warn(`Attempt ${attempt + 1} failed: ${lastError.message}`);

        if (attempt < retries) {
          const delay = 1000 * Math.pow(2, attempt);
          await new Promise((resolve) => setTimeout(resolve, delay));
        }
      }
    }

    throw lastError ?? new Error('AI generation failed');
  }

  /**
   * 生成文本
   * 使用 AI 生成纯文本响应
   */
  async generateText(params: GenerateTextParams): Promise<AIResponse<string>> {
    const { systemPrompt, userPrompt, options } = params;
    const mergedOptions = { ...this.config.defaultOptions, ...options };

    if (!this.anthropic) {
      throw new Error('AI service not available: missing API key');
    }

    const startTime = Date.now();
    let lastError: Error | null = null;
    const retries = mergedOptions.retries ?? DEFAULT_OPTIONS.retries ?? 2;

    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        logger.debug(`Attempt ${attempt + 1}/${retries + 1} generating text`);

        const response = await this.anthropic.messages.create({
          model: this.config.model,
          max_tokens: mergedOptions.maxTokens ?? DEFAULT_OPTIONS.maxTokens ?? 4096,
          temperature: mergedOptions.temperature ?? DEFAULT_OPTIONS.temperature ?? 0.7,
          system: systemPrompt,
          messages: [
            {
              role: 'user',
              content: userPrompt
            }
          ]
        });

        // 提取文本内容
        const textContent = response.content.find((c) => c.type === 'text');
        if (!textContent || textContent.type !== 'text') {
          throw new Error('No text content in response');
        }

        const duration = Date.now() - startTime;

        return {
          result: textContent.text,
          usage: {
            inputTokens: response.usage.input_tokens,
            outputTokens: response.usage.output_tokens,
            totalTokens: response.usage.input_tokens + response.usage.output_tokens
          },
          model: this.config.model,
          provider: this.config.provider,
          duration
        };
      } catch (error) {
        lastError = error as Error;
        logger.warn(`Attempt ${attempt + 1} failed: ${lastError.message}`);

        if (attempt < retries) {
          const delay = 1000 * Math.pow(2, attempt);
          await new Promise((resolve) => setTimeout(resolve, delay));
        }
      }
    }

    throw lastError ?? new Error('AI generation failed');
  }

  /**
   * 获取当前配置
   */
  getConfig(): AIConfig {
    return { ...this.config };
  }

  /**
   * 更新配置
   */
  updateConfig(config: Partial<AIConfig>): void {
    this.config = {
      ...this.config,
      ...config,
      defaultOptions: {
        ...this.config.defaultOptions,
        ...config.defaultOptions
      }
    };
    this.initializeClient();
  }
}

// 单例实例
let aiServiceInstance: AIService | null = null;

/**
 * 获取 AI 服务实例
 */
export function getAIService(config?: Partial<AIConfig>): AIService {
  if (!aiServiceInstance) {
    aiServiceInstance = new AIService(config);
  } else if (config) {
    aiServiceInstance.updateConfig(config);
  }
  return aiServiceInstance;
}

/**
 * 重置 AI 服务实例 (用于测试)
 */
export function resetAIService(): void {
  aiServiceInstance = null;
}
