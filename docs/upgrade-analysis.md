# Milestone 1 现状审查与升级建议

## 1. 当前系统现状

### 1.1 实际目录结构

项目当前采用前后端分离结构：

- `backend/`
  - `app/api/routes`: `auth`、`contracts`、`health`
  - `app/services`: 合同上传/解析、审查、OCR、报告、用户初始化
  - `app/models`: `user`、`contract_file`、`contract_parse_result`、`contract_review_result`
  - `app/schemas`: 认证、合同、审查响应
  - `alembic/versions`: 已有用户表、合同上传表、审查结果表和解析状态迁移
- `frontend/`
  - `src/views`: 登录、合同列表、上传、详情
  - `src/router`: 基础登录校验和页面路由
  - `src/api/http.js`: Axios 实例与 token 注入

### 1.2 当前已完成能力

后端已完成：

- 用户登录接口 `POST /auth/login`
- 默认管理员初始化
- PDF 上传和基础校验
- PDF 文本层提取
- OCR 回退识别
- 大页数扫描件后台 OCR
- 合同列表查询
- 合同详情查询
- 合同审查执行
- 审查摘要生成
- 审查报告导出 PDF

前端已完成：

- 登录页
- 合同列表页
- 合同上传页
- 合同详情页
- OCR 处理中自动轮询
- 重新审查
- 报告下载

### 1.3 当前可复用模块

建议直接复用：

- `backend/app/services/contract_service.py`
- `backend/app/services/contract_review_service.py`
- `backend/app/services/ocr_service.py`
- `backend/app/services/report_service.py`
- `backend/app/services/mock_llm_service.py`
- `backend/app/models/contract_file.py`
- `backend/app/models/contract_parse_result.py`
- `backend/app/models/contract_review_result.py`
- `frontend/src/views/LoginPage.vue`
- `frontend/src/views/ContractListPage.vue`
- `frontend/src/views/ContractUploadPage.vue`
- `frontend/src/views/ContractDetailPage.vue`
- `frontend/src/api/http.js`
- `frontend/src/router/index.js`

这些模块构成了当前最小闭环主链路，不建议推翻重写。

### 1.4 当前结构存在的限制

- 用户模型仍是单表 + `is_admin` 布尔字段，不适合扩展为 RBAC
- JWT 仅写入 `sub=username`，没有角色与用户状态上下文
- `api/deps.py` 只有数据库依赖，没有鉴权与权限依赖
- `contract_files` 目前仅代表上传文件，尚未具备文档管理属性
- `contract_review_results` 为每份合同只保留一份当前审查结果，不支持版本历史
- 风险规则写死在 `contract_review_service.py` 中，不支持后台配置
- 前端权限逻辑仅判断本地是否存在 token，不支持角色态控制
- 项目当前没有 `docs/` 目录，升级分析和产品/接口文档尚未补齐

## 2. 升级架构建议

### 2.1 升级原则

- 基于现有最小闭环扩展，不推翻已有上传、解析、审查、导出链路
- 严格按 Milestone 推进，不跨阶段开发
- 后端继续保持 `route -> service -> model/schema` 分层
- 权限控制同时覆盖接口层和服务层
- 前端通过统一路由和统一权限显示逻辑扩展后台页面

### 2.2 升级后的模块图

```text
Frontend
├── Auth / Permission
│   ├── Login
│   ├── Auth Store
│   └── Route Guard
├── Contract Workspace
│   ├── Contract List
│   ├── Contract Upload
│   ├── Contract Detail
│   └── Contract Versions
└── Admin Console
    ├── User Management
    ├── Rule Management
    └── Operation Logs

Backend
├── Auth Module
├── User & Role Module
├── Contract Module
│   ├── Upload / Parse
│   ├── Document Metadata
│   └── Report Export
├── Review Module
│   ├── Rule Engine
│   ├── AI Summary
│   └── Version History
└── Audit Module
    └── Operation Logs

Database
├── users / roles / user_roles
├── contract_files / contract_parse_results / contract_review_results
├── review_rules
├── review_versions
└── review_logs
```

### 2.3 建议保留与补强边界

保留：

- 上传、OCR、合同详情、审查、导出整体链路
- 现有 4 个核心业务表
- 现有前端 4 个业务页面

补强：

- 认证模型从 `is_admin` 升级到角色体系
- 合同文件扩展为文档管理对象
- 审查结果扩展为“当前结果 + 历史版本”
- 风险规则从代码常量升级为数据库配置
- 页面访问从 token 校验升级到角色权限校验

## 3. 数据库变更建议

### 3.1 现有表

当前已有：

- `users`
- `contract_files`
- `contract_parse_results`
- `contract_review_results`

### 3.2 建议新增表

#### `roles`

- `id`
- `code`
- `name`
- `description`

#### `user_roles`

- `id`
- `user_id`
- `role_id`

#### `review_rules`

- `id`
- `name`
- `risk_type`
- `condition_type`
- `condition_value`
- `risk_level`
- `suggestion`
- `priority`
- `is_active`
- `contract_type_scope`
- `created_by`
- `created_at`
- `updated_at`

#### `review_versions`

- `id`
- `contract_file_id`
- `version_no`
- `summary`
- `risk_items`
- `review_snapshot`
- `reviewed_by`
- `review_source`
- `created_at`

#### `review_logs`

- `id`
- `user_id`
- `action`
- `target_type`
- `target_id`
- `detail`
- `created_at`

### 3.3 建议新增字段

#### `users`

- 保留现有字段
- 后续逐步弱化 `is_admin` 的业务职责，迁移到角色表

#### `contract_files`

- `owner_id`
- `category`
- `tags`
- `status`
- `is_archived`
- `archived_at`
- `updated_at`

#### `contract_review_results`

- 建议保留为“当前最新结果”
- 如有需要，可增加与最新版本的关联字段

### 3.4 数据库设计建议

- 不建议当前阶段新增独立 `contracts` 主表，优先扩展 `contract_files`
- `tags` 初期可用 `JSON` 或 `TEXT`，避免过早拆复杂标签体系
- `review_versions` 负责历史留痕，`contract_review_results` 继续负责详情页快速读取
- 所有结构变更统一走 Alembic migration

## 4. 建议重构点

以下是当前最不利于升级扩展的点：

1. 用户权限模型过于简单，仅有 `is_admin`
2. 路由层当前没有统一的当前用户和角色依赖
3. 审查规则硬编码在 `contract_review_service.py`
4. 审查结果是单版本覆盖式更新
5. 前端未接入 `Pinia`，登录态和权限态管理能力不足
6. 前端菜单和路由未接入角色权限元数据
7. 现有 README 与实际阶段状态存在偏差，后续需要持续同步

## 5. Milestone 2 准备修改的文件清单

后端：

- `backend/app/models/user.py`
- `backend/app/models/role.py`
- `backend/app/models/user_role.py`
- `backend/app/models/__init__.py`
- `backend/app/schemas/auth.py`
- `backend/app/schemas/user.py`
- `backend/app/schemas/role.py`
- `backend/app/services/user_service.py`
- `backend/app/services/permission_service.py`
- `backend/app/api/deps.py`
- `backend/app/api/routes/auth.py`
- `backend/app/api/routes/users.py`
- `backend/app/main.py`
- `backend/alembic/versions/<timestamp>_add_roles_and_user_status.py`

前端：

- `frontend/package.json`
- `frontend/src/main.js`
- `frontend/src/router/index.js`
- `frontend/src/api/http.js`
- `frontend/src/api/users.js`
- `frontend/src/stores/auth.js`
- `frontend/src/stores/permission.js`
- `frontend/src/views/LoginPage.vue`
- `frontend/src/views/admin/UserManagementPage.vue`

文档：

- `README.md`
- `docs/product-spec.md`
- `docs/api-spec.md`

## 6. Milestone 1 验证方法

### 启动命令

本阶段不要求修改业务代码，不需要额外启动新服务。若需复核现有功能，可使用：

- `docker compose up --build`
- 或本地分别启动前后端

### 验证步骤

1. 确认当前项目目录中已有前后端分层结构
2. 确认后端已存在认证、合同、健康检查路由
3. 确认后端已存在 OCR、审查、报告服务
4. 确认前端已存在登录、列表、上传、详情页面
5. 确认现状分析文档已形成
6. 确认已输出升级架构建议、数据库变更建议和 Milestone 2 文件清单

### 失败时排查建议

- 如果代码结构与文档不一致，优先以代码实际实现为准
- 如果文档未覆盖实际现状，补充现有模块与边界说明后再进入下一阶段
- 如果现有表结构与业务命名冲突，优先保留现有核心表并通过新增字段扩展
