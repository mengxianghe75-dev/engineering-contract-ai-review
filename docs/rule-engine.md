# 规则引擎说明

## 目标

规则引擎用于将审查规则从代码常量中抽离到数据库，使后台可以配置和维护规则，并在审查时优先执行规则，再由 AI 能力做补充。

## 所在层次

规则引擎位于后端 `service` 层：

- 模型：`backend/app/models/review_rule.py`
- 规则引擎：`backend/app/services/rule_engine_service.py`
- 管理服务：`backend/app/services/review_rule_service.py`
- 审查接入点：`backend/app/services/contract_review_service.py`

## 数据结构

`review_rules` 字段：

- `id`
- `name`
- `rule_code`
- `risk_type`
- `condition_type`
- `condition_value`
- `risk_level`
- `suggestion`
- `priority`
- `is_active`
- `is_deleted`
- `contract_type_scope`
- `created_by`
- `created_at`
- `updated_at`

## 支持的规则类型

- `keyword`
- `regex`
- `contains_any`
- `contains_all`

## 当前内置规则覆盖方向

当前演示种子会补齐一批工程合同常见风险规则，覆盖以下方向：

- 付款节点与回款条件
- 工期责任与赶工约束
- 单方解除与结算后处理
- 质保金与质保期起算
- 发票前置与结算周期
- 验收标准与验收通过条件
- 垫资施工与包干价调整
- 材料价格波动分担
- 安全事故责任分配
- 索赔权限制
- 争议解决与管辖地点
- 分包转包限制

这些规则仅作为开箱即用的基础规则集，后台仍可继续新增、停用、编辑，不影响历史审查结果。

## 执行流程

1. 解析合同文本并提取基础字段
2. 读取启用且未删除的规则
3. 按 `priority` 升序执行
4. 命中后产出规则风险项
5. 执行原有 AI 风险识别逻辑
6. 以规则结果优先进行合并去重
7. 写入 `contract_review_results.risks`

## 合并策略

- 规则结果先进入最终结果集
- AI 结果后进入
- 以 `code + title` 作为去重键
- 如规则与 AI 产生相同风险键，保留规则结果

## 命中原因

规则命中后应保存命中原因。当前风险项中已保留：

- `rule_id`
- `code`
- `matched_text`
- `match_detail`

其中 `match_detail` 当前记录：

- `condition_type`
- `condition_value`
- `priority`
- `text_span`

这保证后续做规则调试、审计和版本对比时可以解释“为什么命中”。

## 多规则命中策略

- 同一段文本可以命中多个不同规则
- 不应因为 `matched_text` 相同就强行只保留一条
- 当前只对相同 `code + title` 的风险项去重
- 存储层保留细粒度风险项，展示层后续可再做聚合

## 同优先级规则排序

- 先按 `priority` 升序
- 再按 `id` 升序

这样同优先级时执行顺序稳定且可预测。

## 历史结果保留原则

- 规则停用或软删除，只影响后续新审查
- 历史审查结果不回写、不重算、不删除
- 后续进入版本系统后，历史版本应继续保留当时命中的规则信息

## 未来扩展方向

- 在 `condition_type` 上增加更复杂的表达式类型
- 将 `condition_value` 从文本扩展为结构化 JSON DSL
- 引入多字段条件、AND/OR 组合、阈值比较
- 增加规则命中调试信息和执行日志
- 增加规则版本化管理
