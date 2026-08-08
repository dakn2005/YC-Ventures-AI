# Ventures AI
Ask about YC ventures

> Data Source: https://github.com/yc-oss/api (open sourec Y Combinator companies API) gleaned from [Y-Combinator Startup directory](https://www.ycombinator.com/companies)

### Problem Statement
Let's find out about Companies in the Y-Combinator startup directory

<!-- - AI - langchain -->

### Concepts
The project showcases the following concepts from [LLM  Zoomcamp](https://github.com/DataTalksClub/llm-zoomcamp) 

- Chunking - Semantic chunking
- Hybrid search
- RRF
  - Relevance
  - Hit Rate
- Evaluation
  - Cosine similarity index
  - Relevance
  - LLM-as-a-Judge

### Reproducibility

#### Containerization
Using <b>Docker</b>, The app comprises of several smaller apps, each scaffolded by docker into a single system. 

Run the docker compose file with the command below

<code>
  docker compose -p llm-capstone up -d
</code>

This starts up the app and exposes port 8000 for querying with the chatbot on the YC - Startups data 

#### Technologies
- Container :- Docker
- Backend :-Python, FastAPI
- Frontend :- React
- Chat - Chainlit
- Orchestration :- Kestra, dlt, (use dbt to work an online data warehouse)
- DB :- Postgres, pgvector
- Monitoring :- Pydantic Logfire
- Closed source and Open source LLM :- perf between Ollama (Mistral) and Opus (Claude)

### Retrieval Flow


```mermaid
flowchart TD
    A["YC-OSS API<br/>meta.json + tag APIs"] -->|dlt / requests| B[("Postgres<br/>ventures_db.yc_oss")]
    B -->|read rows| C["• Vectorization<br/>• Chunking<br/>• Sentence-transformers embeddings"]
    C -->|store vectors| D[("Vector Store<br/>pgvector")]

    subgraph RAG["RAG Retrieval"]
        direction LR
        Q["User Query"] --> QE["Embed Query<br/>sentence-transformers"]
        QE --> SIM["Similarity Search<br/>cosine / L2 on pgvector"]
        SIM --> TOPK["Top-K Retrieved<br/>company records"]
        TOPK --> CTX["Assemble Context<br/>rank + dedupe + truncate"]
    end

    D -.->|indexed vectors| SIM
    CTX -->|context| F["LLM Answer Generation"]

    classDef api fill:#0969da,color:#ffffff,stroke:#0969da,stroke-width:1px;
    classDef db fill:#9a6700,color:#ffffff,stroke:#9a6700,stroke-width:1px;
    classDef vec fill:#8250df,color:#ffffff,stroke:#8250df,stroke-width:1px;
    classDef rag fill:#1a7f37,color:#ffffff,stroke:#1a7f37,stroke-width:1px;
    classDef gen fill:#cf222e,color:#ffffff,stroke:#cf222e,stroke-width:1px;

    class A api;
    class B,D db;
    class C vec;
    class Q,QE,SIM,TOPK,CTX rag;
    class F gen;

```

### Ingestion Pipeline
Tools: Kestra, DLT, Postgres

```mermaid
flowchart LR
    A["flow: yc_oss_companies_by_tag\n(gets records)"] --> B["flow: yc_oss_to_ventures_db\n(saves to yc_oss table)"]
    B --> C["flow: yc_oss_to_fulltext\n(saves to yc_oss_fulltext table)"]
    B --> D["flow: yc_oss_to_embeddings\n(saves to yc_oss_embeddings table)"]
    C --> E["flow: yc_oss_to_sample_records\n(saves to records table)\n(creates llm_evals table)"]
    D --> E

    classDef flow fill:#0969da,color:#ffffff,stroke:#0969da,stroke-width:1px;
    class A,B,C,D,E flow;
```
`yc_oss_to_sample_records` only fires once **both** `yc_oss_to_fulltext` and `yc_oss_to_embeddings` have succ
eeded (a multi-flow `preconditions` trigger), since it joins their outputs.

For retrieval, Kestra is used as the Orchestration tool, with flows for retrieval from the yc-oss endpoint into postgres. 

Kestra runs the flows below

| flow | topology |
|------|----------|
| [yc_oss_companies_by_tag](./app/kestra/flows/yc_oss_companies_by_tag.yaml) | <img src="./flow-graph-api-retrieve.png" alt="api retrieval" width="300" height="350" /> |
| [yc_oss_to_ventures_db](./app/kestra/flows/yc_oss_to_ventures_db.yaml) | <img src="./flow-graph-output_to_db.png" alt="retrieval output to db" width="300" height="350" /> |
| [yc_oss_to_fulltext](./app/kestra/flows/yc_oss_to_fulltext.yaml) | <img src="./flow-graph-yc_oss_to_fulltext.png" alt="retrieval output to db" width="300" height="350" /> |
| [yc_oss_to_embedding](./app/kestra/flows/yc_oss_to_embeddings.yaml) | <img src="./flow-graph-yc_oss_to_embeddings.png" alt="retrieval output to db" width="300" height="350" /> |
| [yc_oss_to_sample_records](./app/kestra/flows/yc_oss_to_sample_records.yaml) | <img src="./flow-graph-yc_oss_to_sample_records.png" alt="retrieval output to db" width="250" height="350" /> |

<!-- ![retrieval output to db](./flow-graph-api-retrieve.png) -->
<!-- ![retrieval output to db](./flow-graph-output_to_db.png) -->

> Note - that for the db flow, we can use [DBT](https://www.getdbt.com/) tool for scaffolding database schema - especially useful if having none trivial schemas 


### LLM evaluation
Using RAGAs to evaluate results, looking majorly into Faithfulness and Answer relevance

### Interface
Chatting interface exposed via **chainlit**

**Dashboard** - to access the dasboard, type /dashboard in the chainlit app chat interface

### Monitoring
Using Pydantic logfire, with the pydantic Agent wrapped call to pgvector rag.
Using Grafana to graph from the llm_evaluations table

### Conclusion

### Acknowledgment
This project was made possible thanks to:

DataTalks.Club for the excellent LLM course facilitated Alexey Grigorev and the course instructors
LLM community for support, discussions, and shared learning experiences

### AoB
Now that you're here, check out other projects on my profile, and give a follow. :-) [profile](https://github.com/dakn2005)



