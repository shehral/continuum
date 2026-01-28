"""Ontology schema definition for knowledge graph entities and relationships."""

from enum import Enum
from dataclasses import dataclass
from typing import Optional


class EntityType(Enum):
    """Types of entities that can be extracted from decisions."""
    TECHNOLOGY = "technology"      # PostgreSQL, React, Neo4j
    CONCEPT = "concept"            # microservices, REST API, caching
    PATTERN = "pattern"            # singleton, repository pattern
    SYSTEM = "system"              # authentication system, payment gateway
    PERSON = "person"              # team members, stakeholders
    ORGANIZATION = "organization"  # companies, teams


class RelationType(Enum):
    """Types of relationships in the knowledge graph."""
    # Entity-Entity relationships
    IS_A = "IS_A"                   # X is a type/category of Y
    PART_OF = "PART_OF"             # X is a component of Y
    DEPENDS_ON = "DEPENDS_ON"       # X requires Y
    RELATED_TO = "RELATED_TO"       # X is related to Y (general)
    ALTERNATIVE_TO = "ALTERNATIVE_TO"  # X can be used instead of Y

    # Decision-Entity relationships
    INVOLVES = "INVOLVES"           # Decision involves this entity

    # Decision-Decision relationships
    SIMILAR_TO = "SIMILAR_TO"       # Decisions have similar content
    INFLUENCED_BY = "INFLUENCED_BY"  # Decision was influenced by earlier one
    SUPERSEDES = "SUPERSEDES"       # New decision replaces older one
    CONTRADICTS = "CONTRADICTS"     # Decisions conflict with each other


# Canonical name mappings for entity resolution
# Maps various aliases/variations to the canonical name
CANONICAL_NAMES: dict[str, str] = {
    # Databases
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "pg": "PostgreSQL",
    "mongodb": "MongoDB",
    "mongo": "MongoDB",
    "neo4j": "Neo4j",
    "neo": "Neo4j",
    "redis": "Redis",
    "mysql": "MySQL",
    "mariadb": "MariaDB",
    "sqlite": "SQLite",
    "dynamodb": "DynamoDB",
    "dynamo": "DynamoDB",
    "cassandra": "Cassandra",
    "elasticsearch": "Elasticsearch",
    "elastic": "Elasticsearch",
    "es": "Elasticsearch",

    # Programming languages
    "python": "Python",
    "py": "Python",
    "python3": "Python",
    "javascript": "JavaScript",
    "js": "JavaScript",
    "typescript": "TypeScript",
    "ts": "TypeScript",
    "golang": "Go",
    "go": "Go",
    "rust": "Rust",
    "java": "Java",
    "kotlin": "Kotlin",
    "swift": "Swift",
    "c#": "C#",
    "csharp": "C#",
    "c++": "C++",
    "cpp": "C++",
    "ruby": "Ruby",
    "php": "PHP",

    # Frontend frameworks
    "react": "React",
    "reactjs": "React",
    "react.js": "React",
    "vue": "Vue.js",
    "vuejs": "Vue.js",
    "vue.js": "Vue.js",
    "angular": "Angular",
    "angularjs": "Angular",
    "svelte": "Svelte",
    "nextjs": "Next.js",
    "next.js": "Next.js",
    "next": "Next.js",
    "nuxt": "Nuxt.js",
    "nuxtjs": "Nuxt.js",
    "nuxt.js": "Nuxt.js",

    # Backend frameworks
    "fastapi": "FastAPI",
    "fast-api": "FastAPI",
    "django": "Django",
    "flask": "Flask",
    "express": "Express.js",
    "expressjs": "Express.js",
    "express.js": "Express.js",
    "nestjs": "NestJS",
    "nest.js": "NestJS",
    "spring": "Spring",
    "springboot": "Spring Boot",
    "spring boot": "Spring Boot",
    "rails": "Ruby on Rails",
    "ruby on rails": "Ruby on Rails",
    "ror": "Ruby on Rails",

    # API standards
    "api": "API",
    "rest": "REST API",
    "rest api": "REST API",
    "restful": "REST API",
    "graphql": "GraphQL",
    "gql": "GraphQL",
    "grpc": "gRPC",
    "websocket": "WebSocket",
    "websockets": "WebSocket",
    "ws": "WebSocket",

    # Cloud providers
    "aws": "AWS",
    "amazon web services": "AWS",
    "gcp": "GCP",
    "google cloud": "GCP",
    "google cloud platform": "GCP",
    "azure": "Azure",
    "microsoft azure": "Azure",

    # Containerization
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
    "helm": "Helm",

    # Message queues
    "kafka": "Apache Kafka",
    "apache kafka": "Apache Kafka",
    "rabbitmq": "RabbitMQ",
    "rabbit mq": "RabbitMQ",
    "sqs": "Amazon SQS",
    "amazon sqs": "Amazon SQS",

    # AI/ML
    "openai": "OpenAI",
    "gpt": "GPT",
    "chatgpt": "ChatGPT",
    "claude": "Claude",
    "anthropic": "Anthropic",
    "gemini": "Gemini",
    "tensorflow": "TensorFlow",
    "tf": "TensorFlow",
    "pytorch": "PyTorch",
    "torch": "PyTorch",

    # Testing
    "jest": "Jest",
    "pytest": "pytest",
    "py.test": "pytest",
    "mocha": "Mocha",
    "cypress": "Cypress",
    "playwright": "Playwright",

    # ORMs
    "sqlalchemy": "SQLAlchemy",
    "prisma": "Prisma",
    "typeorm": "TypeORM",
    "sequelize": "Sequelize",
    "mongoose": "Mongoose",

    # UI libraries
    "tailwind": "Tailwind CSS",
    "tailwindcss": "Tailwind CSS",
    "tailwind css": "Tailwind CSS",
    "bootstrap": "Bootstrap",
    "material ui": "Material UI",
    "mui": "Material UI",
    "shadcn": "shadcn/ui",
    "shadcn/ui": "shadcn/ui",
    "chakra": "Chakra UI",
    "chakra ui": "Chakra UI",

    # State management
    "redux": "Redux",
    "zustand": "Zustand",
    "mobx": "MobX",
    "recoil": "Recoil",
    "jotai": "Jotai",

    # Build tools
    "webpack": "Webpack",
    "vite": "Vite",
    "esbuild": "esbuild",
    "rollup": "Rollup",
    "parcel": "Parcel",

    # Version control
    "git": "Git",
    "github": "GitHub",
    "gitlab": "GitLab",
    "bitbucket": "Bitbucket",

    # Common patterns/concepts
    "microservices": "Microservices",
    "microservice": "Microservices",
    "monolith": "Monolith",
    "monolithic": "Monolith",
    "serverless": "Serverless",
    "jwt": "JWT",
    "json web token": "JWT",
    "oauth": "OAuth",
    "oauth2": "OAuth 2.0",
    "oauth 2.0": "OAuth 2.0",
    "ci/cd": "CI/CD",
    "ci cd": "CI/CD",
    "continuous integration": "CI/CD",
    "continuous deployment": "CI/CD",
}


@dataclass
class ResolvedEntity:
    """Result of entity resolution."""
    id: Optional[str]
    name: str
    type: str
    is_new: bool = False
    match_method: Optional[str] = None
    confidence: float = 1.0
    canonical_name: Optional[str] = None
    aliases: list[str] = None

    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []


def get_canonical_name(name: str) -> str:
    """Get the canonical name for an entity, or return the original if not found."""
    return CANONICAL_NAMES.get(name.lower(), name)


def normalize_entity_name(name: str) -> str:
    """Normalize an entity name for comparison (lowercase, strip whitespace)."""
    return name.lower().strip()
