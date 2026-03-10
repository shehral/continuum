# Continuum

**A knowledge graph for capturing engineering decisions from human-AI coding sessions**

> Research project exploring how decisions are made, communicated, and preserved during AI-assisted software development.

---

## Demo

[![Watch the demo](https://img.youtube.com/vi/P_yyWTt7Ah0/maxresdefault.jpg)](https://youtu.be/P_yyWTt7Ah0)

---

## Overview

Continuum automatically extracts decision traces from AI-assisted coding conversations and visualizes them as an interactive knowledge graph. It transforms ephemeral human-AI collaboration into structured, searchable knowledge.

**Project Lead**: Ali Shehral (shehral.m@northeastern.edu) | HCAI Lab, Northeastern University

---

## Features

### Knowledge Capture
- **Passive Extraction** -- Automatically extract decisions from Claude Code conversation logs with file watching for continuous monitoring
- **AI-Guided Interviews** -- 7-stage interview agent with stage-specific prompts (opening, trigger, context, options, decision, rationale, summary)
- **Real-time Capture** -- WebSocket streaming for live interview sessions
- **Bulk Import/Export** -- JSON import (up to 500 decisions), export with source filtering

### Knowledge Graph
- **Interactive Visualization** -- React Flow graph with custom decision and entity node types, minimap, zoom controls, keyboard navigation
- **Entity Resolution** -- 8-stage deduplication pipeline (cache, exact match, canonical lookup, alias search, fulltext prefix, fuzzy match, embedding similarity, create new) with ~530 canonical mappings
- **Graph Analysis** -- Batch relationship detection (SUPERSEDES, CONTRADICTS), circular dependency checks, orphan detection, entity deduplication
- **Entity Evolution** -- Timeline tracking and decision evolution chains

### Search & Discovery
- **Hybrid Search** -- Combined lexical (fulltext) and semantic (vector) search with configurable score fusion
- **GraphRAG** -- Graph-aware retrieval-augmented generation with SSE streaming, combining hybrid search + knowledge graph traversal + LLM synthesis
- **Advanced Search UI** -- Mode selector (hybrid/lexical/semantic), confidence slider, matched field highlights, keyboard shortcuts (Cmd+K)
- **Graph Expansion** -- Opt-in subgraph expansion via K-hop traversal on search results

### Agent Integration
- **MCP Server** -- 5 tools for AI agent access: `continuum_check` (prior art), `continuum_remember` (record decisions), `continuum_search` (hybrid query), `continuum_context` (entity details), `continuum_summary` (project overview)
- **Multi-Provider LLM** -- Pluggable provider system supporting NVIDIA NIM and Amazon Bedrock with runtime switching and automatic failover

### Project Management
- **Project Organization** -- Group decisions by project with stats, reset, and deletion
- **Decision Review Queue** -- Confidence-ordered review with agree/disagree voting and human rationale
- **Dashboard Analytics** -- Stats cards, source breakdowns, recent decision summaries
- **Timeline View** -- Chronological decision grouping by month/year

---

## Architecture

```
                     +------------------+
                     |   Next.js 16     |
                     |   (React 19)     |
                     |   Port 3000      |
                     +--------+---------+
                              |
                              | REST / SSE / WebSocket
                              |
                     +--------+---------+
                     |    FastAPI        |
                     |    Port 8000     |
                     +--+-----+-----+--+
                        |     |     |
              +---------+  +--+--+  +----------+
              |            |     |             |
     +--------+---+  +----+----+  +----+------+
     | PostgreSQL  |  |  Neo4j  |  |   Redis   |
     | (Relational |  | (Graph  |  | (Cache,   |
     |  data, auth)|  |  store) |  |  rate     |
     | Port 5432   |  | 7474/   |  |  limits)  |
     |             |  | 7687    |  | Port 6379 |
     +-------------+  +---------+  +-----------+
```

### Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | Next.js 16, React 19, TailwindCSS 4, shadcn/ui, Framer Motion |
| **Backend** | FastAPI, SQLAlchemy (async), Pydantic v2, Python 3.12+ |
| **Databases** | PostgreSQL 18, Neo4j 2025.01, Redis 7.4 |
| **AI** | NVIDIA NIM API (Llama 3.3 Nemotron, NV-EmbedQA), Amazon Bedrock (Claude) |
| **Auth** | Auth.js v5 (next-auth), JWT with per-user isolation |
| **Runtime** | Node.js 24 LTS, pnpm |

---

## Project Structure

```
continuum/
├── apps/
│   ├── web/                    # Next.js frontend
│   │   ├── app/                # App Router pages
│   │   │   ├── dashboard/      # Analytics dashboard
│   │   │   ├── decisions/      # Decision list and detail views
│   │   │   ├── graph/          # Interactive knowledge graph
│   │   │   ├── search/         # Hybrid search interface
│   │   │   ├── ask/            # GraphRAG chat interface
│   │   │   ├── capture/        # Decision capture (interview + import)
│   │   │   ├── projects/       # Project management
│   │   │   └── settings/       # User settings
│   │   ├── components/         # React components
│   │   │   ├── ui/             # shadcn/ui primitives
│   │   │   ├── graph/          # Graph visualization components
│   │   │   ├── ask/            # Chat UI components
│   │   │   ├── capture/        # Capture flow components
│   │   │   └── layout/         # App shell, sidebar
│   │   └── lib/                # Utilities (api client, helpers)
│   │
│   └── api/                    # FastAPI backend
│       ├── routers/            # API endpoints
│       │   ├── ask.py          # GraphRAG SSE streaming
│       │   ├── search.py       # Hybrid search with graph expansion
│       │   ├── decisions.py    # CRUD for decisions
│       │   ├── graph.py        # Graph operations
│       │   ├── capture.py      # WebSocket capture
│       │   ├── agent.py        # MCP server tools
│       │   └── ...
│       ├── services/           # Business logic
│       │   ├── graph_rag.py    # GraphRAG pipeline
│       │   ├── llm.py          # LLM client (provider-agnostic)
│       │   ├── llm_providers/  # NVIDIA NIM + Amazon Bedrock
│       │   ├── embeddings.py   # NVIDIA NV-EmbedQA client
│       │   ├── extractor.py    # Decision extraction from logs
│       │   ├── entity_resolver.py # 8-stage entity deduplication
│       │   └── validator.py    # Graph validation
│       ├── models/             # SQLAlchemy + Pydantic schemas
│       ├── db/                 # Database connections
│       ├── config.py           # All settings with env var defaults
│       └── tests/              # Test suite
│
├── docker-compose.yml          # PostgreSQL, Neo4j, Redis
├── pnpm-workspace.yaml         # Monorepo config
└── docs/                       # Design docs and plans
```

---

## Getting Started

### Prerequisites

- **Node.js 24 LTS** and **pnpm** (package manager)
- **Python 3.12+**
- **Docker** and **Docker Compose** (for databases)
- **NVIDIA NIM API key** (from [build.nvidia.com](https://build.nvidia.com)) or AWS credentials for Bedrock

### 1. Clone and configure

```bash
git clone https://github.com/shehral/continuum.git
cd continuum

# Copy environment template and fill in your keys
cp .env.example .env
```

Edit `.env` with your credentials. At minimum, set:
- `NVIDIA_API_KEY` and `NVIDIA_EMBEDDING_API_KEY` (or configure Bedrock)
- `POSTGRES_PASSWORD`, `NEO4J_PASSWORD`, `REDIS_PASSWORD` (generate secure passwords)
- `SECRET_KEY` and `NEXTAUTH_SECRET` (must match, generate with `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`)
- Update the connection strings (`DATABASE_URL`, `REDIS_URL`) with your passwords

### 2. Start infrastructure

```bash
docker-compose up -d
```

This starts PostgreSQL (5432), Neo4j (7474/7687), and Redis (6379), all bound to localhost only.

### 3. Install dependencies

```bash
# Frontend
pnpm install

# Backend
cd apps/api
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
cd ../..
```

### 4. Run database migrations

```bash
pnpm db:migrate
```

### 5. Start development servers

```bash
pnpm dev        # Both frontend (3000) + backend (8000)
# or individually:
pnpm dev:web    # Frontend at http://localhost:3000
pnpm dev:api    # Backend at http://localhost:8000
```

### 6. Create an account

Navigate to `http://localhost:3000/register` to create your user account.

---

## Available Scripts

```bash
pnpm dev          # Start frontend + backend in parallel
pnpm dev:web      # Frontend only
pnpm dev:api      # Backend only (uvicorn --reload)
pnpm build        # Build frontend
pnpm typecheck    # TypeScript type checking
pnpm lint         # ESLint
pnpm test         # Run all tests
pnpm test:api     # Backend tests (pytest)
pnpm db:migrate   # Run Alembic migrations
pnpm db:reset     # Reset database
pnpm docker:up    # Start Docker services
pnpm docker:down  # Stop Docker services
```

---

## API Overview

All endpoints are prefixed with `/api`. Authentication is via JWT (Bearer token).

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ask` | GET (SSE) | GraphRAG Q&A with streaming responses |
| `/api/search` | GET | Hybrid search with optional graph expansion |
| `/api/decisions` | GET/POST | CRUD for decision traces |
| `/api/graph/*` | GET/POST | Graph operations and statistics |
| `/api/capture/ws` | WebSocket | Real-time interview capture |
| `/api/agent/*` | GET/POST | MCP server tools for AI agents |
| `/api/projects` | GET/POST | Project management |
| `/api/auth/*` | POST | Registration and login |

### GraphRAG (`/api/ask`)

The Ask endpoint uses a hybrid retrieval pipeline:

1. **Parallel retrieval** -- Fulltext search (Neo4j Lucene indexes) + vector search (NVIDIA NV-EmbedQA embeddings) run concurrently
2. **Score fusion** -- Reciprocal Rank Fusion (RRF) combines rankings without normalizing different score scales
3. **Subgraph expansion** -- Top-K seed nodes are expanded via K-hop Cypher traversal (`apoc.path.subgraphAll`)
4. **LLM synthesis** -- Serialized subgraph context is streamed to the LLM for grounded answer generation

Query params: `q` (required), `depth` (1-3, default 2), `top_k` (1-10, default 5)

Response: Server-Sent Events with `context`, `token`, `done`, and `error` event types.

---

## Environment Variables

Copy `.env.example` to `.env`. Key variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `NVIDIA_API_KEY` | Yes (if nvidia) | NVIDIA NIM API key |
| `NVIDIA_EMBEDDING_API_KEY` | Yes (if nvidia) | Separate key for embedding model |
| `LLM_PROVIDER` | No | `nvidia` (default) or `bedrock` |
| `DATABASE_URL` | Yes | PostgreSQL async connection string |
| `NEO4J_URI` / `NEO4J_PASSWORD` | Yes | Neo4j connection |
| `REDIS_URL` | Yes | Redis connection with password |
| `SECRET_KEY` | Yes | JWT signing key (must match `NEXTAUTH_SECRET`) |
| `NEXTAUTH_SECRET` | Yes | Auth.js secret (must match `SECRET_KEY`) |

---

## Testing

```bash
# Backend unit tests
cd apps/api && .venv/bin/pytest tests/ -v

# Frontend type checking
cd apps/web && pnpm typecheck

# Lint
pnpm lint

# Load testing (requires k6)
cd apps/api/tests/load && k6 run load_test.js
```

---

## Contributing

We welcome contributions. See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

Quick summary:
1. Fork the repository
2. Create a feature branch (`feat/your-feature`)
3. Make your changes with tests
4. Run `pnpm lint && pnpm typecheck && cd apps/api && .venv/bin/pytest tests/ -v`
5. Open a pull request

---

## Third-Party Services

- [NVIDIA NIM API](https://developer.nvidia.com/) -- Subject to NVIDIA Terms of Service
- [Amazon Bedrock](https://aws.amazon.com/bedrock/) -- Subject to AWS Terms of Service
- [Claude Code](https://claude.ai/) conversation format from Anthropic

---

## License

All rights reserved. See [LICENSE](./LICENSE) for details.

This software is provided for academic review and research collaboration purposes only.

---

*For collaboration inquiries, contact Ali Shehral at shehral.m@northeastern.edu*
