# 工程合同 AI 审查助手

一个面向工程合同场景的 AI 审查系统演示项目，覆盖合同上传、文本提取、规则审查、AI 补充审查、风险摘要、版本留痕、权限管理和后台管理等流程。

本仓库定位为 **源码开放的产品演示项目**，用于展示工程合同审查自动化、企业内部 AI 工具、规则引擎和多人权限系统的设计与实现能力。

## 作者

- 作者：孟祥和
- 微信：mengxianghe75

可合作方向：

- 工程合同 AI 审查系统定制
- 工程建设企业 AI 工具定制
- 企业知识库 / RAG 应用开发
- 内部业务系统 AI 化改造
- 私有化部署与流程自动化
- FastAPI + Vue 企业级原型开发

## 许可说明

本项目采用 **PolyForm Noncommercial License 1.0.0** 发布。

你可以将本项目用于学习、研究、非商业评估和个人测试。

未经作者书面授权，不得将本项目或其衍生版本用于：

- 商业项目或客户交付
- SaaS 服务、托管服务或收费系统
- 私有化部署、咨询实施或商业集成
- 二次销售、白标包装或作为商业产品的一部分分发
- 去除作者署名、版权声明或许可说明后重新发布

商业使用请阅读 [COMMERCIAL_LICENSE.md](COMMERCIAL_LICENSE.md) 并联系作者。

严格来说，本项目属于 source-available / 源码可见项目，不是 OSI 定义下的无限制开源项目。

## 免责声明

本系统输出的风险识别、审查摘要、修改建议和导出报告仅供辅助参考，不构成法律意见、工程咨询意见或最终合同决策依据。

在真实业务场景中使用前，请由具备资质的法务、律师、造价、工程管理或相关专业人员进行复核。

请勿上传真实客户合同、涉密合同、个人隐私数据或其他敏感材料到公开演示环境。

## 核心能力

| 模块 | 说明 |
| --- | --- |
| 登录与权限 | JWT 认证，admin / reviewer / viewer 三级角色 |
| 用户管理 | 用户列表、新增用户、编辑用户、启用停用、角色分配 |
| 合同管理 | PDF 上传、OCR 解析、归属分类、标签筛选、归档 |
| 审查引擎 | 规则优先 + AI 补充，支持 OpenAI 兼容模型配置 |
| 规则管理 | 后台可配置规则，支持 keyword / regex / contains_any / contains_all |
| 版本管理 | 同一合同多版本上传，支持历史审查版本查看 |
| 操作日志 | 上传、审查、导出、规则变更、用户变更等关键操作留痕 |
| 报告导出 | PDF 格式审查报告导出 |

## 技术栈

前端：

- Vue 3
- Vite
- Element Plus
- Pinia
- Axios

后端：

- FastAPI
- SQLAlchemy 2.x
- Pydantic
- Alembic
- PostgreSQL
- JWT

## 快速启动

确保本机已安装 Docker Desktop，然后执行：

```bash
docker compose up --build -d
```

访问地址：

- 前端：http://127.0.0.1:5173
- 后端 API：http://127.0.0.1:8000
- Swagger：http://127.0.0.1:8000/docs

默认管理员：

```text
admin / Admin123456
```

健康检查：

```bash
curl http://127.0.0.1:8000/health
```

停止服务：

```bash
docker compose down
```

## 本地开发

后端：

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

前端：

```bash
cd frontend
npm install
npm run dev
```

## 项目结构

```text
工程合同AI审查助手/
├── backend/              # FastAPI 后端
│   ├── app/
│   │   ├── api/routes/   # 接口路由
│   │   ├── core/         # 配置与安全
│   │   ├── db/           # 数据库会话
│   │   ├── models/       # ORM 模型
│   │   ├── schemas/      # Pydantic 数据模型
│   │   └── services/     # 业务逻辑层
│   ├── alembic/          # 数据库迁移
│   ├── tests/            # 后端测试
│   └── uploads/          # 本地上传目录，公开仓库不包含真实文件
├── frontend/             # Vue 3 前端
│   ├── src/
│   │   ├── api/          # HTTP 请求封装
│   │   ├── composables/  # 组合式函数
│   │   ├── stores/       # 状态管理
│   │   ├── views/        # 页面组件
│   │   └── router/       # 路由配置
├── docs/                 # 项目文档
├── docker-compose.yml    # Docker Compose 编排
├── LICENSE               # 非商业许可
├── COMMERCIAL_LICENSE.md # 商业授权说明
└── README.md
```

## 文档

- [产品规格](docs/product-spec.md)
- [部署与运行](docs/deployment.md)
- [接口说明](docs/api-spec.md)
- [规则引擎](docs/rule-engine.md)

## 发布前检查

公开发布前请确认：

- `backend/uploads/` 中没有真实合同或客户材料。
- 仓库中没有 `.env`、密钥、Token、数据库备份或内部配置。
- README 中的作者信息、联系方式和商业授权入口已替换。
- 默认管理员密码仅用于本地演示，生产部署必须修改。
- 若你要发布到 GitHub / Gitee，请确认仓库描述中也写明“非商业许可 / 商业使用需授权”。
