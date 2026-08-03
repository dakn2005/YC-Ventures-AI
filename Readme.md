# Ventures AI

Chat Bot To query data from 
> Data Source: https://github.com/yc-oss/api (open sourec Y Combinator companies API) gleaned from [Y-Combinator Startup directory](https://www.ycombinator.com/companies)

## Technologies
- Container - docker
- System Arch - Python, FastAPI
- Orchestration - Kestra, dlt, (use dbt to work an online data warehouse)
- DB - Postgres, pgvector
- Monitoring - Pydantic Logfire
- LLM - perf between Ollama (Mistral) and Opus (Claude)
<!-- - AI - langchain -->

## Concepts

- Chunking - Semantic chunking
- Hybrid search
- RRF
  - Relevance
  - Hit Rate
- Evaluation
  - Cosine similarity index
  - Relevance
  - LLM-as-a-Judge