/**
 * Tag Service
 * 爆改自 claude-task-master/packages/tm-core/src/modules/tasks/services/tag.service.ts
 */

import type { IStorage, TagInfo } from '../common/interfaces/storage.interface';
import {
  TaskMasterError,
  ERROR_CODES
} from '../common/errors/task-master-error';

/**
 * 创建标签选项
 */
export interface CreateTagOptions {
  copyFromCurrent?: boolean;
  copyFromTag?: string;
  description?: string;
  fromBranch?: boolean;
}

/**
 * 删除标签选项
 */
export interface DeleteTagOptions {
  // 保留接口以备将来扩展
}

/**
 * 复制标签选项
 */
export interface CopyTagOptions {
  // 保留接口以备将来扩展
}

const RESERVED_TAG_NAMES = ['master'];
const MAX_TAG_NAME_LENGTH = 50;

/**
 * TagService - 处理标签管理业务逻辑
 */
export class TagService {
  constructor(private storage: IStorage) {}

  /**
   * 验证标签名格式
   */
  private validateTagName(name: string, context = 'Tag name'): void {
    if (!name || typeof name !== 'string') {
      throw new TaskMasterError(
        `${context} is required and must be a string`,
        ERROR_CODES.VALIDATION_ERROR
      );
    }

    if (name.length > MAX_TAG_NAME_LENGTH) {
      throw new TaskMasterError(
        `${context} must be ${MAX_TAG_NAME_LENGTH} characters or less`,
        ERROR_CODES.VALIDATION_ERROR,
        { tagName: name, maxLength: MAX_TAG_NAME_LENGTH }
      );
    }

    if (!/^[a-zA-Z0-9_-]+$/.test(name)) {
      throw new TaskMasterError(
        `${context} can only contain letters, numbers, hyphens, and underscores`,
        ERROR_CODES.VALIDATION_ERROR,
        { tagName: name }
      );
    }

    if (RESERVED_TAG_NAMES.includes(name.toLowerCase())) {
      throw new TaskMasterError(
        `"${name}" is a reserved tag name`,
        ERROR_CODES.VALIDATION_ERROR,
        { tagName: name, reserved: true }
      );
    }
  }

  /**
   * 创建新标签
   */
  async createTag(
    name: string,
    options: CreateTagOptions = {}
  ): Promise<TagInfo> {
    this.validateTagName(name);

    const allTags = await this.storage.getAllTags();
    if (allTags.includes(name)) {
      throw new TaskMasterError(
        `Tag "${name}" already exists`,
        ERROR_CODES.VALIDATION_ERROR,
        { tagName: name }
      );
    }

    if (options.copyFromTag && !allTags.includes(options.copyFromTag)) {
      throw new TaskMasterError(
        `Cannot copy from missing tag "${options.copyFromTag}"`,
        ERROR_CODES.NOT_FOUND,
        { tagName: options.copyFromTag }
      );
    }

    let copyFrom: string | undefined;
    if (options.copyFromTag) {
      copyFrom = options.copyFromTag;
    } else if (options.copyFromCurrent) {
      const result = await this.storage.getTagsWithStats();
      copyFrom = result.currentTag || undefined;
    }

    await this.storage.createTag(name, {
      copyFrom,
      description: options.description
    });

    const tagInfo: TagInfo = {
      name,
      taskCount: 0,
      completedTasks: 0,
      isCurrent: false,
      statusBreakdown: {},
      description:
        options.description ||
        `Tag created on ${new Date().toLocaleDateString()}`
    };

    return tagInfo;
  }

  /**
   * 删除标签
   */
  async deleteTag(name: string, _options: DeleteTagOptions = {}): Promise<void> {
    this.validateTagName(name);

    if (name === 'master') {
      throw new TaskMasterError(
        'Cannot delete the "master" tag',
        ERROR_CODES.VALIDATION_ERROR,
        { tagName: name, protected: true }
      );
    }

    const allTags = await this.storage.getAllTags();
    if (!allTags.includes(name)) {
      throw new TaskMasterError(
        `Tag "${name}" does not exist`,
        ERROR_CODES.NOT_FOUND,
        { tagName: name }
      );
    }

    await this.storage.deleteTag(name);
  }

  /**
   * 重命名标签
   */
  async renameTag(oldName: string, newName: string): Promise<void> {
    this.validateTagName(oldName, 'Old tag name');
    this.validateTagName(newName, 'New tag name');

    if (oldName === 'master') {
      throw new TaskMasterError(
        'Cannot rename the "master" tag',
        ERROR_CODES.VALIDATION_ERROR,
        { tagName: oldName, protected: true }
      );
    }

    const allTags = await this.storage.getAllTags();
    if (!allTags.includes(oldName)) {
      throw new TaskMasterError(
        `Tag "${oldName}" does not exist`,
        ERROR_CODES.NOT_FOUND,
        { tagName: oldName }
      );
    }

    if (allTags.includes(newName)) {
      throw new TaskMasterError(
        `Tag "${newName}" already exists`,
        ERROR_CODES.VALIDATION_ERROR,
        { tagName: newName }
      );
    }

    await this.storage.renameTag(oldName, newName);
  }

  /**
   * 复制标签
   */
  async copyTag(
    sourceName: string,
    targetName: string,
    _options: CopyTagOptions = {}
  ): Promise<void> {
    this.validateTagName(sourceName, 'Source tag name');
    this.validateTagName(targetName, 'Target tag name');

    const allTags = await this.storage.getAllTags();
    if (!allTags.includes(sourceName)) {
      throw new TaskMasterError(
        `Source tag "${sourceName}" does not exist`,
        ERROR_CODES.NOT_FOUND,
        { tagName: sourceName }
      );
    }

    if (allTags.includes(targetName)) {
      throw new TaskMasterError(
        `Target tag "${targetName}" already exists`,
        ERROR_CODES.VALIDATION_ERROR,
        { tagName: targetName }
      );
    }

    await this.storage.copyTag(sourceName, targetName);
  }

  /**
   * 获取带统计信息的所有标签
   */
  async getTagsWithStats() {
    return await this.storage.getTagsWithStats();
  }
}
