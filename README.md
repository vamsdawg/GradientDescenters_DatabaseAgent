# Gradient Descenters: Multimodal Database Agent

**Course:** DSBA 6010 — AI Systems Engineering  
**Team:** Gradient Descenters (Group 1)  
**Database:** AdventureWorksDW2025 (Microsoft sample data warehouse)

## 🚀 Live Demo

**[https://gradientdescentersdatabaseagent.streamlit.app/](https://gradientdescentersdatabaseagent.streamlit.app/)**

1. Click **Initialize Agent** in the left sidebar.
2. Type a question in plain English (or click one of the example queries).
3. Click **Process Query** — the agent will return the SQL it generated, a visualization, and AI-powered business insights.

---

## What Is This?

This project is a production-grade **multimodal AI database agent** that lets users query a SQL Server data warehouse using plain English. No SQL knowledge required. The agent translates the user's natural language question into a T-SQL query, executes it, automatically generates the most appropriate visualization, and then uses GPT-4o's vision capability to analyze the chart and return actionable business insights — all in a single pipeline.

**The full pipeline looks like this:**

```
Natural Language Question
        ↓
  RAG Context Retrieval  (relevant schemas, patterns, business rules)
        ↓
  SQL Generation         (GPT-4o-mini, RAG-enhanced prompt)
        ↓
  SQL Validation         (syntax check + privacy enforcement)
        ↓
  Query Execution        (SQL Server / AdventureWorksDW2025)
        ↓
  Auto Visualization     (chart type auto-selected based on data shape)
        ↓
  Vision Analysis        (GPT-4o reads the chart image)
        ↓
  Business Insights      (returned to the user)
```

The system ships with two execution modes:
- **Pipeline mode** — a clean sequential 4-step orchestrator (default)
- **Agent mode** — an explicit planner-executor architecture with memory, validation retries, and step-by-step tracing

---

## Quick Start

### Prerequisites

- Python 3.9+
- SQL Server with the **AdventureWorksDW2025** database restored (`.bacpac` file included)
- ODBC Driver 17 for SQL Server
- OpenAI API key (GPT-4o and GPT-4o-mini)
- Anthropic API key (optional; used in LLM comparison evaluations)

### 1. Install dependencies

```bash
cd final_project
pip install -r requirements.txt
```

### 2. Configure environment

Create a `.env` file in the `final_project/` directory:

```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...      # optional
DB_SERVER=localhost
DB_NAME=AdventureWorksDW2025
DB_DRIVER=ODBC Driver 17 for SQL Server
DB_USER=                          # leave blank for Windows Auth
DB_PASSWORD=                      # leave blank for Windows Auth
```

### 3. Run the web app

```bash
streamlit run streamlit_app.py
```

Open your browser to `http://localhost:8501`. Click **Initialize Agent** in the sidebar and start asking questions.

---

## Using the Web Interface

The Streamlit app (`streamlit_app.py`) is the primary interface. The sidebar controls the agent configuration:

| Control | Description |
|---|---|
| **Enable RAG Context** | Injects relevant schema info, join patterns, and business rules into the SQL prompt |
| **Enable Vision Analysis** | Sends the generated chart to GPT-4o for business insights |
| **Use Planner-Executor Agent** | Switches from pipeline mode to explicit step-by-step agent mode |
| **Planner Mode** | When in agent mode: `tool_calling` (LLM-planned) or `deterministic` (fixed order) |
| **Vision Model** | `gpt-4o` (higher quality) or `gpt-4o-mini` (lower cost) |

**Example queries to try:**

- *Show me our top 5 customers in the United Kingdom. Who are they?*
- *What 10 products which grew their sales the most, between Q1 and Q2 of 2013?*
- *Show monthly sales trends for 2013*
- *Top 10 products by revenue*
- *What were the highest selling products in December 2013?*

The **Advanced Options** expander lets you override the chart type, toggle SQL display, and enable the agent trace view (for agent mode).

---

## Using the Agent Programmatically

### Pipeline mode

```python
from multimodal_agent import MultimodalDatabaseAgent

agent = MultimodalDatabaseAgent(use_rag=True, enable_vision=True, vision_model="gpt-4o")
result = agent.process_query("Show monthly sales trends for 2013")

print(result["sql_query"])        # Generated T-SQL
print(result["row_count"])        # Number of rows returned
print(result["visualization"])    # Path to the generated chart PNG
print(result["vision_analysis"])  # GPT-4o business insights text
```

### Agent (planner-executor) mode

```python
from agent_orchestrator import AgentOrchestrator

agent = AgentOrchestrator(
    use_rag=True,
    enable_visualization=True,
    enable_vision=True,
    planner_mode="tool_calling"   # or "deterministic"
)
result = agent.process_query("Top 10 products by revenue")

for step in result["plan"]:
    print(f"{step['name']}: {step['status']}")

agent.shutdown()
```

---

## Project Structure

```
final_project/
│
├── streamlit_app.py             # Entry point — Streamlit web UI
├── requirements.txt             # Python dependencies
├── .env                         # API keys + DB config (not in repo)
├── adventureworksdw2025.bacpac  # Database backup for restore
│
├── _prod/                       # Production modules (imported by the app)
│   ├── multimodal_agent.py      # 4-stage pipeline orchestrator
│   ├── agent_orchestrator.py    # Planner-executor agent with memory
│   ├── database_utils.py        # SQL Server connection and query utilities
│   ├── rag_manager.py           # ChromaDB vector store (64 docs, 4 collections)
│   ├── rag_evaluator.py         # RAG-enhanced SQL generation via GPT-4o-mini
│   ├── visualization_generator.py  # Auto chart-type selection and rendering
│   └── vision_analyzer.py       # GPT-4o vision analysis of generated charts
│
├── milestone_scripts/           # Evaluation and utility scripts (not used by app)
│   ├── multimodal_evaluator.py  # Cross-modal consistency testing framework
│   ├── llm_evaluator.py         # Multi-LLM evaluation framework
│   ├── rag_evaluation.py        # RAG retrieval quality evaluation
│   ├── test_cases.py            # 26 labeled test cases (Easy → Very Hard)
│   ├── run_experiments.py       # Full evaluation pipeline runner
│   ├── planner_ab_evaluation.py # A/B test: deterministic vs tool-calling planner
│   └── generate_schema_docs.py  # Generates RAG schema docs from live DB
│
├── rag_content/                 # RAG knowledge base (loaded into ChromaDB)
│   ├── schemas/                 # 14 table schema .txt files
│   ├── patterns/                # 8 reusable SQL join pattern files
│   ├── business_rules/          # Business rules + field glossary
│   └── examples/                # NL→SQL example pairs (JSON)
│
├── notebooks/                   # Jupyter notebooks (milestone demos)
│   ├── 03_llm_experimentation.ipynb
│   ├── 04_prompt_testing.ipynb
│   ├── 05_fewshot_optimizations.ipynb
│   ├── 06_rag_pipeline_demonstration.ipynb
│   ├── 07_multimodal_capabilities_demo.ipynb
│   └── milestone_12_security_audit.ipynb
│
├── milestone submissions/       # All milestone Word/PDF deliverables
├── results/                     # Generated: experiment results, agent memory
├── visualizations/              # Generated: timestamped chart PNGs
└── chroma_db/                   # Generated: persisted ChromaDB vector database
```

---

## Component Reference

### `database_utils.py` — Database Layer
Handles all SQL Server connectivity. Supports both Windows Authentication and SQL/Azure authentication via `.env`. Key methods: `execute_query()`, `get_schema_info()`, `validate_sql_syntax()`.

### `rag_manager.py` — Retrieval-Augmented Generation
Manages a ChromaDB vector database with four collections: table schemas, join patterns, business rules, and NL→SQL examples. At query time, the most relevant documents are retrieved (cosine similarity) and injected into the SQL generation prompt. Uses OpenAI `text-embedding-3-small` for embeddings.

### `rag_evaluator.py` — SQL Generation
The core SQL generation class. Builds a context-rich prompt from RAG retrieval and calls GPT-4o-mini (temperature=0) to produce T-SQL. Also handles output cleaning (strips markdown fences) and token tracking.

### `visualization_generator.py` — Chart Engine
Automatically selects the best chart type for the query result based on data shape and query keywords (line for time-series, bar/horizontal bar for rankings, pie for small-slice distributions, scatter for correlation data). Renders charts with Matplotlib/Seaborn and saves them as timestamped PNGs.

### `vision_analyzer.py` — Multimodal Analysis
Encodes the generated chart as base64 and sends it to GPT-4o's vision API along with a chart-type-specific prompt. Returns structured business insights: trends, patterns, outliers, and recommendations. Supports comparative analysis across multiple charts.

### `multimodal_agent.py` — Pipeline Orchestrator
Wires the four stages together (SQL generation → execution → visualization → vision analysis) into a single `process_query()` call. Returns a unified result dict with SQL, data, chart path, vision insights, and performance metrics.

### `agent_orchestrator.py` — Planner-Executor Agent
An explicit planner-executor architecture built on top of the same components. The **PlannerAgent** (deterministic) or **ToolCallingPlanner** (LLM-driven) produces an ordered list of `AgentStep` objects. The **ExecutorAgent** runs each step, enforces privacy checks, retries failed SQL generation once, and logs every execution to persistent JSON memory.

### `multimodal_evaluator.py` — Consistency Testing
Automated test framework that checks cross-modal consistency: are the values the vision model reads from the chart consistent with the actual data? Tests value extraction, ranking accuracy, and trend direction. Achieved 89% consistency in evaluation.

### `test_cases.py` — Test Suite
26 labeled test cases organized by category (Simple Select, Aggregation, Join, Date Filter, Top N, Complex, Edge Case) and difficulty (Easy through Very Hard). Used by all evaluation scripts.

---

## Privacy & Security

The agent enforces a two-layer privacy system to prevent exposure of sensitive fields:

1. **Prompt-level:** The SQL generation prompt explicitly forbids querying certain fields.
2. **Executor-level:** Before executing any SQL, the agent scans for the following forbidden fields and blocks the query if any are found:

```
EmailAddress, Phone, AddressLine1, AddressLine2,
SalesQuota, SalesQuotaDate, LoginID, NationalIDNumber
```

This was designed and tested as part of the Milestone 4 (Prompt Engineering) and Milestone 12 (Security Audit) deliverables.

---

## Performance Benchmarks

| Metric | Value |
|---|---|
| SQL generation time | ~1.2s (with RAG) |
| Visualization creation | ~0.8s |
| Vision analysis | ~0.7s |
| **Total per query** | **~2.7s** |
| SQL success rate | ~90% |
| Cross-modal consistency | 89% |
| Estimated cost per query | ~$0.013 |

---

## Key Design Decisions

**No fine-tuning.** GPT-4o-mini with RAG-enhanced prompting already achieves 90%+ SQL success rate. Fine-tuning was evaluated and ruled out in Milestone 6 — the cost and complexity were not justified given the prompt-based baseline's performance.

**ChromaDB with cosine similarity.** Cosine distance is more appropriate than L2 for comparing text embeddings because it captures semantic direction rather than absolute vector magnitude.

**Deterministic planner as fallback.** The tool-calling planner uses LLM function calling to determine its execution plan, but falls back to a fixed deterministic plan on any failure to guarantee reliability.

**Retry budget of 1.** The executor retries SQL generation exactly once on validation failure (with the error message as context), then aborts. This balances resilience against runaway API costs.

**Visualizations saved to disk.** Charts are written as PNG files rather than held in memory, so the exact image path can be passed to the GPT-4o vision API without re-encoding.

---

## Milestone Progression

This system was built incrementally across class milestones:

| Milestone | Focus | Outcome |
|---|---|---|
| 3 | LLM comparison (Claude, GPT-4.1, GPT-4o-mini) | Selected GPT-4o-mini (best cost-performance) |
| 4 | Prompt engineering + privacy controls | Advanced+Privacy template chosen for production |
| 6 | Fine-tuning decision | Ruled out; RAG+prompting hits 90% |
| 7 | Multimodal integration | Visualization + GPT-4o vision; 89% consistency |
| 10 | Planner-executor agent | Deterministic + tool-calling planners + agent memory |
| 12 | Security audit | Formal privacy testing and forbidden-field validation |
