"""Knowledge graph API endpoints with semantic search and validation."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from pydantic import BaseModel

from db.neo4j import get_neo4j_session
from models.schemas import (
    GraphData,
    GraphNode,
    GraphEdge,
    SemanticSearchRequest,
    SimilarDecision,
    RelationshipType,
)
from services.embeddings import get_embedding_service

router = APIRouter()


# Response models for new endpoints
class ValidationIssueResponse(BaseModel):
    type: str
    severity: str
    message: str
    affected_nodes: list[str]
    suggested_action: Optional[str] = None
    details: Optional[dict] = None


class ValidationSummary(BaseModel):
    total_issues: int
    by_severity: dict[str, int]
    by_type: dict[str, int]
    issues: list[ValidationIssueResponse]


class ContradictionResponse(BaseModel):
    id: str
    trigger: str
    decision: str
    created_at: Optional[str] = None
    confidence: float
    reasoning: Optional[str] = None


class TimelineEntry(BaseModel):
    id: str
    trigger: str
    decision: str
    rationale: Optional[str] = None
    created_at: Optional[str] = None
    source: Optional[str] = None
    supersedes: list[str] = []
    conflicts_with: list[str] = []


class AnalyzeRelationshipsResponse(BaseModel):
    status: str
    supersedes_found: int
    contradicts_found: int
    supersedes_created: int
    contradicts_created: int


@router.get("", response_model=GraphData)
async def get_graph(
    include_similarity: bool = Query(True, description="Include SIMILAR_TO edges"),
    include_temporal: bool = Query(True, description="Include INFLUENCED_BY edges"),
    include_entity_relations: bool = Query(True, description="Include entity-to-entity edges"),
    include_contradictions: bool = Query(False, description="Include CONTRADICTS edges"),
    include_supersessions: bool = Query(False, description="Include SUPERSEDES edges"),
    source_filter: Optional[str] = Query(None, description="Filter by source: claude_logs, interview, manual, unknown"),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0, description="Minimum confidence for relationships"),
):
    """Get the full knowledge graph with all relationship types."""
    try:
        session = await get_neo4j_session()
        async with session:
            nodes = []
            edges = []

            # Build decision query with optional source filter
            if source_filter:
                decision_query = """
                    MATCH (d:DecisionTrace)
                    WHERE d.source = $source OR (d.source IS NULL AND $source = 'unknown')
                    RETURN d, d.embedding IS NOT NULL AS has_embedding
                """
                result = await session.run(decision_query, source=source_filter)
            else:
                result = await session.run(
                    """
                    MATCH (d:DecisionTrace)
                    RETURN d, d.embedding IS NOT NULL AS has_embedding
                    """
                )

            async for record in result:
                d = record["d"]
                has_embedding = record["has_embedding"]
                nodes.append(
                    GraphNode(
                        id=d["id"],
                        type="decision",
                        label=d.get("trigger", "Decision")[:50],
                        has_embedding=has_embedding,
                        data={
                            "trigger": d.get("trigger", ""),
                            "context": d.get("context", ""),
                            "options": d.get("options", []),
                            "decision": d.get("decision", ""),
                            "rationale": d.get("rationale", ""),
                            "confidence": d.get("confidence", 0.0),
                            "created_at": d.get("created_at", ""),
                            "source": d.get("source", "unknown"),
                        },
                    )
                )

            # Get all entity nodes
            result = await session.run(
                """
                MATCH (e:Entity)
                RETURN e, e.embedding IS NOT NULL AS has_embedding
                """
            )

            async for record in result:
                e = record["e"]
                has_embedding = record["has_embedding"]
                nodes.append(
                    GraphNode(
                        id=e["id"],
                        type="entity",
                        label=e.get("name", "Entity"),
                        has_embedding=has_embedding,
                        data={
                            "name": e.get("name", ""),
                            "type": e.get("type", "concept"),
                            "aliases": e.get("aliases", []),
                        },
                    )
                )

            # Build relationship query based on flags
            rel_types = ["INVOLVES"]
            if include_similarity:
                rel_types.append("SIMILAR_TO")
            if include_temporal:
                rel_types.append("INFLUENCED_BY")
            if include_entity_relations:
                rel_types.extend(["IS_A", "PART_OF", "RELATED_TO", "DEPENDS_ON", "ALTERNATIVE_TO"])
            if include_contradictions:
                rel_types.append("CONTRADICTS")
            if include_supersessions:
                rel_types.append("SUPERSEDES")

            # Get all relationships with confidence filtering
            result = await session.run(
                """
                MATCH (a)-[r]->(b)
                WHERE (a:DecisionTrace OR a:Entity) AND (b:DecisionTrace OR b:Entity)
                AND type(r) IN $rel_types
                AND (r.confidence IS NULL OR r.confidence >= $min_confidence)
                AND (r.score IS NULL OR r.score >= $min_confidence)
                RETURN a.id as source, b.id as target, type(r) as relationship,
                       r.weight as weight, r.score as score, r.confidence as confidence,
                       r.shared_entities as shared_entities, r.reasoning as reasoning
                """,
                rel_types=rel_types,
                min_confidence=min_confidence,
            )

            edge_id = 0
            async for record in result:
                # Determine edge weight from various properties
                weight = (
                    record.get("weight")
                    or record.get("score")
                    or record.get("confidence")
                    or 1.0
                )

                edges.append(
                    GraphEdge(
                        id=f"edge-{edge_id}",
                        source=record["source"],
                        target=record["target"],
                        relationship=record["relationship"],
                        weight=weight,
                    )
                )
                edge_id += 1

            return GraphData(nodes=nodes, edges=edges)
    except Exception as e:
        print(f"[Graph] Error fetching graph: {e}")
        return GraphData(nodes=[], edges=[])


@router.get("/validate", response_model=ValidationSummary)
async def validate_graph():
    """Run validation checks on the knowledge graph.

    Checks for:
    - Circular dependencies in DEPENDS_ON chains
    - Orphan entities with no relationships
    - Low confidence relationships
    - Duplicate entities (via fuzzy matching)
    - Missing embeddings
    - Invalid relationship configurations
    """
    from services.validator import get_graph_validator, ValidationIssue

    session = await get_neo4j_session()
    async with session:
        validator = get_graph_validator(session)
        issues = await validator.validate_all()

        # Convert to response format
        issue_responses = [
            ValidationIssueResponse(
                type=issue.type.value,
                severity=issue.severity.value,
                message=issue.message,
                affected_nodes=issue.affected_nodes,
                suggested_action=issue.suggested_action,
                details=issue.details,
            )
            for issue in issues
        ]

        # Calculate summary
        by_severity = {"error": 0, "warning": 0, "info": 0}
        by_type = {}

        for issue in issues:
            by_severity[issue.severity.value] += 1
            type_key = issue.type.value
            if type_key not in by_type:
                by_type[type_key] = 0
            by_type[type_key] += 1

        return ValidationSummary(
            total_issues=len(issues),
            by_severity=by_severity,
            by_type=by_type,
            issues=issue_responses,
        )


@router.get("/decisions/{decision_id}/contradictions", response_model=list[ContradictionResponse])
async def get_contradictions(decision_id: str):
    """Get decisions that contradict this one.

    First checks existing CONTRADICTS relationships, then analyzes
    similar decisions if no existing relationships found.
    """
    from services.decision_analyzer import get_decision_analyzer

    session = await get_neo4j_session()
    async with session:
        analyzer = get_decision_analyzer(session)
        contradictions = await analyzer.detect_contradictions_for_decision(decision_id)

        return [
            ContradictionResponse(
                id=c["id"],
                trigger=c.get("trigger", ""),
                decision=c.get("decision", ""),
                created_at=c.get("created_at"),
                confidence=c.get("confidence", 0.5),
                reasoning=c.get("reasoning"),
            )
            for c in contradictions
        ]


@router.get("/entities/timeline/{entity_name}", response_model=list[TimelineEntry])
async def get_entity_timeline(entity_name: str):
    """Get chronological decisions about an entity.

    Returns all decisions that involve the specified entity,
    ordered by creation date, with information about supersessions
    and contradictions.
    """
    from services.decision_analyzer import get_decision_analyzer

    session = await get_neo4j_session()
    async with session:
        analyzer = get_decision_analyzer(session)
        timeline = await analyzer.get_entity_timeline(entity_name)

        if not timeline:
            raise HTTPException(
                status_code=404,
                detail=f"No decisions found for entity: {entity_name}"
            )

        return [
            TimelineEntry(
                id=entry["id"],
                trigger=entry.get("trigger", ""),
                decision=entry.get("decision", ""),
                rationale=entry.get("rationale"),
                created_at=entry.get("created_at"),
                source=entry.get("source"),
                supersedes=entry.get("supersedes", []),
                conflicts_with=entry.get("conflicts_with", []),
            )
            for entry in timeline
        ]


@router.post("/analyze-relationships", response_model=AnalyzeRelationshipsResponse)
async def analyze_relationships():
    """Trigger batch analysis for SUPERSEDES/CONTRADICTS relationships.

    Analyzes all decision pairs that share entities and creates
    SUPERSEDES and CONTRADICTS relationships where detected.
    """
    from services.decision_analyzer import get_decision_analyzer

    session = await get_neo4j_session()
    async with session:
        analyzer = get_decision_analyzer(session)

        # Analyze all pairs
        analysis = await analyzer.analyze_all_pairs()

        # Save relationships
        save_stats = await analyzer.save_relationships(analysis)

        return AnalyzeRelationshipsResponse(
            status="completed",
            supersedes_found=len(analysis.get("supersedes", [])),
            contradicts_found=len(analysis.get("contradicts", [])),
            supersedes_created=save_stats.get("supersedes_created", 0),
            contradicts_created=save_stats.get("contradicts_created", 0),
        )


@router.get("/decisions/{decision_id}/evolution")
async def get_decision_evolution(decision_id: str):
    """Get the evolution chain for a decision.

    Returns decisions that influenced this one and decisions it supersedes.
    """
    from services.decision_analyzer import get_decision_analyzer

    session = await get_neo4j_session()
    async with session:
        analyzer = get_decision_analyzer(session)
        evolution = await analyzer.get_decision_evolution(decision_id)

        if not evolution:
            raise HTTPException(
                status_code=404,
                detail=f"Decision not found: {decision_id}"
            )

        return evolution


@router.post("/entities/merge-duplicates")
async def merge_duplicate_entities():
    """Find and merge duplicate entities based on fuzzy matching.

    Uses the entity resolver to find similar entity names and
    merges them, transferring all relationships to the primary entity.
    """
    from services.entity_resolver import get_entity_resolver

    session = await get_neo4j_session()
    async with session:
        resolver = get_entity_resolver(session)
        stats = await resolver.merge_duplicate_entities()

        return {
            "status": "completed",
            "groups_found": stats["groups_found"],
            "entities_merged": stats["entities_merged"],
        }


@router.get("/nodes/{node_id}", response_model=GraphNode)
async def get_node_details(node_id: str):
    """Get details for a specific node including its connections."""
    session = await get_neo4j_session()
    async with session:
        # Try to find as decision
        result = await session.run(
            """
            MATCH (d:DecisionTrace {id: $id})
            OPTIONAL MATCH (d)-[:INVOLVES]->(e:Entity)
            OPTIONAL MATCH (d)-[:SUPERSEDES]->(superseded:DecisionTrace)
            OPTIONAL MATCH (d)-[:CONTRADICTS]-(conflicting:DecisionTrace)
            RETURN d,
                   collect(DISTINCT e.name) as entities,
                   collect(DISTINCT superseded.id) as supersedes,
                   collect(DISTINCT conflicting.id) as conflicts_with,
                   d.embedding IS NOT NULL AS has_embedding
            """,
            id=node_id,
        )

        record = await result.single()
        if record and record["d"]:
            d = record["d"]
            entities = record["entities"]
            supersedes = [s for s in record["supersedes"] if s]
            conflicts_with = [c for c in record["conflicts_with"] if c]
            has_embedding = record["has_embedding"]
            return GraphNode(
                id=d["id"],
                type="decision",
                label=d.get("trigger", "Decision")[:50],
                has_embedding=has_embedding,
                data={
                    "trigger": d.get("trigger", ""),
                    "context": d.get("context", ""),
                    "options": d.get("options", []),
                    "decision": d.get("decision", ""),
                    "rationale": d.get("rationale", ""),
                    "confidence": d.get("confidence", 0.0),
                    "created_at": d.get("created_at", ""),
                    "entities": entities,
                    "supersedes": supersedes,
                    "conflicts_with": conflicts_with,
                },
            )

        # Try to find as entity
        result = await session.run(
            """
            MATCH (e:Entity {id: $id})
            OPTIONAL MATCH (d:DecisionTrace)-[:INVOLVES]->(e)
            OPTIONAL MATCH (e)-[r]->(related:Entity)
            RETURN e,
                   collect(DISTINCT d.trigger) as decisions,
                   collect(DISTINCT {name: related.name, rel: type(r)}) as related_entities,
                   e.embedding IS NOT NULL AS has_embedding
            """,
            id=node_id,
        )

        record = await result.single()
        if record and record["e"]:
            e = record["e"]
            decisions = record["decisions"]
            related_entities = record["related_entities"]
            has_embedding = record["has_embedding"]
            return GraphNode(
                id=e["id"],
                type="entity",
                label=e.get("name", "Entity"),
                has_embedding=has_embedding,
                data={
                    "name": e.get("name", ""),
                    "type": e.get("type", "concept"),
                    "aliases": e.get("aliases", []),
                    "decisions": decisions,
                    "related_entities": related_entities,
                },
            )

        raise HTTPException(status_code=404, detail="Node not found")


@router.get("/nodes/{node_id}/similar", response_model=list[SimilarDecision])
async def get_similar_nodes(
    node_id: str,
    top_k: int = Query(5, ge=1, le=20),
    threshold: float = Query(0.5, ge=0.0, le=1.0),
):
    """Find semantically similar decisions using embeddings."""
    session = await get_neo4j_session()
    embedding_service = get_embedding_service()

    async with session:
        # Get the node's embedding
        result = await session.run(
            """
            MATCH (d:DecisionTrace {id: $id})
            RETURN d.embedding as embedding, d.trigger as trigger
            """,
            id=node_id,
        )

        record = await result.single()
        if not record:
            raise HTTPException(status_code=404, detail="Decision not found")

        embedding = record["embedding"]
        if not embedding:
            raise HTTPException(status_code=400, detail="Decision has no embedding")

        # Find similar decisions (try GDS first, fall back to manual)
        try:
            result = await session.run(
                """
                MATCH (d:DecisionTrace)
                WHERE d.id <> $id AND d.embedding IS NOT NULL
                WITH d, gds.similarity.cosine(d.embedding, $embedding) AS similarity
                WHERE similarity > $threshold
                OPTIONAL MATCH (d)-[:INVOLVES]->(e:Entity)
                RETURN d.id as id, d.trigger as trigger, d.decision as decision,
                       similarity, collect(e.name) as shared_entities
                ORDER BY similarity DESC
                LIMIT $top_k
                """,
                id=node_id,
                embedding=embedding,
                threshold=threshold,
                top_k=top_k,
            )
        except Exception:
            # Fall back to manual similarity calculation
            result = await session.run(
                """
                MATCH (d:DecisionTrace)
                WHERE d.id <> $id AND d.embedding IS NOT NULL
                OPTIONAL MATCH (d)-[:INVOLVES]->(e:Entity)
                RETURN d.id as id, d.trigger as trigger, d.decision as decision,
                       d.embedding as other_embedding, collect(e.name) as shared_entities
                """,
                id=node_id,
            )

            similar = []
            async for r in result:
                other_embedding = r["other_embedding"]
                similarity = _cosine_similarity(embedding, other_embedding)
                if similarity > threshold:
                    similar.append(
                        SimilarDecision(
                            id=r["id"],
                            trigger=r["trigger"] or "",
                            decision=r["decision"] or "",
                            similarity=similarity,
                            shared_entities=r["shared_entities"] or [],
                        )
                    )

            similar.sort(key=lambda x: x.similarity, reverse=True)
            return similar[:top_k]

        similar = []
        async for r in result:
            similar.append(
                SimilarDecision(
                    id=r["id"],
                    trigger=r["trigger"] or "",
                    decision=r["decision"] or "",
                    similarity=r["similarity"],
                    shared_entities=r["shared_entities"] or [],
                )
            )

        return similar


@router.post("/search/semantic", response_model=list[SimilarDecision])
async def semantic_search(request: SemanticSearchRequest):
    """Search for decisions semantically similar to a query."""
    embedding_service = get_embedding_service()

    # Generate embedding for the query
    query_embedding = await embedding_service.embed_text(
        request.query, input_type="query"
    )

    session = await get_neo4j_session()
    async with session:
        # Try vector index search first
        try:
            result = await session.run(
                """
                CALL db.index.vector.queryNodes('decision_embedding', $top_k, $embedding)
                YIELD node, score
                WHERE score > $threshold
                OPTIONAL MATCH (node)-[:INVOLVES]->(e:Entity)
                RETURN node.id as id, node.trigger as trigger, node.decision as decision,
                       score as similarity, collect(e.name) as shared_entities
                """,
                embedding=query_embedding,
                top_k=request.top_k,
                threshold=request.threshold,
            )
        except Exception:
            # Fall back to manual search
            result = await session.run(
                """
                MATCH (d:DecisionTrace)
                WHERE d.embedding IS NOT NULL
                OPTIONAL MATCH (d)-[:INVOLVES]->(e:Entity)
                RETURN d.id as id, d.trigger as trigger, d.decision as decision,
                       d.embedding as other_embedding, collect(e.name) as shared_entities
                """
            )

            similar = []
            async for r in result:
                other_embedding = r["other_embedding"]
                similarity = _cosine_similarity(query_embedding, other_embedding)
                if similarity > request.threshold:
                    similar.append(
                        SimilarDecision(
                            id=r["id"],
                            trigger=r["trigger"] or "",
                            decision=r["decision"] or "",
                            similarity=similarity,
                            shared_entities=r["shared_entities"] or [],
                        )
                    )

            similar.sort(key=lambda x: x.similarity, reverse=True)
            return similar[: request.top_k]

        results = []
        async for r in result:
            results.append(
                SimilarDecision(
                    id=r["id"],
                    trigger=r["trigger"] or "",
                    decision=r["decision"] or "",
                    similarity=r["similarity"],
                    shared_entities=r["shared_entities"] or [],
                )
            )

        return results


@router.get("/stats")
async def get_graph_stats():
    """Get statistics about the knowledge graph."""
    session = await get_neo4j_session()
    async with session:
        result = await session.run(
            """
            MATCH (d:DecisionTrace)
            WITH count(d) as total_decisions,
                 count(CASE WHEN d.embedding IS NOT NULL THEN 1 END) as decisions_with_embeddings
            MATCH (e:Entity)
            WITH total_decisions, decisions_with_embeddings,
                 count(e) as total_entities,
                 count(CASE WHEN e.embedding IS NOT NULL THEN 1 END) as entities_with_embeddings
            MATCH ()-[r]->()
            RETURN total_decisions, decisions_with_embeddings,
                   total_entities, entities_with_embeddings,
                   count(r) as total_relationships
            """
        )

        record = await result.single()
        if record:
            return {
                "decisions": {
                    "total": record["total_decisions"],
                    "with_embeddings": record["decisions_with_embeddings"],
                },
                "entities": {
                    "total": record["total_entities"],
                    "with_embeddings": record["entities_with_embeddings"],
                },
                "relationships": record["total_relationships"],
            }

        return {
            "decisions": {"total": 0, "with_embeddings": 0},
            "entities": {"total": 0, "with_embeddings": 0},
            "relationships": 0,
        }


@router.get("/relationships/types")
async def get_relationship_types():
    """Get all relationship types and their counts."""
    session = await get_neo4j_session()
    async with session:
        result = await session.run(
            """
            MATCH ()-[r]->()
            RETURN type(r) as relationship_type, count(r) as count
            ORDER BY count DESC
            """
        )

        types = {}
        async for record in result:
            types[record["relationship_type"]] = record["count"]

        return types


@router.delete("/reset")
async def reset_graph(confirm: bool = Query(False, description="Must be true to confirm deletion")):
    """Clear all data from the knowledge graph.

    WARNING: This permanently deletes all decisions, entities, and relationships.
    Pass confirm=true to execute.
    """
    if not confirm:
        return {
            "status": "aborted",
            "message": "Pass confirm=true to delete all graph data"
        }

    session = await get_neo4j_session()
    async with session:
        # Delete all relationships first
        await session.run("MATCH ()-[r]->() DELETE r")
        # Delete all nodes
        await session.run("MATCH (n) DELETE n")

    return {
        "status": "completed",
        "message": "All graph data has been deleted"
    }


@router.get("/sources")
async def get_decision_sources():
    """Get decision counts by source type."""
    session = await get_neo4j_session()
    async with session:
        result = await session.run(
            """
            MATCH (d:DecisionTrace)
            RETURN
                COALESCE(d.source, 'unknown') as source,
                count(d) as count
            ORDER BY count DESC
            """
        )

        sources = {}
        async for record in result:
            sources[record["source"]] = record["count"]

        return sources


@router.post("/tag-sources")
async def tag_decision_sources():
    """
    Tag existing decisions with their source based on heuristics.
    - Decisions created before the ingestion feature are likely 'interview' or 'manual'
    - This is a one-time migration helper
    """
    session = await get_neo4j_session()
    results = {"tagged": 0}

    async with session:
        # Tag decisions without source as 'unknown' (legacy)
        result = await session.run(
            """
            MATCH (d:DecisionTrace)
            WHERE d.source IS NULL
            SET d.source = 'unknown'
            RETURN count(d) as count
            """
        )
        record = await result.single()
        results["tagged"] = record["count"] if record else 0

    return {
        "status": "completed",
        "results": results,
    }


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_product / (norm_a * norm_b)


@router.post("/enhance")
async def enhance_graph():
    """
    Backfill embeddings and relationships for existing nodes.
    This enhances the graph by:
    1. Adding embeddings to decisions without them
    2. Adding embeddings to entities without them
    3. Creating SIMILAR_TO edges between similar decisions
    4. Creating entity-to-entity relationships
    """
    from services.extractor import DecisionExtractor

    embedding_service = get_embedding_service()
    extractor = DecisionExtractor()

    session = await get_neo4j_session()
    results = {
        "decisions_enhanced": 0,
        "entities_enhanced": 0,
        "similarity_edges_created": 0,
        "entity_relationships_created": 0,
    }

    async with session:
        # 1. Add embeddings to decisions without them
        result = await session.run(
            """
            MATCH (d:DecisionTrace)
            WHERE d.embedding IS NULL
            RETURN d.id as id, d.trigger as trigger, d.context as context,
                   d.decision as decision, d.rationale as rationale,
                   d.options as options
            """
        )

        decisions_to_enhance = [r async for r in result]
        print(f"[Enhance] Found {len(decisions_to_enhance)} decisions without embeddings")

        for dec in decisions_to_enhance:
            try:
                decision_dict = {
                    "trigger": dec["trigger"] or "",
                    "context": dec["context"] or "",
                    "options": dec["options"] or [],
                    "decision": dec["decision"] or "",
                    "rationale": dec["rationale"] or "",
                }
                embedding = await embedding_service.embed_decision(decision_dict)

                await session.run(
                    """
                    MATCH (d:DecisionTrace {id: $id})
                    SET d.embedding = $embedding
                    """,
                    id=dec["id"],
                    embedding=embedding,
                )
                results["decisions_enhanced"] += 1
                print(f"[Enhance] Added embedding to decision {dec['id'][:8]}...")
            except Exception as e:
                print(f"[Enhance] Failed to enhance decision {dec['id']}: {e}")

        # 2. Add embeddings to entities without them
        result = await session.run(
            """
            MATCH (e:Entity)
            WHERE e.embedding IS NULL
            RETURN e.id as id, e.name as name, e.type as type
            """
        )

        entities_to_enhance = [r async for r in result]
        print(f"[Enhance] Found {len(entities_to_enhance)} entities without embeddings")

        for ent in entities_to_enhance:
            try:
                entity_dict = {"name": ent["name"], "type": ent["type"]}
                embedding = await embedding_service.embed_entity(entity_dict)

                await session.run(
                    """
                    MATCH (e:Entity {id: $id})
                    SET e.embedding = $embedding
                    """,
                    id=ent["id"],
                    embedding=embedding,
                )
                results["entities_enhanced"] += 1
            except Exception as e:
                print(f"[Enhance] Failed to enhance entity {ent['name']}: {e}")

        # 3. Create SIMILAR_TO edges between similar decisions
        result = await session.run(
            """
            MATCH (d:DecisionTrace)
            WHERE d.embedding IS NOT NULL
            RETURN d.id as id, d.embedding as embedding
            """
        )

        decisions_with_embeddings = [r async for r in result]
        print(f"[Enhance] Checking similarity between {len(decisions_with_embeddings)} decisions")

        similarity_threshold = 0.75
        for i, d1 in enumerate(decisions_with_embeddings):
            for d2 in decisions_with_embeddings[i + 1:]:
                similarity = _cosine_similarity(d1["embedding"], d2["embedding"])
                if similarity > similarity_threshold:
                    # Create bidirectional SIMILAR_TO edges
                    await session.run(
                        """
                        MATCH (d1:DecisionTrace {id: $id1})
                        MATCH (d2:DecisionTrace {id: $id2})
                        MERGE (d1)-[r:SIMILAR_TO]->(d2)
                        SET r.score = $score
                        """,
                        id1=d1["id"],
                        id2=d2["id"],
                        score=similarity,
                    )
                    results["similarity_edges_created"] += 1
                    print(f"[Enhance] Created SIMILAR_TO edge (score: {similarity:.3f})")

        # 4. Create entity-to-entity relationships using LLM
        result = await session.run(
            """
            MATCH (e:Entity)
            RETURN e.id as id, e.name as name, e.type as type
            """
        )

        all_entities = [r async for r in result]
        print(f"[Enhance] Analyzing relationships between {len(all_entities)} entities")

        if len(all_entities) >= 2:
            from models.schemas import Entity

            entity_objects = [
                Entity(id=e["id"], name=e["name"], type=e["type"])
                for e in all_entities
            ]

            # Process in batches to avoid token limits
            batch_size = 15
            for i in range(0, len(entity_objects), batch_size):
                batch = entity_objects[i:i + batch_size]
                if len(batch) < 2:
                    continue

                try:
                    relationships = await extractor.extract_entity_relationships(batch)
                    print(f"[Enhance] Found {len(relationships)} relationships in batch")

                    for rel in relationships:
                        rel_type = rel.get("type", rel.get("relationship", "RELATED_TO"))
                        confidence = rel.get("confidence", 0.8)

                        valid_types = ["IS_A", "PART_OF", "RELATED_TO", "DEPENDS_ON", "ALTERNATIVE_TO"]
                        if rel_type not in valid_types:
                            rel_type = "RELATED_TO"

                        await session.run(
                            f"""
                            MATCH (e1:Entity)
                            WHERE toLower(e1.name) = toLower($from_name)
                            MATCH (e2:Entity)
                            WHERE toLower(e2.name) = toLower($to_name)
                            WHERE e1 <> e2
                            MERGE (e1)-[r:{rel_type}]->(e2)
                            SET r.confidence = $confidence
                            """,
                            from_name=rel.get("from"),
                            to_name=rel.get("to"),
                            confidence=confidence,
                        )
                        results["entity_relationships_created"] += 1
                except Exception as e:
                    print(f"[Enhance] Error extracting entity relationships: {e}")

        # 5. Create INFLUENCED_BY temporal chains
        await session.run(
            """
            MATCH (d_new:DecisionTrace)
            MATCH (d_old:DecisionTrace)-[:INVOLVES]->(e:Entity)<-[:INVOLVES]-(d_new)
            WHERE d_old.id <> d_new.id AND d_old.created_at < d_new.created_at
            WITH d_new, d_old, count(DISTINCT e) AS shared_count
            WHERE shared_count >= 2
            MERGE (d_new)-[r:INFLUENCED_BY]->(d_old)
            SET r.shared_entities = shared_count
            """
        )

    return {
        "status": "completed",
        "results": results,
    }
