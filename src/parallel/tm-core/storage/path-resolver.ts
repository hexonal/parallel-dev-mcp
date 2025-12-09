/**
 * 路径解析工具
 * 爆改自 claude-task-master/packages/tm-core/src/modules/storage/adapters/file-storage/path-resolver.ts
 */

import path from 'node:path';

/**
 * 处理单一 tasks.json 文件存储的路径解析
 */
export class PathResolver {
  private readonly basePath: string;
  private readonly tasksDir: string;
  private readonly tasksFilePath: string;

  constructor(projectPath: string) {
    // 使用 .pdev 目录作为 ParallelDev 的存储根目录
    this.basePath = path.join(projectPath, '.pdev');
    this.tasksDir = path.join(this.basePath, 'tasks');
    this.tasksFilePath = path.join(this.tasksDir, 'tasks.json');
  }

  /**
   * 获取基础存储目录路径
   */
  getBasePath(): string {
    return this.basePath;
  }

  /**
   * 获取任务目录路径
   */
  getTasksDir(): string {
    return this.tasksDir;
  }

  /**
   * 获取 tasks.json 文件路径
   */
  getTasksPath(): string {
    return this.tasksFilePath;
  }
}
