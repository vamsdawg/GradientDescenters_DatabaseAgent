# Tool Calling Planner and Evaluation Summary

## Overview
This milestone adds a tool-calling planner to the existing deterministic planner-executor pipeline, then compares both approaches with a unified evaluation harness and a human A/B protocol.

Key goals:
- Improve planning flexibility using LLM tool calling
- Maintain the same execution tools for a clean A/B comparison
- Measure accuracy, relevance, coherence, and faithfulness with repeatable metrics
- Capture edge cases and failure modes

## What Changed
### 1) Tool-Calling Planner (Default)
- Added a tool-calling planner that uses the LLM to decide which tools to call.
- Allowed tools mirror the existing executor steps:
  - retrieve_context (optional)
  - generate_sql
  - validate_sql
  - execute_sql
  - visualize (optional)
  - vision_analyze (optional)
- The plan is converted into AgentStep objects and executed by the same executor.
- Tool calling is the default behavior, but deterministic planning can be run per request.

### 2) Planner Mode Switch
- The orchestrator now accepts planner_mode:
  - tool_calling (default)
  - deterministic
- The same query can be run through both modes for direct comparison.

### 3) Combined A/B Evaluation Runner
- A new A/B script runs both planners against the same test suite.
- Produces a single JSON report plus optional blind A/B files for human review.

## How to Run
1) Run the combined A/B evaluation:

```bash
python planner_ab_evaluation.py
```

Outputs:
- results/planner_ab_report_YYYYMMDD_HHMMSS.json
- results/planner_ab_blind_YYYYMMDD_HHMMSS.csv
- results/planner_ab_key_YYYYMMDD_HHMMSS.csv

The blind CSV is used for human evaluation. The key file maps A/B back to the planner mode.

## Evaluation Metrics (Mapped to Requirements)
### Accuracy
- SQL execution success rate
- Valid execution completion of generate -> validate -> execute steps
- Row count sanity checks from query results

### Relevance
- Table coverage: how many expected tables appear in the SQL
- Derived by parsing FROM/JOIN tables and matching against expected tables

### Coherence
- Plan completeness and valid tool ordering
- Ensures the pipeline follows a consistent, logical sequence

### Faithfulness
- Privacy compliance: no forbidden fields
- Schema faithfulness: no unknown tables referenced in SQL

### Efficiency (Supporting)
- Total latency and SQL generation latency
- Token usage from the SQL generation step

## Human Evaluation / A-B Testing
A blind A/B CSV is produced for reviewers:
- Each row contains the query, Output A SQL, and Output B SQL
- Reviewers score each output on:
  - Correctness
  - Relevance
  - Clarity
  - Trustworthiness
- The key file maps A/B back to deterministic or tool_calling

Suggested rubric:
- 1: Poor
- 2: Fair
- 3: Acceptable
- 4: Good
- 5: Excellent

## Evaluation Tools
- Custom test suite (required): planner_ab_evaluation.py
- Existing RAG evaluation: rag_evaluation.py (retrieval precision/recall and baseline vs RAG)
- Optional add-ons:
  - RAGAS for faithfulness and answer relevance
  - TruLens for trace-level feedback and custom scoring

## Edge Cases and Failure Modes
Tracked in the report per test case:
- SQL syntax errors
- Privacy violations (forbidden fields)
- Unknown table references
- Missing plan steps or invalid tool order

These are logged in the combined report and can be summarized in the write-up.

## Summary of Comparison Approach
- Same tools and executor for both planners
- Only the planner decision logic differs
- Automated metrics + human A/B review
- Single combined report for submission

## Results (Run 2026-03-31 15:17:59)
Source files:
- results/planner_ab_report_20260331_151759.json
- results/planner_ab_blind_20260331_151759.csv
- results/planner_ab_key_20260331_151759.csv

High-level summary (26 cases, including edge cases):
- Success rate: 100% for both planners
- Plan completeness: 100% for both planners
- Table coverage: 100% for both planners
- Privacy violations: 0% for both planners
- Unknown tables: 0% for both planners
- Average latency: deterministic 12.001s, tool_calling 12.894s (+0.893s)
- SQL generation latency: deterministic 3.011s, tool_calling 2.584s (-0.427s)
- Token usage: deterministic 1785.2, tool_calling 1785.7 (roughly equal)

Human A/B review notes:
- Most A/B pairs produced identical SQL outputs.
- The blind CSV is still useful for independent scoring, but reviewers will likely score many cases as ties.

## Edge Case Observations
- Test 20 (privacy request for emails/phones): both planners omitted sensitive fields and returned allowed columns only.
- Test 22 ("last 4 quarters"): outputs diverged. Deterministic produced a single-year, four-quarter filter, while tool_calling included two years of quarters. The deterministic output is closer to the intended window.
- Test 24 ("products with no sales"): both planners used left joins and null filtering; deterministic included an extra product identifier column. Both are acceptable for the intent.

## Decision Guidance
Given identical correctness and faithfulness metrics, the deterministic planner is faster in this run. Tool calling remains the default for flexibility and future generalization, but in the current test suite it does not yet yield accuracy gains.
