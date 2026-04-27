"""
RAG-Enhanced LLM Evaluator
Integrates RAG retrieval with LLM text-to-SQL generation
"""
import os
import time
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dotenv import load_dotenv

# LLM imports
import openai
from anthropic import Anthropic

# Database and RAG
from database_utils import DatabaseManager
from rag_manager import RAGManager, initialize_rag_system

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))


class RAGEnabledEvaluator:
    """LLM Evaluator with RAG retrieval for enhanced context"""
    
    def __init__(self, use_rag: bool = True):
        """Initialize evaluator with optional RAG"""
        self.use_rag = use_rag
        self.openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.anthropic_client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        self.db = DatabaseManager()
        self.db.connect()
        
        # Initialize RAG system if enabled
        if self.use_rag:
            print("Initializing RAG system...")
            self.rag = initialize_rag_system()
        else:
            self.rag = None
            print("RAG disabled - using baseline approach")
        
        # Model configuration
        self.models = {
            'gpt-4o-mini': {
                'name': 'GPT 4o Mini',
                'provider': 'openai',
                'model_id': 'gpt-4o-mini',
                'input_cost': 0.15,
                'output_cost': 0.60,
            },
        }
        
        self.results = []
    
    def create_prompt_with_rag(self, natural_language_query: str) -> str:
        """Create prompt with RAG-retrieved context"""
        
        # Retrieve relevant context
        context = self.rag.retrieve_all_context(
            natural_language_query,
            k_examples=3,
            k_patterns=2,
            k_schemas=5,
            k_business=2
        )
        
        # Build enhanced prompt
        prompt = f"""You are an expert SQL database assistant for AdventureWorksDW2025. Generate optimized, secure T-SQL queries.

RETRIEVED CONTEXT:
==================

SIMILAR EXAMPLE QUERIES:
------------------------
"""
        
        # Add similar examples
        for i, ex in enumerate(context['examples'], 1):
            prompt += f"\nExample {i}:\n{ex['document']}\n"
        
        prompt += f"""
RELEVANT JOIN PATTERNS:
-----------------------
"""
        
        # Add join patterns
        for pat in context['patterns']:
            prompt += f"\n{pat['document'][:500]}...\n"  # First 500 chars
        
        prompt += f"""
RELEVANT TABLE SCHEMAS:
-----------------------
"""
        
        # Add relevant schemas
        for schema in context['schemas']:
            # Extract key information from schema
            lines = schema['document'].split('\n')[:25]  # First 25 lines
            prompt += f"\n{chr(10).join(lines)}\n"
        
        prompt += f"""
BUSINESS RULES:
---------------
"""
        
        # Add business rules
        for rule in context['business_rules']:
            prompt += f"\n{rule['document'][:400]}...\n"
        
        prompt += f"""

==================
TASK:
==================

Natural Language Query: {natural_language_query}

Based on the retrieved context above, generate the SQL query following these guidelines:
1. Use patterns from similar examples
2. Follow the join patterns shown
3. Use correct table schemas
4. Apply relevant business rules
5. Ensure privacy compliance (no confidential fields)

Generate ONLY the SQL query (no explanations):"""
        
        return prompt
    
    def create_prompt_baseline(self, natural_language_query: str) -> str:
        """Create baseline prompt without RAG (full schema)"""
        from database_utils import get_schema_context
        
        schema_context = get_schema_context()
        
        prompt = f"""You are an expert SQL database assistant for AdventureWorksDW2025. Generate optimized, secure T-SQL queries.

Database Schema:
{schema_context}

SQL Generation Rules:
1. Use explicit schema names (dbo.TableName)
2. Use appropriate JOIN types (INNER, LEFT, etc.)
3. Include TOP clause when limiting results
4. Use proper date formatting for SQL Server
5. Write clean, readable SQL with proper indentation
6. Use meaningful column aliases

CRITICAL PRIVACY & SECURITY RULES:
CONFIDENTIAL FIELDS - NEVER INCLUDE IN SELECT:
- Customer: EmailAddress, Phone, AddressLine1, AddressLine2
- Employee: EmailAddress, Phone
- Sales: SalesQuota, SalesQuotaDate

Natural Language Query: {natural_language_query}

Generate the SQL query (ONLY the query, no explanations):"""
        
        return prompt
    
    def call_model(self, model_id: str, prompt: str) -> Tuple[str, float, Dict]:
        """Call LLM and return SQL, latency, and tokens"""
        start_time = time.time()
        
        try:
            response = self.openai_client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": "You are a SQL expert that generates T-SQL queries."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=1000  # Increased for RAG context
            )
            
            latency = time.time() - start_time
            sql_query = response.choices[0].message.content.strip()
            
            # Clean up SQL query
            sql_query = self._clean_sql_output(sql_query)
            
            token_usage = {
                'input_tokens': response.usage.prompt_tokens,
                'output_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.total_tokens
            }
            
            return sql_query, latency, token_usage
            
        except Exception as e:
            return f"ERROR: {str(e)}", 0, {'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0}
    
    def _clean_sql_output(self, sql: str) -> str:
        """Clean SQL output from LLM"""
        # Remove markdown code blocks
        if '```sql' in sql:
            sql = sql.split('```sql')[1].split('```')[0]
        elif '```' in sql:
            sql = sql.split('```')[1].split('```')[0]
        
        return sql.strip()
    
    def generate_sql(self, natural_language: str) -> Dict:
        """
        Simple SQL generation (for demo/interactive use)
        Returns dict with: generated_sql, execution_success, result_count, total_tokens, latency_seconds
        """
        # Create prompt
        if self.use_rag:
            prompt = self.create_prompt_with_rag(natural_language)
        else:
            prompt = self.create_prompt_baseline(natural_language)
        
        # Generate SQL
        model_id = self.models['gpt-4o-mini']['model_id']
        sql_query, latency, token_usage = self.call_model(model_id, prompt)
        
        # Try to execute
        execution_success = False
        result_count = 0
        error_message = None
        
        if not sql_query.startswith('ERROR:'):
            cleaned_sql = self._clean_sql_output(sql_query)
            try:
                results = self.db.execute_query(cleaned_sql)
                execution_success = True
                result_count = len(results) if results else 0
            except Exception as e:
                error_message = str(e)
        else:
            error_message = sql_query
        
        return {
            'natural_language': natural_language,
            'generated_sql': self._clean_sql_output(sql_query),
            'execution_success': execution_success,
            'result_count': result_count,
            'error_message': error_message,
            'total_tokens': token_usage['total_tokens'],
            'input_tokens': token_usage['input_tokens'],
            'output_tokens': token_usage['output_tokens'],
            'latency_seconds': latency,
            'method': 'RAG' if self.use_rag else 'Baseline'
        }
    
    def evaluate_query(
        self,
        natural_language: str,
        expected_tables: List[str],
        test_id: int
    ) -> Dict:
        """Evaluate a single query with or without RAG (for evaluation framework)"""
        
        # Create prompt
        if self.use_rag:
            prompt = self.create_prompt_with_rag(natural_language)
            method = "RAG"
        else:
            prompt = self.create_prompt_baseline(natural_language)
            method = "Baseline"
        
        # Generate SQL
        model_id = self.models['gpt-4o-mini']['model_id']
        sql_query, latency, token_usage = self.call_model(model_id, prompt)
        
        # Test execution
        df, error = self.db.execute_query(sql_query)
        
        # Calculate metrics
        result = {
            'test_id': test_id,
            'method': method,
            'natural_language': natural_language,
            'generated_sql': sql_query,
            'expected_tables': expected_tables,
            'execution_success': error is None,
            'error_message': error,
            'result_count': len(df) if df is not None else 0,
            'latency_seconds': round(latency, 3),
            'input_tokens': token_usage['input_tokens'],
            'output_tokens': token_usage['output_tokens'],
            'total_tokens': token_usage['total_tokens'],
            'timestamp': datetime.now().isoformat()
        }
        
        return result
    
    def run_evaluation(self, test_cases: List[Dict]) -> List[Dict]:
        """Run evaluation on all test cases"""
        results = []
        
        print(f"\nRunning evaluation with {'RAG' if self.use_rag else 'Baseline'} method")
        print(f"Total test cases: {len(test_cases)}")
        print("=" * 70)
        
        for i, test in enumerate(test_cases, 1):
            print(f"\n[{i}/{len(test_cases)}] {test['natural_language']}")
            
            result = self.evaluate_query(
                test['natural_language'],
                test['expected_tables'],
                test['id']
            )
            
            results.append(result)
            
            # Print result
            if result['execution_success']:
                print(f"  ✓ Success | Rows: {result['result_count']} | "
                      f"Latency: {result['latency_seconds']}s | "
                      f"Tokens: {result['total_tokens']}")
            else:
                print(f"  ✗ Failed | Error: {result['error_message'][:100]}")
        
        print("\n" + "=" * 70)
        print(f"✓ Evaluation complete!")
        
        # Summary statistics
        successful = sum(1 for r in results if r['execution_success'])
        total_tokens = sum(r['total_tokens'] for r in results)
        avg_latency = sum(r['latency_seconds'] for r in results) / len(results)
        
        print(f"\nSummary:")
        print(f"  Success Rate: {successful}/{len(results)} ({successful/len(results)*100:.1f}%)")
        print(f"  Total Tokens: {total_tokens:,}")
        print(f"  Avg Latency: {avg_latency:.2f}s")
        
        return results
    
    def save_results(self, results: List[Dict], filename: str):
        """Save results to JSON file"""
        output_dir = os.path.join(os.path.dirname(__file__), 'results')
        os.makedirs(output_dir, exist_ok=True)
        
        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n✓ Results saved to: {filepath}")


if __name__ == "__main__":
    # Load test cases
    test_cases_file = os.path.join(os.path.dirname(__file__), 
                                   'rag_content', 'examples', 'test_cases_with_sql.json')
    
    with open(test_cases_file, 'r') as f:
        test_cases = json.load(f)
    
    # Test first 5 cases with RAG
    test_sample = test_cases[:5]
    
    print("="  * 70)
    print("RAG-ENABLED EVALUATION TEST")
    print("=" * 70)
    
    evaluator = RAGEnabledEvaluator(use_rag=True)
    results = evaluator.run_evaluation(test_sample)
    evaluator.save_results(results, 'rag_test_results.json')
