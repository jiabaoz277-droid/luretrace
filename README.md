# 路迹（对话式路亚决策助手 MVP）

用对话帮助路亚用户完成一次出钓决策，并覆盖「计划 → 临场排障 → 战报复盘」完整闭环。

当前为 **第 2 阶段**：在出钓决策基础上，补齐临场排障（FR-05）、个人装备与偏好（FR-06）、战报与复盘（FR-07）。钓点收藏提醒、图片识鱼、海水路亚、真实数据源、正式视觉等在后续阶段。

## 技术栈

- 后端：Python 3.11 + FastAPI + Pydantic + SQLAlchemy(SQLite) + pytest
- 前端：Next.js + TypeScript + Tailwind CSS（H5 对话切片）
- 模型：真实模型（DeepSeek，OpenAI 兼容）+ 规则兑底；决策/排障/复盘结构化规则为确定性代码

## 目录结构

```text
backend/        # FastAPI 后端
  app/          # api / core / models / schemas / services
  tests/        # mock 自动化测试
frontend/       # Next.js 对话界面
docs/           # PRD、技术栈手册、技术适配声明、阶段文档
data/           # SQLite 数据库（自动生成，不入库）
.env.example    # 环境变量模板（复制为 .env 后填写）
```

## 快速启动

### 1. 后端（端口 8003）

```bash
cd backend
python3.11 -m venv .venv            # 首次
.venv/bin/pip install -r requirements.txt   # 首次
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8003
```

### 2. 前端（端口 3002）

```bash
cd frontend
npm install                         # 首次
npm run dev -- -p 3002
```

浏览器打开 <http://localhost:3002>。

> 端口说明：8003 避开系统已占用的 8000/8001/8002；前端 3002 避开已占用的 3000（如端口空闲可改回，需同步改后端 `CORS_ORIGINS`）。

## 环境变量

复制 `.env.example` 为 `.env`（勿提交真实密钥）：

| 变量 | 说明 |
| --- | --- |
| `ENV` | `prod` 时启用强制登录、数据库默认切到 `/tmp/data/app.db`；本地 `dev` |
| `INVITE_CODES` | 邀请码（逗号分隔），登录用；一个码 = 一个独立用户 |
| `TOKEN_SECRET` | 登录 token 签名密钥（生产必填，用 `openssl rand -hex 32` 生成） |
| `ADMIN_TOKEN` | 提示词管理后台令牌（访问 `/admin` 时填入，用 `openssl rand -hex 16` 生成） |
| `MODEL_API_KEY` | 模型 Key（开发期可空，验收前提供） |
| `MODEL_BASE_URL` / `MODEL_NAME` | 模型接口（接入真实 LLM 后使用） |
| `QWEATHER_KEY` | 和风天气 Key（不填则天气降级为 mock） |
| `QWEATHER_API_HOST` | 和风天气专属 API Host（控制台-设置中查看） |
| `DATABASE_URL` | 本地默认 `sqlite:///./data/fishing.db`；生产默认 `sqlite:////tmp/data/app.db` |
| `CORS_ORIGINS` | 前端来源，默认 `http://localhost:3000,http://localhost:3002` |
| `SENTRY_DSN` | 错误监控（可选） |
| `STORAGE_PROVIDER` / `S3_*` | 对象存储备份（可选；未配置时退化为本地 `/tmp` 副本） |

## 提示词管理后台

后端内置了可在线编辑的「提示词 / 回复文案」管理页，用于不重新部署就调整系统提示词、追问话术、合规提醒、安全/技巧/误区条目等：

- 地址：后端 URL + `/admin`（本地 `http://127.0.0.1:8003/admin`）
- 在页面顶部填入 `ADMIN_TOKEN` 后即可编辑，保存即时生效
- 内容保存在数据库 `prompt_overrides` 表（随数据备份一起持久化）

## 登录

正式环境需要邀请码登录：前端输入邀请码 → 后端 `/api/v1/auth/login` 换取 token → 后续请求带 `Authorization: Bearer <token>`。所有数据接口按当前用户隔离（A 看不到 B 的数据）。

## 线上部署（火山引擎 veFaaS）

- 前端（正式入口）：<https://saukkdce3ioiapisnhd2c.apigateway-cn-beijing.volceapi.com/>
- 后端（API 直连）：<https://seqhldkjqtj9oocse7tho.apigateway-cn-beijing.volceapi.com/>
- 登录方式：邀请码登录（邀请码由产品经理分发，对应环境变量 `INVITE_CODES`）
- 数据保障：预留实例常驻 + 每 5 分钟备份到对象存储 TOS + 启动自动恢复
- 部署命令：
  ```bash
  # 后端
  cd backend && vefaas deploy --command "python -m uvicorn app.main:app --host 0.0.0.0 --port 8000" --port 8000 --yes
  # 前端（BACKEND_URL 在 build 时固化到 rewrites）
  cd frontend && BACKEND_URL="https://seqhldkjqtj9oocse7tho.apigateway-cn-beijing.volceapi.com" vefaas deploy --appId 96035ee6f4ee --buildCommand "npm run build && cp -r .next/static .next/standalone/.next/static && cp -r public .next/standalone/public" --outputPath ".next/standalone" --command "node server.js" --port 3000 --yes
  ```

## 运行测试（第一层 mock 自动化）

```bash
cd backend
.venv/bin/python -m pytest -q
```

覆盖：意图/槽位解析、决策引擎（含安全优先）、SSE 端到端、方案卡持久化。

## 槽位抽取验收评测（FR-01）

100 条语料（50 标准 + 50 边界/难例），验证地点/目标鱼/时间三槽位：

```bash
cd backend
.venv/bin/python -m eval.eval_slots --offline   # 仅规则，离线
.venv/bin/python -m eval.eval_slots            # 规则 + LLM 增强
```

结果（2026-08-25）：标准语料三槽位完全正确率 100%（目标 ≥90%）；规则+LLM 难例 100%。

## 第二层真实冒烟（待 Key）

接入真实模型后，用 `curl -N` 验证 SSE：

```bash
curl -N -X POST http://127.0.0.1:8003/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"明早杭州周边两小时，想打翘嘴"}'
```

确认：首个 chunk 时间达标、事件以 `done` 或 `error` 正确收尾、失败时错误结构统一。

## 接入真实模型（第二层冒烟）

代码已就绪：填了 Key 后，槽位抽取 + 自然语言回复自动切换为真实模型；决策引擎和安全提示仍由确定性代码保证。未填 Key 时用规则 + 模板兜底，不影响运行。

1. 申请 Key（二选一）：
   - DeepSeek：<https://platform.deepseek.com> → 创建 API Key（默认 `deepseek-chat`）
   - 火山方舟（豆包）：<https://console.volcengine.com/ark> → 开通并创建推理接入点
2. 配置：
   ```bash
   cp .env.example .env
   # 编辑 .env，填入 MODEL_API_KEY；用火山方舟则同时改 BASE_URL/MODEL_NAME
   ```
3. 重启后端，确认接入：
   ```bash
   curl http://127.0.0.1:8003/api/v1/model/status   # configured 应为 true
   ```
4. 真实模型冒烟：
   ```bash
   cd backend
   .venv/bin/python -m pytest tests/test_real_model_smoke.py -v
   ```

> 注意：`.env` 已在 `.gitignore` 中，密钥不会被提交；对话、日志、命令输出中不回显密钥。

## 验收清单（第 1 阶段）

- [ ] 打开 <http://localhost:3002>
- [ ] 输入「明早杭州周边两小时，想打翘嘴」→ 流式输出并得到方案卡
- [ ] 输入「明早想去路亚」→ 一次只追问一个缺口
- [ ] 补齐地点/目标鱼后得到方案
- [ ] 输入「雷暴天能去吗」→ 首屏出现安全提示而非鼓励出钓
- [ ] 刷新页面后历史方案仍可查询（数据持久化）

## 上线验收清单（产品经理照做）

- [ ] 打开前端地址（https 开头），看到邀请码登录页
- [ ] 输入邀请码能登录；输错被拒并有明确提示
- [ ] 用两个不同邀请码登录，A 看不到 B 的记录
- [ ] 核心链路跑通：输入「明早杭州周边两小时，想打翘嘴」→ 出方案
- [ ] 手机上也能用（HTTPS 下定位正常）
- [ ] 刷新页面、关掉重开，之前的记录还在
