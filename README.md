# 🧠 AI Codebase Explainer

> **RAG-powered tool that lets you ask questions about any codebase in plain English.**
> Upload a ZIP or paste a GitHub URL — get instant, context-aware answers.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61dafb?logo=react)](https://react.dev)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-0.5-orange)](https://www.trychroma.com)
[![Groq](https://img.shields.io/badge/Groq-Llama3_70B-purple)](https://console.groq.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
[![Deploy on Render](https://img.shields.io/badge/Deploy-Render-46E3B7?logo=render)](https://render.com)
[![Deploy on Vercel](https://img.shields.io/badge/Deploy-Vercel-black?logo=vercel)](https://vercel.com)

---

## 📸 Overview

AI Codebase Explainer is a full-stack application that transforms how developers understand unfamiliar codebases. Instead of manually reading through hundreds of files, you can ask natural language questions and get precise, sourced answers.

**Built entirely on free-tier technologies:**

| Layer | Technology | Cost |
|-------|-----------|------|
| LLM Inference | Groq (Llama3-70B) | Free tier |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` | Local / Free |
| Vector DB | ChromaDB (persistent) | Free / Self-hosted |
| Backend | FastAPI + Python 3.11 | Free |
| Frontend | React + Vite + TypeScript | Free |
| Deployment | Render (backend) + Vercel (frontend) | Free tier |

---

## ✨ Features

### Core
- 📁 **ZIP Upload** — Upload any project as a `.zip` file
- 🔗 **GitHub Integration** — Paste any public GitHub repo URL
- 🔍 **Semantic Search** — Vector similarity search across all code chunks
- 💬 **Chat Interface** — Conversational Q&A with full chat history

### Analysis Modes
| Mode | Description |
|------|-------------|
| 💬 **General** | Ask any question about the codebase |
| 📖 **Explain** | Get deep explanations of specific code |
| 🔄 **Flow** | Trace execution paths step-by-step |
| 🐛 **Issues** | Find bugs, anti-patterns, security risks |
| 🏗️ **Architecture** | Understand design patterns and structure |

### Engineering
- ⚡ **LRU Query Cache** — Repeated questions served instantly
- 🌲 **File Explorer** — Visual tree with search, language detection
- 📄 **File Viewer** — Code viewer + per-file AI explanations
- 🎯 **Smart Chunking** — Splits at class/function boundaries
- 🔒 **Session Management** — Isolated sessions per codebase
- 🚀 **Background Indexing** — Non-blocking vector index builds

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Frontend (React)                    │
│  UploadPanel → MainWorkspace → FileExplorer + ChatPanel  │
└──────────────────────┬──────────────────────────────────┘
                       │  REST API
┌──────────────────────▼──────────────────────────────────┐
│                   FastAPI Backend                         │
│                                                          │
│  /ingest/zip      /ingest/github                        │
│  /chat            /explain/file                         │
│  /session/{id}    /file/{id}                            │
└────────┬───────────────────┬────────────────────────────┘
         │                   │
┌────────▼──────┐   ┌────────▼──────────────────────────┐
│   ChromaDB    │   │         Groq API                   │
│ (Vector Store)│   │   Llama3-70B-8192 Inference        │
│               │   │   6000 tokens/min (free tier)      │
│ - Embeddings  │   └────────────────────────────────────┘
│ - Similarity  │
│   Search      │   ┌────────────────────────────────────┐
└───────────────┘   │   Sentence Transformers (Local)    │
                    │   all-MiniLM-L6-v2 Embeddings      │
                    │   Runs 100% locally, zero API cost  │
                    └────────────────────────────────────┘
```

### RAG Pipeline

```
Input (ZIP/GitHub URL)
  │
  ▼
Code Parser
  ├── Filter: ignored dirs, binary files, unsupported extensions
  ├── Detect: language per file extension
  └── Extract: clean UTF-8 text content
  │
  ▼
Smart Chunker
  ├── Small files (<60 lines): single chunk
  ├── Large files: detect class/function boundaries
  └── Fallback: sliding window with overlap
  │
  ▼
Embedding Model (local, sentence-transformers)
  └── 384-dim dense vectors per chunk
  │
  ▼
ChromaDB (cosine similarity index)
  │
  ▼
Query: User question → embed → top-k retrieval
  │
  ▼
Groq LLM: question + retrieved context → answer
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- [Free Groq API key](https://console.groq.com)

### 1. Clone

```bash
git clone https://github.com/yourusername/ai-codebase-explainer.git
cd ai-codebase-explainer
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
nano .env

# Run the server
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Set VITE_API_URL=http://localhost:8000

# Run development server
npm run dev
```

Open **http://localhost:5173** in your browser.

### 4. Docker Compose (Optional)

```bash
# Copy and configure environment
cp backend/.env.example backend/.env
# Add your GROQ_API_KEY to backend/.env

docker compose up --build
```

---

## ⚙️ Configuration

### Backend (`.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | *(required)* | Your Groq API key |
| `GROQ_MODEL` | `llama3-70b-8192` | LLM model |
| `CHUNK_SIZE` | `800` | Characters per chunk |
| `CHUNK_OVERLAP` | `100` | Overlap between chunks |
| `TOP_K_RESULTS` | `6` | Chunks retrieved per query |
| `CACHE_TTL_SECONDS` | `3600` | Query cache TTL |
| `MAX_FILE_SIZE_MB` | `50` | Max ZIP upload size |

### Frontend (`.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://localhost:8000` | Backend API URL |

---

## 🧪 Running Tests

```bash
cd backend

# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

---

## 🌐 Deployment

### Backend → Render (Free)

1. Fork this repository
2. Go to [render.com](https://render.com) → New Web Service
3. Connect your GitHub repo
4. Set **Root Directory**: `backend`
5. Set **Build Command**: `pip install -r requirements.txt`
6. Set **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
7. Add environment variable: `GROQ_API_KEY=your_key`
8. Add a **Disk** (1GB, mount path: `/opt/render/project/src/data/vector_store`)

Or use the included `render.yaml` with Render's Blueprint feature.

### Frontend → Vercel (Free)

```bash
# Install Vercel CLI
npm i -g vercel

cd frontend
# Set VITE_API_URL to your Render backend URL in .env
vercel --prod
```

Or connect your GitHub repo directly in the [Vercel dashboard](https://vercel.com/new).

---

## 📁 Project Structure

```
ai-codebase-explainer/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + middleware
│   │   ├── api/
│   │   │   └── routes.py        # All API endpoints
│   │   ├── core/
│   │   │   ├── config.py        # Pydantic settings
│   │   │   └── vector_store.py  # ChromaDB wrapper
│   │   └── services/
│   │       ├── parser.py        # ZIP/GitHub parser + chunker
│   │       ├── llm.py           # Groq LLM service
│   │       └── session.py       # Session + LRU cache
│   ├── tests/
│   │   └── test_main.py         # Comprehensive tests
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Root component + state
│   │   ├── components/
│   │   │   ├── UploadPanel.tsx  # Landing / upload UI
│   │   │   ├── MainWorkspace.tsx# Layout with sidebar
│   │   │   ├── FileExplorer.tsx # File tree component
│   │   │   ├── ChatPanel.tsx    # Chat interface
│   │   │   └── FileViewer.tsx   # Code + AI explanation
│   │   ├── utils/
│   │   │   ├── api.ts           # Axios API client
│   │   │   └── types.ts         # TypeScript types
│   │   └── styles/
│   │       └── globals.css      # Tailwind + custom CSS
│   ├── package.json
│   ├── vite.config.ts
│   └── .env.example
│
├── docker-compose.yml
├── render.yaml
├── vercel.json
└── README.md
```

---

## 💡 Sample Prompts for Demo

Try these when demoing the project:

```
"What is the overall architecture of this codebase?"
"How does a request travel through the system from entry point to response?"
"What are the main security vulnerabilities or code quality issues?"
"How would a new developer set up and run this project locally?"
"What APIs are exposed? Describe each endpoint and its purpose."
"What testing strategy is used? Are there unit or integration tests?"
"Trace the data flow — how does data move through this application?"
"What are the main dependencies and why are they used?"
"Identify any performance bottlenecks or improvement opportunities."
"How is authentication/authorization handled in this project?"
```

---

## 🔧 Chunking Strategy

The parser uses a multi-tier strategy:

1. **Small files** (≤60 lines): Single chunk — keep full context
2. **Logical boundary detection**: Parse class/function definitions per language
   - Python: `class`, `def`, `async def`
   - JS/TS: `class`, `function`, `const fn = () =>`
   - Java/C#: method signatures with access modifiers
   - Go: `func`, `type ... struct`
   - Rust: `fn`, `impl`, `struct`
3. **Sliding window fallback**: Character-based with configurable overlap
4. **Sub-chunking**: Oversized logical sections get windowed

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch: `git checkout -b feat/amazing-feature`
3. Commit changes: `git commit -m 'feat: add amazing feature'`
4. Push to branch: `git push origin feat/amazing-feature`
5. Open a Pull Request

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- [Groq](https://groq.com) for blazing-fast free LLM inference
- [ChromaDB](https://www.trychroma.com) for the excellent open-source vector DB
- [Sentence Transformers](https://sbert.net) for local embedding models
- [FastAPI](https://fastapi.tiangolo.com) for the elegant Python web framework

---

<p align="center">Built with ❤️ as a production-grade portfolio project</p>
