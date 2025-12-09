/**
 * MCP 检查器 - 检查 .mcp.json 配置
 */

import * as fs from 'fs';
import * as path from 'path';
import { Checker, CheckResult } from '../types';

/** 必需的 MCP 服务器列表 */
const REQUIRED_SERVERS = [
  'sequential-thinking',
  'context7',
  'git-config',
  'mcp-datetime',
  'deepwiki'
];

export class McpChecker implements Checker {
  category = 'MCP 服务器';
  icon = '🔌';

  constructor(private projectRoot: string) {}

  async check(): Promise<CheckResult[]> {
    const results: CheckResult[] = [];

    // 1. 检查 .mcp.json 文件
    const fileCheck = this.checkFile();
    results.push(fileCheck);

    if (fileCheck.status === 'fail') {
      return results;
    }

    // 2. 检查 JSON 格式和 mcpServers 字段
    const formatCheck = this.checkFormat();
    results.push(formatCheck);

    if (formatCheck.status === 'fail') {
      return results;
    }

    // 3. 检查必需的服务器
    results.push(...this.checkRequiredServers());

    return results;
  }

  private checkFile(): CheckResult {
    const mcpPath = path.join(this.projectRoot, '.mcp.json');
    if (fs.existsSync(mcpPath)) {
      return {
        name: '.mcp.json 文件',
        status: 'pass',
        message: '文件存在'
      };
    }
    return {
      name: '.mcp.json 文件',
      status: 'fail',
      message: '文件不存在',
      detail: '运行 pdev init 初始化项目'
    };
  }

  private checkFormat(): CheckResult {
    const mcpPath = path.join(this.projectRoot, '.mcp.json');
    try {
      const content = fs.readFileSync(mcpPath, 'utf-8');
      const config = JSON.parse(content);

      if (!config.mcpServers) {
        return {
          name: 'mcpServers 字段',
          status: 'fail',
          message: '缺少 mcpServers 字段'
        };
      }

      return {
        name: 'mcpServers 字段',
        status: 'pass',
        message: 'JSON 格式有效'
      };
    } catch {
      return {
        name: 'mcpServers 字段',
        status: 'fail',
        message: 'JSON 格式无效'
      };
    }
  }

  private checkRequiredServers(): CheckResult[] {
    const mcpPath = path.join(this.projectRoot, '.mcp.json');
    const results: CheckResult[] = [];

    try {
      const content = fs.readFileSync(mcpPath, 'utf-8');
      const config = JSON.parse(content);
      const servers = config.mcpServers || {};

      for (const server of REQUIRED_SERVERS) {
        if (servers[server]) {
          results.push({
            name: server,
            status: 'pass',
            message: '已配置'
          });
        } else {
          results.push({
            name: server,
            status: 'warn',
            message: '未配置',
            detail: '运行 pdev init --force 重新初始化'
          });
        }
      }
    } catch {
      // 已在 checkFormat 中处理
    }

    return results;
  }
}
