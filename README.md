# ⚡ DocInsights — AI Document Intelligence (RAG) Platform

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Render-46E3B7?style=for-the-badge&logo=render&logoColor=white)](https://docinsights.onrender.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

Upload documents, ask questions, and get **source-cited** answers with complete transparency. **DocInsights** is a production-grade Retrieval-Augmented Generation (RAG) platform featuring **explainable retrieval** — every answer shows the exact document chunks and relevance scores used to generate it.

---

### 🌐 Live Demo

👉 **[Launch DocInsights Live App](https://docinsights.onrender.com)**

> **Note:** The live demo is hosted on a free cloud instance with an ephemeral disk. To preserve privacy, uploaded documents and indices reset on server redeployments.

---

## 🚀 Key Features

* **🔍 Semantic Search & Retrieval:** High-performance vector search powered by an on-disk FAISS index.
* **💬 RAG Document Chat:** Ask complex questions across single or multiple documents with precise citations and source chunk verification.
* **📊 Document Insights:** Automatic generation of executive summaries, key bullet takeaways, and operational risk detection.
* **⚖️ Multi-Document Comparison:** Compare up to 5 documents side-by-side and export downloadable PDF comparison reports.
* **🔑 Bring Your Own Key (BYOK):** Seamless OpenAI compatibility. No key required for basic semantic search & extractive analysis; bring your own API key for full generative LLM answers.
* **🛡️ Privacy-First:** User API keys are held only in browser session memory — never saved to disk, database, or server logs.

---

## 🛠️ The Engineering Architecture

* **FAISS Flat → IVF Adaptive Index:** Begins with exact `IndexFlatIP` (cosine similarity via normalized inner product). When the collection surpasses 256 vectors, it automatically upgrades into an `IndexIVFFlat` for sub-linear search latency.
* **Resilient LLM Wrapper:** All model calls pass through an LRU cache (256 items, 1-hour TTL), exponential-backoff retries, and strict worker thread timeouts with graceful extractive fallbacks.
* **Zero-Config Local Embeddings:** Runs embeddings locally using `all-MiniLM-L6-v2` (384-dimensional) by default, ensuring immediate out-of-the-box functionality without paid embedding APIs.
* **Bounded Multi-Document Context:** Multi-document chat employs over-fetching with deduplication, document chunk caps, and a token-budgeted round-robin context assembler (≤6,000 token limit across top chunks).
* **Unified Single-Container Deployment:** FastAPI backend serves both the REST API and the optimized React SPA from a single lightweight Docker container.

---

## 💻 Tech Stack

| Component | Technology |
|---|---|
| **Backend** | Python 3.11, FastAPI, Uvicorn, SQLAlchemy (async), SQLite |
| **Frontend** | React 18, Vite, Tailwind CSS, Lucide Icons |
| **Vector Index** | FAISS (Facebook AI Similarity Search), sentence-transformers |
| **Document Parsers** | PyMuPDF (fitz), pdfplumber, python-docx |
| **Container & CI/CD** | Docker multi-stage build, GitHub, Render Cloud |

---

## 🏃 Run It Locally

### Prerequisites
* Node.js 18+ & npm
* Python 3.10+ (or Docker)

### Option 1: Running with Docker (Recommended)
```bash
docker build -t docinsights .
docker run -p 7860:7860 docinsights
```
Open **[http://localhost:7860](http://localhost:7860)** in your browser.

### Option 2: Running from Source
```bash
# 1. Build the React frontend
cd frontend
npm install
npm run build
cd ..

# 2. Set up Python virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements-docker.txt

# 4. Start the application
uvicorn backend.main:app --host 0.0.0.0 --port 7860 --reload
```
Open **[http://localhost:7860](http://localhost:7860)** in your browser.

---

## ⚙️ Configuration

Environment variables are loaded via `.env` (see `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `PORT` | `7860` | Server listening port |
| `USE_LOCAL_EMBEDDINGS` | `true` | Runs local sentence-transformers (free, no API key needed) |
| `OPENAI_API_KEY` | *(optional)* | Global server-side LLM key (can be overridden per-user in UI) |
| `OPENAI_MODEL` | `gpt-3.5-turbo` | OpenAI or OpenAI-compatible model name |
| `OPENAI_API_BASE` | *(optional)* | Custom API endpoint (e.g. OpenRouter, Ollama, vLLM) |
| `USE_CELERY` | `false` | Inline processing (set `true` only if Celery/Redis are configured) |

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
