# Test Specification Template

Use this template when creating test specifications for new features or services.

## Overview

- **Feature/Service Name**: [Name]
- **Target Coverage**: [X]%
- **Test Type**: [Unit/Integration/E2E]

## Test Cases

### Category: [Category Name]

| Test ID | Description | Priority | Status |
|---------|-------------|----------|--------|
| TC-001 | [Description] | High/Medium/Low | Pending/Done |

### Detailed Test Cases

#### TC-001: [Test Name]

**Purpose**: [What this test verifies]

**Preconditions**:
- [Condition 1]
- [Condition 2]

**Test Steps**:
1. [Step 1]
2. [Step 2]
3. [Step 3]

**Expected Result**:
- [Expected outcome 1]
- [Expected outcome 2]

**Mock Requirements**:
- [Mock 1]: [Description]
- [Mock 2]: [Description]

---

## Example: Entity Resolver Test Spec

### Overview

- **Feature/Service Name**: EntityResolver
- **Target Coverage**: 90%
- **Test Type**: Unit

### Test Cases

#### Category: Exact Match (Stage 1)

| Test ID | Description | Priority | Status |
|---------|-------------|----------|--------|
| ER-001 | Matches entity with exact lowercase name | High | Done |
| ER-002 | Matches entity with uppercase input | High | Done |
| ER-003 | Matches entity with mixed case | Medium | Done |
| ER-004 | Normalizes whitespace before matching | Medium | Done |
| ER-005 | Returns correct entity ID on match | High | Done |

#### Category: Canonical Lookup (Stage 2)

| Test ID | Description | Priority | Status |
|---------|-------------|----------|--------|
| ER-006 | Resolves 'postgres' to 'PostgreSQL' | High | Done |
| ER-007 | Resolves 'k8s' to 'Kubernetes' | Medium | Done |
| ER-008 | Continues to next stage if canonical not found | High | Done |

#### Category: Fuzzy Match (Stage 4)

| Test ID | Description | Priority | Status |
|---------|-------------|----------|--------|
| ER-009 | Matches similar names above 85% threshold | High | Done |
| ER-010 | Handles common typos | Medium | Done |
| ER-011 | Selects best match when multiple exist | High | Done |
| ER-012 | Skips matches below threshold | High | Done |

### Mock Requirements

```python
# Neo4j Session Mock
mock_session = MockNeo4jSession()
mock_session.set_response("toLower(e.name)", single_value=entity_record)

# Embedding Service Mock
mock_embedding = MockEmbeddingService()
mock_embedding.embed_text = AsyncMock(return_value=[0.5] * 2048)
```

### Implementation Notes

- Use `pytest.mark.asyncio` for all async tests
- Use `MockNeo4jSession` from `tests/mocks/neo4j_mock.py`
- Each test should be independent and not rely on state from other tests
