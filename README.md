# 智服云 · 电商智能客服系统

基于原型「智服云」落地的电商智能客服：Vue 3 + Element Plus 前端，FastAPI + LangGraph 后端，MySQL / SQLite 业务库，Milvus（含 Lite）向量库，本地 Qwen（OpenAI 兼容接口，默认可 Mock）。

## 今日已实现范围

1. **登录 / 注册**：JWT 鉴权  
2. **客服工作台**：公众号 / 企微 / App / Web 多渠道会话；LangGraph 问答智能体生成推荐答案；人工确认后发送  
3. **知识库**：FAQ 增删改查（含相似问）；文档上传（PDF / Word / txt）、自动分片、向量索引、分片与原始文件预览  

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

## MySQL + Milvus 正式依赖

```bash
docker compose up -d
```

修改 `backend/.env`：

```env
DATABASE_URL=mysql+pymysql://root:root@127.0.0.1:3306/zhifu
VECTOR_URI=http://127.0.0.1:19530
LLM_MOCK=false
LLM_BASE_URL=http://127.0.0.1:11434/v1
LLM_MODEL=qwen2.5:7b
EMBEDDING_BASE_URL=http://127.0.0.1:11434/v1
EMBEDDING_MODEL=qwen3-embedding:0.6b
```

本地 Qwen 可用 Ollama / vLLM 等提供 OpenAI 兼容接口。

## 目录

- `frontend/` — Vue3 + Element Plus（若依风格侧栏布局）  
- `backend/` — FastAPI、LangGraph、RAG、鉴权  
- `docker-compose.yml` — MySQL + Milvus 栈  
- `uploads/index_04b7.html` — 原始原型参考  

## API 前缀

`/api/v1/auth` · `/api/v1/workspace` · `/api/v1/knowledge`
