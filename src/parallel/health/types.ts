/**
 * 健康检查类型定义
 */

/** 检查状态 */
export type CheckStatus = 'pass' | 'warn' | 'fail';

/** 单项检查结果 */
export interface CheckResult {
  name: string;
  status: CheckStatus;
  message: string;
  detail?: string;
}

/** 分类检查结果 */
export interface CategoryResult {
  category: string;
  icon: string;
  checks: CheckResult[];
  passed: number;
  warnings: number;
  failed: number;
}

/** 完整诊断结果 */
export interface DiagnosticResult {
  categories: CategoryResult[];
  totalPassed: number;
  totalWarnings: number;
  totalFailed: number;
  healthy: boolean;
}

/** 检查器接口 */
export interface Checker {
  category: string;
  icon: string;
  check(): Promise<CheckResult[]>;
}
