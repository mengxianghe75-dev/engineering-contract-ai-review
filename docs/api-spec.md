# API 说明

本文档面向联调和演示说明，使用尽量直白的表达。

## 一、认证接口

### `POST /auth/login`

说明：

- 用户登录
- 成功后返回访问令牌和当前用户信息

请求体示例：

```json
{
  "username": "admin",
  "password": "Admin123456"
}
```

响应体示例：

```json
{
  "access_token": "jwt-token",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "admin",
    "is_active": true,
    "roles": ["admin"]
  }
}
```

### `GET /auth/me`

说明：

- 获取当前登录用户信息
- 需要 `Authorization: Bearer <token>`

## 二、用户管理接口

以下接口仅 `admin` 可用。

### `GET /users`

说明：

- 获取用户列表

### `POST /users`

说明：

- 新建用户

请求体示例：

```json
{
  "username": "zhangsan",
  "password": "Reviewer123",
  "is_active": true,
  "role_codes": ["reviewer"]
}
```

### `PATCH /users/{user_id}`

说明：

- 编辑用户
- 可用于启用/停用用户

请求体示例：

```json
{
  "username": "lisi",
  "is_active": false,
  "role_codes": ["viewer"]
}
```

## 三、系统设置接口

以下接口仅 `admin` 可用。

### `GET /system-settings`

说明：

- 获取当前系统设置
- 前端页面不会回显 API Key 明文
- 只返回 `llm_api_key_configured=true/false`
- 同时返回：
  - `effective_provider`
  - `llm_ready`
  - `status_message`
  - `last_test_success`
  - `last_test_message`
  - `last_tested_at`
  - `last_summary_call_success`
  - `last_summary_call_message`
  - `last_summary_called_at`
  - `last_risk_call_success`
  - `last_risk_call_message`
  - `last_risk_called_at`

### `PATCH /system-settings`

说明：

- 更新模型 provider 和大模型配置
- 配置保存到数据库，保存后立即生效

请求体示例：

```json
{
  "review_provider": "openai_compatible",
  "llm_base_url": "https://api.openai.com/v1",
  "llm_model": "gpt-4o-mini",
  "llm_timeout_seconds": 30,
  "llm_api_key": "example-api-key",
  "clear_llm_api_key": false
}
```

### `POST /system-settings/test`

说明：

- 测试当前模型配置是否可连通
- `mock` 模式会直接返回成功
- `openai_compatible` 会发起一次最小摘要测试

## 四、规则管理接口

以下接口仅 `admin` 可用。

### `GET /review-rules`

说明：

- 获取规则列表

### `POST /review-rules`

说明：

- 新增规则

请求体示例：

```json
{
  "name": "付款条款风险",
  "rule_code": "payment_terms_risk",
  "risk_type": "付款条件偏严或付款节点不明确，可能导致回款滞后。",
  "condition_type": "contains_any",
  "condition_value": "[\"结清\",\"无预付款\"]",
  "risk_level": "high",
  "suggestion": "补充预付款和节点支付约定。",
  "priority": 10,
  "is_active": true,
  "contract_type_scope": null
}
```

### `PATCH /review-rules/{rule_id}`

说明：

- 编辑规则
- 可用于启用/停用
- 可通过 `is_deleted=true` 进行软删除

## 五、合同管理接口

### `GET /contracts`

说明：

- 获取合同列表
- 支持筛选

支持查询参数：

- `contract_name`
- `project_name`
- `owner_id`
- `status`
- `category`
- `tag`
- `risk_level`
- `created_from`
- `created_to`
- `include_archived`

返回中常用字段：

- `contract_name`
- `project_name`
- `owner_username`
- `category`
- `tags`
- `status`
- `archived_at`
- `risk_levels`

### `GET /contracts/{contract_file_id}`

说明：

- 获取合同详情

返回中常用字段：

- `owner_id`
- `owner_username`
- `category`
- `tags`
- `status`
- `archived_at`
- `updated_by`
- `updated_at`
- `latest_version_id`
- `latest_version_no`

### `PATCH /contracts/{contract_file_id}`

说明：

- 更新文档基础信息
- 需要 `admin` 或 `reviewer`

请求体示例：

```json
{
  "original_filename": "施工总包合同.pdf",
  "owner_id": 1,
  "category": "施工合同",
  "tags": ["重点项目", "华东"],
  "archived": false
}
```

### `POST /contracts/upload`

说明：

- 上传合同 PDF
- 可选通过 `version_of_contract_id` 将文件上传为现有合同组的新版本
- 仅 `admin / reviewer` 可用

### `POST /contracts/{contract_file_id}/review`

说明：

- 触发合同审查
- 每次触发都会生成新的审查版本
- 仅 `admin / reviewer` 可用
- 摘要生成支持两种 provider：
  - `mock`
  - `openai_compatible`
- 风险补充识别支持 OpenAI 兼容模型
- LLM 风险输出要求为 JSON 数组，服务端会做结构校验
- 合并顺序为：规则 -> 内置启发式 -> LLM 补充
- 当真实模型调用失败时，会自动降级回 `mock` 摘要

### `GET /contracts/{contract_file_id}/report`

说明：

- 导出报告
- 所有角色均可查看和导出
- 支持 `version_id` 参数

## 六、审查版本接口

### `GET /contracts/{contract_id}/versions`

说明：

- 获取同一合同组下的上传版本列表
- `contract_id` 可传该合同组任意一个文件版本 ID

返回常用字段：

- `version_no`
- `triggered_by_username`
- `trigger_source`
- `overall_risk_level`
- `risk_count`
- `summary`
- `created_at`

### `GET /contracts/{contract_id}/versions/{version_id}`

说明：

- 获取单个上传版本详情
- `version_id` 为目标文件版本 ID
- 返回中还会包含：
  - `summary_provider`
  - `summary_success`
  - `summary_message`
  - `risk_provider`
  - `risk_success`
  - `risk_message`
- 这些字段用于记录该版本生成时，模型在“摘要生成”和“风险补充”两个环节中的真实参与状态

### `GET /contracts/{contract_id}/versions/compare/result`

说明：

- 对比同一合同组下两个上传版本
- 适合演示“重新上传合同版本后哪些字段和风险发生了变化”

请求参数：

- `base_version_id`
- `target_version_id`

以上两个参数传文件版本 ID。

返回重点字段：

- `summary_changed`
- `runtime_changed`
- `summary_degraded`
- `risk_degraded`
- `degradation_events`
- `summary_recovered`
- `risk_recovered`
- `recovery_events`
- `runtime_changes`
- `field_changes`
- `added_risks`
- `removed_risks`
- `level_changed_risks`

## 七、操作日志接口

### `GET /review-logs`

以下接口仅 `admin` 可用。

说明：

- 查询系统关键操作日志

支持筛选参数：

- `operator_id`
- `action_type`
- `created_from`
- `created_to`

当前记录范围：

- 上传合同
- 编辑合同
- 触发审查
- LLM 摘要链路降级
- LLM 摘要链路恢复
- LLM 风险补充链路降级
- LLM 风险补充链路恢复
- LLM 风险补充成功
- LLM 风险补充降级
- 导出报告
- 新增规则
- 编辑规则
- 启用/停用规则
- 新增用户
- 编辑用户
- 启用/停用用户

## 八、风险项结构说明

审查结果中的每条风险项可能包含：

- `code`
- `title`
- `level`
- `matched_text`
- `description`
- `recommendation`
- `source`
- `rule_id`
- `match_detail`

`match_detail` 示例：

```json
{
  "condition_type": "contains_any",
  "condition_value": "[\"结清\",\"无预付款\"]",
  "priority": 10,
  "text_span": "无预付款"
}
```

## 九、角色权限说明

- `admin`
  - 全部权限
- `reviewer`
  - 上传、审查、查看、导出
- `viewer`
  - 只读查看、导出
