# Continuum

A knowledge management platform for capturing, organizing, and transferring engineering knowledge.

## Features

- **Passive Knowledge Capture**: Automatically extract decisions from Claude Code conversation logs
- **AI-Guided Interviews**: NVIDIA Llama-powered interview agent guides knowledge capture
- **Knowledge Graph**: Visual representation of decisions and their relationships
- **Decision Traces**: Structured capture of trigger, context, options, decision, and rationale
- **Entity Resolution**: 5-stage deduplication pipeline (exact, canonical, alias, fuzzy, embedding)
- **Graph Validation**: Detect circular dependencies, orphans, and duplicates
- **Search**: Case-insensitive full-text search across decisions and entities

## Tech Stack

- **Frontend**: Next.js 14, React Flow, TailwindCSS, shadcn/ui
- **Backend**: FastAPI, SQLAlchemy (async)
- **Databases**: PostgreSQL, Neo4j, Redis
- **AI**: NVIDIA NIM API (Llama 3.3 Nemotron for LLM, NV-EmbedQA for embeddings)

## Prerequisites

- Node.js >= 20.x
- pnpm >= 8.x
- Python >= 3.11
- Docker & Docker Compose
- NVIDIA NIM API key from [NVIDIA AI](https://build.nvidia.com/)

## Quick Start

### 1. Clone and Configure Environment

```bash
# Copy the example env file
cp .env.example .env

# Edit .env and add your NVIDIA API keys
# NVIDIA_API_KEY=nvapi-...
# NVIDIA_EMBEDDING_API_KEY=nvapi-...
```

### 2. Start Infrastructure

```bash
# Start PostgreSQL, Neo4j, and Redis (ports bound to localhost only)
docker-compose up -d

# Verify services are healthy
docker-compose ps
```

### 3. Install Dependencies

```bash
# Install Node.js dependencies
pnpm install

# Set up Python virtual environment
cd apps/api
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
cd ../..
```

### 4. Run Database Migrations

```bash
cd apps/api
.venv/bin/alembic upgrade head
```

### 5. Start Development Servers

```bash
# Terminal 1: Start frontend
pnpm dev:web

# Terminal 2: Start backend (uses virtual environment)
pnpm dev:api
```

Visit:
- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs
- Neo4j Browser: http://localhost:7474

## Project Structure

```
continuum/
├── apps/
│   ├── web/                    # Next.js frontend
│   │   ├── app/               # App Router pages
│   │   ├── components/        # React components
│   │   └── lib/               # Utilities and API client
│   │
│   └── api/                    # FastAPI backend
│       ├── .venv/             # Python virtual environment
│       ├── routers/           # API endpoints
│       ├── services/          # Business logic
│       │   ├── llm.py         # NVIDIA NIM LLM client
│       │   ├── embeddings.py  # NVIDIA NV-EmbedQA client
│       │   ├── extractor.py   # Decision extraction with CoT prompts
│       │   ├── entity_resolver.py  # Entity deduplication
│       │   ├── validator.py   # Graph validation
│       │   └── decision_analyzer.py  # Relationship detection
│       ├── models/            # Database models + ontology
│       ├── db/                # Database connections
│       └── tests/             # E2E test suite (31 tests)
│
├── docker-compose.yml          # Infrastructure services
├── pnpm-workspace.yaml         # Monorepo config
└── package.json               # Root scripts
```

## Usage

### Ingest Claude Code Logs

Click "Ingest Logs" on the dashboard or call the API:

```bash
curl -X POST http://localhost:8000/api/ingest/trigger
```

### Start a Capture Session

1. Navigate to the Capture page
2. Click "New Session"
3. Answer the interview agent's questions
4. Complete the session to save to your knowledge graph

### Explore the Knowledge Graph

1. Navigate to the Graph page
2. Click nodes to see details
3. Use zoom/pan controls to navigate
4. Enable "Show Contradictions" to see CONTRADICTS edges

### Delete Decisions or Entities

```bash
# Delete a decision
curl -X DELETE http://localhost:8000/api/decisions/{id}

# Delete an entity (use force=true if it has relationships)
curl -X DELETE "http://localhost:8000/api/entities/{id}?force=true"
```

### Validate the Graph

```bash
curl http://localhost:8000/api/graph/validate
```

## Development

### Quality Checks

```bash
# Frontend
cd apps/web
pnpm typecheck
pnpm lint

# Backend (uses virtual environment)
cd apps/api
.venv/bin/ruff check .
.venv/bin/pytest tests/ -v
```

### Run E2E Tests

```bash
# Ensure API is running first
pnpm dev:api

# In another terminal
cd apps/api
.venv/bin/pytest tests/test_e2e.py -v
```

### Database Access

```bash
# PostgreSQL
docker-compose exec postgres psql -U continuum -d continuum

# Neo4j (via browser)
# Visit http://localhost:7474
# Login: neo4j / neo4jpassword

# Redis
docker-compose exec redis redis-cli -a continuum_redis_2024
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/dashboard/stats` | GET | Dashboard statistics |
| `/api/decisions` | GET | List all decisions |
| `/api/decisions/{id}` | GET | Get single decision |
| `/api/decisions/{id}` | DELETE | Delete decision |
| `/api/entities` | GET | List all entities |
| `/api/entities/{id}` | GET | Get single entity |
| `/api/entities/{id}` | DELETE | Delete entity (use `?force=true` if has relationships) |
| `/api/graph` | GET | Full knowledge graph |
| `/api/graph/stats` | GET | Graph statistics |
| `/api/graph/sources` | GET | List of source files |
| `/api/graph/validate` | GET | Run validation checks |
| `/api/search?query=...` | GET | Search decisions and entities |
| `/api/capture/sessions` | POST | Start capture session |
| `/api/ingest/trigger` | POST | Trigger log ingestion |

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `NVIDIA_API_KEY` | NVIDIA NIM API key for LLM | Yes |
| `NVIDIA_EMBEDDING_API_KEY` | NVIDIA NIM API key for embeddings | Yes |
| `DATABASE_URL` | PostgreSQL connection string | No (has default) |
| `NEO4J_URI` | Neo4j bolt URI | No (has default) |
| `REDIS_URL` | Redis connection string | No (has default) |
| `NEXTAUTH_SECRET` | NextAuth.js secret | Yes (for auth) |

### AI Configuration

| Component | Model | Details |
|-----------|-------|---------|
| LLM | nvidia/llama-3.3-nemotron-super-49b-v1.5 | Via NVIDIA NIM API |
| Embeddings | nvidia/llama-3.2-nv-embedqa-1b-v2 | 2048 dimensions |
| Rate Limit | 30 requests/minute | Redis token bucket |

### Security

- Docker ports are bound to `127.0.0.1` (localhost only)
- Python dependencies isolated in virtual environment
- Never commit `.env` file (use `.env.example` as template)
- Database passwords should be changed from defaults in production

## License

MIT
