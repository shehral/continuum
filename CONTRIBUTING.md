# Contributing to Continuum

Thank you for your interest in contributing to Continuum.

## Getting Started

1. **Fork** the repository and clone your fork
2. Follow the [Getting Started](./README.md#getting-started) section to set up your dev environment
3. Create a feature branch: `git checkout -b feat/your-feature`

## Development Workflow

### Branch naming

- `feat/` -- New features
- `fix/` -- Bug fixes
- `refactor/` -- Code refactoring
- `docs/` -- Documentation changes

### Before submitting

Run the quality checks:

```bash
# Frontend
cd apps/web && pnpm typecheck && pnpm lint

# Backend
cd apps/api && .venv/bin/ruff check . && .venv/bin/pytest tests/ -v
```

### Pull Requests

- Keep PRs focused on a single change
- Include tests for new functionality
- Update documentation if behavior changes
- Write a clear description of what and why

## Code Conventions

### Frontend (Next.js / React)

- Use `cn()` from `@/lib/utils` for className composition
- Use semantic color tokens (`bg-primary`, `text-foreground`) -- never hardcode colors
- Icons: `lucide-react` exclusively
- Components: `React.forwardRef`, CVA for variants
- See `apps/web/CLAUDE.md` for the full design system

### Backend (FastAPI / Python)

- All database operations use `async`/`await`
- Pydantic models for request/response validation
- Neo4j queries: always pass parameters via `parameters={}` dict (never `**kwargs`)
- Run `ruff check` before committing

## Architecture Notes

- **PostgreSQL** -- Relational data (users, sessions, decision metadata)
- **Neo4j** -- Knowledge graph (decisions, entities, relationships)
- **Redis** -- Caching, rate limiting, session storage
- **NVIDIA NIM** -- LLM inference and embeddings (with Bedrock as fallback)

For detailed architecture info, see the [README](./README.md#architecture).

## Questions?

For questions about the project or potential research collaboration:

**Ali Shehral** -- shehral.m@northeastern.edu
HCAI Lab, Northeastern University
