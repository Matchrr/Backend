"""Seed corpus for the MVP.

Stands in for the SerpApi harvest so the product runs end to end without any
API keys. Shapes mirror what the live Google Jobs / event harvest returns, so
swapping in the real pipeline means replacing these lists, not the callers.
"""

from typing import Any

JOB_SEED: list[dict[str, Any]] = [
    {
        "id": "job_stripe_be",
        "title": "Senior Backend Engineer, Payments Infrastructure",
        "company": "Stripe",
        "location": "Remote (US)",
        "source": "LinkedIn via Google Jobs",
        "posted_at": "2 days ago",
        "salary": "$196k – $265k",
        "apply_url": "https://stripe.com/jobs",
        "description": (
            "Build and scale the ledger services that move billions of dollars a day. "
            "You will design idempotent REST APIs in Python, model financial state in "
            "PostgreSQL, and publish events through Kafka to downstream consumers. "
            "We run everything on Kubernetes with Terraform-managed AWS infrastructure "
            "and expect strong system design instincts around consistency, high "
            "availability, and distributed systems failure modes. Experience with "
            "observability tooling and a rigorous testing culture is required. You will "
            "mentor engineers and lead cross-functional design reviews."
        ),
    },
    {
        "id": "job_anthropic_ai",
        "title": "AI Engineer, Applied Products",
        "company": "Anthropic",
        "location": "San Francisco, CA (Hybrid)",
        "source": "Greenhouse via Google Jobs",
        "posted_at": "4 days ago",
        "salary": "$230k – $310k",
        "apply_url": "https://www.anthropic.com/careers",
        "description": (
            "Ship product features powered by large language models. You will build "
            "retrieval augmented generation pipelines in Python, tune prompt engineering "
            "strategies, and operate vector search over embeddings stored in pgvector. "
            "Familiarity with LangChain or comparable orchestration, evaluation harnesses, "
            "and MLOps practices for model deployment is expected. You will own REST APIs "
            "serving inference traffic and partner with research on quality measurement."
        ),
    },
    {
        "id": "job_datadog_platform",
        "title": "Platform Engineer, Developer Infrastructure",
        "company": "Datadog",
        "location": "New York, NY (Hybrid)",
        "source": "Indeed via Google Jobs",
        "posted_at": "1 day ago",
        "salary": "$170k – $225k",
        "apply_url": "https://careers.datadoghq.com",
        "description": (
            "Own the internal platform that hundreds of engineers deploy through. You will "
            "write Go and Python services, manage Kubernetes clusters, codify AWS resources "
            "in Terraform, and maintain CI/CD pipelines with GitHub Actions. Deep "
            "observability experience with Prometheus, Grafana, and OpenTelemetry is core "
            "to the role. Containerization with Docker and a bias toward automation and "
            "reliability engineering are essential."
        ),
    },
    {
        "id": "job_openai_ml",
        "title": "Machine Learning Engineer, Model Serving",
        "company": "OpenAI",
        "location": "San Francisco, CA",
        "source": "Google Jobs",
        "posted_at": "6 days ago",
        "salary": "$245k – $340k",
        "apply_url": "https://openai.com/careers",
        "description": (
            "Take deep learning models from research to production. You will optimize "
            "PyTorch inference paths, build model serving infrastructure on Kubernetes, "
            "and own MLOps tooling for deployment, rollback, and monitoring. Strong Python "
            "engineering, distributed systems knowledge, and experience with GPU scheduling "
            "and throughput benchmarking are expected. Familiarity with LLMs and large scale "
            "training pipelines is a plus."
        ),
    },
    {
        "id": "job_airbnb_be",
        "title": "Senior Software Engineer, Booking Platform",
        "company": "Airbnb",
        "location": "Remote (US)",
        "source": "LinkedIn via Google Jobs",
        "posted_at": "3 days ago",
        "salary": "$185k – $250k",
        "apply_url": "https://careers.airbnb.com",
        "description": (
            "Lead backend work on the reservations platform. You will design microservices "
            "in Java and Python, expose gRPC and REST APIs, and tune PostgreSQL and Redis "
            "for read-heavy traffic. The role demands strong system design, experience "
            "operating services on Kubernetes in AWS, and a track record of mentoring "
            "engineers. You will define testing standards and drive observability for "
            "critical booking flows."
        ),
    },
    {
        "id": "job_snowflake_data",
        "title": "Data Engineer, Analytics Platform",
        "company": "Snowflake",
        "location": "Remote (US)",
        "source": "Glassdoor via Google Jobs",
        "posted_at": "5 days ago",
        "salary": "$155k – $205k",
        "apply_url": "https://careers.snowflake.com",
        "description": (
            "Build the ELT backbone for company-wide analytics. You will author Spark jobs, "
            "orchestrate data pipelines in Airflow, and model warehouse layers with dbt and "
            "SQL on Snowflake. Solid data modeling fundamentals, Python proficiency, and "
            "experience with data quality testing are required. You will partner with "
            "analysts on dimensional models that power Tableau reporting."
        ),
    },
    {
        "id": "job_vercel_fe",
        "title": "Senior Frontend Engineer, Dashboard",
        "company": "Vercel",
        "location": "Remote (Global)",
        "source": "Google Jobs",
        "posted_at": "1 week ago",
        "salary": "$160k – $215k",
        "apply_url": "https://vercel.com/careers",
        "description": (
            "Own the customer-facing dashboard. You will write TypeScript and React, ship "
            "Next.js applications at scale, and consume GraphQL and REST APIs. Strong "
            "product sense, accessibility rigor, and a real testing discipline with Jest "
            "are expected. Experience with performance profiling and design systems will "
            "set you apart."
        ),
    },
    {
        "id": "job_notion_ai",
        "title": "AI Product Engineer",
        "company": "Notion",
        "location": "New York, NY (Hybrid)",
        "source": "LinkedIn via Google Jobs",
        "posted_at": "2 days ago",
        "salary": "$190k – $250k",
        "apply_url": "https://www.notion.so/careers",
        "description": (
            "Turn LLM capability into shipped product surfaces. You will build retrieval "
            "augmented generation over user workspaces, run vector search with embeddings, "
            "and write TypeScript and Python across the stack. You will design evaluation "
            "loops, manage prompt engineering iterations, and expose REST APIs backed by "
            "PostgreSQL. Comfort with ambiguity and fast iteration is essential."
        ),
    },
    {
        "id": "job_ramp_be",
        "title": "Backend Engineer, Risk",
        "company": "Ramp",
        "location": "New York, NY",
        "source": "Greenhouse via Google Jobs",
        "posted_at": "3 days ago",
        "salary": "$175k – $230k",
        "apply_url": "https://ramp.com/careers",
        "description": (
            "Build the services that score transaction risk in real time. You will write "
            "Python with FastAPI, persist to PostgreSQL, cache in Redis, and stream events "
            "through Kafka. Machine learning familiarity helps but is not required. Docker "
            "based deployment, meaningful test coverage, and clean REST API design matter "
            "more than credentials here."
        ),
    },
    {
        "id": "job_hashicorp_platform",
        "title": "Senior Platform Engineer, Cloud",
        "company": "HashiCorp",
        "location": "Remote (US)",
        "source": "Indeed via Google Jobs",
        "posted_at": "1 week ago",
        "salary": "$180k – $240k",
        "apply_url": "https://www.hashicorp.com/careers",
        "description": (
            "Operate multi-region infrastructure for a developer tooling company. Deep "
            "Terraform, Kubernetes, and AWS expertise is the baseline. You will write Go "
            "services, harden CI/CD, and build observability into every layer with "
            "Prometheus and OpenTelemetry. Security-minded engineering around "
            "authentication, authorization, and SOC 2 controls is part of the job."
        ),
    },
    {
        "id": "job_figma_be",
        "title": "Software Engineer, Collaboration Backend",
        "company": "Figma",
        "location": "San Francisco, CA (Hybrid)",
        "source": "Google Jobs",
        "posted_at": "4 days ago",
        "salary": "$165k – $220k",
        "apply_url": "https://www.figma.com/careers",
        "description": (
            "Work on the realtime multiplayer engine. You will write TypeScript and Rust, "
            "design distributed systems that resolve concurrent edits, and operate services "
            "with strict latency budgets. Experience with WebSockets, Redis, and "
            "high-availability architecture is valued. Strong testing habits and system "
            "design depth are required."
        ),
    },
    {
        "id": "job_databricks_ml",
        "title": "Machine Learning Engineer, Recommendations",
        "company": "Databricks",
        "location": "Remote (US)",
        "source": "LinkedIn via Google Jobs",
        "posted_at": "5 days ago",
        "salary": "$200k – $270k",
        "apply_url": "https://www.databricks.com/company/careers",
        "description": (
            "Own recommendation models end to end. You will engineer features with Spark "
            "and Pandas, train models in PyTorch, and deploy through an MLOps stack on AWS. "
            "Strong machine learning fundamentals, Python skill, and experience running "
            "A/B testing to validate model impact are required. SQL fluency for analysis is "
            "expected."
        ),
    },
    {
        "id": "job_linear_fullstack",
        "title": "Full Stack Engineer",
        "company": "Linear",
        "location": "Remote (Global)",
        "source": "Google Jobs",
        "posted_at": "6 days ago",
        "salary": "$170k – $225k",
        "apply_url": "https://linear.app/careers",
        "description": (
            "Ship across the stack on a small, senior team. You will write TypeScript with "
            "React and Node.js, design GraphQL APIs, and model data in PostgreSQL. Product "
            "taste matters as much as engineering depth. You will own features from spec to "
            "production, including testing and observability."
        ),
    },
    {
        "id": "job_scale_data",
        "title": "Senior Data Engineer",
        "company": "Scale AI",
        "location": "San Francisco, CA",
        "source": "Greenhouse via Google Jobs",
        "posted_at": "1 week ago",
        "salary": "$180k – $235k",
        "apply_url": "https://scale.com/careers",
        "description": (
            "Build ETL infrastructure for training data at petabyte scale. You will run "
            "Spark on Kubernetes, orchestrate with Airflow, and write Python and SQL daily. "
            "Data modeling rigor, Docker fluency, and experience with data quality "
            "monitoring are required. Exposure to machine learning workflows is a strong "
            "plus."
        ),
    },
    {
        "id": "job_shopify_be",
        "title": "Senior Backend Developer, Merchant Services",
        "company": "Shopify",
        "location": "Remote (North America)",
        "source": "Indeed via Google Jobs",
        "posted_at": "3 days ago",
        "salary": "$165k – $215k",
        "apply_url": "https://www.shopify.com/careers",
        "description": (
            "Scale the APIs that thousands of merchants build on. You will design REST and "
            "GraphQL interfaces, optimize PostgreSQL queries, and use Redis and Kafka for "
            "asynchronous workloads. The team values microservices discipline, strong "
            "system design, CI/CD automation, and mentoring across the org."
        ),
    },
    {
        "id": "job_mistral_ai",
        "title": "LLM Infrastructure Engineer",
        "company": "Mistral AI",
        "location": "Remote (US/EU)",
        "source": "Google Jobs",
        "posted_at": "2 days ago",
        "salary": "$210k – $290k",
        "apply_url": "https://mistral.ai/careers",
        "description": (
            "Run the serving layer for frontier models. You will optimize PyTorch inference, "
            "operate Kubernetes GPU clusters, and build MLOps pipelines for continuous model "
            "deployment. Python and Rust engineering, deep observability practice, and "
            "distributed systems fundamentals are core. Familiarity with vector databases "
            "and RAG serving patterns is welcome."
        ),
    },
]

EVENT_SEED: list[dict[str, Any]] = [
    {
        "id": "event_ai_eng_summit",
        "name": "AI Engineer Summit 2026",
        "organizer": "AI Engineer",
        "location": "San Francisco, CA",
        "format": "in-person",
        "starts_at": "2026-09-18",
        "url": "https://www.ai.engineer",
        "attendee_profile": "Applied AI engineers, LLM infrastructure teams, founders",
        "description": (
            "Two days on production LLMs: retrieval augmented generation architectures, "
            "vector search at scale, evaluation harnesses, prompt engineering, and MLOps "
            "for model deployment. Talks from teams running Python inference services on "
            "Kubernetes."
        ),
    },
    {
        "id": "event_kubecon",
        "name": "KubeCon + CloudNativeCon North America",
        "organizer": "CNCF",
        "location": "Salt Lake City, UT",
        "format": "in-person",
        "starts_at": "2026-11-10",
        "url": "https://www.cncf.io/kubecon-cloudnativecon-events",
        "attendee_profile": "Platform engineers, SREs, infrastructure leads",
        "description": (
            "The flagship Kubernetes conference. Deep tracks on Kubernetes operators, "
            "Terraform workflows, observability with Prometheus and OpenTelemetry, CI/CD "
            "at scale, container security, and multi-cloud AWS and GCP architecture."
        ),
    },
    {
        "id": "event_pgconf",
        "name": "PGConf NYC",
        "organizer": "PostgreSQL Community",
        "location": "New York, NY",
        "format": "in-person",
        "starts_at": "2026-10-02",
        "url": "https://postgresql.us",
        "attendee_profile": "Backend engineers, database engineers, data architects",
        "description": (
            "PostgreSQL internals, query optimization, replication and high availability, "
            "and a growing pgvector track covering embeddings and vector search for "
            "retrieval augmented generation workloads."
        ),
    },
    {
        "id": "event_ny_backend_meetup",
        "name": "NYC Backend Engineering Meetup",
        "organizer": "NYC Backend Collective",
        "location": "New York, NY",
        "format": "in-person",
        "starts_at": "2026-09-04",
        "url": "https://www.meetup.com",
        "attendee_profile": "Senior backend engineers and tech leads from NYC startups",
        "description": (
            "Monthly evening talks on distributed systems, Kafka event pipelines, "
            "microservices decomposition, PostgreSQL scaling, and API design. Hiring "
            "managers from local fintech and infrastructure companies regularly attend."
        ),
    },
    {
        "id": "event_data_council",
        "name": "Data Council",
        "organizer": "Data Council",
        "location": "Austin, TX",
        "format": "in-person",
        "starts_at": "2026-10-21",
        "url": "https://www.datacouncil.ai",
        "attendee_profile": "Data engineers, analytics engineers, ML platform teams",
        "description": (
            "Practitioner conference on ETL architecture, Spark and Airflow orchestration, "
            "dbt modeling patterns, Snowflake warehouse design, and the data layer beneath "
            "machine learning systems."
        ),
    },
    {
        "id": "event_rag_workshop",
        "name": "Building Production RAG Systems (Workshop)",
        "organizer": "LangChain",
        "location": "Virtual",
        "format": "virtual",
        "starts_at": "2026-09-11",
        "url": "https://www.langchain.com",
        "attendee_profile": "Engineers shipping LLM features",
        "description": (
            "Hands-on workshop building a retrieval augmented generation pipeline with "
            "LangChain, embeddings, and a vector database. Covers chunking strategy, "
            "reranking, evaluation, and serving RAG behind REST APIs."
        ),
    },
    {
        "id": "event_sre_office_hours",
        "name": "SRE & Observability Office Hours",
        "organizer": "Grafana Labs",
        "location": "Virtual",
        "format": "virtual",
        "starts_at": "2026-08-28",
        "url": "https://grafana.com/community",
        "attendee_profile": "Platform and reliability engineers",
        "description": (
            "Open Q&A on observability practice: Prometheus metric design, Grafana "
            "dashboards, OpenTelemetry tracing, and incident response for Kubernetes "
            "workloads."
        ),
    },
    {
        "id": "event_pytorch_conf",
        "name": "PyTorch Conference",
        "organizer": "PyTorch Foundation",
        "location": "San Francisco, CA",
        "format": "hybrid",
        "starts_at": "2026-10-14",
        "url": "https://pytorch.org/events",
        "attendee_profile": "ML engineers and researchers",
        "description": (
            "Deep learning engineering at scale: PyTorch performance tuning, distributed "
            "training, GPU inference optimization, and MLOps pipelines for model serving."
        ),
    },
    {
        "id": "event_gotham_go",
        "name": "GothamGo",
        "organizer": "GothamGo",
        "location": "New York, NY",
        "format": "in-person",
        "starts_at": "2026-11-06",
        "url": "https://gothamgo.com",
        "attendee_profile": "Go developers, platform and infrastructure engineers",
        "description": (
            "Go language conference covering concurrency patterns, gRPC service design, "
            "building CLI and platform tooling, and running Go services on Kubernetes."
        ),
    },
    {
        "id": "event_frontend_nation",
        "name": "Frontend Nation",
        "organizer": "Frontend Nation",
        "location": "Virtual",
        "format": "virtual",
        "starts_at": "2026-09-25",
        "url": "https://frontendnation.com",
        "attendee_profile": "Frontend and full stack engineers",
        "description": (
            "TypeScript and React ecosystem talks, Next.js rendering strategies, design "
            "systems, accessibility, and frontend performance measurement."
        ),
    },
    {
        "id": "event_fintech_mixer",
        "name": "Fintech Engineering Mixer",
        "organizer": "NY Fintech Network",
        "location": "New York, NY",
        "format": "in-person",
        "starts_at": "2026-09-30",
        "url": "https://www.meetup.com",
        "attendee_profile": "Engineers and hiring managers at payments and risk companies",
        "description": (
            "Informal evening mixer for payments, ledger, and risk engineering. Attendees "
            "come from teams building high availability transaction systems with Kafka, "
            "PostgreSQL, and strict security and authorization requirements."
        ),
    },
    {
        "id": "event_system_design_jam",
        "name": "Distributed Systems Design Jam",
        "organizer": "Papers We Love",
        "location": "Virtual",
        "format": "virtual",
        "starts_at": "2026-09-08",
        "url": "https://paperswelove.org",
        "attendee_profile": "Senior engineers preparing for staff-level scope",
        "description": (
            "Group whiteboarding on system design problems: consistency models, "
            "scalability tradeoffs, high availability patterns, and microservices "
            "boundaries. Useful preparation for senior and staff interview loops."
        ),
    },
]

# Ranked resource packs keyed by canonical skill. Every entry is a real,
# high-signal destination; the growth advisor picks from here rather than
# inventing links.
RESOURCE_LIBRARY: dict[str, list[dict[str, str]]] = {
    "Kubernetes": [
        {
            "title": "Kubernetes Fundamentals (LFS258)",
            "kind": "course",
            "provider": "Linux Foundation",
            "url": "https://training.linuxfoundation.org/training/kubernetes-fundamentals/",
        },
        {
            "title": "Certified Kubernetes Administrator (CKA)",
            "kind": "certification",
            "provider": "CNCF",
            "url": "https://www.cncf.io/training/certification/cka/",
        },
        {
            "title": "Kubernetes Course — Full Beginners Tutorial",
            "kind": "video",
            "provider": "YouTube / TechWorld with Nana",
            "url": "https://www.youtube.com/watch?v=X48VuDVv0do",
        },
        {
            "title": "Kubernetes Concepts documentation",
            "kind": "docs",
            "provider": "kubernetes.io",
            "url": "https://kubernetes.io/docs/concepts/",
        },
    ],
    "Terraform": [
        {
            "title": "HashiCorp Certified: Terraform Associate",
            "kind": "certification",
            "provider": "HashiCorp",
            "url": "https://developer.hashicorp.com/certifications/infrastructure-automation",
        },
        {
            "title": "Terraform Tutorials",
            "kind": "docs",
            "provider": "HashiCorp Developer",
            "url": "https://developer.hashicorp.com/terraform/tutorials",
        },
        {
            "title": "Terraform Course — Automate your AWS cloud infrastructure",
            "kind": "video",
            "provider": "YouTube / freeCodeCamp",
            "url": "https://www.youtube.com/watch?v=SLB_c_ayRMo",
        },
    ],
    "AWS": [
        {
            "title": "AWS Certified Solutions Architect — Associate",
            "kind": "certification",
            "provider": "AWS",
            "url": "https://aws.amazon.com/certification/certified-solutions-architect-associate/",
        },
        {
            "title": "AWS Cloud Practitioner Essentials",
            "kind": "course",
            "provider": "AWS Skill Builder",
            "url": "https://explore.skillbuilder.aws/learn",
        },
        {
            "title": "AWS Well-Architected Framework",
            "kind": "docs",
            "provider": "AWS",
            "url": "https://aws.amazon.com/architecture/well-architected/",
        },
    ],
    "Kafka": [
        {
            "title": "Apache Kafka for Developers",
            "kind": "course",
            "provider": "Confluent Developer",
            "url": "https://developer.confluent.io/courses/",
        },
        {
            "title": "Kafka Tutorial for Beginners",
            "kind": "video",
            "provider": "YouTube / TechWorld with Nana",
            "url": "https://www.youtube.com/watch?v=QkdkLdMBuL0",
        },
        {
            "title": "Designing Event-Driven Systems",
            "kind": "reading",
            "provider": "Confluent (free book)",
            "url": "https://www.confluent.io/designing-event-driven-systems/",
        },
    ],
    "System Design": [
        {
            "title": "System Design Primer",
            "kind": "reading",
            "provider": "GitHub (donnemartin)",
            "url": "https://github.com/donnemartin/system-design-primer",
        },
        {
            "title": "Designing Data-Intensive Applications",
            "kind": "reading",
            "provider": "Martin Kleppmann",
            "url": "https://dataintensive.net/",
        },
        {
            "title": "System Design Interview walkthroughs",
            "kind": "video",
            "provider": "YouTube / ByteByteGo",
            "url": "https://www.youtube.com/@ByteByteGo",
        },
    ],
    "Observability": [
        {
            "title": "Prometheus Fundamentals",
            "kind": "course",
            "provider": "Grafana Labs",
            "url": "https://grafana.com/tutorials/",
        },
        {
            "title": "OpenTelemetry documentation",
            "kind": "docs",
            "provider": "CNCF",
            "url": "https://opentelemetry.io/docs/",
        },
        {
            "title": "Observability Engineering",
            "kind": "reading",
            "provider": "O'Reilly / Honeycomb",
            "url": "https://www.honeycomb.io/observability-engineering-oreilly-book-2022",
        },
    ],
    "CI/CD": [
        {
            "title": "GitHub Actions documentation",
            "kind": "docs",
            "provider": "GitHub",
            "url": "https://docs.github.com/en/actions",
        },
        {
            "title": "Continuous Delivery",
            "kind": "reading",
            "provider": "Jez Humble & David Farley",
            "url": "https://continuousdelivery.com/",
        },
    ],
    "Docker": [
        {
            "title": "Docker Get Started guide",
            "kind": "docs",
            "provider": "Docker",
            "url": "https://docs.docker.com/get-started/",
        },
        {
            "title": "Docker Tutorial for Beginners",
            "kind": "video",
            "provider": "YouTube / TechWorld with Nana",
            "url": "https://www.youtube.com/watch?v=3c-iBn73dDE",
        },
    ],
    "LLMs": [
        {
            "title": "ChatGPT Prompt Engineering for Developers",
            "kind": "course",
            "provider": "DeepLearning.AI",
            "url": "https://www.deeplearning.ai/short-courses/",
        },
        {
            "title": "Let's build GPT: from scratch, in code",
            "kind": "video",
            "provider": "YouTube / Andrej Karpathy",
            "url": "https://www.youtube.com/watch?v=kCc8FmEb1nY",
        },
        {
            "title": "OpenAI API documentation",
            "kind": "docs",
            "provider": "OpenAI",
            "url": "https://platform.openai.com/docs/",
        },
    ],
    "RAG": [
        {
            "title": "Building and Evaluating Advanced RAG Applications",
            "kind": "course",
            "provider": "DeepLearning.AI",
            "url": "https://www.deeplearning.ai/short-courses/",
        },
        {
            "title": "RAG from scratch",
            "kind": "video",
            "provider": "YouTube / LangChain",
            "url": "https://www.youtube.com/watch?v=wd7TZ4w1mSw",
        },
        {
            "title": "Retrieval augmented generation concepts",
            "kind": "docs",
            "provider": "LangChain",
            "url": "https://python.langchain.com/docs/concepts/rag/",
        },
    ],
    "Vector Databases": [
        {
            "title": "Vector Databases: from Embeddings to Applications",
            "kind": "course",
            "provider": "DeepLearning.AI",
            "url": "https://www.deeplearning.ai/short-courses/",
        },
        {
            "title": "pgvector",
            "kind": "docs",
            "provider": "GitHub (pgvector)",
            "url": "https://github.com/pgvector/pgvector",
        },
    ],
    "LangChain": [
        {
            "title": "LangChain for LLM Application Development",
            "kind": "course",
            "provider": "DeepLearning.AI",
            "url": "https://www.deeplearning.ai/short-courses/",
        },
        {
            "title": "LangGraph documentation",
            "kind": "docs",
            "provider": "LangChain",
            "url": "https://langchain-ai.github.io/langgraph/",
        },
    ],
    "MLOps": [
        {
            "title": "Machine Learning Engineering for Production (MLOps)",
            "kind": "course",
            "provider": "DeepLearning.AI / Coursera",
            "url": "https://www.coursera.org/specializations/machine-learning-engineering-for-production-mlops",
        },
        {
            "title": "Made With ML — MLOps course",
            "kind": "course",
            "provider": "Made With ML",
            "url": "https://madewithml.com/",
        },
    ],
    "PyTorch": [
        {
            "title": "Deep Learning with PyTorch: Zero to GANs",
            "kind": "course",
            "provider": "PyTorch / Jovian",
            "url": "https://pytorch.org/tutorials/",
        },
        {
            "title": "PyTorch for Deep Learning — full course",
            "kind": "video",
            "provider": "YouTube / freeCodeCamp",
            "url": "https://www.youtube.com/watch?v=V_xro1bcAuA",
        },
    ],
    "Spark": [
        {
            "title": "Databricks Certified Associate Developer for Apache Spark",
            "kind": "certification",
            "provider": "Databricks",
            "url": "https://www.databricks.com/learn/certification/apache-spark-developer-associate",
        },
        {
            "title": "Spark SQL and DataFrames guide",
            "kind": "docs",
            "provider": "Apache Spark",
            "url": "https://spark.apache.org/docs/latest/sql-programming-guide.html",
        },
    ],
    "Airflow": [
        {
            "title": "Astronomer Certification: Apache Airflow Fundamentals",
            "kind": "certification",
            "provider": "Astronomer",
            "url": "https://academy.astronomer.io/",
        },
        {
            "title": "Airflow core concepts",
            "kind": "docs",
            "provider": "Apache Airflow",
            "url": "https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/index.html",
        },
    ],
    "dbt": [
        {
            "title": "dbt Fundamentals",
            "kind": "course",
            "provider": "dbt Labs",
            "url": "https://learn.getdbt.com/",
        },
        {
            "title": "dbt Analytics Engineering Certification",
            "kind": "certification",
            "provider": "dbt Labs",
            "url": "https://www.getdbt.com/certifications",
        },
    ],
    "Snowflake": [
        {
            "title": "SnowPro Core Certification",
            "kind": "certification",
            "provider": "Snowflake",
            "url": "https://www.snowflake.com/certifications/",
        },
    ],
    "Go": [
        {
            "title": "A Tour of Go",
            "kind": "docs",
            "provider": "Go team",
            "url": "https://go.dev/tour/",
        },
        {
            "title": "Learn Go Programming — full course",
            "kind": "video",
            "provider": "YouTube / freeCodeCamp",
            "url": "https://www.youtube.com/watch?v=un6ZyFkqFKo",
        },
    ],
    "Rust": [
        {
            "title": "The Rust Programming Language (the book)",
            "kind": "reading",
            "provider": "Rust team",
            "url": "https://doc.rust-lang.org/book/",
        },
        {
            "title": "Rustlings exercises",
            "kind": "course",
            "provider": "Rust team",
            "url": "https://github.com/rust-lang/rustlings",
        },
    ],
    "GraphQL": [
        {
            "title": "How to GraphQL",
            "kind": "course",
            "provider": "Prisma",
            "url": "https://www.howtographql.com/",
        },
        {
            "title": "GraphQL documentation",
            "kind": "docs",
            "provider": "GraphQL Foundation",
            "url": "https://graphql.org/learn/",
        },
    ],
    "gRPC": [
        {
            "title": "gRPC core concepts and tutorials",
            "kind": "docs",
            "provider": "gRPC",
            "url": "https://grpc.io/docs/what-is-grpc/introduction/",
        },
    ],
    "PostgreSQL": [
        {
            "title": "PostgreSQL performance and internals",
            "kind": "docs",
            "provider": "PostgreSQL",
            "url": "https://www.postgresql.org/docs/current/performance-tips.html",
        },
        {
            "title": "Use The Index, Luke — SQL indexing",
            "kind": "reading",
            "provider": "Markus Winand",
            "url": "https://use-the-index-luke.com/",
        },
    ],
    "Redis": [
        {
            "title": "Redis University",
            "kind": "course",
            "provider": "Redis",
            "url": "https://university.redis.io/",
        },
    ],
    "TypeScript": [
        {
            "title": "Total TypeScript — free tutorials",
            "kind": "course",
            "provider": "Matt Pocock",
            "url": "https://www.totaltypescript.com/tutorials",
        },
        {
            "title": "TypeScript Handbook",
            "kind": "docs",
            "provider": "Microsoft",
            "url": "https://www.typescriptlang.org/docs/handbook/intro.html",
        },
    ],
    "React": [
        {
            "title": "React Learn",
            "kind": "docs",
            "provider": "Meta",
            "url": "https://react.dev/learn",
        },
    ],
    "Next.js": [
        {
            "title": "Next.js App Router course",
            "kind": "course",
            "provider": "Vercel",
            "url": "https://nextjs.org/learn",
        },
    ],
    "Testing": [
        {
            "title": "pytest documentation",
            "kind": "docs",
            "provider": "pytest",
            "url": "https://docs.pytest.org/en/stable/",
        },
        {
            "title": "Testing JavaScript",
            "kind": "course",
            "provider": "Kent C. Dodds",
            "url": "https://testingjavascript.com/",
        },
    ],
    "Security": [
        {
            "title": "OWASP Top 10",
            "kind": "docs",
            "provider": "OWASP",
            "url": "https://owasp.org/www-project-top-ten/",
        },
        {
            "title": "OAuth 2.0 Simplified",
            "kind": "reading",
            "provider": "Aaron Parecki",
            "url": "https://www.oauth.com/",
        },
    ],
    "Machine Learning": [
        {
            "title": "Machine Learning Specialization",
            "kind": "course",
            "provider": "DeepLearning.AI / Coursera",
            "url": "https://www.coursera.org/specializations/machine-learning-introduction",
        },
    ],
    "Deep Learning": [
        {
            "title": "Deep Learning Specialization",
            "kind": "course",
            "provider": "DeepLearning.AI / Coursera",
            "url": "https://www.coursera.org/specializations/deep-learning",
        },
    ],
    "Microservices": [
        {
            "title": "Building Microservices",
            "kind": "reading",
            "provider": "Sam Newman",
            "url": "https://samnewman.io/books/building_microservices_2nd_edition/",
        },
    ],
    "Data Modeling": [
        {
            "title": "The Data Warehouse Toolkit",
            "kind": "reading",
            "provider": "Kimball Group",
            "url": "https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/books/",
        },
    ],
    "ETL": [
        {
            "title": "Fundamentals of Data Engineering",
            "kind": "reading",
            "provider": "O'Reilly",
            "url": "https://www.oreilly.com/library/view/fundamentals-of-data/9781098108298/",
        },
    ],
    "A/B Testing": [
        {
            "title": "Trustworthy Online Controlled Experiments",
            "kind": "reading",
            "provider": "Kohavi, Tang & Xu",
            "url": "https://experimentguide.com/",
        },
    ],
    "Leadership": [
        {
            "title": "The Staff Engineer's Path",
            "kind": "reading",
            "provider": "Tanya Reilly",
            "url": "https://www.oreilly.com/library/view/the-staff-engineers/9781098118723/",
        },
    ],
}

# Stands in for the LinkedIn OAuth payload until the real connector lands.
DEMO_LINKEDIN_PROFILE: dict[str, Any] = {
    "full_name": "Alex Rivera",
    "headline": "Backend Engineer | Python, FastAPI, PostgreSQL | Building payment systems",
    "location": "New York, NY",
    "summary": (
        "Backend engineer with 5 years building transactional services for fintech and "
        "marketplace products. I care about clean REST API design, data correctness, and "
        "systems that stay debuggable under load."
    ),
    "experience": [
        {
            "title": "Backend Engineer",
            "company": "Northwind Payments",
            "start_date": "2023",
            "end_date": "Present",
            "bullets": [
                "Designed and shipped a FastAPI settlement service processing 40k transactions per day with 99.95% uptime.",
                "Cut p95 API latency from 820ms to 190ms by adding Redis caching and rewriting three N+1 PostgreSQL query paths.",
                "Built an idempotency layer that eliminated duplicate charge incidents, reducing support escalations by 62%.",
                "Introduced pytest integration coverage across the payments module, raising coverage from 34% to 81%.",
            ],
        },
        {
            "title": "Software Engineer",
            "company": "Vantage Marketplace",
            "start_date": "2021",
            "end_date": "2023",
            "bullets": [
                "Built REST APIs in Python and Django serving 1.2M monthly active buyers.",
                "Migrated the order service into Docker containers and automated deploys with GitHub Actions, cutting release time from 45 to 8 minutes.",
                "Modeled a reporting schema in PostgreSQL that replaced nightly spreadsheet exports for the operations team.",
                "Mentored two junior engineers through their first production on-call rotations.",
            ],
        },
        {
            "title": "Software Engineering Intern",
            "company": "Beacon Analytics",
            "start_date": "2020",
            "end_date": "2021",
            "bullets": [
                "Wrote Python ETL jobs consolidating five vendor feeds into a single analytics table used by the growth team.",
                "Automated a weekly reporting pipeline with Pandas, saving roughly 6 analyst hours per week.",
            ],
        },
    ],
    "skills": [
        "Python",
        "FastAPI",
        "Django",
        "PostgreSQL",
        "Redis",
        "REST APIs",
        "Docker",
        "SQL",
        "Testing",
        "CI/CD",
        "Pandas",
        "ETL",
        "Agile",
    ],
    "education": ["B.S. Computer Science, Rutgers University (2020)"],
    "certifications": [],
}

DEMO_RESUME_TEXT = """Alex Rivera — Backend Engineer
New York, NY

SUMMARY
Backend engineer with 5 years building transactional services for fintech and marketplace
products. Focused on REST API design, data correctness, and observable systems.

EXPERIENCE
Northwind Payments — Backend Engineer (2023–Present)
- Designed and shipped a FastAPI settlement service processing 40k transactions per day.
- Cut p95 API latency from 820ms to 190ms with Redis caching and PostgreSQL query rewrites.
- Built an idempotency layer that reduced support escalations by 62%.

Vantage Marketplace — Software Engineer (2021–2023)
- Built REST APIs in Python and Django serving 1.2M monthly active buyers.
- Containerized services with Docker and automated deploys via GitHub Actions.

SKILLS
Python, FastAPI, Django, PostgreSQL, Redis, Docker, SQL, pytest, CI/CD, Pandas
"""
