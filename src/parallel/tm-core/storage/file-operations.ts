/**
 * 文件操作（原子写入和锁定）
 * 爆改自 claude-task-master/packages/tm-core/src/modules/storage/adapters/file-storage/file-operations.ts
 */

import { constants } from 'node:fs';
import fs from 'node:fs/promises';

/**
 * 处理带锁定机制的原子文件操作
 */
export class FileOperations {
  private fileLocks: Map<string, Promise<void>> = new Map();

  /**
   * 读取并解析 JSON 文件
   */
  async readJson(filePath: string): Promise<unknown> {
    try {
      const content = await fs.readFile(filePath, 'utf-8');
      return JSON.parse(content);
    } catch (error: unknown) {
      const err = error as NodeJS.ErrnoException;
      if (err.code === 'ENOENT') {
        throw error;
      }
      if (error instanceof SyntaxError) {
        throw new Error(`Invalid JSON in file ${filePath}: ${error.message}`);
      }
      throw new Error(
        `Failed to read file ${filePath}: ${err.message || 'Unknown error'}`
      );
    }
  }

  /**
   * 原子写入 JSON 文件（带锁定）
   */
  async writeJson(filePath: string, data: unknown): Promise<void> {
    const lockKey = filePath;
    const existingLock = this.fileLocks.get(lockKey);

    if (existingLock) {
      await existingLock;
    }

    const lockPromise = this.performAtomicWrite(filePath, data);
    this.fileLocks.set(lockKey, lockPromise);

    try {
      await lockPromise;
    } finally {
      this.fileLocks.delete(lockKey);
    }
  }

  /**
   * 使用临时文件执行原子写入
   */
  private async performAtomicWrite(
    filePath: string,
    data: unknown
  ): Promise<void> {
    const tempPath = `${filePath}.tmp`;

    try {
      const content = JSON.stringify(data, null, 2);
      await fs.writeFile(tempPath, content, 'utf-8');
      await fs.rename(tempPath, filePath);
    } catch (error: unknown) {
      try {
        await fs.unlink(tempPath);
      } catch {
        // 忽略清理错误
      }

      const err = error as Error;
      throw new Error(
        `Failed to write file ${filePath}: ${err.message || 'Unknown error'}`
      );
    }
  }

  /**
   * 检查文件是否存在
   */
  async exists(filePath: string): Promise<boolean> {
    try {
      await fs.access(filePath, constants.F_OK);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * 获取文件状态
   */
  async getStats(filePath: string) {
    return fs.stat(filePath);
  }

  /**
   * 读取目录内容
   */
  async readDir(dirPath: string): Promise<string[]> {
    return fs.readdir(dirPath);
  }

  /**
   * 递归创建目录
   */
  async ensureDir(dirPath: string): Promise<void> {
    try {
      await fs.mkdir(dirPath, { recursive: true });
    } catch (error: unknown) {
      const err = error as Error;
      throw new Error(
        `Failed to create directory ${dirPath}: ${err.message || 'Unknown error'}`
      );
    }
  }

  /**
   * 删除文件
   */
  async deleteFile(filePath: string): Promise<void> {
    try {
      await fs.unlink(filePath);
    } catch (error: unknown) {
      const err = error as NodeJS.ErrnoException;
      if (err.code !== 'ENOENT') {
        throw new Error(
          `Failed to delete file ${filePath}: ${err.message || 'Unknown error'}`
        );
      }
    }
  }

  /**
   * 重命名/移动文件
   */
  async moveFile(oldPath: string, newPath: string): Promise<void> {
    try {
      await fs.rename(oldPath, newPath);
    } catch (error: unknown) {
      const err = error as Error;
      throw new Error(
        `Failed to move file from ${oldPath} to ${newPath}: ${err.message || 'Unknown error'}`
      );
    }
  }

  /**
   * 复制文件
   */
  async copyFile(srcPath: string, destPath: string): Promise<void> {
    try {
      await fs.copyFile(srcPath, destPath);
    } catch (error: unknown) {
      const err = error as Error;
      throw new Error(
        `Failed to copy file from ${srcPath} to ${destPath}: ${err.message || 'Unknown error'}`
      );
    }
  }

  /**
   * 清理所有待处理的文件操作
   */
  async cleanup(): Promise<void> {
    const locks = Array.from(this.fileLocks.values());
    if (locks.length > 0) {
      await Promise.all(locks);
    }
    this.fileLocks.clear();
  }
}
