# AI Codebase Explainer — Resume & Portfolio Guide

This document is designed to help you showcase this project on your resume, LinkedIn, and during technical interviews. It translates the codebase's features into high-impact, metrics-driven bullet points that recruiters and engineering managers look for.

---

## 📄 Resume Bullet Points

*Choose 3-4 bullet points that best align with the role you are applying for (e.g., Frontend, Backend, or Full-Stack).*

### Option 1: Full-Stack / Software Engineer Focus
* **Architected a full-stack Retrieval-Augmented Generation (RAG) application** using React, FastAPI, and ChromaDB, enabling developers to query entire codebases via natural language.
* **Engineered a scalable ingestion pipeline** capable of parsing `.zip` files and cloning GitHub repositories, extracting text across 40+ programming languages while intelligently chunking code by class and function boundaries.
* **Integrated Groq's Llama3-70B API and local sentence-transformers** (`all-MiniLM-L6-v2`) to perform millisecond-latency semantic searches over thousands of code chunks with zero API token cost for embeddings.
* **Designed a premium, dynamic UI** using Tailwind CSS, featuring glassmorphism, fluid micro-animations, and real-time execution flow tracing for a seamless developer experience.

### Option 2: AI / Backend Engineer Focus
* **Developed a highly performant RAG backend** in FastAPI with async Python, handling concurrent GitHub repository indexing and vector similarity searches.
* **Implemented an optimized chunking strategy** using AST-like boundary detection, fallback sliding windows, and a Least Recently Used (LRU) cache, significantly reducing context pollution and LLM hallucination.
* **Built a local persistent vector database** with ChromaDB to store 384-dimensional dense vectors, allowing instant querying of past sessions without re-indexing.
* **Ensured 100% free-tier operation** by leveraging Groq for blazing-fast inference and running embedding models entirely locally, eliminating ongoing cloud costs.

### Option 3: Frontend / UI Engineer Focus
* **Built a responsive, SPA React frontend** powered by Vite and TypeScript, featuring a robust custom File Explorer and conversational chat panel.
* **Implemented a modern, premium design system** utilizing Tailwind CSS, incorporating glassmorphic panels, animated mesh gradients, and interactive glowing elements to increase user engagement.
* **Managed complex asynchronous states** bridging file uploading, polling for backend vector indexing completion, and streaming LLM chat responses.

---

## 🎙️ Interview Talking Points

When asked, *"Tell me about a challenging project you've worked on,"* use the **STAR** method (Situation, Task, Action, Result) based on these challenges:

### Challenge 1: Context Window Limits (The "Chunking" Problem)
* **The Problem**: You can't fit an entire repository into an LLM prompt. If you just split code randomly by character count, you break functions in half, ruining the AI's understanding.
* **The Solution**: I implemented a multi-tier chunking strategy. The parser detects logical boundaries (like `class` or `function` keywords in Python/JS). Small files are kept whole. Large files are split cleanly at logical breakpoints, with a sliding window fallback for massive files.
* **The Result**: The retrieval became highly accurate, as the LLM received complete, self-contained blocks of logic instead of fragmented code.

### Challenge 2: Speed and Latency
* **The Problem**: Running vector embeddings via OpenAI's API would be slow and expensive for thousands of files.
* **The Solution**: I moved the embedding layer locally using `sentence-transformers` (`all-MiniLM-L6-v2`). I also implemented an LRU cache for frequent queries. For the generation step, I swapped to Groq's Llama3 model.
* **The Result**: Indexing became free, and query answers stream back in under a second.

### Challenge 3: Seamless Developer Experience
* **The Problem**: Users don't want to wait blindly while a 50MB codebase indexes.
* **The Solution**: I designed a polling mechanism on the React frontend that dynamically updates the UI based on indexing status, culminating in a workspace that features an interactive file tree and synced chat panel.

---

## 💡 How to Demo This Project
1. Open the app and upload a well-known open source repository (e.g., `tiangolo/fastapi`).
2. Ask: *"What is the overall architecture of this codebase?"*
3. Ask: *"Find any security vulnerabilities in the authentication flow."*
4. Click on a file in the File Explorer and show how the AI explains it on the right panel.
