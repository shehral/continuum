# Continuum

**A knowledge graph for capturing engineering decisions from human-AI coding sessions**

> 🔬 Research project in development
> ⚠️ **This project is not yet ready for public use. Please do not fork or redistribute.**

---

## Overview

Continuum automatically extracts decision traces from AI-assisted coding conversations and visualizes them as an interactive knowledge graph. It transforms ephemeral human-AI collaboration into structured, searchable knowledge.

### Research Context

This project explores human-AI collaboration patterns in software engineering—specifically how decisions are made, communicated, and can be preserved during AI-assisted development.

**Project Lead**: Ali Shehral (shehral.m@northeastern.edu)

**Affiliation**: HCAI Lab, Northeastern University

**Status**: Active Development

---

## Demo

[![Watch the demo](https://img.youtube.com/vi/P_yyWTt7Ah0/maxresdefault.jpg)](https://youtu.be/P_yyWTt7Ah0)

---

## Features

### Knowledge Capture
- **Passive Extraction**: Automatically extract decisions from Claude Code conversation logs with file watching for continuous monitoring
- **AI-Guided Interviews**: 7-stage interview agent with stage-specific prompts (opening, trigger, context, options, decision, rationale, summary)
- **Real-time Capture**: WebSocket streaming for live interview sessions
- **Bulk Import/Export**: JSON import (up to 500 decisions), export with source filtering and timestamped downloads

### Knowledge Graph
- **Interactive Visualization**: React Flow graph with custom decision and entity node types, minimap, zoom controls, and keyboard navigation
- **Entity Resolution**: 8-stage deduplication pipeline (cache, exact match, canonical lookup, alias search, fulltext prefix, fuzzy match, embedding similarity, create new) with ~530 canonical mappings
- **Graph Analysis**: Batch relationship detection (SUPERSEDES, CONTRADICTS), circular dependency checks, orphan detection, entity deduplication
- **Entity Evolution**: Timeline tracking and decision evolution chains across supersessions and contradictions

### Search & Discovery
- **Hybrid Search**: Combined lexical and semantic search with configurable score fusion
- **Advanced Search UI**: Mode selector (hybrid/lexical/semantic), confidence slider, matched field highlights, keyboard shortcuts (Cmd+K)
- **Graph Validation**: Detect circular dependencies, orphan entities, duplicates, and relationship issues

### Agent Integration
- **MCP Server**: 5 tools for AI agent access — `continuum_check` (prior art), `continuum_remember` (record decisions), `continuum_search` (hybrid query), `continuum_context` (entity details), `continuum_summary` (project overview)
- **Multi-Provider LLM**: Pluggable provider system supporting NVIDIA NIM and Amazon Bedrock with runtime switching

### Project Management
- **Project Organization**: Group decisions by project with stats, reset, and deletion
- **Decision Review Queue**: Confidence-ordered review with agree/disagree voting and human rationale
- **Dashboard Analytics**: Stats cards, source breakdowns, and recent decision summaries
- **Timeline View**: Chronological decision grouping by month/year

---

## Tech Stack

| Layer | Technologies |
|-------|--------------|
| **Frontend** | Next.js 16, React 19, TailwindCSS 4, shadcn/ui, Framer Motion |
| **Backend** | FastAPI, SQLAlchemy (async), Pydantic, Python 3.12+ |
| **Databases** | PostgreSQL 18, Neo4j 2025.01, Redis 7.4 |
| **AI** | NVIDIA NIM API (Llama 3.3 Nemotron, NV-EmbedQA), Amazon Bedrock (Claude) |
| **Auth** | Auth.js v5 (next-auth), JWT with per-user isolation |
| **Infrastructure** | Docker, Kubernetes, GitHub Actions, Node.js 24 LTS |

---

## Project Status

- ✅ JWT authentication with per-user data isolation
- ✅ Kubernetes-ready with CI/CD pipelines (build, deploy, rollback, security scan)
- ✅ 735+ tests including E2E workflows
- ✅ Circuit breakers and retry logic for external service calls
- ✅ 8-stage entity resolution with ~530 canonical mappings
- ✅ Rate limiting with Redis token bucket (per-user)
- ✅ GZip response compression and Redis query caching

---

## Installation

> **Note**: Public installation instructions are not available at this time.
> This project requires NVIDIA NIM API access and specific infrastructure setup.

For authorized collaborators, please refer to the internal documentation.

---

## License

All rights reserved. See [LICENSE](./LICENSE) for details.

This software is provided for academic review and research collaboration purposes only.

---

## Third-Party Services

This project uses:
- [NVIDIA NIM API](https://developer.nvidia.com/) - Subject to NVIDIA Terms of Service
- [Amazon Bedrock](https://aws.amazon.com/bedrock/) - Subject to AWS Terms of Service
- [Claude Code](https://claude.ai/) conversation format from Anthropic

---

## Acknowledgments

Built as part of ongoing research in human-AI collaboration for software engineering.

---

*For collaboration inquiries, please contact Ali Shehral at shehral.m@northeastern.edu*
