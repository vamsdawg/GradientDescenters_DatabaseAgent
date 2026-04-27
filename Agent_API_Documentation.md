# Agent API Documentation

This document describes the two agent classes that power the application and the result structure they return.

---

## `MultimodalDatabaseAgent`
*`_prod/multimodal_agent.py`*

The default execution mode. Runs a fixed four-step sequential pipeline: SQL generation → execution → visualization → vision analysis.

### Constructor

```python
MultimodalDatabaseAgent(
    use_rag: bool = True,
    enable_vision: bool = True,
    vision_model: str = "gpt-4o"
)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `use_rag` | bool | `True` | Inject RAG context (schemas, patterns, business rules) into the SQL prompt |
| `enable_vision` | bool | `True` | Analyze the generated chart with a vision model |
| `vision_model` | str | `"gpt-4o"` | Vision model to use — `"gpt-4o"` or `"gpt-4o-mini"` |

### `process_query()`

```python
agent.process_query(
    natural_language_query: str,
    enable_visualization: bool = True,
    enable_vision_analysis: bool = True,
    chart_type: str | None = None
) -> dict
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `natural_language_query` | str | — | The user's question in plain English |
| `enable_visualization` | bool | `True` | Generate a chart from the query results |
| `enable_vision_analysis` | bool | `True` | Send the chart to the vision model for insights |
| `chart_type` | str \| None | `None` | Force a specific chart type (`"line"`, `"bar"`, `"horizontal_bar"`, `"pie"`). `None` = auto-detect |

---

## `AgentOrchestrator`
*`_prod/agent_orchestrator.py`*

The planner-executor mode. An LLM (or deterministic logic) first produces an explicit step-by-step plan, then an executor runs each step with validation and retry logic.

### Constructor

```python
AgentOrchestrator(
    use_rag: bool = True,
    enable_visualization: bool = True,
    enable_vision: bool = True,
    vision_model: str = "gpt-4o",
    planner_mode: str = "tool_calling"
)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `use_rag` | bool | `True` | Enable RAG context retrieval |
| `enable_visualization` | bool | `True` | Include a visualization step in the plan |
| `enable_vision` | bool | `True` | Include a vision analysis step in the plan |
| `vision_model` | str | `"gpt-4o"` | Vision model — `"gpt-4o"` or `"gpt-4o-mini"` |
| `planner_mode` | str | `"tool_calling"` | `"tool_calling"` = LLM decides step order; `"deterministic"` = fixed order |

### `process_query()`

```python
agent.process_query(
    query: str,
    planner_mode: str | None = None
) -> dict
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `query` | str | — | The user's question in plain English |
| `planner_mode` | str \| None | `None` | Override the planner mode for this call only |

### `shutdown()`

```python
agent.shutdown()
```

Closes the database connection. Call this when the agent is no longer needed.

---

## Result Dictionary

Both agents return the same result shape, which the Streamlit UI reads directly.

```python
{
    # Query info
    "query":              str,        # Original natural language question
    "timestamp":          str,        # ISO 8601 timestamp

    # SQL generation
    "sql_query":          str,        # Generated T-SQL
    "sql_generation_time": float,     # Seconds taken to generate SQL
    "tokens_used":        dict,       # {"input_tokens": int, "output_tokens": int, "total_tokens": int}

    # Execution
    "execution_success":  bool,
    "data":               DataFrame,  # Full query result
    "row_count":          int,
    "column_count":       int,
    "columns":            list[str],
    "data_preview":       list[dict], # First 10 rows as records

    # Visualization
    "visualization":      str | None, # Absolute path to the PNG chart file
    "chart_type":         str | None, # e.g. "bar", "line", "pie"
    "data_summary":       dict,       # min/max/mean/total per numeric column

    # Vision analysis
    "vision_analysis":    str | None, # Business insights text from GPT-4o
    "vision_tokens":      dict,       # {"prompt": int, "completion": int, "total": int}

    # Status
    "success":            bool,
    "errors":             list[str],  # Empty list on success
    "total_time":         float,      # End-to-end seconds

    # Agent mode only
    "plan":               list[dict], # Each step: {step_id, name, tool, status, error}
    "planner_mode":       str
}
```

---

## Chart Types

The visualization engine auto-selects a chart type based on the data and query. You can also force one via the `chart_type` parameter.

| Value | When used |
|---|---|
| `"line"` | Time-series data or queries containing "trend" / "over time" |
| `"bar"` | Rankings, comparisons, or category breakdowns (≤ 10 rows) |
| `"horizontal_bar"` | Same as bar but for larger result sets (> 10 rows) |
| `"pie"` | Small distributions (≤ 8 distinct values) |
| `"scatter"` | Two or more numeric columns with ≤ 100 rows |
| `"table"` | Fallback when no chart type is appropriate |
