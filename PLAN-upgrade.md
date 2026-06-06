# 升级实施计划（已完成）

> 本文档为历史记录，所有里程碑均已完成。

## 总体原则

- 严格按 Milestone 推进，不跨阶段开发
- 每个阶段完成后验证通过再进入下一阶段
- 每个阶段都补充了 README 和相关 docs
- 所有后端业务逻辑放在 service 层

## Milestone 1：现状审查与重构准备 — 已完成

交付了现状分析、模块拆分方案、数据模型调整建议。

## Milestone 2：用户与权限系统 — 已完成

实现了用户/角色/user_roles 表及迁移，用户管理接口，JWT + RBAC，前端登录态管理。

## Milestone 3：文档管理增强 — 已完成

实现了 contract_files 的 owner_id/category/tags/status 字段，列表筛选与归档功能。

## Milestone 4：规则系统 — 已完成

实现了 review_rules 表、规则管理接口、规则执行逻辑（规则优先 + AI 补充）、规则管理页面。

## Milestone 5：审查版本与日志 — 已完成

实现了 review_version 模型、历史版本查询、操作日志记录。

## Milestone 6：前端后台页面 — 已完成

实现了用户管理页、规则管理页、日志页、系统设置页、文档管理增强页面。

## Milestone 7：联调、文档、演示准备 — 已完成

完成了 Docker / 本地运行验证，补齐了 README / docs。
