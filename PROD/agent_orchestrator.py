"""
Agent Orchestrator - Planner/Executor architecture for the database agent.
Implements explicit agent roles, tool orchestration, and stateful memory.
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional
import json
import os

from openai import OpenAI

from database_utils import DatabaseManager
from rag_manager import initialize_rag_system
from rag_evaluator import RAGEnabledEvaluator
from visualization_generator import VisualizationGenerator
from vision_analyzer import VisionAnalyzer


FORBIDDEN_FIELDS = {
    "EmailAddress",
    "Phone",
    "AddressLine1",
    "AddressLine2",
    "SalesQuota",
    "SalesQuotaDate",
    "LoginID",
    "NationalIDNumber",
}


@dataclass
class AgentStep:
    """Represents a planned step in the agent workflow."""

    step_id: int
    name: str
    tool: str
    input: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class ConversationState:
    """Captures state across a multi-step interaction."""

    query: str
    plan: List[AgentStep]
    started_at: str
    last_sql: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentMemory:
    """Lightweight memory store with optional persistence to disk."""

    def __init__(self, persist_path: Optional[str] = None):
        self.persist_path = persist_path
        self.events: List[Dict[str, Any]] = []

        if persist_path:
            self._load()

    def record(self, event: Dict[str, Any]):
        self.events.append(event)
        self._save()

    def _load(self):
        if not self.persist_path or not os.path.exists(self.persist_path):
            return
        try:
            with open(self.persist_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, list):
                self.events = data
        except Exception:
            self.events = []

    def _save(self):
        if not self.persist_path:
            return
        os.makedirs(os.path.dirname(self.persist_path), exist_ok=True)
        try:
            with open(self.persist_path, "w", encoding="utf-8") as handle:
                json.dump(self.events, handle, indent=2)
        except Exception:
            pass


class PlannerAgent:
    """Creates a step-by-step plan for the executor to follow."""

    def plan(
        self,
        query: str,
        use_rag: bool,
        enable_visualization: bool,
        enable_vision: bool,
    ) -> List[AgentStep]:
        steps: List[AgentStep] = []
        step_id = 1

        if use_rag:
            steps.append(
                AgentStep(
                    step_id=step_id,
                    name="Retrieve context",
                    tool="retrieve_context",
                    input={"query": query},
                )
            )
            step_id += 1

        steps.append(
            AgentStep(
                step_id=step_id,
                name="Generate SQL",
                tool="generate_sql",
                input={"query": query},
            )
        )
        step_id += 1

        steps.append(
            AgentStep(
                step_id=step_id,
                name="Validate SQL",
                tool="validate_sql",
                input={},
            )
        )
        step_id += 1

        steps.append(
            AgentStep(
                step_id=step_id,
                name="Execute SQL",
                tool="execute_sql",
                input={},
            )
        )
        step_id += 1

        if enable_visualization:
            steps.append(
                AgentStep(
                    step_id=step_id,
                    name="Generate visualization",
                    tool="visualize",
                    input={},
                )
            )
            step_id += 1

        if enable_visualization and enable_vision:
            steps.append(
                AgentStep(
                    step_id=step_id,
                    name="Analyze visualization",
                    tool="vision_analyze",
                    input={},
                )
            )

        return steps


class ToolCallingPlanner:
    """Uses LLM tool calling to build an execution plan."""

    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def _build_tools(
        self,
        use_rag: bool,
        enable_visualization: bool,
        enable_vision: bool,
    ) -> List[Dict[str, Any]]:
        tools: List[Dict[str, Any]] = []

        if use_rag:
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": "retrieve_context",
                        "description": "Retrieve relevant RAG context for the query.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"},
                            },
                            "required": ["query"],
                        },
                    },
                }
            )

        tools.append(
            {
                "type": "function",
                "function": {
                    "name": "generate_sql",
                    "description": "Generate SQL for the natural language query.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                        },
                        "required": ["query"],
                    },
                },
            }
        )

        tools.append(
            {
                "type": "function",
                "function": {
                    "name": "validate_sql",
                    "description": "Validate SQL syntax and privacy compliance.",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        )

        tools.append(
            {
                "type": "function",
                "function": {
                    "name": "execute_sql",
                    "description": "Execute SQL against the database.",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        )

        if enable_visualization:
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": "visualize",
                        "description": "Create a visualization from query results.",
                        "parameters": {"type": "object", "properties": {}},
                    },
                }
            )

        if enable_visualization and enable_vision:
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": "vision_analyze",
                        "description": "Analyze the visualization using the vision model.",
                        "parameters": {"type": "object", "properties": {}},
                    },
                }
            )

        return tools

    def _tool_sequence_is_valid(self, tool_names: List[str]) -> bool:
        allowed_order = [
            "retrieve_context",
            "generate_sql",
            "validate_sql",
            "execute_sql",
            "visualize",
            "vision_analyze",
        ]
        last_index = -1
        for name in tool_names:
            if name not in allowed_order:
                return False
            index = allowed_order.index(name)
            if index < last_index:
                return False
            last_index = index
        return True

    def plan(
        self,
        query: str,
        use_rag: bool,
        enable_visualization: bool,
        enable_vision: bool,
        fallback_planner: PlannerAgent,
    ) -> List[AgentStep]:
        tools = self._build_tools(use_rag, enable_visualization, enable_vision)
        system_prompt = (
            "You are a planning agent for a database assistant. "
            "Call tools in a valid order to answer the query. "
            "Allowed order: retrieve_context (optional) -> generate_sql -> "
            "validate_sql -> execute_sql -> visualize (optional) -> vision_analyze (optional). "
            "Call each tool at most once and only use provided tools."
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query},
                ],
                tools=tools,
                tool_choice="auto",
                temperature=0,
            )
        except Exception:
            return fallback_planner.plan(
                query,
                use_rag=use_rag,
                enable_visualization=enable_visualization,
                enable_vision=enable_vision,
            )

        message = response.choices[0].message
        tool_calls = getattr(message, "tool_calls", None) or []
        if not tool_calls:
            return fallback_planner.plan(
                query,
                use_rag=use_rag,
                enable_visualization=enable_visualization,
                enable_vision=enable_vision,
            )

        tool_names = [call.function.name for call in tool_calls]
        required = {"generate_sql", "validate_sql", "execute_sql"}
        if not required.issubset(set(tool_names)):
            return fallback_planner.plan(
                query,
                use_rag=use_rag,
                enable_visualization=enable_visualization,
                enable_vision=enable_vision,
            )

        if not self._tool_sequence_is_valid(tool_names):
            return fallback_planner.plan(
                query,
                use_rag=use_rag,
                enable_visualization=enable_visualization,
                enable_vision=enable_vision,
            )

        step_id = 1
        steps: List[AgentStep] = []
        step_name_map = {
            "retrieve_context": "Retrieve context",
            "generate_sql": "Generate SQL",
            "validate_sql": "Validate SQL",
            "execute_sql": "Execute SQL",
            "visualize": "Generate visualization",
            "vision_analyze": "Analyze visualization",
        }

        for call in tool_calls:
            name = call.function.name
            if name not in step_name_map:
                continue

            try:
                args = json.loads(call.function.arguments) if call.function.arguments else {}
            except json.JSONDecodeError:
                args = {}

            if name in {"retrieve_context", "generate_sql"}:
                args.setdefault("query", query)
            else:
                args = {}

            steps.append(
                AgentStep(
                    step_id=step_id,
                    name=step_name_map[name],
                    tool=name,
                    input=args,
                )
            )
            step_id += 1

        return steps


class ExecutorAgent:
    """Executes the plan using available tools and tracks state."""

    def __init__(
        self,
        db: DatabaseManager,
        sql_generator: RAGEnabledEvaluator,
        rag_manager=None,
        viz_generator: Optional[VisualizationGenerator] = None,
        vision_analyzer: Optional[VisionAnalyzer] = None,
        retry_budget: int = 1,
    ):
        self.db = db
        self.sql_generator = sql_generator
        self.rag_manager = rag_manager
        self.viz_generator = viz_generator
        self.vision_analyzer = vision_analyzer
        self.retry_budget = retry_budget

    def run(self, state: ConversationState) -> Dict[str, Any]:
        context = None
        df = None
        visualization_path = None
        chart_type = None
        data_summary = None
        tokens_used = {}
        sql_generation_time = 0.0
        vision_tokens = None
        vision_analysis = None

        for step in state.plan:
            step.status = "in_progress"
            try:
                if step.tool == "retrieve_context":
                    if not self.rag_manager:
                        step.status = "skipped"
                        continue
                    context = self.rag_manager.retrieve_all_context(
                        step.input["query"],
                        k_examples=3,
                        k_patterns=2,
                        k_schemas=5,
                        k_business=2,
                    )
                    step.output = {"context": context}

                elif step.tool == "generate_sql":
                    result = self.sql_generator.generate_sql(step.input["query"])
                    state.last_sql = result.get("generated_sql")
                    sql_generation_time = result.get("latency_seconds", 0)
                    tokens_used = {
                        "total_tokens": result.get("total_tokens", 0),
                        "input_tokens": result.get("input_tokens", 0),
                        "output_tokens": result.get("output_tokens", 0),
                    }
                    step.output = {
                        "sql": state.last_sql,
                        "latency_seconds": sql_generation_time,
                    }

                elif step.tool == "validate_sql":
                    if not state.last_sql:
                        raise ValueError("No SQL available for validation")

                    is_valid, error = self.db.validate_sql_syntax(state.last_sql)
                    privacy_ok, privacy_violations = self._check_privacy(state.last_sql)

                    if not is_valid or not privacy_ok:
                        if error:
                            state.errors.append(error)
                        if privacy_violations:
                            state.errors.append(
                                "Privacy violations: " + ", ".join(privacy_violations)
                            )

                        if self.retry_budget > 0:
                            self.retry_budget -= 1
                            repaired_sql = self._retry_sql(state.last_sql, state.query)
                            state.last_sql = repaired_sql
                            is_valid, error = self.db.validate_sql_syntax(state.last_sql)
                            privacy_ok, privacy_violations = self._check_privacy(
                                state.last_sql
                            )

                    step.output = {
                        "is_valid": is_valid,
                        "privacy_ok": privacy_ok,
                        "privacy_violations": privacy_violations,
                    }

                    if not is_valid or not privacy_ok:
                        step.status = "failed"
                        step.error = error or "Validation failed"
                        break

                elif step.tool == "execute_sql":
                    if not state.last_sql:
                        raise ValueError("No SQL available for execution")
                    df, error = self.db.execute_query(state.last_sql)
                    if error:
                        step.status = "failed"
                        step.error = error
                        state.errors.append(error)
                        break
                    step.output = {
                        "row_count": len(df) if df is not None else 0
                    }

                elif step.tool == "visualize":
                    if df is None or self.viz_generator is None:
                        step.status = "skipped"
                        continue
                    viz_result = self.viz_generator.create_visual_summary(
                        df, state.query, state.last_sql or ""
                    )
                    visualization_path = viz_result.get("chart_path")
                    chart_type = viz_result.get("chart_type")
                    data_summary = viz_result.get("data_summary")
                    step.output = {
                        "chart_path": visualization_path,
                        "chart_type": chart_type,
                    }

                elif step.tool == "vision_analyze":
                    if not visualization_path or self.vision_analyzer is None:
                        step.status = "skipped"
                        continue
                    analysis = self.vision_analyzer.analyze_visualization(
                        image_path=visualization_path,
                        chart_type=chart_type or "unknown",
                        query_context=state.query,
                        data_summary=data_summary or {},
                    )
                    step.output = analysis
                    if analysis.get("success"):
                        vision_analysis = analysis.get("analysis")
                        vision_tokens = analysis.get("tokens")

                step.status = "completed"

            except Exception as exc:
                step.status = "failed"
                step.error = str(exc)
                state.errors.append(str(exc))
                break

        return {
            "context": context,
            "sql_query": state.last_sql,
            "sql_generation_time": sql_generation_time,
            "tokens_used": tokens_used,
            "data": df,
            "visualization": visualization_path,
            "chart_type": chart_type,
            "data_summary": data_summary,
            "vision_analysis": vision_analysis,
            "vision_tokens": vision_tokens,
        }

    def _retry_sql(self, sql: str, query: str) -> str:
        """Retry SQL generation with a correction hint."""
        hint = (
            "Please fix any syntax or privacy issues. "
            "Do not include confidential fields like email, phone, or addresses."
        )
        retry_query = f"{query}\n\nCorrection request: {hint}"
        result = self.sql_generator.generate_sql(retry_query)
        return result.get("generated_sql", sql)

    def _check_privacy(self, sql: str) -> (bool, List[str]):
        sql_upper = sql.upper()
        violations = [field for field in FORBIDDEN_FIELDS if field.upper() in sql_upper]
        return len(violations) == 0, violations


class AgentOrchestrator:
    """End-to-end agent system with explicit planning and execution."""

    def __init__(
        self,
        use_rag: bool = True,
        enable_visualization: bool = True,
        enable_vision: bool = True,
        vision_model: str = "gpt-4o",
        planner_mode: str = "tool_calling",
        tool_calling_model: str = "gpt-4o-mini",
        persist_memory: bool = True,
        memory_path: str = "results/agent_memory.json",
    ):
        self.use_rag = use_rag
        self.enable_visualization = enable_visualization
        self.enable_vision = enable_vision
        self.planner_mode = planner_mode

        self.db = DatabaseManager()
        self.db.connect()

        self.rag_manager = initialize_rag_system() if use_rag else None
        self.sql_generator = RAGEnabledEvaluator(use_rag=use_rag)
        self.viz_generator = VisualizationGenerator() if enable_visualization else None
        self.vision_analyzer = (
            VisionAnalyzer(model=vision_model) if enable_vision else None
        )

        self.deterministic_planner = PlannerAgent()
        self.tool_calling_planner = (
            ToolCallingPlanner(model=tool_calling_model)
            if planner_mode == "tool_calling"
            else None
        )
        self.executor = ExecutorAgent(
            db=self.db,
            sql_generator=self.sql_generator,
            rag_manager=self.rag_manager,
            viz_generator=self.viz_generator,
            vision_analyzer=self.vision_analyzer,
        )

        persist_path = memory_path if persist_memory else None
        self.memory = AgentMemory(persist_path=persist_path)

    def process_query(self, query: str, planner_mode: Optional[str] = None) -> Dict[str, Any]:
        start_time = datetime.now()
        mode = planner_mode or self.planner_mode
        if mode == "tool_calling" and self.tool_calling_planner:
            plan = self.tool_calling_planner.plan(
                query,
                use_rag=self.use_rag,
                enable_visualization=self.enable_visualization,
                enable_vision=self.enable_vision,
                fallback_planner=self.deterministic_planner,
            )
        else:
            plan = self.deterministic_planner.plan(
                query,
                use_rag=self.use_rag,
                enable_visualization=self.enable_visualization,
                enable_vision=self.enable_vision,
            )

        state = ConversationState(
            query=query,
            plan=plan,
            started_at=datetime.now().isoformat(),
        )

        execution = self.executor.run(state)
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()

        result = {
            "query": query,
            "timestamp": state.started_at,
            "planner_mode": mode,
            "plan": [asdict(step) for step in plan],
            "errors": state.errors,
            "sql_query": execution.get("sql_query"),
            "sql_generation_time": execution.get("sql_generation_time"),
            "tokens_used": execution.get("tokens_used"),
            "total_time": total_time,
            "data": execution.get("data"),
            "data_preview": (
                execution.get("data").head(10).to_dict(orient="records")
                if execution.get("data") is not None
                else None
            ),
            "row_count": len(execution.get("data"))
            if execution.get("data") is not None
            else 0,
            "visualization": execution.get("visualization"),
            "chart_type": execution.get("chart_type"),
            "data_summary": execution.get("data_summary"),
            "vision_analysis": execution.get("vision_analysis"),
            "vision_tokens": execution.get("vision_tokens"),
            "success": len(state.errors) == 0,
        }

        self.memory.record(
            {
                "timestamp": state.started_at,
                "query": query,
                "success": result["success"],
                "errors": state.errors,
                "planner_mode": mode,
                "plan": [step.name for step in plan],
            }
        )

        return result

    def shutdown(self):
        self.db.disconnect()


if __name__ == "__main__":
    orchestrator = AgentOrchestrator(use_rag=True, enable_visualization=True, enable_vision=True)
    output = orchestrator.process_query("Top 10 products by revenue")
    print("\nAgent run complete")
    print(f"Success: {output['success']}")
    if output.get("sql_query"):
        print("Generated SQL:")
        print(output["sql_query"])
    orchestrator.shutdown()
