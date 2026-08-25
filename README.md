# 法规变更情报与影响研判平台

面向合规团队的监管网站变更监测闭环平台：管理员维护采集来源白名单与抓取频率，系统按 robots 规则采集公开页面及附件、留存可追溯快照、识别正文与附件变化、按文号/标题归并同一法规，变更进入人工复核队列；分析师在「来源管理 → 采集运行 → 变更对比 → 复核队列 → 影响研判 → 订阅通知」各页面完成闭环。

## 技术栈

- **后端**：Python 3.12 / FastAPI / SQLAlchemy 2 / PostgreSQL / Celery + Redis（Beat 定时调度）
- **采集**：httpx（HTTP 抓取）+ BeautifulSoup（HTML 解析）+ pypdf（PDF）+ zipfile/XML（DOCX），不依赖云爬虫、BaaS 或浏览器自动化
- **前端**：React 18 + TypeScript + Vite + Ant Design 5

## 快速启动（完整技术栈，Docker Compose）

```bash
docker compose up --build
```

- 前端：http://localhost:5173 （Nginx 容器，代理 API）
- 后端 API：http://localhost:8000 （Swagger 文档 /docs）
- 含 PostgreSQL、Redis、API 服务、Celery Worker、Celery Beat 五个服务；首次启动自动建表并写入演示数据。

## 本地开发（免外部依赖模式）

无需 PostgreSQL/Redis，使用 SQLite + 任务同步执行，适合本地调试：

```bash
# 后端
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
DATABASE_URL="sqlite:///./data/app.db" CRAWL_EAGER=1 uvicorn app.main:app --reload --port 8000

# 前端（另开终端）
cd frontend
npm install
npm run dev   # http://127.0.0.1:5173
```

生产/完整栈连接 PostgreSQL 与 Redis 时使用 `docker-compose.yml` 中的环境变量（`DATABASE_URL`、`REDIS_URL`、`CRAWL_EAGER=false`）。

## 演示账号与闭环演练

| 账号 | 密码 | 角色 |
| --- | --- | --- |
| admin | admin123 | 管理员（来源维护、采集配置） |
| analyst | analyst123 | 分析师（复核、研判、订阅） |

内置一个演示监管站点（由后端挂载在 `/demo-site/`，含 robots.txt、通知正文、DOCX 附件、征求意见页与禁抓目录），用于演练完整闭环：

1. **来源管理**：查看白名单来源（robots 遵守、路径前缀白名单、抓取频率），点击「立即采集」——首次采集建立基线快照；
2. 点击「模拟法规修订（演示）」：演示站新增第十五/十六条、更新 DOCX 附件、新增年度检查计划；
3. 再次「立即采集」：采集运行页可见日志（含 robots 禁抓目录被拦截记录）；
4. **变更对比**：查看正文逐行 diff、附件变更提示、新旧快照哈希与原始文件下载（结论来源可追溯）；
5. **复核队列**：认领任务并出具结论（确认 / 需跟踪 / 误报）；
6. **影响研判**：登记受影响团队、业务条线、风险等级与行动项并发布；
7. **订阅通知**：变更、复核结论、研判发布按订阅规则（事件/来源/关键词/渠道）生成通知，铃铛实时提醒。

## 主要能力与实现位置

| 能力 | 实现 |
| --- | --- |
| 来源白名单与频率管理 | [sources.py](backend/app/api/sources.py)、[models.py](backend/app/models.py)（Source） |
| robots.txt 遵守与 Crawl-delay | [robots.py](backend/app/services/robots.py) |
| HTTP 采集（同源 + 路径白名单 + BFS 深度控制） | [crawl.py](backend/app/services/crawl.py)、[fetcher.py](backend/app/services/fetcher.py) |
| HTML/PDF/DOCX 正文与附件解析 | [parser.py](backend/app/services/parser.py) |
| 不可变快照留存（原始文件 + 抽取文本 + 哈希） | [storage.py](backend/app/services/storage.py)、Snapshot 模型 |
| 正文/附件/标题变更识别与逐行 diff | [differ.py](backend/app/services/differ.py)、[changes.py](backend/app/api/changes.py) |
| 同一法规归并（文号正则 + 标题相似度） | [dedupe.py](backend/app/services/dedupe.py) |
| 人工复核队列（认领/结论） | [review.py](backend/app/api/review.py) |
| 影响研判（团队/业务/风险/行动项） | [impact.py](backend/app/api/impact.py) |
| 订阅与通知分发（站内/邮件/Webhook 模拟） | [notifier.py](backend/app/services/notifier.py)、[subscriptions.py](backend/app/api/subscriptions.py) |
| Celery 定时调度 | [celery_app.py](backend/app/celery_app.py)、[crawl_tasks.py](backend/app/tasks/crawl_tasks.py) |
| 前端闭环页面 | [frontend/src/pages](frontend/src/pages) |

## 目录结构

```
fagui_Odysseus/
├── docker-compose.yml          # postgres + redis + backend + worker + beat + frontend
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py             # FastAPI 入口（启动自动建表/种子数据/挂载演示站点）
│       ├── config.py database.py security.py celery_app.py seed.py
│       ├── models.py schemas.py
│       ├── services/           # robots/fetcher/parser/differ/dedupe/notifier/crawl/storage
│       ├── tasks/              # Celery 任务
│       └── api/                # auth/sources/crawls/regulations/changes/review/impact/subscriptions/notifications/dashboard/demo
└── frontend/
    ├── Dockerfile nginx.conf
    └── src/ (pages / api / auth / components)
```
