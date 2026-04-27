"""
Streamlit Web Interface for Multimodal Database Agent
Interactive demo application for class presentation
"""
import streamlit as st
import pandas as pd
from PIL import Image
import sys
from pathlib import Path

# Add _prod to path so application modules are importable
sys.path.insert(0, str(Path(__file__).parent / '_prod'))

from multimodal_agent import MultimodalDatabaseAgent
from agent_orchestrator import AgentOrchestrator

# Page configuration
st.set_page_config(
    page_title="AdventureWorks Multimodal Agent",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        padding: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #ff7f0e;
        margin-top: 1rem;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        margin: 1rem 0;
    }
    .insight-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8f9fa;
        border: 2px solid #1f77b4;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'agent' not in st.session_state:
    st.session_state.agent = None
if 'query_history' not in st.session_state:
    st.session_state.query_history = []
if 'agent_mode' not in st.session_state:
    st.session_state.agent_mode = 'pipeline'
if 'planner_mode' not in st.session_state:
    st.session_state.planner_mode = 'tool_calling'
if 'planner_visualization' not in st.session_state:
    st.session_state.planner_visualization = True

# Header
st.markdown('<h1 class="main-header">🤖 AdventureWorks Multimodal Database Agent</h1>', unsafe_allow_html=True)
st.markdown("### Natural Language → SQL → Visualization → AI Insights")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    use_rag = st.checkbox("Enable RAG Context", value=True, help="Use RAG retrieval for enhanced SQL generation")
    enable_vision = st.checkbox("Enable Vision Analysis", value=True, help="Analyze charts with GPT-4o vision")
    use_planner = st.checkbox(
        "Use Planner-Executor Agent",
        value=False,
        help="Enable explicit planning, validation, and tool orchestration",
    )

    if use_planner:
        planner_mode = st.selectbox(
            "Planner Mode",
            options=["tool_calling", "deterministic"],
            index=0,
            help="Tool calling is the default planner behavior",
        )
        planner_visualization = st.checkbox(
            "Enable Planner Visualizations",
            value=True,
            help="Controls whether the planner includes visualization steps",
        )
        st.session_state.planner_mode = planner_mode
        st.session_state.planner_visualization = planner_visualization
    
    vision_model = st.selectbox(
        "Vision Model",
        options=["gpt-4o", "gpt-4o-mini"],
        index=0,
        help="Select vision model for chart analysis"
    )
    
    st.markdown("---")
    
    if st.button("🚀 Initialize Agent"):
        with st.spinner("Initializing agent..."):
            try:
                if use_planner:
                    st.session_state.agent = AgentOrchestrator(
                        use_rag=use_rag,
                        enable_visualization=st.session_state.planner_visualization,
                        enable_vision=enable_vision,
                        vision_model=vision_model,
                        planner_mode=st.session_state.planner_mode,
                    )
                    st.session_state.agent_mode = 'planner'
                else:
                    st.session_state.agent = MultimodalDatabaseAgent(
                        use_rag=use_rag,
                        enable_vision=enable_vision,
                        vision_model=vision_model
                    )
                    st.session_state.agent_mode = 'pipeline'
                st.success("✅ Agent initialized successfully!")
            except Exception as e:
                st.error(f"❌ Initialization failed: {e}")
    
    st.markdown("---")
    st.header("📋 Example Queries")
    
    example_queries = [
        "Show me our top 5 customers in the United Kingdom. Who are they?",
        "What 10 products which grew their sales the most, between Q1 and Q2 of 2013?",
        "Show monthly sales trends for 2013",
        "Top 10 products by revenue",
        "What were the highest selling products in December 2013?"
    ]
    
    for query in example_queries:
        if st.button(query, key=f"example_{query}"):
            st.session_state.current_query = query
    
    st.markdown("---")
    st.header("📊 Session Stats")
    
    if st.session_state.query_history:
        st.metric("Total Queries", len(st.session_state.query_history))
        successful = sum(1 for q in st.session_state.query_history if q.get('success'))
        st.metric("Successful", successful)

# Main content
if st.session_state.agent is None:
    st.info("👈 Please initialize the agent in the sidebar to get started!")
    
    st.markdown("""
    ## About This Demo
    
    This application demonstrates **multimodal capabilities** integrated into a natural language database agent:
    
    ### Features:
    - 🗣️ **Natural Language Queries**: Ask questions in plain English
    - 🔍 **SQL Generation**: Automatic T-SQL query generation with RAG
    - 📊 **Smart Visualization**: Automatic chart selection and creation
    - 🤖 **AI Vision Analysis**: GPT-4o analyzes charts and provides insights
    - ✅ **Cross-Modal Consistency**: Insights validated against actual data
    
    ### Workflow:
    1. Enter your question about sales data
    2. AI generates and executes SQL query
    3. Results automatically visualized
    4. Vision model analyzes chart
    5. Receive actionable business insights
    
    ### Database:
    **AdventureWorksDW2025** - Microsoft's sample data warehouse containing:
    - Product sales data
    - Customer information
    - Geographic distribution
    - Time-series analytics
    """)

else:
    # Query input
    col1, col2 = st.columns([4, 1])
    
    with col1:
        query_input = st.text_input(
            "Ask a question about the sales data:",
            value=st.session_state.get('current_query', ''),
            placeholder="e.g., Show me monthly sales trends for 2013",
            key="query_input"
        )
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        process_button = st.button("🔍 Process Query", type="primary", use_container_width=True)
    
    # Advanced options
    with st.expander("🔧 Advanced Options"):
        col_a, col_b = st.columns(2)
        with col_a:
            enable_viz = st.checkbox("Generate Visualization", value=True)
            force_chart_type = st.selectbox(
                "Force Chart Type (optional)",
                options=["Auto", "line", "bar", "horizontal_bar", "pie"],
                index=0
            )
        with col_b:
            enable_vision_analysis = st.checkbox("Enable Vision Analysis", value=True)
            show_sql = st.checkbox("Show Generated SQL", value=True)
            show_agent_trace = st.checkbox("Show Agent Trace", value=False)
    
    # Process query
    if process_button and query_input:
        with st.spinner("🔄 Processing your query..."):
            try:
                if st.session_state.agent_mode == 'planner':
                    result = st.session_state.agent.process_query(
                        query_input,
                        planner_mode=st.session_state.planner_mode,
                    )
                else:
                    # Process with multimodal agent
                    result = st.session_state.agent.process_query(
                        natural_language_query=query_input,
                        enable_visualization=enable_viz,
                        enable_vision_analysis=enable_vision_analysis,
                        chart_type=force_chart_type if force_chart_type != "Auto" else None
                    )
                if 'total_time' not in result:
                    result['total_time'] = 0
                
                # Store in history
                st.session_state.query_history.append(result)
                
                # Display results
                if result.get('success'):
                    st.markdown("---")
                    
                    # SQL Query
                    if show_sql:
                        st.markdown('<p class="sub-header">📝 Generated SQL</p>', unsafe_allow_html=True)
                        st.code(result['sql_query'], language='sql')
                    
                    # Data results
                    st.markdown('<p class="sub-header">📊 Query Results</p>', unsafe_allow_html=True)
                    st.info(f"✅ Returned {result['row_count']} rows in {result.get('total_time', 0):.2f}s")
                    
                    col1, col2 = st.columns([1, 1])
                    
                    with col1:
                        st.dataframe(result['data'], use_container_width=True, height=400)
                    
                    # Visualization
                    if result.get('visualization') and result['visualization'] is not None:
                        with col2:
                            st.markdown(f"**Chart Type:** {result['chart_type']}")
                            image = Image.open(result['visualization'])
                            st.image(image, use_column_width=True)
                    
                    # Vision Analysis
                    if result.get('vision_analysis'):
                        st.markdown('<p class="sub-header">🤖 AI Visual Insights</p>', unsafe_allow_html=True)
                        st.markdown(f'<div class="insight-box">{result["vision_analysis"]}</div>', unsafe_allow_html=True)
                        
                        st.caption(f"Vision tokens used: {result.get('vision_tokens', {}).get('total', 0)}")

                    # Agent Trace
                    if show_agent_trace and result.get('plan'):
                        st.markdown('<p class="sub-header">🧭 Agent Trace</p>', unsafe_allow_html=True)
                        trace_rows = []
                        for step in result.get('plan', []):
                            trace_rows.append({
                                'step': step.get('step_id'),
                                'name': step.get('name'),
                                'status': step.get('status'),
                                'error': step.get('error')
                            })
                        st.dataframe(trace_rows, use_container_width=True)
                    
                    # Metadata
                    with st.expander("📈 Performance Metrics"):
                        metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
                        with metrics_col1:
                            st.metric("SQL Generation", f"{result.get('sql_generation_time', 0):.2f}s")
                        with metrics_col2:
                            st.metric("Total Time", f"{result.get('total_time', 0):.2f}s")
                        with metrics_col3:
                            total_tokens = result.get('tokens_used', {}).get('total_tokens', 0)
                            vision_tokens = result.get('vision_tokens', {}).get('total', 0)
                            st.metric("Total Tokens", total_tokens + vision_tokens)
                
                else:
                    st.error("❌ Query processing failed")
                    for error in result.get('errors', []):
                        st.error(error)
            
            except Exception as e:
                st.error(f"❌ An error occurred: {e}")
    
    # Query history
    if st.session_state.query_history:
        st.markdown("---")
        st.markdown('<p class="sub-header">📜 Query History</p>', unsafe_allow_html=True)
        
        for i, hist_query in enumerate(reversed(st.session_state.query_history[-5:]), 1):
            with st.expander(f"{i}. {hist_query['query']}", expanded=False):
                st.write(f"**Status:** {'✅ Success' if hist_query.get('success') else '❌ Failed'}")
                st.write(f"**Rows:** {hist_query.get('row_count', 0)}")
                st.write(f"**Time:** {hist_query.get('total_time', 0):.2f}s")
                if hist_query.get('vision_analysis'):
                    st.write("**AI Insights:** ✅ Generated")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>Gradient Descenters: Multimodal Database Agent</p>
</div>
""", unsafe_allow_html=True)
