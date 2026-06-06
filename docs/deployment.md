# 部署与运行指南

本文档面向需要部署、启动和演示系统的用户。

## 一、最短 Docker 部署

### 1. 进入项目目录

```bash
cd "/Users/mengxianghe/Documents/Codex项目/工程合同AI审查助手"
```

### 2. 启动服务

```bash
docker compose up --build -d
```

### 3. 访问地址

| 服务 | 地址 |
|------|------|
| 前端 | http://127.0.0.1:5173 |
| 后端 API | http://127.0.0.1:8000 |
| Swagger 文档 | http://127.0.0.1:8000/docs |

### 4. 停止服务

```bash
docker compose down            # 停止并保留数据
docker compose down -v         # 停止并清除所有数据
```

## 二、本地开发部署

### 1. 启动数据库

```bash
docker compose up -d postgres
```

### 2. 启动后端

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

> 当前后端兼容 Python 3.9+，推荐使用 Python 3.11 或 3.12。如果系统 `python3` 版本较老，请使用明确的版本号（如 `python3.11`）创建虚拟环境。

如果需要 OCR 识别扫描件：

- **macOS**: `brew install tesseract tesseract-lang`
- **Ubuntu / Debian**: `sudo apt-get install -y tesseract-ocr tesseract-ocr-chi-sim`

#### 大模型配置（可选）

启动前设置环境变量：

```bash
REVIEW_PROVIDER=openai_compatible \
LLM_BASE_URL=https://your-llm-endpoint/v1 \
LLM_API_KEY=your_api_key \
LLM_MODEL=your_model_name \
uvicorn app.main:app --reload
```

或在系统启动后通过前端 `/admin/settings` 页面配置。

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

如果需要指定后端地址：

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

## 三、默认账号

系统启动后自动初始化管理员账号：

- 用户名：`admin`
- 密码：`Admin123456`

## 四、服务组成

| 服务 | 镜像 | 端口 | 说明 |
|------|------|------|------|
| postgres | postgres:16 | 5432 | 数据库，数据卷 `postgres_data` |
| backend | 自建 | 8000 | 启动时自动执行 Alembic 迁移、初始化管理员 |
| frontend | Nginx 静态服务 | 5173 | 通过 Nginx 代理 `/api` 到后端 |

数据持久化使用两个 Docker 数据卷：

- `postgres_data` — 数据库数据
- `backend_uploads` — 上传的合同文件

## 五、启动后自检

1. 打开前端页面，使用 `admin` 登录
2. 进入"用户管理"，确认有页面和数据
3. 进入"系统设置"，确认模型配置表单可见
4. 进入"规则管理"，确认规则列表正常
5. 上传一份 PDF 合同，确认跳转到详情页
6. 执行审查，确认风险项和摘要生成
7. 查看上传版本列表，确认版本号递增
8. 导出 PDF 报告
9. 进入"操作日志"，确认有操作记录
10. 对同一合同重新审查，确认版本对比可用

## 六、演示推荐流程

1. 用 `admin` 登录
2. 进入"规则管理"展示规则可配置
3. 上传自有的 PDF 合同文件
4. 进入合同详情页执行审查，展示：
   - 基础字段提取
   - 风险识别结果（规则命中 + AI 补充）
   - 审查摘要
   - 上传版本列表
   - 版本差异对比
   - 指定版本报告导出
5. 进入"操作日志"展示留痕能力

## 七、常见问题

### 端口被占用

- **5173 被占用**: 修改 `docker-compose.yml` 中前端端口映射为 `"8080:80"`
- **5432 被占用**: 修改 `docker-compose.yml` 中数据库端口映射为 `"15432:5432"`

### 前端能打开但数据为空

- 确认后端容器健康
- 确认前端容器已启动
- 确认 Nginx 正常代理 `/api`
- 确认浏览器 token 有效

### 扫描件无法识别

- 确认后端已安装 `pymupdf`、`tesseract-ocr`、`tesseract-ocr-chi-sim`
- 确认 PDF 清晰度足够
- 大页数扫描件走后台 OCR，需等待解析状态变为 `completed`

### 摘要仍像模板/模型未生效

- 确认 `REVIEW_PROVIDER=openai_compatible`
- 确认 `LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL` 已配置
- 确认模型接口是 OpenAI 兼容的 `/chat/completions`
- 模型调用失败会自动降级为 `mock`，`provider` 记录为 `mock_fallback`

### LLM 补充风险未出现

- 确认 `REVIEW_PROVIDER=openai_compatible`
- 确认模型输出的是 JSON 数组格式
- 确认模型未输出与已有规则重复的风险项
- 格式不合法的输出会被服务端直接丢弃

## 八、升级流程

```bash
docker compose down
docker compose up --build -d
```

后端启动时会自动执行最新的 Alembic 迁移。
