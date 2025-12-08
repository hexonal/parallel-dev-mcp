/**
 * Prompt 模块导出
 * @module tm-core/prompts
 */

export {
  parsePrdPrompt,
  getSystemPrompt as getParsePrdSystemPrompt,
  getUserPrompt as getParsePrdUserPrompt,
  type ParsePrdParams
} from './parse-prd';

export {
  expandTaskPrompt,
  getSystemPrompt as getExpandTaskSystemPrompt,
  getUserPrompt as getExpandTaskUserPrompt,
  type ExpandTaskParams
} from './expand-task';
