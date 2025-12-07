# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

对话的时候，始终使用的是中文
                          
## 本项目为 java 项目，采用 jdk 17 完成开发迭代
- 尽可能采用 jdk17的优秀风格开发
- 文档一律放到[docs](docs),并做好分类
                       

## 🚨 严格开发规范 (2025最新标准)
## 🎯 核心设计原则

### 1. YAGNI 原则（You Aren't Gonna Need It）
- ✅ 只实现当前需要的功能
### 符合依赖倒置原则（DIP）

### 接口架构严格标准

#### HTTP方法严格限制
**🔴 强制要求**：
- **业务接口**: 所有业务逻辑接口**有且仅**接受POST请求
- **严格禁止**: RESTful风格的GET/PUT/DELETE用于业务逻辑

### 代码质量严格标准
                     
com.ima.infra.utils.bean.XBeanCopier 使用这个进行 bean拷贝
#### 方法长度严格限制

#### 方法长度严格限制
**🔴 强制要求**：
- **入参变动**： 当参数大于 4 个，需要使用对象来承接。避免参数过多
- **所有方法**: 不得超过50行（包含注释和空行）
- **超长处理**: 必须拆分为多个 private 方法或使用设计模式
- **设计模式**: 优先使用 Template Method、Strategy、Factory 模式
- **注释规范**: 禁止使用行尾注释，所有注释必须独立成行
- **方法注释**: 每个方法必须在方法签名前添加注释，格式为 /** ... */，包含功能说明、参数说明、返回值说明
- **字段注释**: 每个字段必须添加 Javadoc 注释，包含字段说明和相关信息
  - **注释结构**: 说明文本 → 空行 → `@see` 标签区域
  - **说明内容**: 根据字段类型包含必要信息（数据库字段、类型、约定等）
  - **Javadoc 标签规范**: `@see` 标签必须单独成行，放在说明文本之后，确保 IDE 正确识别和高亮
  - **字段注释通用格式**：
    ```java
    /**
     * 字段说明（必需，简明扼要）
     * <p>
     * [可选说明] 例如：
     * - 数据库字段：field_name（DO 实体时）
     * - 字段类型：VARCHAR(255)（DO 实体时）
     * - 应用场景：用于...
     * - 约定规范：格式为...
     * - 特殊说明：不能为 null、自动生成等
     * </p>
     *
     * @see package.Class#methodName(Type) [可选说明]
     * @see package.UtilClass#parse(String) [可选说明]
     */
    private String fieldName;
    ```
  - **不同场景示例**：
    ```java
    // DO 实体字段 - 包含数据库信息
    /**
     * 主键ID
     * <p>
     * 数据库字段：id
     * 字段类型：BIGINT
     * 说明：自增主键
     * </p>
     *
     * @see com.ima.infra.commons.base.BaseDO
     */
    @TableId(type = IdType.AUTO)
    private Long id;

    // DTO 字段 - 不需要数据库信息
    /**
     * 用户名
     * <p>
     * 说明：长度限制 3-32 字符
     * </p>
     *
     * @see com.ima.task.dao.campaign.dto.UserDTO
     */
    private String username;

    // 枚举或常量字段 - 说明可选值
    /**
     * 奖励类型编码
     * <p>
     * 可选值：1=积分, 2=实物, 3=徽章, 4=会员
     * </p>
     *
     * @see com.ima.task.common.enums.campaign.RewardType
     */
    private Integer rewardType;
    ```
  - **禁止格式**:
    - ❌ 在说明文本中间嵌入 `@see`
    - ❌ 行尾注释 `private String name; // 用户名`
    - ❌ 多行说明后没有空行就跟 `@see` 标签
- **步骤注释**: 方法体内部代码必须逐步编号注释（如 // 1. 初始化参数、// 2. 执行核心逻辑），覆盖所有逻辑步骤

  - 规则：
  - 每行或每个逻辑步骤，都要写编号注释（// 1. 或 # 1.）。
  - 注释说明的是“做什么”，而不是简单重复代码。

  - 适用于 Java、Go、Python 等语言，只需替换注释符号即可。

    - Java / Go 版本（`//` 注释）
```java
/**
 * 方法：${METHOD_NAME}
 * 描述：${METHOD_DESCRIPTION}
 * <p>
 * 这里可以补充详细说明，例如：
 * <ul>
 *   <li>方法的业务语义</li>
 *   <li>特殊的边界条件或性能特性</li>
 *   <li>调用顺序或使用约定</li>
 * </ul>
 * </p>
 *
 * @param param1 参数说明
 * @param param2 参数说明
 * @return 返回值说明
 * @throws IllegalArgumentException 参数非法时抛出
 * @see java.util.Objects#requireNonNull(Object)
 * @see #otherMethod(String)
 */
public ReturnType ${METHOD_NAME}(ParamType1 param1, ParamType2 param2) {
    // 1. 初始化参数或对象

    // 2. 校验输入数据

    // 3. 执行核心逻辑

    // 4. 处理结果（如保存、返回、输出）

    // 5. 记录日志 / 异常处理

    // 6. 返回最终结果
}

```
    - Go 版本
```GO
// 方法：${METHOD_NAME}
// 描述：${METHOD_DESCRIPTION}
//
// 详细说明（可选）：
//   - 方法的业务语义
//   - 边界条件与性能注意事项
//   - 调用顺序或使用约定
//
// 参数：
//   - param1: 参数说明
//   - param2: 参数说明
// 返回：返回值说明
// 错误：当输入参数非法时返回错误
func ${METHOD_NAME}(param1 ParamType1, param2 ParamType2) (ReturnType, error) {
    // 1. 初始化参数或对象

    // 2. 校验输入数据

    // 3. 执行核心逻辑

    // 4. 处理结果（如保存、返回、输出）

    // 5. 记录日志 / 异常处理

    // 6. 返回最终结果
}

```

    - Python 版本（`#` 注释）
```python
# 方法：${METHOD_NAME}
# 描述：${METHOD_DESCRIPTION}
def ${METHOD_NAME}():
    # 1. 初始化参数或对象
    
    # 2. 校验输入数据
    
    # 3. 执行核心逻辑
    
    # 4. 处理结果（如保存、返回、输出）
    
    # 5. 记录日志 / 异常处理
    
    # 6. 返回最终结果
```
📖 **使用规范**：

* 第 1 行：方法名说明。
* 第 2 行：方法作用描述。
* 每个逻辑步骤用 **数字编号**（保持 1 → N 顺序）。
* 如果步骤内部有多行代码，可以在每行继续加 `//` 或 `#` 解释。

#### 类型安全严格标准

**🔴 严格禁止**：

- `Map<String, Object>` - 严禁在任何场景使用
- `Object` 参数 - 严禁作为方法参数或返回值
- **替代方案**: 必须创建类型安全的专用类

#### 推荐使用的注解

**核心注解**:

- `@Data` - 自动生成getter/setter/toString/equals/hashCode
- `@Value` - 不可变对象，适用于值对象设计
- `@Slf4j` - 自动注入Logger，统一日志规范

**构造函数注解**:

- `@AllArgsConstructor` - 生成全参构造函数
- `@NoArgsConstructor` - 生成无参构造函数
- `@RequiredArgsConstructor` - 为final字段生成构造函数

#### DTO设计严格标准  
**🔴 强制要求**：
- **最小化原则**: 避免创建过多DTO，优先复用现有类
- **严禁嵌套**: DTO内不允许嵌套其他POJO对象
- **扁平化设计**: 所有DTO必须是扁平结构

#### 类注解严格标准
**🔴 强制要求**：
- **作者信息**: 通过MCP Git集成自动获取，严禁手动设置
- **时间信息**: 通过MCP DateTime集成自动获取
- **注解格式**: 标准化类注解包含author、date、description

#### Service层严格标准
**🔴 强制要求**：
- **Interface+Implementation模式**: 所有Service必须有接口和实现类
- **@Override注解**: 所有重写方法必须添加@Override注解
- **Bean 拷贝规范**: 使用统一的Bean拷贝工具，参考[ima-infra-utils](ima-infra-utils)和[ima-common](ima-common)提供的统一的bean 拷贝方法

#### 外部集成严格标准
**🔴 强制要求**：
- **Context7+DeepWiki**: 用于研究正确的jdk17 和遇到问题时候的开发方式

### 编译和部署严格标准

#### 编译成功强制要求
**🔴 强制要求**：
- **必须成功**: 必须在当前所需该的父 pom 下执行 mvn clean package 是成功，且当前修改的子模块是成功的
- **无失败测试**: 所有单元测试必须通过
- **无编译警告**: 消除所有编译警告和错误

### 禁用功能清单
**❌ 明确删除**：
- **过度复杂化**: 避免引入不必要的企业级特性
- **DDD设计**: 禁用领域驱动设计，采用简单三层架构
- **Map<String, Object>**: 任何场景下都禁止使用
- **Object参数**: 禁止作为方法参数或返回值
- **行尾注释**: 所有注释必须独立成行
- **嵌套DTO**: DTO必须扁平化，禁止嵌套POJO
- **过度设计模式**: 避免为了模式而模式



### MCP工具集成
项目集成了以下MCP工具以提供增强功能：
- **sequential-thinking**: 复杂问题分析和决策支持
- **context7**: 技术文档和API查询
- **deepwiki**: 深度技术知识查询
- **git-config**: Git仓库配置管理
- **mcp-datetime**: 时间戳生成
- **yapi-auto-mcp**: API文档自动化
- **其他的 mcp 均按需使用**

## 常用命令

### 构建和打包
```bash
# 跳过测试进行编译
mvn clean package -DskipTests
```


## 架构概览

### 多模块 Maven 项目结构
- 开发模式:
  - 采用分层开发模式，各层职责清晰：
    - xxx-api 层：定义对外暴露的 RPC 接口
    - xxx-api-impl 层：实现 API 层接口，承接 RPC 调用，向下委派至 Biz 层
    - xxx-integration 层：对接第三方系统
    - xxx-dao 层：负责数据库访问
    - Web 层：负责对外 HTTP 接口暴露与请求处理
    - Biz 层：承载业务逻辑，协调 DAO 与 Integration
    - Domain 层：实体与模型定义
    - Common 层：通用配置与工具
  - 系统交互主路径：
    - HTTP 请求链路：Web → Biz → DAO / Integration
    - RPC 调用链路：API → API-Impl → Biz → DAO / Integration

### 核心技术栈

- **Spring Boot** 配合 IMA 基础设施 starter
- **MyBatis-plus** 用于数据库操作，使用 XML mapper
- **MySQL** 主数据库
- **Elasticsearch** 搜索功能
- **Redis** 缓存
- **Dubbo** RPC 服务
- **XXL-Job** 分布式任务调度
- **Nacos** 配置管理
- **RocketMQ** 消息队列
- 优先参考当前项目下的 starter

### 开发模式

1. **实体继承**：所有实体继承自 BaseDO 基类
2. **Repository 模式**：通过 repository 接口和实现类进行数据访问
3. **Service 层**：业务逻辑在 service 实现类中
4. **VO/DTO 模式**：视图和数据传输使用独立对象
5. **MyBatis XML Mapper**：SQL 查询在 resources/mapper/ 下的 XML 文件中

### 配置说明

- **应用配置**: 数据库、ES、Redis 配置在 `application.yml`
- **Apollo 配置**: 环境配置在 `apollo-env.properties`，支持 dev/fat/uat/pro 环境
- **日志配置**: Log4j2 配置文件为 `log4j2.properties` 和 `log4j2.component.properties`
- **启用组件**: 通过 `Application.java` 中的注解启用 IMA 基础设施组件：
  - `@EnableImaDataSources`: 数据源
  - `@EnableImaRedis`: Redis
  - `@EnableImaDubbo`: Dubbo RPC
  - `@EnableImaXxlJob`: 分布式任务调度
  - `@EnableImaNacos`: 配置中心
  - `@EnableImaMq`: 消息队列


### 架构设计规范

#### Web层 - 接口控制器设计
**Controller层职责**：
- **统一入口**：xxx-web提供统一启动入口
- **接口控制器**：xxx-web 处理HTTP请求和响应
- **响应封装**：不做任何接口封装
- 禁止在类中创建内部类

**Controller开发规范**：
- 所有业务接口只接受POST+ResuestBody请求
- 返回值禁止使用 void 方式，如果不做返回，可以使用 EmptyResp
- 使用@Valid进行参数校验
- 自行按需设置用户id，或者 appId


#### Biz层 - 业务逻辑设计
**Service层职责**：
- **业务组装集成**：
  - 提供对 api 的调用
  - 提供对 web 的业务接口调用

**Service开发规范**：
- 必须使用Interface + Implementation模式
- 所有方法不得超过50行
- 所以方法需要有标准的 java 注释
- 禁止使用Map<String, Object>，必须创建类型安全的类
- 使用@Override注解标注重写方法
- 事务管理使用@Transactional注解

#### DAO层 - 数据访问设计与开发规范  
**DAO层职责**：
- **数据访问**：medical-common 提供统一的数据访问组件

**DAO开发规范**：
- **组件优先**: 优先使用 ima-infra 中的工具类和组件
- **基类继承**: 所有mysql实体必须继承 `com.ima.infra.commons.base.BaseDO`
  - 后缀统一使用 DO
- **包扫描**: Mapper 扫描路径为 `com.ima.*.dao.mapper`
- **Mysql Repository 模式**: 使用后缀为 Mapper并增加标准的 mysql-plus注解,不能在 Mapper 上编写任何 sql 
- **Mysql  DAO**：必须完整的集成标准的 mysql-plus ,使用标准的Interface+Implementation模式
  - Interface: DAO extends IService<XXXDO>
  - Implementation: Impl extends ServiceImpl<XxXMapper, XXXDO> implements XxxDAO
  - 使用正确的 mybatis-plus的开发规范

#### 命名规范
- **RPC 接口**: 必须带 `Rpc` 关键字，如 `*RpcResp`, `*RpcReq`
- **方法命名**: 
  - 分页：`page*()`
  - 列表：`list*()`
  - 详情：`detail*()` 
  - 新增：`add*()`
  - 修改：`update*()`
  - 删除：`delete*()`
- **RPC 响应规范**:
  ```java
  /**
   *  必须使用标准的 java 注释
   */
  Result<ViewRpcResp> listByCon(ViewRpcReq viewRpcReq);
  ```





### MCP工具集成开发

#### 自动化类注解生成

**MCP Git集成**：

- 自动获取Git用户信息作为author
- 自动获取提交时间作为创建时间
- 禁止手动设置作者和时间信息

**MCP DateTime集成**：

- 自动生成标准时间戳
- 支持多种日期格式
- 用于类创建时间字段
              
##### **标准类代码注释模板**：

```java
#if (${PACKAGE_NAME} && ${PACKAGE_NAME} != "")
package ${PACKAGE_NAME};
#end
#parse("File Header.java")
/**
 * The {@code ${NAME}} class represents XXX (类的核心职责简述).
 * <p>
 * 特性概述：
 * <ul>
 *   <li>特性一：这里写类的核心特性或语义说明</li>
 *   <li>特性二：应用场景、边界条件</li>
 *   <li>特性三：线程安全性、不可变性等约定</li>
 * </ul>
 * </p>
 *
 * <h2>Usage Examples</h2>
 * <blockquote><pre>
 *     ${NAME} obj = new ${NAME}(...);
 *     obj.doSomething();
 * </pre></blockquote>
 * 
 * 
 * <p>通用约定：
 * <ul>
 *   <li>除非特别说明，传入 {@code null} 将抛出 {@link NullPointerException}</li>
 *   <li>方法调用的返回值/副作用应在具体方法 Javadoc 中详细说明</li>
 * </ul>
 * </p>
 *
 * @implNote 可用于记录实现细节，例如编译器行为、性能优化或版本差异
 *
 * @author  {{通过MCP Git自动获取}}
 * @date    {{通过MCP DateTime自动获取}}
 * @description ${NAME} 类
 * @see     java.lang.Object
 * @see     java.util.Objects
 * @see     java.util.Collections
 * @jls     4.3 Classes and Interfaces
 */
public class ${NAME} {
}

```

```java
#if (${PACKAGE_NAME} && ${PACKAGE_NAME} != "")
package ${PACKAGE_NAME};
#end
#parse("File Header.java")
/**
 * The {@code ${NAME}} interface defines the contract for XXX (接口的核心作用简述).
 * <p>
 * 特性概述：
 * <ul>
 *   <li>特性一：这里写接口的主要职责或语义说明</li>
 *   <li>特性二：典型实现类/应用场景</li>
 *   <li>特性三：线程安全性或可扩展性约定</li>
 * </ul>
 * </p>
 * <h2>Usage Examples</h2>
 * <blockquote><pre>
 *     public class ${NAME}Impl implements ${NAME} {
 *         &#64;Override
 *         public void doSomething() {
 *             // 实现逻辑
 *         }
 *     }
 * </pre></blockquote>
 *
 * <p>通用约定：
 * <ul>
 *   <li>除非特别说明，传入 {@code null} 参数将抛出 {@link NullPointerException}</li>
 *   <li>接口方法应在具体实现类中定义异常语义与副作用</li>
 * </ul>
 * </p>
 * 
 * @implNote 此接口的实现类需遵循约定，例如性能、线程安全性或兼容性要求
 *
 * @author  {{通过MCP Git自动获取}}
 * @date    {{通过MCP DateTime自动获取}}
 * @description ${NAME} 接口
 * @see     java.lang.Object
 * @see     java.util.Objects
 * @jls     9.1 Interfaces
 */
public interface ${NAME} {
}

```


```java
#if (${PACKAGE_NAME} && ${PACKAGE_NAME} != "")
package ${PACKAGE_NAME};
#end
#parse("File Header.java")
/**
 * The {@code ${NAME}} enum defines a fixed set of constants representing XXX (枚举的核心作用简述).
 * <p>
 * 特性概述：
 * <ul>
 *   <li>特性一：枚举常量的含义与使用场景</li>
 *   <li>特性二：是否需要关联字段或方法</li>
 *   <li>特性三：线程安全性与序列化约定</li>
 * </ul>
 * </p>
 *
 * <h2>Usage Examples</h2>
 * <blockquote><pre>
 *     ${NAME} type = ${NAME}.EXAMPLE;
 *     switch (type) {
 *         case EXAMPLE:
 *             // 处理逻辑
 *             break;
 *         default:
 *             break;
 *     }
 * </pre></blockquote>
 *
 * <p>通用约定：
 * <ul>
 *   <li>除非特别说明，枚举常量不应为 {@code null}</li>
 *   <li>若枚举包含方法，需在文档中明确方法的契约语义</li>
 * </ul>
 * </p>
 *
 * @implNote 可记录枚举与数据库映射、序列化行为或扩展策略
 *
 * @author  {{通过MCP Git自动获取}}
 * @date    {{通过MCP DateTime自动获取}}
 * @description ${NAME} 枚举
 * @see     java.lang.Enum
 * @see     java.util.EnumSet
 * @see     java.util.EnumMap
 * @jls     8.9 Enums
 */
public enum ${NAME} {
}

```

```java
#if (${PACKAGE_NAME} && ${PACKAGE_NAME} != "")
package ${PACKAGE_NAME};
#end
#parse("File Header.java")
/**
 * The {@code ${NAME}} annotation is used to XXX (注解的核心作用简述).
 * <p>
 * 特性概述：
 * <ul>
 *   <li>特性一：注解的适用目标（类、方法、字段、参数等）</li>
 *   <li>特性二：注解的保留策略（源码级、编译期、运行时）</li>
 *   <li>特性三：与框架/运行时的交互约定</li>
 * </ul>
 * </p>
 *
 * <h2>Usage Examples</h2>
 * <blockquote><pre>
 *     &#64;${NAME}(value = "example")
 *     public class Demo {
 *     }
 * </pre></blockquote>
 *
 * <p>通用约定：
 * <ul>
 *   <li>除非特别说明，注解参数不允许为 {@code null}</li>
 *   <li>应在具体文档中明确注解与处理器/框架的契约语义</li>
 * </ul>
 * </p>
 *
 * @implNote 注解的解析逻辑通常依赖 APT 或运行时反射，可在此处说明实现注意事项
 *
 * @author  {{通过MCP Git自动获取}}
 * @date    {{通过MCP DateTime自动获取}}
 * @description ${NAME} 注解
 * @see     java.lang.annotation.Target
 * @see     java.lang.annotation.Retention
 * @see     java.lang.annotation.Documented
 * @jls     9.6 Annotation Types
 */
public @interface ${NAME} {
}

```

```java
#if (${PACKAGE_NAME} && ${PACKAGE_NAME} != "")
package ${PACKAGE_NAME};
#end
#parse("File Header.java")
/**
 * The {@code ${NAME}} is a custom unchecked exception (运行时异常).
 * <p>
 * 特性概述：
 * <ul>
 *   <li>用于表示特定业务语义下的运行时错误</li>
 *   <li>不强制调用方捕获，可由全局异常处理器统一处理</li>
 *   <li>应在文档中说明触发场景和处理策略</li>
 * </ul>
 * </p>
 *
 * <h2>Usage Examples</h2>
 * <blockquote><pre>
 *     if (input == null) {
 *         throw new ${NAME}("输入参数不能为空");
 *     }
 * </pre></blockquote>
 *
 * <p>通用约定：
 * <ul>
 *   <li>异常消息应清晰描述错误原因，便于排查</li>
 *   <li>必要时可扩展构造函数以支持 {@code cause} 链</li>
 * </ul>
 * </p>
 *
 * @implNote 建议在全局异常处理器中对该异常进行统一捕获和日志记录
 *
 * @author  {{通过MCP Git自动获取}}
 * @date    {{通过MCP DateTime自动获取}}
 * @description ${NAME} 异常
 * @see     java.lang.RuntimeException
 * @see     java.lang.Exception
 * @jls     11.2 Compile-Time Checking of Exceptions
 */
public class ${NAME} extends RuntimeException {

    /**
     * Constructs a new {@code ${NAME}} with the specified detail message.
     *
     * @param message the detail message
     */
    public ${NAME}(String message) {
        super(message);
    }

    /**
     * Constructs a new {@code ${NAME}} with the specified detail message and cause.
     *
     * @param message the detail message
     * @param cause the cause (which is saved for later retrieval by the {@link Throwable#getCause()} method)
     */
    public ${NAME}(String message, Throwable cause) {
        super(message, cause);
    }
}

```

```java
#parse("File Header.java")
/**
 * 程序入口类
 * <p>
 * The {@code ${NAME}} class serves as the entry point of the application.
 * </p>
 * 
 * <p>
 * 特性概述：
 * <ul>
 *   <li>包含标准的 {@code public static void main(String[] args)} 方法</li>
 *   <li>应用的启动逻辑应从该入口开始</li>
 *   <li>main 方法中不建议包含复杂业务逻辑，应委托给独立的服务类</li>
 * </ul>
 * </p>
 *
 * <h2>Usage Example</h2>
 * <blockquote><pre>
 *     java ${NAME}
 * </pre></blockquote>
 *
 * @implNote 可在此类中添加日志初始化、Spring Boot 启动、或命令行参数解析等逻辑
 *
 * @author  {{通过MCP Git自动获取}}
 * @date    {{通过MCP DateTime自动获取}}
 * @description 程序入口
 */
public class ${NAME} {

    /**
     * The main entry point of the application.
     *
     * @param args the command-line arguments
     */
    public static void main(String[] args) {
        #[[$END$]]#
    }
}

```

```java
#if (${PACKAGE_NAME} && ${PACKAGE_NAME} != "")
package ${PACKAGE_NAME};
#end
#parse("File Header.java")
/**
 * The {@code ${NAME}} record represents an immutable data carrier for XXX (记录类的核心作用简述).
 * <p>
 * 特性概述：
 * <ul>
 *   <li>Record 类是不可变的，所有字段均为 {@code final}</li>
 *   <li>编译器会自动生成构造方法、访问器、{@code equals}、{@code hashCode} 和 {@code toString}</li>
 *   <li>适用于纯数据载体（Data Transfer Object, DTO）场景</li>
 * </ul>
 * </p>
 *
 * <h2>Usage Example</h2>
 * <blockquote><pre>
 *     ${NAME} user = new ${NAME}("Alice", 18);
 *     System.out.println(user.name());
 *     System.out.println(user.age());
 * </pre></blockquote>
 *
 * <p>通用约定：
 * <ul>
 *   <li>Record 字段不能为空时，应在构造方法中添加显式校验</li>
 *   <li>不建议在 Record 中引入复杂业务逻辑</li>
 * </ul>
 * </p>
 *
 * @implNote 可通过定义 compact constructor 来添加参数校验逻辑
 *
 * @author  {{通过MCP Git自动获取}}
 * @date    {{通过MCP DateTime自动获取}}
 * @description ${NAME} 记录类
 * @see     java.lang.Record
 * @jls     8.10 Record Classes
 */
public record ${NAME}() {
}

```


### 🟨 Go 模板
```go
// Package ${PACKAGE_NAME} 
//
// ${NAME} 模块
//
// @author {{通过MCP Git自动获取}}
// @date   {{通过MCP DateTime自动获取}}
// @description ${NAME} 功能实现
package ${PACKAGE_NAME}

// ${NAME} 结构体
type ${NAME} struct {
    // 字段定义
}
```

```go
// Package ${PACKAGE_NAME} 
//
// ${NAME} 接口
//
// @author {{通过MCP Git自动获取}}
// @date   {{通过MCP DateTime自动获取}}
// @description ${NAME} 接口定义
package ${PACKAGE_NAME}

// ${NAME} 接口
type ${NAME} interface {
    // 方法定义
}

```

```go
// Package ${PACKAGE_NAME} 
//
// ${NAME} 枚举常量
//
// @author {{通过MCP Git自动获取}}
// @date   {{通过MCP DateTime自动获取}}
// @description ${NAME} 枚举
package ${PACKAGE_NAME}

const (
    ${NAME}A = iota
    ${NAME}B
    ${NAME}C
)
```

```go
// Package ${PACKAGE_NAME} 
//
// ${NAME} 错误类型
//
// @author {{通过MCP Git自动获取}}
// @date   {{通过MCP DateTime自动获取}}
// @description ${NAME} 自定义错误
package ${PACKAGE_NAME}

import "fmt"

// ${NAME} 错误
type ${NAME} struct {
    msg string
}

func (e *${NAME}) Error() string {
    return fmt.Sprintf("${NAME} error: %s", e.msg)
}

```
         
## python 模板
```python
# -*- coding: utf-8 -*-
"""
${NAME} 模块

@author {{通过MCP Git自动获取}}
@date   {{通过MCP DateTime自动获取}}
@description ${NAME} 功能实现
"""

class ${NAME}:
    """
    ${NAME} 类
    """
    def __init__(self):
        # 属性初始化
        pass

```

```python
# -*- coding: utf-8 -*-
"""
${NAME} 接口 (抽象基类)

@author {{通过MCP Git自动获取}}
@date   {{通过MCP DateTime自动获取}}
@description ${NAME} 接口定义
"""

from abc import ABC, abstractmethod

class ${NAME}(ABC):
    @abstractmethod
    def execute(self):
        pass

```

```python
# -*- coding: utf-8 -*-
"""
${NAME} 枚举类

@author {{通过MCP Git自动获取}}
@date   {{通过MCP DateTime自动获取}}
@description ${NAME} 枚举
"""

from enum import Enum

class ${NAME}(Enum):
    OPTION_A = 1
    OPTION_B = 2
    OPTION_C = 3

```

```python
# -*- coding: utf-8 -*-
"""
${NAME} 自定义异常类

@author {{通过MCP Git自动获取}}
@date   {{通过MCP DateTime自动获取}}
@description ${NAME} 异常
"""

class ${NAME}(Exception):
    def __init__(self, message: str):
        super().__init__(message)


```
         
```python
# -*- coding: utf-8 -*-
"""
${NAME} 主函数脚本

@author {{通过MCP Git自动获取}}
@date   {{通过MCP DateTime自动获取}}
@description 程序入口
"""

def main():
    pass

if __name__ == "__main__":
    main()

```

## Task Master AI Instructions
**Import Task Master's development workflow commands and guidelines, treat as if import is in the main CLAUDE.md file.**
@./.taskmaster/CLAUDE.md