"""
Multimodal Evaluator - Tests cross-modal consistency and relevance
Implements testing framework for Requirement 3
"""
import sys
from pathlib import Path
_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT / 'PROD'))
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from typing import Dict, List, Tuple
import re
from datetime import datetime
import json

from multimodal_agent import MultimodalDatabaseAgent
from agent_orchestrator import AgentOrchestrator
from test_cases import TEST_CASES


class MultimodalEvaluator:
    """
    Evaluate multimodal capabilities for:
    - Cross-modal consistency (do vision insights match actual data?)
    - Visual analysis accuracy
    - Chart type appropriateness
    - End-to-end pipeline reliability
    """
    
    def __init__(self, agent: MultimodalDatabaseAgent):
        """Initialize evaluator with multimodal agent"""
        self.agent = agent
        self.evaluation_results = []
    
    def evaluate_cross_modal_consistency(self, result: Dict) -> Dict:
        """
        Test if vision analysis aligns with actual data values
        
        This is the core cross-modal consistency test (Requirement 3)
        """
        consistency_score = {
            'test': 'cross_modal_consistency',
            'query': result.get('query'),
            'passed': False,
            'issues': [],
            'score': 0.0
        }
        
        if not result.get('vision_analysis') or not result.get('data') is not None:
            consistency_score['issues'].append("Missing vision analysis or data")
            return consistency_score
        
        df = result['data']
        analysis = result['vision_analysis']
        
        checks = []
        
        # Check 1: Value extraction accuracy
        numeric_cols = df.select_dtypes(include=['int64', 'float64', 'int32', 'float32']).columns
        if len(numeric_cols) > 0:
            # Get actual top values
            value_col = numeric_cols[0]
           
            actual_max = df[value_col].max()
            actual_min = df[value_col].min()
            actual_mean = df[value_col].mean()
            
            # Extract numbers from vision analysis
            numbers_in_analysis = re.findall(r'[\d,]+(?:\.\d+)?', analysis)
            # Filter out empty strings and convert to float
            numbers_in_analysis = []
            for n in numbers_in_analysis:
                cleaned = n.replace(',', '').strip()
                if cleaned:  # Only process non-empty strings
                    try:
                        numbers_in_analysis.append(float(cleaned))
                    except ValueError:
                        pass  # Skip invalid numbers
            
            # Check if actual values appear in analysis (with some tolerance)
            max_mentioned = any(abs(n - actual_max) / actual_max < 0.1 for n in numbers_in_analysis) if numbers_in_analysis else False
            
            checks.append({
                'check': 'value_accuracy',
                'passed': max_mentioned,
                'details': f"Max value {actual_max:.0f} {'found' if max_mentioned else 'not found'} in analysis"
            })
        
        # Check 2: Ranking consistency (for top-N queries)
        if 'top' in result['query'].lower() and len(df) > 0:
            # Get actual top item
            if len(df.columns) >= 2:
                first_col = df.columns[0]
                actual_top_item = str(df.iloc[0][first_col])
                
                # Check if mentioned in analysis
                top_mentioned = actual_top_item.lower() in analysis.lower()
                
                checks.append({
                    'check': 'ranking_consistency',
                    'passed': top_mentioned,
                    'details': f"Top item '{actual_top_item}' {'mentioned' if top_mentioned else 'not mentioned'}"
                })
        
        # Check 3: Trend direction (for time-series)
        if result.get('chart_type') == 'line' and len(df) > 2:
            if len(numeric_cols) > 0:
                value_col = numeric_cols[0]
                # Simple trend check: compare first and last values
                first_val = df[value_col].iloc[0]
                last_val = df[value_col].iloc[-1]
                
                actual_trend = "upward" if last_val > first_val * 1.1 else "downward" if last_val < first_val * 0.9 else "flat"
                
                analysis_lower = analysis.lower()
                trend_mentioned = (
                    ('upward' in analysis_lower or 'increase' in analysis_lower or 'growth' in analysis_lower) if actual_trend == 'upward'
                    else ('downward' in analysis_lower or 'decrease' in analysis_lower or 'decline' in analysis_lower) if actual_trend == 'downward'
                    else ('flat' in analysis_lower or 'stable' in analysis_lower or 'steady' in analysis_lower)
                )
                
                checks.append({
                    'check': 'trend_accuracy',
                    'passed': trend_mentioned,
                    'details': f"Actual trend: {actual_trend}, {'correctly' if trend_mentioned else 'not'} identified"
                })
        
        # Check 4: Count accuracy
        if 'count' in analysis.lower() or 'number' in analysis.lower():
            actual_count = len(df)
            # Look for the count in analysis
            count_mentioned = str(actual_count) in analysis or (actual_count <= 20 and any(str(i) in analysis for i in range(actual_count-2, actual_count+3)))
            
            checks.append({
                'check': 'count_accuracy',
                'passed': count_mentioned,
                'details': f"Actual count: {actual_count}, {'found' if count_mentioned else 'not found'} in analysis"
            })
        
        # Calculate overall score
        if checks:
            passed_checks = sum(1 for c in checks if c['passed'])
            consistency_score['score'] = passed_checks / len(checks)
            consistency_score['passed'] = consistency_score['score'] >= 0.5
            consistency_score['checks'] = checks
        else:
            consistency_score['score'] = 1.0
            consistency_score['passed'] = True
            consistency_score['checks'] = []
            consistency_score['issues'].append("No specific checks applicable")
        
        return consistency_score
    
    def evaluate_chart_appropriateness(self, result: Dict) -> Dict:
        """
        Evaluate if the chosen chart type is appropriate for the data
        """
        appropriateness = {
            'test': 'chart_appropriateness',
            'query': result.get('query'),
            'chart_type': result.get('chart_type'),
            'passed': False,
            'reasoning': ''
        }
        
        if not result.get('chart_type') or result['chart_type'] == 'none':
            appropriateness['reasoning'] = "No chart created"
            return appropriateness
        
        query_lower = result['query'].lower()
        chart_type = result['chart_type']
        df = result.get('data')
        
        # Heuristic checks
        appropriate = False
        
        if 'trend' in query_lower or 'over time' in query_lower or 'monthly' in query_lower:
            appropriate = chart_type == 'line'
            appropriateness['reasoning'] = f"Time-series query should use line chart. Used: {chart_type}"
        
        elif 'top' in query_lower or 'bottom' in query_lower:
            appropriate = chart_type in ['bar', 'horizontal_bar']
            appropriateness['reasoning'] = f"Ranking query should use bar chart. Used: {chart_type}"
        
        elif 'category' in query_lower or 'breakdown' in query_lower:
            appropriate = chart_type in ['bar', 'pie']
            appropriateness['reasoning'] = f"Category comparison should use bar/pie chart. Used: {chart_type}"
        
        elif df is not None and len(df) > 20:
            appropriate = chart_type in ['horizontal_bar', 'line']
            appropriateness['reasoning'] = f"Many data points ({len(df)}) - horizontal bar or line recommended. Used: {chart_type}"
        
        else:
            # No strong opinion
            appropriate = True
            appropriateness['reasoning'] = f"Chart type {chart_type} is acceptable"
        
        appropriateness['passed'] = appropriate
        return appropriateness
    
    def evaluate_vision_relevance(self, result: Dict) -> Dict:
        """
        Evaluate if vision analysis is relevant and useful
        """
        relevance = {
            'test': 'vision_relevance',
            'query': result.get('query'),
            'passed': False,
            'score': 0.0,
            'issues': []
        }
        
        if not result.get('vision_analysis'):
            relevance['issues'].append("No vision analysis available")
            return relevance
        
        analysis = result['vision_analysis']
        query = result['query']
        
        # Relevance checks
        checks = []
        
        # Check 1: Analysis mentions query context
        query_terms = set(word.lower() for word in query.split() if len(word) > 3)
        analysis_lower = analysis.lower()
        terms_mentioned = sum(1 for term in query_terms if term in analysis_lower)
        
        checks.append({
            'check': 'context_relevance',
            'passed': terms_mentioned >= len(query_terms) * 0.3,
            'score': min(terms_mentioned / max(len(query_terms), 1), 1.0)
        })
        
        # Check 2: Provides actionable insights (indicator keywords)
        insight_keywords = ['recommend', 'suggest', 'should', 'opportunity', 'consider', 
                           'focus', 'improve', 'strategy', 'increase', 'decrease']
        has_insights = any(keyword in analysis_lower for keyword in insight_keywords)
        
        checks.append({
            'check': 'actionable_insights',
            'passed': has_insights,
            'score': 1.0 if has_insights else 0.0
        })
        
        # Check 3: Mentions specific data points/values
        has_specifics = bool(re.search(r'\d+', analysis))
        
        checks.append({
            'check': 'specific_values',
            'passed': has_specifics,
            'score': 1.0 if has_specifics else 0.5
        })
        
        # Check 4: Reasonable length (not too short, not too long)
        analysis_length = len(analysis.split())
        appropriate_length = 50 <= analysis_length <= 500
        
        checks.append({
            'check': 'appropriate_length',
            'passed': appropriate_length,
            'score': 1.0 if appropriate_length else 0.5
        })
        
        # Calculate overall relevance score
        relevance['score'] = sum(c['score'] for c in checks) / len(checks)
        relevance['passed'] = relevance['score'] >= 0.6
        relevance['checks'] = checks
        
        return relevance
    
    def evaluate_query(self, natural_language_query: str) -> Dict:
        """
        Run complete evaluation on a single query
        """
        print(f"\n{'='*70}")
        print(f"Evaluating: {natural_language_query}")
        print(f"{'='*70}")
        
        # Process query with multimodal agent
        result = self.agent.process_query(natural_language_query)
        
        if not result.get('success'):
            print("✗ Query failed - skipping evaluation")
            return {
                'query': natural_language_query,
                'success': False,
                'errors': result.get('errors', [])
            }
        
        # Run evaluations
        evaluations = {
            'query': natural_language_query,
            'success': True,
            'result': result
        }
        
        # Test 1: Cross-modal consistency
        print("\n→ Testing cross-modal consistency...")
        consistency = self.evaluate_cross_modal_consistency(result)
        evaluations['consistency'] = consistency
        print(f"  {'✓' if consistency['passed'] else '✗'} Score: {consistency['score']:.2f}")
        
        # Test 2: Chart appropriateness
        print("→ Testing chart appropriateness...")
        appropriateness = self.evaluate_chart_appropriateness(result)
        evaluations['appropriateness'] = appropriateness
        print(f"  {'✓' if appropriateness['passed'] else '✗'} {appropriateness['reasoning']}")
        
        # Test 3: Vision relevance
        print("→ Testing vision analysis relevance...")
        relevance = self.evaluate_vision_relevance(result)
        evaluations['relevance'] = relevance
        print(f"  {'✓' if relevance['passed'] else '✗'} Score: {relevance['score']:.2f}")
        
        # Overall assessment
        all_passed = (consistency['passed'] and appropriateness['passed'] and relevance['passed'])
        evaluations['overall_passed'] = all_passed
        
        print(f"\n{'='*70}")
        print(f"Overall: {'✓ PASSED' if all_passed else '✗ ISSUES FOUND'}")
        print(f"{'='*70}")
        
        self.evaluation_results.append(evaluations)
        return evaluations
    
    def evaluate_test_suite(self, test_cases: List[Dict] = None, max_cases: int = 10) -> Dict:
        """
        Run evaluation on multiple test cases
        """
        if test_cases is None:
            # Use subset of standard test cases
            test_cases = TEST_CASES[:max_cases]
        
        print(f"\n{'='*70}")
        print(f"MULTIMODAL EVALUATION SUITE")
        print(f"Testing {len(test_cases)} queries")
        print(f"{'='*70}\n")
        
        results = []
        
        for i, test_case in enumerate(test_cases, 1):
            query = test_case.get('natural_language', test_case.get('query', ''))
            print(f"\n[{i}/{len(test_cases)}] {query}")
            
            eval_result = self.evaluate_query(query)
            results.append(eval_result)
        
        # Generate summary report
        successful = [r for r in results if r.get('success')]
        
        summary = {
            'total_queries': len(results),
            'successful_executions': len(successful),
            'failed_executions': len(results) - len(successful),
            'consistency_pass_rate': sum(1 for r in successful if r.get('consistency', {}).get('passed')) / len(successful) if successful else 0,
            'appropriateness_pass_rate': sum(1 for r in successful if r.get('appropriateness', {}).get('passed')) / len(successful) if successful else 0,
            'relevance_pass_rate': sum(1 for r in successful if r.get('relevance', {}).get('passed')) / len(successful) if successful else 0,
            'overall_pass_rate': sum(1 for r in successful if r.get('overall_passed')) / len(successful) if successful else 0,
            'avg_consistency_score': sum(r.get('consistency', {}).get('score', 0) for r in successful) / len(successful) if successful else 0,
            'avg_relevance_score': sum(r.get('relevance', {}).get('score', 0) for r in successful) / len(successful) if successful else 0
        }
        
        # Save detailed results
        output_file = Path(f"results/multimodal_evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        output_file.parent.mkdir(exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump({
                'summary': summary,
                'detailed_results': results
            }, f, indent=2, default=str)
        
        print(f"\n{'='*70}")
        print("EVALUATION SUMMARY")
        print(f"{'='*70}")
        for key, value in summary.items():
            if 'rate' in key or 'score' in key:
                print(f"{key}: {value:.2%}")
            else:
                print(f"{key}: {value}")
        print(f"\nDetailed results saved to: {output_file}")
        print(f"{'='*70}\n")
        
        return summary

    def evaluate_agent_execution(self, orchestrator: AgentOrchestrator, query: str) -> Dict:
        """Evaluate planner-executor flow and execution success for a single query."""
        result = orchestrator.process_query(query)

        plan_steps = [step["name"] for step in result.get("plan", [])]
        required_steps = [
            "Generate SQL",
            "Validate SQL",
            "Execute SQL",
        ]

        missing_steps = [step for step in required_steps if step not in plan_steps]
        completed_steps = [
            step for step in result.get("plan", []) if step.get("status") == "completed"
        ]

        return {
            "query": query,
            "success": result.get("success", False),
            "missing_steps": missing_steps,
            "completed_steps": len(completed_steps),
            "total_steps": len(result.get("plan", [])),
            "errors": result.get("errors", []),
        }

    def evaluate_agent_suite(self, queries: List[str]) -> Dict:
        """Run multi-step reasoning tests across several scenarios."""
        orchestrator = AgentOrchestrator(
            use_rag=True,
            enable_visualization=True,
            enable_vision=False,
        )

        results = []
        for query in queries:
            results.append(self.evaluate_agent_execution(orchestrator, query))

        orchestrator.shutdown()

        success_rate = (
            sum(1 for r in results if r["success"]) / len(results)
            if results
            else 0
        )
        missing_step_count = sum(1 for r in results if r["missing_steps"])

        return {
            "total_queries": len(results),
            "success_rate": success_rate,
            "missing_step_cases": missing_step_count,
            "details": results,
        }


if __name__ == "__main__":
    print("\n" + "="*70)
    print("MULTIMODAL CAPABILITY EVALUATION")
    print("="*70)
    
    # Initialize agent and evaluator
    agent = MultimodalDatabaseAgent(use_rag=True, enable_vision=True)
    evaluator = MultimodalEvaluator(agent)
    
    # Run evaluation suite
    test_queries = [
        "Show monthly sales trends for 2013",
        "Top 10 products by revenue",
        "Sales by product category",
        "What were sales in December 2013?",
        "Show me the highest selling products"
    ]
    
    test_cases = [{'natural_language': q} for q in test_queries]
    summary = evaluator.evaluate_test_suite(test_cases, max_cases=5)
    
    print("\n✓ Evaluation complete!")
