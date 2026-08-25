# 路亚问问（对话式路亚决策助手 MVP）

用对话帮助路亚用户完成一次出钓决策：输入自然语言，得到「是否建议出钓 + 时间窗口 + 标点/水层/拟饵/手法」的可执行方案。

当前为 **第 1 阶段**：出钓决策最小闭环（Web/H5 纵向切片）。临场排障、战报复盘、装备偏好、真实数据源、正式视觉等在后续阶段。

## 技术栈

- 后端：Python 3.11 + FastAPI + Pydantic + SQLAlchemy(SQLite) + pytest
- 前端：Next.js + TypeScript + Tailwind CSS（最小对话切片）
- 模型：本阶段用规则 + 模板 mock（无 Key）；真实 LLM 接入点为 `backend/app/services/llm.py`

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
| `MODEL_API_KEY` | 模型 Key（开发期可空，验收前提供） |
| `MODEL_BASE_URL` / `MODEL_NAME` | 模型接口（接入真实 LLM 后使用） |
| `DATABASE_URL` | 默认 `sqlite:///<项目>/data/fishing.db` |
| `CORS_ORIGINS` | 前端来源，默认 `http://localhost:3000,http://localhost:3002` |

## 运行测试（第一层 mock 自动化）

```bash
cd backend
.venv/bin/python -m pytest -q
```

覆盖：意图/槽位解析、决策引擎（含安全优先）、SSE 端到端、方案卡持久化。

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
