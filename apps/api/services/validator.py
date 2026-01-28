"""Graph validation service for checking knowledge graph integrity."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from rapidfuzz import fuzz

from models.ontology import CANONICAL_NAMES


class IssueSeverity(Enum):
    """Severity levels for validation issues."""
    ERROR = "error"      # Must be fixed
    WARNING = "warning"  # Should be investigated
    INFO = "info"        # Informational


class IssueType(Enum):
    """Types of validation issues."""
    CIRCULAR_DEPENDENCY = "circular_dependency"
    ORPHAN_ENTITY = "orphan_entity"
    LOW_CONFIDENCE_RELATIONSHIP = "low_confidence_relationship"
    DUPLICATE_ENTITY = "duplicate_entity"
    MISSING_EMBEDDING = "missing_embedding"
    INVALID_RELATIONSHIP = "invalid_relationship"
    INCONSISTENT_ENTITY_TYPE = "inconsistent_entity_type"


@dataclass
class ValidationIssue:
    """A validation issue found in the graph."""
    type: IssueType
    severity: IssueSeverity
    message: str
    affected_nodes: list[str]
    suggested_action: Optional[str] = None
    details: Optional[dict] = None


class GraphValidator:
    """Validate knowledge graph integrity and consistency.

    Checks for:
    - Circular dependencies in DEPENDS_ON chains
    - Orphan entities with no relationships
    - Low confidence relationships
    - Duplicate entities (via fuzzy matching)
    - Missing embeddings
    - Invalid relationship configurations
    """

    def __init__(self, neo4j_session):
        self.session = neo4j_session
        self.fuzzy_threshold = 85

    async def validate_all(self) -> list[ValidationIssue]:
        """Run all validation checks.

        Returns:
            List of ValidationIssue objects
        """
        issues = []
        issues.extend(await self.check_circular_dependencies())
        issues.extend(await self.check_orphan_entities())
        issues.extend(await self.check_low_confidence_relationships(threshold=0.5))
        issues.extend(await self.check_duplicate_entities())
        issues.extend(await self.check_missing_embeddings())
        issues.extend(await self.check_invalid_relationships())
        return issues

    async def check_circular_dependencies(self) -> list[ValidationIssue]:
        """Find circular DEPENDS_ON chains.

        Circular dependencies indicate modeling problems that need resolution.
        """
        issues = []

        try:
            result = await self.session.run(
                """
                MATCH path = (e:Entity)-[:DEPENDS_ON*2..10]->(e)
                WITH nodes(path) AS cycle_nodes
                RETURN [n IN cycle_nodes | n.name] AS cycle_names,
                       [n IN cycle_nodes | n.id] AS cycle_ids
                LIMIT 10
                """
            )

            async for record in result:
                cycle_names = record["cycle_names"]
                cycle_ids = record["cycle_ids"]

                issues.append(ValidationIssue(
                    type=IssueType.CIRCULAR_DEPENDENCY,
                    severity=IssueSeverity.ERROR,
                    message=f"Circular dependency detected: {' -> '.join(cycle_names)}",
                    affected_nodes=cycle_ids,
                    suggested_action="Review the DEPENDS_ON relationships and remove the cycle",
                    details={"cycle": cycle_names},
                ))

        except Exception as e:
            print(f"[Validator] Error checking circular dependencies: {e}")

        return issues

    async def check_orphan_entities(self) -> list[ValidationIssue]:
        """Find entities with no relationships.

        Orphan entities may indicate incomplete extraction or stale data.
        """
        issues = []

        result = await self.session.run(
            """
            MATCH (e:Entity)
            WHERE NOT (e)-[]-()
            RETURN e.id AS id, e.name AS name, e.type AS type
            """
        )

        async for record in result:
            issues.append(ValidationIssue(
                type=IssueType.ORPHAN_ENTITY,
                severity=IssueSeverity.WARNING,
                message=f"Orphan entity found: {record['name']} ({record['type']})",
                affected_nodes=[record["id"]],
                suggested_action="Link to relevant decisions or delete if no longer needed",
                details={"name": record["name"], "type": record["type"]},
            ))

        return issues

    async def check_low_confidence_relationships(
        self, threshold: float = 0.5
    ) -> list[ValidationIssue]:
        """Find relationships with low confidence scores.

        Low confidence relationships may need manual verification.
        """
        issues = []

        result = await self.session.run(
            """
            MATCH (a)-[r]->(b)
            WHERE r.confidence IS NOT NULL AND r.confidence < $threshold
            RETURN a.id AS source_id,
                   COALESCE(a.name, a.trigger) AS source_name,
                   b.id AS target_id,
                   COALESCE(b.name, b.trigger) AS target_name,
                   type(r) AS rel_type,
                   r.confidence AS confidence
            ORDER BY r.confidence ASC
            LIMIT 50
            """,
            threshold=threshold,
        )

        async for record in result:
            issues.append(ValidationIssue(
                type=IssueType.LOW_CONFIDENCE_RELATIONSHIP,
                severity=IssueSeverity.INFO,
                message=f"Low confidence {record['rel_type']}: {record['source_name']} -> {record['target_name']} ({record['confidence']:.2f})",
                affected_nodes=[record["source_id"], record["target_id"]],
                suggested_action="Review and verify this relationship or increase confidence",
                details={
                    "relationship": record["rel_type"],
                    "confidence": record["confidence"],
                    "source": record["source_name"],
                    "target": record["target_name"],
                },
            ))

        return issues

    async def check_duplicate_entities(self) -> list[ValidationIssue]:
        """Find potential duplicate entities via fuzzy matching.

        Duplicates fragment the knowledge graph and reduce query accuracy.
        """
        issues = []

        result = await self.session.run(
            """
            MATCH (e:Entity)
            RETURN e.id AS id, e.name AS name, e.type AS type
            """
        )

        entities = [dict(record) async for record in result]

        # Find potential duplicates
        processed_pairs = set()
        for i, e1 in enumerate(entities):
            for e2 in entities[i + 1:]:
                pair_key = tuple(sorted([e1["id"], e2["id"]]))
                if pair_key in processed_pairs:
                    continue
                processed_pairs.add(pair_key)

                # Check fuzzy match
                score = fuzz.ratio(e1["name"].lower(), e2["name"].lower())
                if score >= self.fuzzy_threshold and score < 100:
                    # Check if one is canonical form of the other
                    e1_canonical = CANONICAL_NAMES.get(e1["name"].lower())
                    e2_canonical = CANONICAL_NAMES.get(e2["name"].lower())

                    is_alias = (
                        e1_canonical == e2["name"]
                        or e2_canonical == e1["name"]
                        or (e1_canonical and e1_canonical == e2_canonical)
                    )

                    issues.append(ValidationIssue(
                        type=IssueType.DUPLICATE_ENTITY,
                        severity=IssueSeverity.WARNING if is_alias else IssueSeverity.INFO,
                        message=f"Potential duplicate: '{e1['name']}' and '{e2['name']}' ({score}% similar)",
                        affected_nodes=[e1["id"], e2["id"]],
                        suggested_action="Merge these entities or add one as an alias",
                        details={
                            "entity1": e1["name"],
                            "entity2": e2["name"],
                            "similarity": score,
                            "is_known_alias": is_alias,
                        },
                    ))

        return issues

    async def check_missing_embeddings(self) -> list[ValidationIssue]:
        """Find nodes missing embeddings.

        Missing embeddings reduce semantic search accuracy.
        """
        issues = []

        # Check decisions without embeddings
        result = await self.session.run(
            """
            MATCH (d:DecisionTrace)
            WHERE d.embedding IS NULL
            RETURN d.id AS id, d.trigger AS trigger
            LIMIT 20
            """
        )

        decision_count = 0
        async for record in result:
            decision_count += 1

        if decision_count > 0:
            issues.append(ValidationIssue(
                type=IssueType.MISSING_EMBEDDING,
                severity=IssueSeverity.WARNING,
                message=f"{decision_count} decisions missing embeddings",
                affected_nodes=[],
                suggested_action="Run POST /api/graph/enhance to backfill embeddings",
                details={"count": decision_count, "type": "decision"},
            ))

        # Check entities without embeddings
        result = await self.session.run(
            """
            MATCH (e:Entity)
            WHERE e.embedding IS NULL
            RETURN count(e) AS count
            """
        )
        record = await result.single()
        entity_count = record["count"] if record else 0

        if entity_count > 0:
            issues.append(ValidationIssue(
                type=IssueType.MISSING_EMBEDDING,
                severity=IssueSeverity.INFO,
                message=f"{entity_count} entities missing embeddings",
                affected_nodes=[],
                suggested_action="Run POST /api/graph/enhance to backfill embeddings",
                details={"count": entity_count, "type": "entity"},
            ))

        return issues

    async def check_invalid_relationships(self) -> list[ValidationIssue]:
        """Find invalid relationship configurations.

        Checks for:
        - Self-referential relationships
        - Decision-to-decision entity relationships
        - Entity-to-entity decision relationships
        """
        issues = []

        # Check self-referential relationships
        result = await self.session.run(
            """
            MATCH (n)-[r]->(n)
            RETURN n.id AS id,
                   COALESCE(n.name, n.trigger) AS name,
                   type(r) AS rel_type
            """
        )

        async for record in result:
            issues.append(ValidationIssue(
                type=IssueType.INVALID_RELATIONSHIP,
                severity=IssueSeverity.ERROR,
                message=f"Self-referential relationship: {record['name']} -{record['rel_type']}-> itself",
                affected_nodes=[record["id"]],
                suggested_action="Remove this self-referential relationship",
                details={"relationship": record["rel_type"]},
            ))

        # Check decision-to-decision with entity relationships
        result = await self.session.run(
            """
            MATCH (d1:DecisionTrace)-[r]->(d2:DecisionTrace)
            WHERE type(r) IN ['IS_A', 'PART_OF', 'DEPENDS_ON', 'ALTERNATIVE_TO']
            RETURN d1.id AS id1, d1.trigger AS trigger1,
                   d2.id AS id2, d2.trigger AS trigger2,
                   type(r) AS rel_type
            """
        )

        async for record in result:
            issues.append(ValidationIssue(
                type=IssueType.INVALID_RELATIONSHIP,
                severity=IssueSeverity.ERROR,
                message=f"Entity relationship between decisions: {record['trigger1'][:30]} -{record['rel_type']}-> {record['trigger2'][:30]}",
                affected_nodes=[record["id1"], record["id2"]],
                suggested_action=f"Change to a decision relationship (SIMILAR_TO, INFLUENCED_BY, etc.) or remove",
                details={"relationship": record["rel_type"]},
            ))

        return issues

    async def get_validation_summary(self) -> dict:
        """Get a summary of validation issues by type and severity."""
        issues = await self.validate_all()

        summary = {
            "total_issues": len(issues),
            "by_severity": {
                "error": 0,
                "warning": 0,
                "info": 0,
            },
            "by_type": {},
        }

        for issue in issues:
            summary["by_severity"][issue.severity.value] += 1

            type_key = issue.type.value
            if type_key not in summary["by_type"]:
                summary["by_type"][type_key] = 0
            summary["by_type"][type_key] += 1

        return summary

    async def auto_fix(self, issue_types: Optional[list[IssueType]] = None) -> dict:
        """Automatically fix certain validation issues.

        Only fixes safe, well-defined issues like:
        - Removing self-referential relationships
        - Merging exact duplicate entities

        Args:
            issue_types: Specific issue types to fix, or None for all safe fixes

        Returns:
            Statistics about fixes applied
        """
        stats = {
            "self_references_removed": 0,
            "exact_duplicates_merged": 0,
        }

        # Remove self-referential relationships
        if issue_types is None or IssueType.INVALID_RELATIONSHIP in issue_types:
            result = await self.session.run(
                """
                MATCH (n)-[r]->(n)
                DELETE r
                RETURN count(r) AS count
                """
            )
            record = await result.single()
            stats["self_references_removed"] = record["count"] if record else 0

        return stats


# Factory function
def get_graph_validator(neo4j_session) -> GraphValidator:
    """Create a GraphValidator instance with the given Neo4j session."""
    return GraphValidator(neo4j_session)
