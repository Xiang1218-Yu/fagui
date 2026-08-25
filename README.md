# 法规变更情报与影响研判平台

面向合规团队的法规变更监测闭环平台：**来源白名单采集 → 快照留痕 → 变更识别 → 法规归并 → 人工复核与影响研判 → 订阅通知**。

系统只采集**白名单来源**下的公开页面与附件，遵从目标站点的 `robots.txt`，并对每次抓取的正文与附件保留可追溯快照，帮助分析师判断哪次变化需要处理、并向业务团队说明结论从何而来。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | Python 3.12 · FastAPI · SQLAlchemy 2 |
| 数据库 | PostgreSQL 16 |
| 任务队列 | Celery + Redis（beat 定时调度，worker 执行采集） |
| 采集 | httpx（HTTP 抓取）· BeautifulSoup/lxml（HTML 解析）· pypdf/python-docx（附件解析） |
| 前端 | React 18 + TypeScript + Vite · React Router · Axios |

> 采集仅使用 HTTP 抓取与 HTML/文档解析库，**不接入任何云爬虫、BaaS 或浏览器自动化服务**。

## 功能模块

- **来源管理**：管理员维护允许采集的来源、类型、抓取频率、host 白名单、robots 遵从与附件抓取开关。
- **采集运行**：按频率（Celery beat）或手动触发采集；记录页面/附件数量、检测到的变更、robots 拦截数与快照。
- **快照留痕**：每次抓取的原始字节与抽取文本均落盘存储，附 SHA-256 哈希，可追溯。
- **法规归并**：对同一法规被多来源转载的情况，按标题归一化生成归并键合并为一条法规，展开可见各来源出处。
- **变更对比**：基于内容哈希识别正文/附件变化，生成相似度、逐行 diff、变更摘要与新旧快照并排对比。
- **复核 / 影响研判**：每条变更进入人工复核队列，分析师确认/忽略并记录影响等级、受影响业务与研判结论。
- **订阅通知**：按关键词、来源、最低影响等级订阅，命中变更即生成站内通知。

## 采集与合规约束

1. **来源白名单**：仅抓取来源 `allowed_hosts`（含来源自身 host）内的 URL，越界目标直接跳过（`HostNotAllowed`）。
2. **robots 遵从**：抓取前读取并缓存目标站 `robots.txt`，`can_fetch` 为假则跳过（`RobotsBlocked`）并计数。
3. **附件解析**：PDF（pypdf）、DOCX（python-docx）、TXT 抽取纯文本；其余类型保留原始快照但标注不解析。
4. **变更判定**：页面按抽取正文哈希、附件按原始字节哈希比对最近一次快照，变化则生成 `ChangeEvent` 并入复核队列。

## 快速启动（Docker 推荐）

```bash
docker compose up -d --build
# 初始化演示数据（来源白名单 + 订阅）
docker compose exec backend python -m app.seed
```

- 后端 API：http://localhost:8000 （文档 http://localhost:8000/docs ）
- 前端界面：http://localhost:5174 （宿主机 5173 若被占用，compose 已映射到 5174）
- PostgreSQL 暴露在宿主机 `5433`，Redis 暴露在 `6380`（避免与本机默认端口冲突）。

登录后使用演示账号（`app/seed.py` 生成）：

- `admin / admin123`：**管理员**，可增删改来源、触发采集。
- `analyst / analyst123`：**分析师**，来源页只读，可复核 / 影响研判 / 订阅。

在「来源管理」页对某个来源点击 **立即采集** 即可完成一次同步抓取，随后在「采集运行 / 变更对比 / 复核 / 通知」页看到闭环结果。

## 权限与安全

- **认证**：所有业务 API 需登录（JWT Bearer）。密码经 bcrypt 加盘存储，登录签发 JWT。
- **管理员权限**：来源的增删改（`POST/PUT/DELETE /sources`）与手动采集（`POST /sources/{id}/crawl`）仅管理员可用，分析师访问返回 403；前端对分析师隐藏相应操作并标注“只读”。
- **重定向再校验**：抓取时禁用自动跳转，手动逐跳解析，**每个中间地址与最终目标都重新校验 host 白名单与 robots**，跳转无法绕过白名单（越界目标抛 `HostNotAllowed`）。
- **正文链接采集**：从来源入口页解析站内文章链接（可选 CSS 选择器 `link_selector`、上限 `max_links`），仅跟进白名单内链接，逐条作为法规文档采集。
- **邮件通知**：邮件订阅通过真实 SMTP 投递（`app/services/email_service.py`），并在通知上记录投递状态（sent / failed / skipped）；未配置 SMTP 时降级为“仅站内记录”。可用 `POST /api/subscriptions/test-email` 验证 SMTP 配置。

相关 SMTP / 账号环境变量（见 `app/core/config.py`）：`SMTP_HOST`、`SMTP_PORT`、`SMTP_USER`、`SMTP_PASSWORD`、`SMTP_USE_TLS`、`SMTP_FROM`、`ADMIN_PASSWORD`、`ANALYST_PASSWORD`、`SECRET_KEY`。

## 本地开发（不使用 Docker）

后端：

```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# 需本地可用的 PostgreSQL 与 Redis，并相应设置环境变量
export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/fagui
uvicorn app.main:app --reload
# 另开终端启动 Celery（可选，定时采集用）
celery -A app.core.celery_app.celery_app worker --loglevel=info
celery -A app.core.celery_app.celery_app beat --loglevel=info
```

前端：

```bash
cd frontend
npm install
npm run dev   # 默认代理 /api 到 http://localhost:8000
```

## 目录结构

```
backend/
  app/
    core/        配置、数据库会话、Celery 实例
    models/      SQLAlchemy 模型
    schemas/     Pydantic DTO
    crawler/     robots、fetcher（白名单）、parser、diff、storage
    services/    crawl_service（采集编排 + 变更识别 + 归并 + 通知）
    tasks/       Celery 任务（定时/按需采集）
    api/routes/  sources / runs / changes / reviews / regulations / subscriptions / dashboard
    main.py      FastAPI 应用
    seed.py      演示数据
frontend/
  src/
    api/         Axios 客户端
    pages/       各业务页面
    types/       TS 类型
    App.tsx      布局与路由
docker-compose.yml
```

## 主要 API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET/POST/PUT/DELETE | `/api/sources` | 来源 CRUD |
| POST | `/api/sources/{id}/crawl` | 立即采集（同步） |
| GET | `/api/runs` | 采集运行记录 |
| GET | `/api/runs/{id}/snapshots` | 运行快照 |
| GET | `/api/changes` `/api/changes/{id}/snapshots` | 变更列表与并排对比 |
| GET/POST | `/api/reviews` `/api/reviews/{id}/decide` | 复核队列与影响研判 |
| GET | `/api/regulations` `/api/regulations/{id}/documents` | 法规归并与来源出处 |
| GET/POST/DELETE | `/api/subscriptions` | 订阅管理 |
| GET/POST | `/api/notifications` | 通知列表与已读 |
| GET | `/api/dashboard/stats` | 总览统计 |
