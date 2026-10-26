# 智服云 · 电商智能客服系统

基于原型「智服云」落地的电商智能客服：Vue 3 + Element Plus 前端，FastAPI + LangGraph 后端，MySQL / SQLite 业务库，Milvus（含 Lite）向量库，本地 Qwen（OpenAI 兼容接口，默认可 Mock）。

## 已实现范围

1. **登录 / 注册**：JWT 鉴权  
2. **运营概览**：KPI、趋势、渠道、知识命中、质检分布、实时预警  
3. **客服工作台**：公众号 / 企微 / App / Web 多渠道会话；LangGraph 推荐答案；人工确认发送  
4. **知识库**：FAQ（含相似问）与文档上传/分片/预览  
5. **知识查询**：混合/语义/关键词检索、AI 聚合答案、召回调试与反馈  
6. **质检系统**：规则配置、发起抽检、复核队列、LangGraph 质检打分  
7. **系统设置**：模型/渠道开关/质检通知/团队配置（渠道为配置面模拟，非真实 webhook）  

## 快速启动（本机演示默认）

默认使用 **SQLite + Milvus Lite + LLM Mock**，无需 Docker / GPU。

```bash
# 后端
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # 已有 .env 可跳过
uvicorn app.main:app --host 0.0.0.0 --port 18766 --reload

# 前端（另开终端）
cd frontend
npm install
npm run dev
```

打开 [http://127.0.0.1:18765](http://127.0.0.1:18765)  
演示账号：`admin` / `admin123`

## 本机已有 MySQL + Milvus（推荐你这样接）

项目已支持直连你现成的 MySQL / Milvus，不必再用 SQLite / Milvus Lite。

1. MySQL 建库：

```sql
CREATE DATABASE zhifu DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

2. 配置后端环境变量：

```bash
cd backend
cp .env.mysql.example .env
# 编辑 .env：改 DATABASE_URL 里的账号密码端口；VECTOR_URI 指向 Milvus
```

示例：

```env
DATABASE_URL=mysql+pymysql://root:你的密码@127.0.0.1:3306/zhifu?charset=utf8mb4
VECTOR_URI=http://127.0.0.1:19530
MILVUS_COLLECTION=kb_chunks
LLM_MOCK=true
```

3. 启动（与上面相同）：

```bash
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 18766 --reload
```

首次启动会自动建表并写入演示账号 `admin` / `admin123`、示例会话与 FAQ。

**WSL 注意：** 若 MySQL / Milvus 跑在 Windows Docker 里、后端跑在 WSL，`127.0.0.1` 可能连不上。可把主机改成 Windows 宿主机 IP（WSL2 常见：`cat /etc/resolv.conf` 里的 `nameserver`），例如：

```env
DATABASE_URL=mysql+pymysql://root:密码@172.x.x.x:3306/zhifu?charset=utf8mb4
VECTOR_URI=http://172.x.x.x:19530
```

也可用仓库自带 Compose 再起一套：`docker compose up -d`（端口 3306 / 19530）。

本地 Qwen 可用 Ollama / vLLM；有模型后设 `LLM_MOCK=false`。

## 目录

- `frontend/` — Vue3 + Element Plus（若依风格侧栏布局）  
- `backend/` — FastAPI、LangGraph、RAG、鉴权  
- `docker-compose.yml` — MySQL + Milvus 栈  
- `uploads/index_04b7.html` — 原始原型参考  

## API 前缀

`/api/v1/auth` · `/api/v1/workspace` · `/api/v1/knowledge`
