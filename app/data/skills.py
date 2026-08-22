"""Canonical skill taxonomy used to extract structured skills from free text.

Maps a canonical skill name to the surface forms that should resolve to it.
Alias matching is word-boundary based, so "Go" does not match "Google".
"""

SKILL_ALIASES: dict[str, list[str]] = {
    "Python": ["python", "py3"],
    "TypeScript": ["typescript", "ts"],
    "JavaScript": ["javascript", "js", "es6"],
    "Go": ["golang", "go"],
    "Rust": ["rust"],
    "Java": ["java"],
    "SQL": ["sql", "ansi sql"],
    "FastAPI": ["fastapi"],
    "Django": ["django"],
    "Flask": ["flask"],
    "Node.js": ["node.js", "nodejs", "node"],
    "React": ["react", "react.js", "reactjs"],
    "Next.js": ["next.js", "nextjs"],
    "GraphQL": ["graphql"],
    "gRPC": ["grpc"],
    "REST APIs": ["rest api", "rest apis", "restful", "rest"],
    "PostgreSQL": ["postgresql", "postgres", "psql"],
    "Redis": ["redis"],
    "MongoDB": ["mongodb", "mongo"],
    "Elasticsearch": ["elasticsearch", "opensearch"],
    "pgvector": ["pgvector"],
    "Kafka": ["kafka"],
    "RabbitMQ": ["rabbitmq"],
    "Spark": ["spark", "pyspark"],
    "Airflow": ["airflow"],
    "dbt": ["dbt"],
    "Snowflake": ["snowflake"],
    "Docker": ["docker", "containerization"],
    "Kubernetes": ["kubernetes", "k8s", "eks", "gke"],
    "Terraform": ["terraform", "opentofu"],
    "AWS": ["aws", "amazon web services", "ec2", "lambda", "s3"],
    "GCP": ["gcp", "google cloud"],
    "Azure": ["azure"],
    "CI/CD": ["ci/cd", "continuous integration", "continuous delivery", "github actions", "jenkins"],
    "Observability": ["observability", "datadog", "prometheus", "grafana", "opentelemetry"],
    "System Design": ["system design", "distributed systems", "scalability", "high availability"],
    "Microservices": ["microservices", "service oriented"],
    "Machine Learning": ["machine learning", "ml", "predictive model"],
    "Deep Learning": ["deep learning", "neural network"],
    "PyTorch": ["pytorch", "torch"],
    "TensorFlow": ["tensorflow", "keras"],
    "LLMs": ["llm", "llms", "large language model", "gpt", "prompt engineering"],
    "RAG": ["rag", "retrieval augmented generation", "retrieval-augmented"],
    "LangChain": ["langchain", "langgraph"],
    "Vector Databases": ["vector database", "vector search", "pinecone", "weaviate", "embeddings"],
    "MLOps": ["mlops", "model deployment", "model serving"],
    "Data Modeling": ["data modeling", "dimensional model", "star schema"],
    "ETL": ["etl", "elt", "data pipeline", "data pipelines"],
    "Pandas": ["pandas", "numpy"],
    "Tableau": ["tableau", "looker", "power bi"],
    "A/B Testing": ["a/b testing", "experimentation", "ab test"],
    "Product Analytics": ["product analytics", "amplitude", "mixpanel"],
    "Testing": ["pytest", "unit test", "unit tests", "integration test", "test coverage", "jest"],
    "Security": ["oauth", "authentication", "authorization", "soc 2", "encryption"],
    "Leadership": ["mentoring", "mentored", "tech lead", "led a team", "cross-functional"],
    "Agile": ["agile", "scrum", "sprint planning"],
}

# Skills a hiring market typically expects for a given target title. Used to
# compute gaps even before any live posting mentions them.
ROLE_CORE_SKILLS: dict[str, list[str]] = {
    "senior software engineer": [
        "System Design",
        "Kubernetes",
        "AWS",
        "PostgreSQL",
        "CI/CD",
        "Observability",
        "Testing",
        "Leadership",
    ],
    "backend engineer": [
        "Python",
        "PostgreSQL",
        "REST APIs",
        "Docker",
        "Kafka",
        "System Design",
        "Redis",
    ],
    "ai engineer": [
        "LLMs",
        "RAG",
        "Vector Databases",
        "LangChain",
        "Python",
        "MLOps",
        "PyTorch",
    ],
    "machine learning engineer": [
        "PyTorch",
        "MLOps",
        "Machine Learning",
        "Spark",
        "Python",
        "AWS",
        "Deep Learning",
    ],
    "data engineer": [
        "Spark",
        "Airflow",
        "dbt",
        "SQL",
        "Snowflake",
        "ETL",
        "Data Modeling",
    ],
    "frontend engineer": [
        "TypeScript",
        "React",
        "Next.js",
        "Testing",
        "GraphQL",
        "JavaScript",
    ],
    "platform engineer": [
        "Kubernetes",
        "Terraform",
        "AWS",
        "CI/CD",
        "Observability",
        "Docker",
        "Go",
    ],
    "data analyst": [
        "SQL",
        "Tableau",
        "Product Analytics",
        "A/B Testing",
        "Pandas",
        "Data Modeling",
    ],
}

DEFAULT_ROLE_SKILLS = ROLE_CORE_SKILLS["senior software engineer"]


def core_skills_for_title(title: str | None) -> list[str]:
    """Best-effort lookup of expected skills for a free-text target title."""
    if not title:
        return DEFAULT_ROLE_SKILLS
    normalized = title.strip().lower()
    if normalized in ROLE_CORE_SKILLS:
        return ROLE_CORE_SKILLS[normalized]
    for role, skills in ROLE_CORE_SKILLS.items():
        # "Senior Backend Engineer" should resolve to the backend engineer set.
        if role in normalized or normalized in role:
            return skills
    tokens = set(normalized.split())
    best_role, best_overlap = None, 0
    for role in ROLE_CORE_SKILLS:
        overlap = len(tokens & set(role.split()))
        if overlap > best_overlap:
            best_role, best_overlap = role, overlap
    return ROLE_CORE_SKILLS[best_role] if best_role else DEFAULT_ROLE_SKILLS
