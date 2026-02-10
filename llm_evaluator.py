"""
LLM Evaluator - Tests multiple models for text-to-SQL generation
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

# Database and test cases
from database_utils import DatabaseManager, get_schema_context
from test_cases import TEST_CASES

# Load .env file from the same directory as this script
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))


class LLMEvaluator:
    """Evaluates multiple LLMs for text-to-SQL generation"""
    
    def __init__(self):
        self.openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.anthropic_client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        self.db = DatabaseManager()
        self.db.connect()
        
        # Get schema context once
        self.schema_context = get_schema_context()
        
        # Model configurations with pricing (per 1M tokens)
        self.models = {
            'claude-sonnet-4.5': {
                'name': 'Claude Sonnet 4.5',
                'provider': 'anthropic',
                'model_id': 'claude-sonnet-4-5-20250929',
                'input_cost': 3.00,  # USD per 1M input tokens
                'output_cost': 15.00,  # USD per 1M output tokens
            },
            'gpt-4.1': {
                'name': 'GPT 4.1',
                'provider': 'openai',
                'model_id': 'gpt-4-turbo',
                'input_cost': 10.00,
                'output_cost': 30.00,
            },
            'gpt-4o-mini': {
                'name': 'GPT 4o Mini',
                'provider': 'openai',
                'model_id': 'gpt-4o-mini',
                'input_cost': 0.15,
                'output_cost': 0.60,
            },
        }
        
        self.results = []
    
    def create_prompt(self, natural_language_query: str) -> str:
        """Create prompt for text-to-SQL generation with privacy controls"""
        prompt = f"""You are an expert SQL database assistant for AdventureWorksDW2025. Generate optimized, secure T-SQL queries.

Database Schema:
{self.schema_context}

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

ALLOWED IDENTIFICATION:
- Customer: CustomerKey, FirstName, LastName, City, StateProvinceName, CountryRegionName
- Employee: EmployeeKey, FirstName, LastName, Title

Validation Checklist:
- Schema names included?
- Proper joins used?
- No confidential fields?
- Query is executable?

Natural Language Query: {natural_language_query}

Generate the SQL query (ONLY the query, no explanations):"""
        return prompt
    
    def call_openai_model(self, model_id: str, prompt: str) -> Tuple[str, float, Dict]:
        """Call OpenAI model and return response, latency, and token usage"""
        start_time = time.time()
        
        try:
            response = self.openai_client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": "You are a SQL expert that generates T-SQL queries."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=500
            )
            
            latency = time.time() - start_time
            sql_query = response.choices[0].message.content.strip()
            
            # Clean up SQL query (remove markdown formatting if present)
            sql_query = self._clean_sql_output(sql_query)
            
            token_usage = {
                'input_tokens': response.usage.prompt_tokens,
                'output_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.total_tokens
            }
            
            return sql_query, latency, token_usage
            
        except Exception as e:
            return f"ERROR: {str(e)}", 0, {'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0}
    
    def call_anthropic_model(self, model_id: str, prompt: str) -> Tuple[str, float, Dict]:
        """Call Anthropic model and return response, latency, and token usage"""
        start_time = time.time()
        
        try:
            response = self.anthropic_client.messages.create(
                model=model_id,
                max_tokens=500,
                temperature=0,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            latency = time.time() - start_time
            sql_query = response.content[0].text.strip()
            
            # Clean up SQL query
            sql_query = self._clean_sql_output(sql_query)
            
            token_usage = {
                'input_tokens': response.usage.input_tokens,
                'output_tokens': response.usage.output_tokens,
                'total_tokens': response.usage.input_tokens + response.usage.output_tokens
            }
            
            return sql_query, latency, token_usage
            
        except Exception as e:
            return f"ERROR: {str(e)}", 0, {'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0}
    
    def _clean_sql_output(self, sql: str) -> str:
        """Remove markdown formatting and extra whitespace from SQL output"""
        # Remove markdown code blocks
        if sql.startswith("```sql"):
            sql = sql[6:]
        elif sql.startswith("```"):
            sql = sql[3:]
        
        if sql.endswith("```"):
            sql = sql[:-3]
        
        return sql.strip()
    
    def evaluate_sql(self, sql: str) -> Dict:
        """
        Evaluate generated SQL query
        Returns: {is_valid, is_executable, error_message, row_count}
        """
        result = {
            'is_valid_syntax': False,
            'is_executable': False,
            'error_message': None,
            'row_count': 0,
            'execution_time': 0
        }
        
        # Check if it's an error
        if sql.startswith("ERROR:"):
            result['error_message'] = sql
            return result
        
        # Validate syntax
        is_valid, error = self.db.validate_sql_syntax(sql)
        result['is_valid_syntax'] = is_valid
        
        if not is_valid:
            result['error_message'] = error
            return result
        
        # Try to execute
        start_time = time.time()
        df, error = self.db.execute_query(sql)
        execution_time = time.time() - start_time
        
        if error:
            result['error_message'] = error
        else:
            result['is_executable'] = True
            result['row_count'] = len(df) if df is not None else 0
            result['execution_time'] = execution_time
        
        return result
    
    def calculate_cost(self, token_usage: Dict, model_config: Dict) -> float:
        """Calculate cost in USD for a single query"""
        input_cost = (token_usage['input_tokens'] / 1_000_000) * model_config['input_cost']
        output_cost = (token_usage['output_tokens'] / 1_000_000) * model_config['output_cost']
        return input_cost + output_cost
    
    def test_model_on_case(self, model_key: str, test_case: Dict) -> Dict:
        """Test a single model on a single test case"""
        model_config = self.models[model_key]
        prompt = self.create_prompt(test_case['natural_language'])
        
        print(f"  Testing {model_config['name']}...", end=" ")
        
        # Call appropriate model
        if model_config['provider'] == 'openai':
            sql_query, latency, token_usage = self.call_openai_model(
                model_config['model_id'], 
                prompt
            )
        elif model_config['provider'] == 'anthropic':
            sql_query, latency, token_usage = self.call_anthropic_model(
                model_config['model_id'],
                prompt
            )
        else:
            print("Unsupported provider")
            return None
        
        # Evaluate the generated SQL
        evaluation = self.evaluate_sql(sql_query)
        
        # Calculate cost
        cost = self.calculate_cost(token_usage, model_config)
        
        # Compile result
        result = {
            'timestamp': datetime.now().isoformat(),
            'test_case_id': test_case['id'],
            'test_case_category': test_case['category'],
            'test_case_difficulty': test_case['difficulty'],
            'natural_language': test_case['natural_language'],
            'model_key': model_key,
            'model_name': model_config['name'],
            'generated_sql': sql_query,
            'latency': latency,
            'token_usage': token_usage,
            'cost_usd': cost,
            'evaluation': evaluation
        }
        
        # Print status
        status = "✓" if evaluation['is_executable'] else "✗"
        print(f"{status} ({latency:.2f}s, ${cost:.6f})")
        
        return result
    
    def run_full_evaluation(self, test_case_ids: Optional[List[int]] = None):
        """Run evaluation on all models and test cases"""
        # Select test cases
        if test_case_ids:
            test_cases = [tc for tc in TEST_CASES if tc['id'] in test_case_ids]
        else:
            test_cases = TEST_CASES
        
        print(f"\n{'='*80}")
        print(f"Starting LLM Evaluation")
        print(f"Test Cases: {len(test_cases)}")
        print(f"Models: {len(self.models)}")
        print(f"{'='*80}\n")
        
        for test_case in test_cases:
            print(f"\nTest Case {test_case['id']}: {test_case['natural_language']}")
            print(f"Category: {test_case['category']} | Difficulty: {test_case['difficulty']}")
            
            for model_key in self.models.keys():
                result = self.test_model_on_case(model_key, test_case)
                if result:
                    self.results.append(result)
        
        print(f"\n{'='*80}")
        print(f"Evaluation Complete!")
        print(f"Total Tests: {len(self.results)}")
        print(f"{'='*80}\n")
        
        # Return results in the expected format
        return self.get_results_summary()
    
    def get_results_summary(self):
        """Get results organized by model with summary statistics"""
        model_results = {}
        for model_key in self.models.keys():
            # Get results for this model and transform to match expected format
            raw_results = [r for r in self.results if r['model_key'] == model_key]
            model_results[model_key] = []
            
            for r in raw_results:
                # Transform to expected format
                transformed = {
                    'test_case_id': r['test_case_id'],
                    'category': r['test_case_category'],
                    'difficulty': r['test_case_difficulty'],
                    'natural_language': r['natural_language'],
                    'model_key': r['model_key'],
                    'model_name': r['model_name'],
                    'generated_sql': r['generated_sql'],
                    'latency': r['latency'],
                    'cost': r['cost_usd'],  # Map cost_usd to cost
                    'success': r['evaluation']['is_executable'],  # Map evaluation to success
                    'error_message': r['evaluation'].get('error_message', '')
                }
                model_results[model_key].append(transformed)
        
        # Calculate summary statistics
        total_cost = sum(r['cost_usd'] for r in self.results)
        total_time = sum(r['latency'] for r in self.results)
        
        return {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'total_test_cases': len(set(r['test_case_id'] for r in self.results)),
                'total_models': len(self.models)
            },
            'model_results': model_results,
            'summary': {
                'total_cost': total_cost,
                'total_time': total_time,
                'total_queries': len(self.results)
            }
        }
    
    def save_results(self, filename: str = "results/experiment_results.json"):
        """Save results to JSON file"""
        os.makedirs("results", exist_ok=True)
        
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"✓ Results saved to {filename}")
    
    def cleanup(self):
        """Close database connection"""
        self.db.disconnect()


if __name__ == "__main__":
    evaluator = LLMEvaluator()
    
    # Test on a subset first (first 5 test cases)
    # Testing 3 models: Claude Sonnet 4.5, GPT 4.1, GPT 4o Mini
    evaluator.run_full_evaluation(test_case_ids=[1, 2, 3, 4, 5])
    
    # Save results
    evaluator.save_results()
    
    # Cleanup
    evaluator.cleanup()
