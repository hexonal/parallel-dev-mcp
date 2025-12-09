/**
 * 项目初始化器 - 处理 pdev init 命令
 * @module parallel/init/ProjectInitializer
 *
 * 功能：
 * 1. 创建 .pdev/ 目录结构
 * 2. 生成默认配置文件
 * 3. 创建 Worker 级 CLAUDE.md
 * 4. 配置 .claude/ 目录（commands、agents、skills 等）
 */

import * as fs from 'fs';
import * as path from 'path';
import {
  PDEV_DIR,
  PDEV_PATHS,
  CLAUDE_PATHS
} from '../config';

/** 初始化选项 */
export interface InitOptions {
  /** 强制覆盖现有文件 */
  force?: boolean;
  /** 静默模式 */
  silent?: boolean;
}

/** 初始化结果 */
export interface InitResult {
  success: boolean;
  /** 创建的文件列表 */
  createdFiles: string[];
  /** 创建的目录列表 */
  createdDirs: string[];
  /** 错误信息 */
  error?: string;
}

/**
 * Worker 级 CLAUDE.md 模板
 */
const WORKER_CLAUDE_MD_TEMPLATE = `# ParallelDev Worker 指令

## 角色定义
你是 ParallelDev Worker，正在执行分配给你的任务。

## 任务来源
任务定义在 \`.pdev/tasks/tasks.json\`

## 执行规范
1. **专注任务**: 只完成任务描述中指定的需求
2. **最小修改**: 不要修改不相关的文件
3. **代码规范**: 遵循项目的 CLAUDE.md 规范
4. **质量保证**: 确保代码质量（无 lint 错误、类型正确）
5. **简洁原则**: 保持代码简洁，遵循 YAGNI 原则

## 完成报告
完成任务后，输出以下格式的报告：
- **修改的文件**: 列出所有修改的文件
- **完成摘要**: 简要说明做了什么
- **遇到的问题**: 如有问题，说明处理方式

## 注意事项
- 如有疑问，优先选择简单方案
- 不要添加超出任务范围的功能
- 确保修改后代码可以正常编译运行
`;

/**
 * 根目录 CLAUDE.md 追加内容
 */
const ROOT_CLAUDE_MD_APPEND = `

---

# ParallelDev 集成

本项目已集成 ParallelDev 并行开发系统。

## 可用命令
- \`/status\` - 查看 ParallelDev 当前状态
- \`/start --prd <file>\` - 启动并行开发
- \`/stop\` - 停止执行
- \`/report\` - 生成执行报告

## 配置文件
- \`.pdev/config.json\` - ParallelDev 配置
- \`.pdev/state.json\` - 当前执行状态
- \`.pdev/tasks/tasks.json\` - 任务列表
- \`.pdev/CLAUDE.md\` - Worker 级指令

## 使用流程
1. \`pdev generate --prd prd.md\` - 从 PRD 生成任务
2. \`pdev start --prd prd.md\` - 启动并行执行
3. \`pdev status\` - 监控执行状态
4. \`pdev report\` - 查看执行报告
`;

/**
 * 默认 config.json 内容
 */
const DEFAULT_PDEV_CONFIG = {
  version: '1.0.0',
  maxWorkers: 3,
  tmuxPrefix: 'pdev',
  permissionMode: 'acceptEdits',
  timeout: 600000,
  autoCleanup: true
};

/**
 * 项目初始化器
 */
export class ProjectInitializer {
  private projectRoot: string;
  private options: InitOptions;

  constructor(projectRoot: string, options: InitOptions = {}) {
    this.projectRoot = projectRoot;
    this.options = options;
  }

  /**
   * 执行初始化
   */
  async initialize(): Promise<InitResult> {
    const result: InitResult = {
      success: false,
      createdFiles: [],
      createdDirs: []
    };

    try {
      // 1. 检查是否已初始化
      if (this.isInitialized() && !this.options.force) {
        throw new Error(
          `项目已初始化。使用 --force 强制重新初始化。`
        );
      }

      // 2. 创建 .pdev 目录结构
      await this.createPdevStructure(result);

      // 3. 创建配置文件
      await this.createConfigFiles(result);

      // 4. 创建 Worker CLAUDE.md
      await this.createWorkerClaudeMd(result);

      // 5. 配置 .claude 目录
      await this.configureClaudeDir(result);

      // 6. 追加根目录 CLAUDE.md
      await this.appendRootClaudeMd(result);

      result.success = true;
      return result;
    } catch (error) {
      result.error = error instanceof Error ? error.message : String(error);
      return result;
    }
  }

  /**
   * 检查是否已初始化
   */
  isInitialized(): boolean {
    const pdevPath = path.join(this.projectRoot, PDEV_DIR);
    return fs.existsSync(pdevPath);
  }

  /**
   * 创建 .pdev 目录结构
   */
  private async createPdevStructure(result: InitResult): Promise<void> {
    const dirs = [
      PDEV_PATHS.root,
      PDEV_PATHS.tasks,
      PDEV_PATHS.docs,
      PDEV_PATHS.workers
    ];

    for (const dir of dirs) {
      const fullPath = path.join(this.projectRoot, dir);
      if (!fs.existsSync(fullPath)) {
        fs.mkdirSync(fullPath, { recursive: true });
        result.createdDirs.push(dir);
      }
    }
  }

  /**
   * 创建配置文件
   */
  private async createConfigFiles(result: InitResult): Promise<void> {
    // config.json
    const configPath = path.join(this.projectRoot, PDEV_PATHS.config);
    if (!fs.existsSync(configPath) || this.options.force) {
      fs.writeFileSync(
        configPath,
        JSON.stringify(DEFAULT_PDEV_CONFIG, null, 2)
      );
      result.createdFiles.push(PDEV_PATHS.config);
    }

    // state.json
    const statePath = path.join(this.projectRoot, PDEV_PATHS.state);
    if (!fs.existsSync(statePath) || this.options.force) {
      const initialState = {
        status: 'idle',
        activeWorkers: 0,
        completedTasks: 0,
        lastUpdated: new Date().toISOString()
      };
      fs.writeFileSync(statePath, JSON.stringify(initialState, null, 2));
      result.createdFiles.push(PDEV_PATHS.state);
    }

    // 创建空的 tasks.json
    const tasksPath = path.join(this.projectRoot, PDEV_PATHS.tasksJson);
    if (!fs.existsSync(tasksPath) || this.options.force) {
      const emptyTasks = {
        tasks: [],
        metadata: {
          generatedAt: new Date().toISOString(),
          source: null,
          version: '1.0.0'
        }
      };
      fs.writeFileSync(tasksPath, JSON.stringify(emptyTasks, null, 2));
      result.createdFiles.push(PDEV_PATHS.tasksJson);
    }
  }

  /**
   * 创建 Worker 级 CLAUDE.md
   */
  private async createWorkerClaudeMd(result: InitResult): Promise<void> {
    const claudeMdPath = path.join(this.projectRoot, PDEV_PATHS.claudeMd);

    if (!fs.existsSync(claudeMdPath) || this.options.force) {
      fs.writeFileSync(claudeMdPath, WORKER_CLAUDE_MD_TEMPLATE);
      result.createdFiles.push(PDEV_PATHS.claudeMd);
    }
  }

  /**
   * 追加根目录 CLAUDE.md
   * 如果已存在，追加 ParallelDev 相关内容
   * 如果不存在，创建新文件
   */
  private async appendRootClaudeMd(result: InitResult): Promise<void> {
    const rootClaudeMdPath = path.join(this.projectRoot, 'CLAUDE.md');
    const marker = '# ParallelDev 集成';

    if (fs.existsSync(rootClaudeMdPath)) {
      // 读取现有内容
      const existingContent = fs.readFileSync(rootClaudeMdPath, 'utf-8');

      // 检查是否已包含 ParallelDev 内容
      if (existingContent.includes(marker)) {
        // 已经包含，不重复追加
        return;
      }

      // 追加内容
      fs.appendFileSync(rootClaudeMdPath, ROOT_CLAUDE_MD_APPEND);
      result.createdFiles.push('CLAUDE.md (追加)');
    } else {
      // 创建新文件
      const newContent = `# ${path.basename(this.projectRoot)}
${ROOT_CLAUDE_MD_APPEND}`;
      fs.writeFileSync(rootClaudeMdPath, newContent);
      result.createdFiles.push('CLAUDE.md');
    }
  }

  /**
   * 配置 .claude 目录
   * 将 paralleldev-plugin 内容直接复制到 .claude/
   */
  private async configureClaudeDir(result: InitResult): Promise<void> {
    // 创建 .claude 目录
    const claudeDir = path.join(this.projectRoot, CLAUDE_PATHS.root);
    if (!fs.existsSync(claudeDir)) {
      fs.mkdirSync(claudeDir, { recursive: true });
      result.createdDirs.push(CLAUDE_PATHS.root);
    }

    // 获取插件源路径
    const pluginSource = this.getPluginSourcePath();

    // 要复制的目录（排除 .claude-plugin 和 .mcp.json）
    const itemsToCopy = ['commands', 'agents', 'skills', 'hooks', 'scripts'];

    // 复制目录
    for (const item of itemsToCopy) {
      const srcPath = path.join(pluginSource, item);
      const destPath = path.join(claudeDir, item);

      if (fs.existsSync(srcPath)) {
        if (this.options.force && fs.existsSync(destPath)) {
          fs.rmSync(destPath, { recursive: true, force: true });
        }

        if (!fs.existsSync(destPath)) {
          this.copyDirectory(srcPath, destPath);
          result.createdDirs.push(path.join(CLAUDE_PATHS.root, item));
        }
      }
    }

    // 创建/更新 .claude/settings.json
    await this.updateClaudeSettings(result);

    // 合并 MCP 配置到项目根目录 .mcp.json
    await this.mergeMcpConfig(result);
  }

  /**
   * 创建/更新 .claude/settings.json
   */
  private async updateClaudeSettings(result: InitResult): Promise<void> {
    const settingsPath = path.join(this.projectRoot, CLAUDE_PATHS.settings);

    // 加载或创建 settings
    let settings: Record<string, unknown> = {};
    if (fs.existsSync(settingsPath)) {
      try {
        settings = JSON.parse(fs.readFileSync(settingsPath, 'utf-8'));
      } catch {
        settings = {};
      }
    }

    // 设置默认配置
    if (!settings.permissions) {
      settings.permissions = {
        allow: ['Read', 'Write', 'Edit', 'Bash', 'Glob', 'Grep']
      };
    }

    // 保存 settings
    fs.writeFileSync(settingsPath, JSON.stringify(settings, null, 2));

    if (!result.createdFiles.includes(CLAUDE_PATHS.settings)) {
      result.createdFiles.push(CLAUDE_PATHS.settings);
    }
  }

  /**
   * 合并 MCP 配置到项目根目录 .mcp.json
   * 从 pdev 主项目根目录读取 MCP 配置并合并到目标项目
   */
  private async mergeMcpConfig(result: InitResult): Promise<void> {
    // 获取 pdev 主项目根目录的 .mcp.json
    const pdevRoot = this.getPdevRootPath();
    const srcMcpPath = path.join(pdevRoot, '.mcp.json');
    const destMcpPath = path.join(this.projectRoot, '.mcp.json');

    if (!fs.existsSync(srcMcpPath)) {
      return;
    }

    // 读取源 MCP 配置
    let srcMcp: { mcpServers?: Record<string, unknown> } = {};
    try {
      srcMcp = JSON.parse(fs.readFileSync(srcMcpPath, 'utf-8'));
    } catch {
      return;
    }

    // 读取或创建目标 MCP 配置
    let destMcp: { mcpServers?: Record<string, unknown> } = { mcpServers: {} };
    if (fs.existsSync(destMcpPath)) {
      try {
        destMcp = JSON.parse(fs.readFileSync(destMcpPath, 'utf-8'));
        if (!destMcp.mcpServers) {
          destMcp.mcpServers = {};
        }
      } catch {
        destMcp = { mcpServers: {} };
      }
    }

    // 合并 MCP 服务器配置（追加不覆盖）
    if (srcMcp.mcpServers) {
      for (const [name, config] of Object.entries(srcMcp.mcpServers)) {
        if (!destMcp.mcpServers![name]) {
          destMcp.mcpServers![name] = config;
        }
      }
    }

    // 保存合并后的配置
    fs.writeFileSync(destMcpPath, JSON.stringify(destMcp, null, 2));

    if (!result.createdFiles.includes('.mcp.json')) {
      result.createdFiles.push('.mcp.json');
    }
  }

  /**
   * 获取插件源路径
   */
  private getPluginSourcePath(): string {
    const possiblePaths = [
      // 开发环境：相对于当前模块
      path.resolve(__dirname, '../../../paralleldev-plugin'),
      // npm 全局安装
      path.resolve(__dirname, '../../paralleldev-plugin'),
      // 相对于项目根目录
      path.resolve(process.cwd(), 'paralleldev-plugin')
    ];

    for (const p of possiblePaths) {
      if (fs.existsSync(p)) {
        return p;
      }
    }

    throw new Error(
      'paralleldev-plugin 目录未找到。请确保已正确安装 pdev。'
    );
  }

  /**
   * 获取 pdev 主项目根目录
   */
  private getPdevRootPath(): string {
    const possiblePaths = [
      // 开发环境：相对于当前模块 (dist/parallel/init -> root)
      path.resolve(__dirname, '../../..'),
      // npm 全局安装
      path.resolve(__dirname, '../..'),
    ];

    for (const p of possiblePaths) {
      // 检查是否存在 .mcp.json 作为标识
      if (fs.existsSync(path.join(p, '.mcp.json'))) {
        return p;
      }
    }

    // 如果找不到，返回第一个路径（开发环境）
    return possiblePaths[0];
  }

  /**
   * 复制目录
   */
  private copyDirectory(src: string, dest: string): void {
    fs.mkdirSync(dest, { recursive: true });

    const entries = fs.readdirSync(src, { withFileTypes: true });

    for (const entry of entries) {
      const srcPath = path.join(src, entry.name);
      const destPath = path.join(dest, entry.name);

      if (entry.isDirectory()) {
        this.copyDirectory(srcPath, destPath);
      } else {
        fs.copyFileSync(srcPath, destPath);
      }
    }
  }

  /**
   * 打印初始化结果
   */
  printResult(result: InitResult): void {
    if (this.options.silent) {
      return;
    }

    if (result.success) {
      console.log('');
      console.log('✅ ParallelDev 初始化完成！');
      console.log('');
      console.log('📁 创建的目录:');
      for (const dir of result.createdDirs) {
        console.log(`   ${dir}`);
      }
      console.log('');
      console.log('📄 创建的文件:');
      for (const file of result.createdFiles) {
        console.log(`   ${file}`);
      }
      console.log('');
      console.log('🚀 下一步:');
      console.log('   pdev generate --prd your-prd.md   # 从 PRD 生成任务');
      console.log('   pdev start --prd your-prd.md      # 启动并行开发');
      console.log('');
    } else {
      console.error('❌ 初始化失败:', result.error);
    }
  }
}

/**
 * 便捷初始化函数
 */
export async function initProject(
  projectRoot: string,
  options: InitOptions = {}
): Promise<InitResult> {
  const initializer = new ProjectInitializer(projectRoot, options);
  const result = await initializer.initialize();
  initializer.printResult(result);
  return result;
}
