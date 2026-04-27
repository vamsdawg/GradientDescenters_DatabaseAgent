"""
RAG Evaluation Framework
Evaluates retrieval quality (precision@k, recall) and answer quality
"""
import sys
from pathlib import Path
_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT / 'PROD'))
sys.path.insert(0, str(Path(__file__).parent))

import os
import json
import pandas as pd
from typing import List, Dict, Tuple
from collections import defaultdict

from rag_manager import RAGManager, initialize_rag_system
from rag_evaluator import RAGEnabledEvaluator


class RAGEvaluationFramework:
    """Comprehensive evaluation of RAG system performance"""
    
    def __init__(self, rag_manager=None):
        """Initialize evaluation framework
        
        Args:
            rag_manager: Optional pre-initialized RAG manager. If None, creates a new one.
        """
        self.rag = rag_manager if rag_manager is not None else initialize_rag_system()
        
    def evaluate_retrieval_precision_recall(
        self,
        test_cases: List[Dict],
        k: int = 3
    ) -> Dict:
        """
        Evaluate retrieval quality using precision@k and recall
        
        For each test case, manually identify which retrieved documents are relevant,
        then calculate precision and recall.
        """
        
        print(f"\n{'='*70}")
        print(f"RETRIEVAL QUALITY EVALUATION (Precision@{k}, Recall)")
        print(f"{'='*70}\n")
        
        retrieval_results = []
        
        for test in test_cases:
            query = test['natural_language']
            expected_tables = set(test['expected_tables'])
            test_id = test['id']
            
            # Retrieve similar examples
            examples = self.rag.retrieve_similar_examples(query, k=k)
            
            # Retrieve relevant schemas
            schemas = self.rag.retrieve_relevant_schemas(query, k=5)
            
            # Evaluate schema retrieval (most important)
            retrieved_tables = set()
            for schema in schemas:
                table_name = schema['metadata']['table_name']
                # Convert table name format (e.g., "FactInternetSales" to match expected)
                for expected in expected_tables:
                    if table_name in expected or expected.split('.')[-1] == table_name:
                        retrieved_tables.add(expected)
            
            # Calculate metrics for table retrieval
            relevant_retrieved = len(expected_tables & retrieved_tables)
            precision = relevant_retrieved / len(retrieved_tables) if retrieved_tables else 0
            recall = relevant_retrieved / len(expected_tables) if expected_tables else 0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            
            retrieval_results.append({
                'test_id': test_id,
                'query': query,
                'expected_tables': list(expected_tables),
                'retrieved_tables': list(retrieved_tables),
                'relevant_retrieved': relevant_retrieved,
                'precision': round(precision, 3),
                'recall': round(recall, 3),
                'f1_score': round(f1, 3),
                'num_examples_retrieved': len(examples),
                'example_distances': [round(ex['distance'], 3) for ex in examples] if examples else []
            })
            
            print(f"[{test_id}] {query[:60]}...")
            print(f"  Expected: {expected_tables}")
            print(f"  Retrieved: {retrieved_tables}")
            print(f"  Precision@{k}: {precision:.3f} | Recall: {recall:.3f} | F1: {f1:.3f}")
        
        # Calculate aggregate statistics
        avg_precision = sum(r['precision'] for r in retrieval_results) / len(retrieval_results)
        avg_recall = sum(r['recall'] for r in retrieval_results) / len(retrieval_results)
        avg_f1 = sum(r['f1_score'] for r in retrieval_results) / len(retrieval_results)
        
        perfect_retrievals = sum(1 for r in retrieval_results if r['recall'] == 1.0)
        
        summary = {
            'average_precision': round(avg_precision, 3),
            'average_recall': round(avg_recall, 3),
            'average_f1': round(avg_f1, 3),
            'perfect_retrievals': perfect_retrievals,
            'total_queries': len(retrieval_results),
            'perfect_retrieval_rate': round(perfect_retrievals / len(retrieval_results) * 100, 1)
        }
        
        print(f"\n{'-'*70}")
        print(f"RETRIEVAL SUMMARY:")
        print(f"  Average Precision@{k}: {summary['average_precision']}")
        print(f"  Average Recall: {summary['average_recall']}")
        print(f"  Average F1 Score: {summary['average_f1']}")
        print(f"  Perfect Retrievals: {summary['perfect_retrievals']}/{summary['total_queries']} ({summary['perfect_retrieval_rate']}%)")
        print(f"{'-'*70}\n")
        
        return {
            'summary': summary,
            'details': retrieval_results
        }
    
    def compare_rag_vs_baseline(
        self,
        test_cases: List[Dict]
    ) -> Dict:
        """
        Compare RAG-enabled vs baseline approach
        Measures end-to-end SQL generation quality
        """
        
        print(f"\n{'='*70}")
        print("COMPARING RAG vs BASELINE")
        print(f"{'='*70}\n")
        
        # Run baseline evaluation
        print("\n--- BASELINE EVALUATION ---")
        baseline_evaluator = RAGEnabledEvaluator(use_rag=False)
        baseline_results = baseline_evaluator.run_evaluation(test_cases)
        
        # Run RAG evaluation
        print("\n--- RAG-ENABLED EVALUATION ---")
        rag_evaluator = RAGEnabledEvaluator(use_rag=True)
        rag_results = rag_evaluator.run_evaluation(test_cases)
        
        # Compare results
        comparison = []
        
        for base, rag in zip(baseline_results, rag_results):
            comparison.append({
                'test_id': base['test_id'],
                'query': base['natural_language'],
                'baseline_success': base['execution_success'],
                'rag_success': rag['execution_success'],
                'baseline_tokens': base['total_tokens'],
                'rag_tokens': rag['total_tokens'],
                'baseline_latency': base['latency_seconds'],
                'rag_latency': rag['latency_seconds'],
                'improvement': 'RAG Better' if rag['execution_success'] and not base['execution_success'] else
                               'Baseline Better' if base['execution_success'] and not rag['execution_success'] else
                               'Both Success' if base['execution_success'] and rag['execution_success'] else
                               'Both Failed'
            })
        
        # Calculate summary statistics
        baseline_success_rate = sum(1 for r in baseline_results if r['execution_success']) / len(baseline_results)
        rag_success_rate = sum(1 for r in rag_results if r['execution_success']) / len(rag_results)
        
        baseline_avg_tokens = sum(r['total_tokens'] for r in baseline_results) / len(baseline_results)
        rag_avg_tokens = sum(r['total_tokens'] for r in rag_results) / len(rag_results)
        
        baseline_avg_latency = sum(r['latency_seconds'] for r in baseline_results) / len(baseline_results)
        rag_avg_latency = sum(r['latency_seconds'] for r in rag_results) / len(rag_results)
        
        # Count improvement cases
        rag_better = sum(1 for c in comparison if c['improvement'] == 'RAG Better')
        baseline_better = sum(1 for c in comparison if c['improvement'] == 'Baseline Better')
        both_success = sum(1 for c in comparison if c['improvement'] == 'Both Success')
        
        summary = {
            'baseline_success_rate': round(baseline_success_rate * 100, 1),
            'rag_success_rate': round(rag_success_rate * 100, 1),
            'success_rate_improvement': round((rag_success_rate - baseline_success_rate) * 100, 1),
            'baseline_avg_tokens': round(baseline_avg_tokens),
            'rag_avg_tokens': round(rag_avg_tokens),
            'token_increase_pct': round((rag_avg_tokens - baseline_avg_tokens) / baseline_avg_tokens * 100, 1),
            'baseline_avg_latency': round(baseline_avg_latency, 2),
            'rag_avg_latency': round(rag_avg_latency, 2),
            'rag_only_better': rag_better,
            'baseline_only_better': baseline_better,
            'both_successful': both_success,
            'total_cases': len(comparison)
        }
        
        print(f"\n{'='*70}")
        print("COMPARISON SUMMARY:")
        print(f"{'='*70}")
        print(f"\nSuccess Rates:")
        print(f"  Baseline: {summary['baseline_success_rate']}%")
        print(f"  RAG: {summary['rag_success_rate']}%")
        print(f"  Improvement: {summary['success_rate_improvement']:+.1f}%")
        print(f"\nToken Usage:")
        print(f"  Baseline Avg: {summary['baseline_avg_tokens']} tokens")
        print(f"  RAG Avg: {summary['rag_avg_tokens']} tokens")
        print(f"  Increase: {summary['token_increase_pct']:+.1f}%")
        print(f"\nLatency:")
        print(f"  Baseline Avg: {summary['baseline_avg_latency']}s")
        print(f"  RAG Avg: {summary['rag_avg_latency']}s")
        print(f"\nOutcome Distribution:")
        print(f"  RAG Better: {summary['rag_only_better']} cases")
        print(f"  Baseline Better: {summary['baseline_only_better']} cases")
        print(f"  Both Successful: {summary['both_successful']} cases")
        print(f"{'='*70}\n")
        
        return {
            'summary': summary,
            'comparison_details': comparison,
            'baseline_results': baseline_results,
            'rag_results': rag_results
        }
    
    def run_full_evaluation(
        self,
        test_cases: List[Dict],
        output_dir: str = './results'
    ) -> Dict:
        """Run complete evaluation pipeline"""
        
        print(f"\n{'#'*70}")
        print("# RAG SYSTEM FULL EVALUATION")
        print(f"# Test Cases: {len(test_cases)}")
        print(f"{'#'*70}\n")
        
        os.makedirs(output_dir, exist_ok=True)
        
        # 1. Evaluate retrieval quality
        retrieval_eval = self.evaluate_retrieval_precision_recall(test_cases, k=3)
        
        # 2. Compare RAG vs Baseline
        comparison_eval = self.compare_rag_vs_baseline(test_cases)
        
        # 3. Combine results
        full_results = {
            'evaluation_type': 'RAG Full Evaluation',
            'test_cases_count': len(test_cases),
            'retrieval_metrics': retrieval_eval['summary'],
            'comparison_metrics': comparison_eval['summary'],
            'retrieval_details': retrieval_eval['details'],
            'comparison_details': comparison_eval['comparison_details'],
            'baseline_results': comparison_eval['baseline_results'],
            'rag_results': comparison_eval['rag_results']
        }
        
        # 4. Save results
        timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
        
        # Save JSON
        json_file = os.path.join(output_dir, f'rag_full_evaluation_{timestamp}.json')
        with open(json_file, 'w') as f:
            json.dump(full_results, f, indent=2)
        print(f"✓ Saved full results to: {json_file}")
        
        # Save summary CSV
        summary_data = {
            'Metric': [
                'Retrieval Precision@3',
                'Retrieval Recall',
                'Retrieval F1 Score',
                'Baseline Success Rate (%)',
                'RAG Success Rate (%)',
                'Success Rate Improvement (%)',
                'Baseline Avg Tokens',
                'RAG Avg Tokens',
                'Token Increase (%)',
                'Baseline Avg Latency (s)',
                'RAG Avg Latency (s)'
            ],
            'Value': [
                full_results['retrieval_metrics']['average_precision'],
                full_results['retrieval_metrics']['average_recall'],
                full_results['retrieval_metrics']['average_f1'],
                full_results['comparison_metrics']['baseline_success_rate'],
                full_results['comparison_metrics']['rag_success_rate'],
                full_results['comparison_metrics']['success_rate_improvement'],
                full_results['comparison_metrics']['baseline_avg_tokens'],
                full_results['comparison_metrics']['rag_avg_tokens'],
                full_results['comparison_metrics']['token_increase_pct'],
                full_results['comparison_metrics']['baseline_avg_latency'],
                full_results['comparison_metrics']['rag_avg_latency']
            ]
        }
        
        summary_df = pd.DataFrame(summary_data)
        csv_file = os.path.join(output_dir, f'rag_evaluation_summary_{timestamp}.csv')
        summary_df.to_csv(csv_file, index=False)
        print(f"✓ Saved summary to: {csv_file}")
        
        return full_results


if __name__ == "__main__":
    # Load test cases
    test_cases_file = os.path.join(os.path.dirname(__file__), 
                                   'rag_content', 'examples', 'test_cases_with_sql.json')
    
    with open(test_cases_file, 'r') as f:
        test_cases = json.load(f)
    
    # Run evaluation on first 10 test cases (for time/cost)
    test_sample = test_cases[:10]
    
    framework = RAGEvaluationFramework()
    results = framework.run_full_evaluation(test_sample)
    
    print(f"\n{'='*70}")
    print("EVALUATION COMPLETE!")
    print(f"{'='*70}")
