# Test Coverage Status

Last Updated: 2026-01-28

## Summary

| Component | Coverage | Tests | Status |
|-----------|----------|-------|--------|
| Backend Services | 53% | 132 | In Progress |
| Frontend Components | 70%+ | 23 | Good |

## Backend Services Coverage

### Critical Services (Target: 80%+)

| Service | Lines | Coverage | Tests | Target | Status |
|---------|-------|----------|-------|--------|--------|
| entity_resolver.py | 138 | 87% | 39 | 90% | Almost |
| validator.py | 121 | 96% | 36 | 85% | Exceeded |
| decision_analyzer.py | 124 | 89% | 27 | 85% | Exceeded |
| embeddings.py | 49 | 100% | 30 | 80% | Exceeded |

### Other Services (Lower Priority)

| Service | Lines | Coverage | Tests | Notes |
|---------|-------|----------|-------|-------|
| llm.py | 80 | 19% | 17* | *Existing tests |
| extractor.py | 188 | 0% | 0 | Needs tests |
| parser.py | 78 | 0% | 0 | Needs tests |

*Note: llm.py has existing tests in test_llm.py

## Frontend Coverage

### Components

| Component | Tests | Status |
|-----------|-------|--------|
| KnowledgeGraph | 23 | Complete |
| ChatInterface | 0 | Pending |
| Sidebar | 0 | Pending |

## Test Infrastructure

### Backend

- pytest with pytest-asyncio
- pytest-cov for coverage
- pytest-mock for mocking
- Custom mocks: MockNeo4jSession, MockLLMClient, MockEmbeddingService

### Frontend

- Vitest test runner
- @testing-library/react
- @testing-library/jest-dom
- jsdom environment

## Running Tests

### Backend

```bash
cd apps/api

# Run all unit tests
.venv/bin/pytest tests/services/ -v

# Run with coverage
.venv/bin/pytest tests/services/ --cov=services --cov-report=term-missing

# Run specific test file
.venv/bin/pytest tests/services/test_entity_resolver.py -v
```

### Frontend

```bash
cd apps/web

# Run all tests
pnpm test

# Run with coverage
pnpm test:coverage

# Watch mode
pnpm test
```

## CI/CD Pipeline

- GitHub Actions workflow: `.github/workflows/ci.yml`
- Pre-commit hooks: `.pre-commit-config.yaml`

### Jobs

1. **backend-lint**: Ruff linting
2. **backend-typecheck**: mypy type checking
3. **backend-tests**: pytest with coverage
4. **frontend-lint**: ESLint
5. **frontend-typecheck**: TypeScript checking
6. **frontend-tests**: Vitest with coverage
7. **quality-gate**: Ensures all checks pass

## Next Steps

### Phase 2: Expand Coverage

1. Add tests for `extractor.py` - Decision extraction logic
2. Add tests for `parser.py` - Claude log parsing
3. Increase `llm.py` coverage

### Phase 3: Frontend Tests

1. Add ChatInterface component tests
2. Add Sidebar component tests
3. Add E2E tests with Playwright

### Phase 4: Integration Tests

1. API endpoint tests (existing in test_e2e.py)
2. Database integration tests
3. Neo4j graph operation tests
