"""
Multimodal Database Agent - Integrates text-to-SQL with visualization and vision analysis
Implements complete multimodal query pipeline with image understanding
"""
import os
from typing import Dict, Optional, Tuple, List
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv

# Import existing components
from database_utils import DatabaseManager
from rag_manager import RAGManager, initialize_rag_system
from rag_evaluator import RAGEnabledEvaluator

# Import new multimodal components
from visualization_generator import VisualizationGenerator
from vision_analyzer import VisionAnalyzer

load_dotenv()


class MultimodalDatabaseAgent:
    """
    Complete multimodal database agent with:
    - Natural language to SQL (text modality)
    - Automatic visualization generation (visual modality)
    - AI-powered visual analysis (multimodal understanding)
    """
    
    def __init__(
        self, 
        use_rag: bool = True,
        enable_vision: bool = True,
        vision_model: str = "gpt-4o"
    ):
        """
        Initialize multimodal agent
        
        Args:
            use_rag: Enable RAG-enhanced context retrieval
            enable_vision: Enable vision-based chart analysis
            vision_model: Vision model to use (gpt-4o, gpt-4o-mini)
        """
        print("="*70)
        print("Initializing Multimodal Database Agent")
        print("="*70)
        
        # Initialize core SQL generation
        self.sql_generator = RAGEnabledEvaluator(use_rag=use_rag)
        self.db = self.sql_generator.db
        
        # Initialize multimodal components
        self.viz_generator = VisualizationGenerator()
        
        self.enable_vision = enable_vision
        if enable_vision:
            self.vision_analyzer = VisionAnalyzer(model=vision_model)
            print("✓ Vision analysis enabled")
        else:
            self.vision_analyzer = None
            print("⚠️  Vision analysis disabled")
        
        # Query history
        self.query_history = []
        
        print("✓ Multimodal Agent Ready")
        print("="*70 + "\n")
    
    def _clean_sql(self, sql: str) -> str:
        """Remove markdown formatting from SQL query"""
        sql = sql.strip()
        # Remove markdown code blocks
        if sql.startswith('```'):
            lines = sql.split('\n')
            # Remove first line (```sql or ```)
            lines = lines[1:]
            # Remove last line if it's ```
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            sql = '\n'.join(lines)
        return sql.strip()
    
    def process_query(
        self,
        natural_language_query: str,
        enable_visualization: bool = True,
        enable_vision_analysis: bool = True,
        chart_type: Optional[str] = None
    ) -> Dict:
        """
        Process natural language query with full multimodal pipeline
        
        Args:
            natural_language_query: User's question in natural language
            enable_visualization: Generate chart from results
            enable_vision_analysis: Analyze chart with vision model
            chart_type: Force specific chart type (optional)
        
        Returns:
            Dictionary containing:
            - sql_query: Generated SQL
            - execution_success: Whether query executed
            - data: Query results as DataFrame
            - data_preview: First 10 rows as dict
            - visualization: Path to chart image (if enabled)
            - chart_type: Type of chart created
            - vision_analysis: AI insights from chart (if enabled)
            - errors: Any errors encountered
            - metadata: Timing and token usage
        """
        start_time = datetime.now()
        result = {
            'query': natural_language_query,
            'timestamp': start_time.isoformat(),
            'errors': []
        }
        
        try:
            # ===== STEP 1: TEXT → SQL (Text Modality) =====
            print(f"\n{'='*70}")
            print(f"Query: {natural_language_query}")
            print(f"{'='*70}\n")
            print("STEP 1: Generating SQL from natural language...")
            
            # Generate SQL using RAG-enabled evaluator
            sql_result = self.sql_generator.generate_sql(natural_language_query)
            
            result['sql_query'] = sql_result['generated_sql']
            result['sql_generation_time'] = sql_result['latency_seconds']
            result['tokens_used'] = {
                'total_tokens': sql_result['total_tokens'],
                'input_tokens': sql_result['input_tokens'],
                'output_tokens': sql_result.get('output_tokens', 0)
            }
            
            if not result['sql_query'] or len(result['sql_query'].strip()) < 10:
                result['execution_success'] = False
                result['errors'].append(f"SQL generation failed: {sql_result.get('error_message', 'Unknown error')}")
                print(f"✗ SQL generation failed")
                return result
            
            print(f"✓ SQL generated ({result['sql_generation_time']:.2f}s)")
            print(f"\nGenerated SQL:\n{result['sql_query']}\n")
            
            # ===== STEP 2: EXECUTE SQL =====
            print("STEP 2: Executing SQL query...")
            
            df, error = self.db.execute_query(result['sql_query'])
            
            if error:
                result['execution_success'] = False
                result['errors'].append(f"Execution error: {error}")
                print(f"✗ Query execution failed: {error}")
                return result
            
            result['execution_success'] = True
            result['data'] = df
            result['row_count'] = len(df)
            result['column_count'] = len(df.columns)
            result['columns'] = df.columns.tolist()
            
            # Store preview (first 10 rows)
            result['data_preview'] = df.head(10).to_dict(orient='records')
            
            print(f"✓ Query executed successfully")
            print(f"  Rows: {len(df)}, Columns: {len(df.columns)}")
            
            if len(df) == 0:
                print("⚠️  Query returned no results")
                result['visualization'] = None
                result['vision_analysis'] = None
                return result
            
            # ===== STEP 3: VISUALIZATION (Visual Modality) =====
            if enable_visualization and not df.empty:
                print(f"\nSTEP 3: Creating visualization...")
                
                viz_result = self.viz_generator.create_visual_summary(
                    df,
                    natural_language_query,
                    result['sql_query']
                )
                
                result['visualization'] = viz_result['chart_path']
                result['chart_type'] = viz_result['chart_type']
                result['data_summary'] = viz_result['data_summary']
                
                if viz_result['chart_path']:
                    print(f"✓ Visualization created: {viz_result['chart_type']}")
                    print(f"  Saved to: {viz_result['chart_path']}")
                else:
                    print(f"⚠️  No visualization created (data shown as table)")
            else:
                result['visualization'] = None
                result['chart_type'] = 'none'
            
            # ===== STEP 4: VISION ANALYSIS (Multimodal Understanding) =====
            if (enable_vision_analysis and 
                self.enable_vision and 
                result.get('visualization') and 
                result['visualization'] is not None):
                
                print(f"\nSTEP 4: Analyzing visualization with AI vision...")
                
                vision_result = self.vision_analyzer.analyze_visualization(
                    image_path=result['visualization'],
                    chart_type=result['chart_type'],
                    query_context=natural_language_query,
                    data_summary=result['data_summary']
                )
                
                if vision_result['success']:
                    result['vision_analysis'] = vision_result['analysis']
                    result['vision_tokens'] = vision_result['tokens']
                    print(f"✓ Vision analysis complete")
                    print(f"  Tokens: {vision_result['tokens']['total']}")
                else:
                    result['vision_analysis'] = None
                    result['errors'].append(f"Vision analysis failed: {vision_result.get('error')}")
                    print(f"✗ Vision analysis failed")
            else:
                result['vision_analysis'] = None
            
            # ===== COMPLETION =====
            end_time = datetime.now()
            result['total_time'] = (end_time - start_time).total_seconds()
            result['success'] = True
            
            print(f"\n{'='*70}")
            print(f"✓ Query processed successfully in {result['total_time']:.2f}s")
            print(f"{'='*70}\n")
            
            # Save to history
            self.query_history.append(result)
            
            return result
            
        except Exception as e:
            result['success'] = False
            result['errors'].append(f"Unexpected error: {str(e)}")
            print(f"\n✗ Error processing query: {e}")
            return result
    
    def display_results(self, result: Dict, show_data: bool = True, max_rows: int = 10):
        """
        Display query results in a formatted way
        
        Args:
            result: Result dictionary from process_query
            show_data: Whether to display data table
            max_rows: Maximum rows to display
        """
        print("\n" + "="*70)
        print("MULTIMODAL QUERY RESULTS")
        print("="*70)
        
        # Query and SQL
        print(f"\n📝 Query: {result['query']}")
        print(f"\n💾 Generated SQL:\n{result.get('sql_query', 'N/A')}")
        
        # Execution status
        if result.get('execution_success'):
            print(f"\n✅ Execution: SUCCESS ({result.get('row_count', 0)} rows)")
        else:
            print(f"\n❌ Execution: FAILED")
            if result.get('errors'):
                for error in result['errors']:
                    print(f"   Error: {error}")
            return
        
        # Data preview
        if show_data and result.get('data') is not None:
            print(f"\n📊 Data Preview (showing {min(max_rows, result['row_count'])} of {result['row_count']} rows):")
            print(result['data'].head(max_rows).to_string(index=False))
        
        # Visualization
        if result.get('visualization'):
            print(f"\n📈 Visualization: {result['chart_type']}")
            print(f"   File: {result['visualization']}")
        
        # Vision Analysis
        if result.get('vision_analysis'):
            print(f"\n🔍 AI VISUAL INSIGHTS:")
            print("="*70)
            print(result['vision_analysis'])
            print("="*70)
        
        # Metadata
        print(f"\n⏱️  Performance:")
        print(f"   SQL Generation: {result.get('sql_generation_time', 0):.2f}s")
        print(f"   Total Time: {result.get('total_time', 0):.2f}s")
        if result.get('tokens_used'):
            print(f"   Tokens (SQL): {result['tokens_used'].get('total_tokens', 0)}")
        if result.get('vision_tokens'):
            print(f"   Tokens (Vision): {result['vision_tokens'].get('total', 0)}")
        
        print("\n" + "="*70 + "\n")
    
    def compare_queries(self, queries: List[str]) -> Dict:
        """
        Process multiple queries and provide comparative analysis
        
        Demonstrates multimodal comparative analysis
        """
        print(f"\n{'='*70}")
        print(f"COMPARATIVE MULTIMODAL ANALYSIS ({len(queries)} queries)")
        print(f"{'='*70}\n")
        
        results = []
        visualizations = []
        descriptions = []
        
        for i, query in enumerate(queries, 1):
            print(f"\n--- Processing Query {i}/{len(queries)} ---")
            result = self.process_query(
                query,
                enable_visualization=True,
                enable_vision_analysis=False  # Skip individual analysis
            )
            results.append(result)
            
            if result.get('visualization'):
                visualizations.append(result['visualization'])
                descriptions.append(f"{query} ({result['chart_type']})")
        
        # Comparative vision analysis
        if len(visualizations) >= 2 and self.enable_vision:
            print(f"\n{'='*70}")
            print("CROSS-CHART COMPARATIVE ANALYSIS")
            print(f"{'='*70}\n")
            
            comparison = self.vision_analyzer.compare_visualizations(
                image_paths=visualizations,
                comparison_context="Comparing multiple sales analytics queries from AdventureWorks database",
                chart_descriptions=descriptions
            )
            
            if comparison['success']:
                print(comparison['comparative_analysis'])
            else:
                print(f"✗ Comparison failed: {comparison.get('error')}")
        
        return {
            'individual_results': results,
            'comparison': comparison if len(visualizations) >= 2 else None
        }
    
    def get_session_summary(self) -> Dict:
        """Get summary of all queries in this session"""
        if not self.query_history:
            return {'total_queries': 0}
        
        successful = [q for q in self.query_history if q.get('success')]
        
        summary = {
            'total_queries': len(self.query_history),
            'successful': len(successful),
            'failed': len(self.query_history) - len(successful),
            'visualizations_created': sum(1 for q in successful if q.get('visualization')),
            'vision_analyses': sum(1 for q in successful if q.get('vision_analysis')),
            'total_rows_returned': sum(q.get('row_count', 0) for q in successful),
            'avg_query_time': sum(q.get('total_time', 0) for q in successful) / len(successful) if successful else 0
        }
        
        return summary


if __name__ == "__main__":
    # Test multimodal agent
    print("\n" + "="*70)
    print("MULTIMODAL DATABASE AGENT - TEST")
    print("="*70)
    
    # Initialize agent
    agent = MultimodalDatabaseAgent(use_rag=True, enable_vision=True)
    
    # Test queries
    test_queries = [
        "Show monthly sales trends for 2013",
        "Top 10 products by revenue",
        "Sales by product category"
    ]
    
    print(f"\nTesting with {len(test_queries)} queries...")
    
    for query in test_queries:
        result = agent.process_query(query)
        agent.display_results(result, show_data=True, max_rows=5)
        
        # Pause between queries
        input("\nPress Enter to continue to next query...")
    
    # Show session summary
    summary = agent.get_session_summary()
    print("\n" + "="*70)
    print("SESSION SUMMARY")
    print("="*70)
    for key, value in summary.items():
        print(f"{key}: {value}")
    print("="*70)
