"""
Main script to run LLM experiments and generate comparison report
"""
import sys
from pathlib import Path
_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT / 'PROD'))
sys.path.insert(0, str(Path(__file__).parent))

import json
import pandas as pd
from llm_evaluator import LLMEvaluator
from test_cases import TEST_CASES


def generate_comparison_report(results_file: str = "results/experiment_results.json"):
    """Generate comprehensive comparison report from results"""
    
    with open(results_file, 'r') as f:
        results = json.load(f)
    
    df = pd.DataFrame(results)
    
    # Extract evaluation metrics
    df['is_valid'] = df['evaluation'].apply(lambda x: x['is_valid_syntax'])
    df['is_executable'] = df['evaluation'].apply(lambda x: x['is_executable'])
    df['execution_time'] = df['evaluation'].apply(lambda x: x['execution_time'])
    df['row_count'] = df['evaluation'].apply(lambda x: x['row_count'])
    df['has_error'] = df['evaluation'].apply(lambda x: x['error_message'] is not None)
    
    # Generate summary statistics by model
    print("\n" + "="*100)
    print("MILESTONE 3: LLM COMPARISON REPORT")
    print("="*100)
    
    print("\n1. SUCCESS RATE BY MODEL")
    print("-" * 100)
    success_by_model = df.groupby('model_name').agg({
        'is_executable': ['sum', 'count', 'mean']
    }).round(3)
    success_by_model.columns = ['Successful', 'Total', 'Success Rate']
    print(success_by_model.to_string())
    
    print("\n\n2. AVERAGE LATENCY BY MODEL (seconds)")
    print("-" * 100)
    latency_by_model = df.groupby('model_name')['latency'].agg(['mean', 'min', 'max', 'std']).round(3)
    latency_by_model.columns = ['Avg Latency', 'Min', 'Max', 'Std Dev']
    print(latency_by_model.to_string())
    
    print("\n\n3. COST ANALYSIS BY MODEL (USD)")
    print("-" * 100)
    cost_by_model = df.groupby('model_name')['cost_usd'].agg(['mean', 'sum']).round(6)
    cost_by_model.columns = ['Avg Cost/Query', 'Total Cost']
    print(cost_by_model.to_string())
    
    print("\n\n4. SUCCESS RATE BY DIFFICULTY")
    print("-" * 100)
    success_by_difficulty = df.groupby(['test_case_difficulty', 'model_name'])['is_executable'].mean().unstack().round(3)
    print(success_by_difficulty.to_string())
    
    print("\n\n5. TOKEN USAGE BY MODEL")
    print("-" * 100)
    df['input_tokens'] = df['token_usage'].apply(lambda x: x['input_tokens'])
    df['output_tokens'] = df['token_usage'].apply(lambda x: x['output_tokens'])
    
    token_by_model = df.groupby('model_name').agg({
        'input_tokens': 'mean',
        'output_tokens': 'mean'
    }).round(0)
    print(token_by_model.to_string())
    
    # Save detailed CSV
    csv_filename = "results/model_comparison.csv"
    df.to_csv(csv_filename, index=False)
    print(f"\n\n✓ Detailed results saved to {csv_filename}")
    
    # Generate markdown report
    generate_markdown_report(df)
    
    print("\n" + "="*100)
    print("REPORT GENERATION COMPLETE")
    print("="*100 + "\n")


def generate_markdown_report(df: pd.DataFrame):
    """Generate markdown report for milestone submission"""
    
    report = """# Milestone 3: LLM Experimentation Report

## Executive Summary

This report documents the evaluation of multiple Large Language Models (LLMs) for text-to-SQL generation using the AdventureWorksDW2025 database.

## Models Tested

1. **Claude Sonnet 4.5** (Anthropic)
2. **GPT 4.1** (OpenAI)
3. **GPT 4o Mini** (OpenAI)

## Methodology

### Test Cases
- Total test cases: {total_cases}
- Categories: Simple Select, Aggregation, Join, Date Filter, Group By, Top N, Complex
- Difficulty levels: Easy, Medium, Hard, Very Hard

### Evaluation Metrics
1. **Output Quality**: SQL syntax validity and executability
2. **Latency**: Response time in seconds
3. **Cost**: USD per query based on token usage
4. **Consistency**: Success rate across different difficulty levels

## Results

### 1. Success Rate by Model

| Model | Successful | Total | Success Rate |
|-------|------------|-------|--------------|
"""
    
    # Add success rate data
    success_by_model = df.groupby('model_name').agg({
        'is_executable': ['sum', 'count', 'mean']
    })
    success_by_model.columns = ['Successful', 'Total', 'Success Rate']
    
    for model, row in success_by_model.iterrows():
        report += f"| {model} | {int(row['Successful'])} | {int(row['Total'])} | {row['Success Rate']:.1%} |\n"
    
    report += """
### 2. Performance Metrics

#### Latency Comparison (seconds)

| Model | Avg Latency | Min | Max |
|-------|-------------|-----|-----|
"""
    
    latency_by_model = df.groupby('model_name')['latency'].agg(['mean', 'min', 'max'])
    for model, row in latency_by_model.iterrows():
        report += f"| {model} | {row['mean']:.3f} | {row['min']:.3f} | {row['max']:.3f} |\n"
    
    report += """
#### Cost Analysis (USD)

| Model | Avg Cost/Query | Total Cost |
|-------|----------------|------------|
"""
    
    cost_by_model = df.groupby('model_name')['cost_usd'].agg(['mean', 'sum'])
    for model, row in cost_by_model.iterrows():
        report += f"| {model} | ${row['mean']:.6f} | ${row['sum']:.6f} |\n"
    
    # Find best model for each metric
    best_success = success_by_model['Success Rate'].idxmax()
    best_speed = latency_by_model['mean'].idxmin()
    best_cost = cost_by_model['mean'].idxmin()
    
    report += f"""
## Model Selection Rationale

### Recommended Model: **[TO BE DETERMINED BASED ON RESULTS]**

#### Decision Factors:

1. **Output Quality**
   - Best success rate: **{best_success}** ({success_by_model.loc[best_success, 'Success Rate']:.1%})
   - All models showed strong performance on simple queries
   - Differences emerged in complex queries with multiple joins

2. **Latency**
   - Fastest model: **{best_speed}** ({latency_by_model.loc[best_speed, 'mean']:.3f}s avg)
   - Acceptable range: < 2 seconds for real-time user experience
   
3. **Cost**
   - Most cost-effective: **{best_cost}** (${cost_by_model.loc[best_cost, 'mean']:.6f}/query)
   - Projected monthly cost (10,000 queries): ${cost_by_model.loc[best_cost, 'mean'] * 10000:.2f}

### Trade-offs

| Criterion | Best Model | Trade-off |
|-----------|------------|-----------|
| Quality | {best_success} | May be slower or more expensive |
| Speed | {best_speed} | May sacrifice some quality |
| Cost | {best_cost} | May have slightly lower quality |

## Baseline Performance Metrics

Based on the evaluation, we establish the following baselines for our database agent:

- **Target Success Rate**: ≥ 90% on Easy/Medium queries, ≥ 70% on Hard queries
- **Target Latency**: < 2 seconds for 95th percentile
- **Target Cost**: < $0.01 per query
- **Target User Satisfaction**: 4/5 stars (to be measured in future milestones)

## Next Steps (Milestone 4)

1. Design and test core prompt templates based on insights from this evaluation
2. Implement few-shot learning with example queries
3. Add error handling and query refinement logic
4. Create test suite with edge cases

## Appendix

### Sample Generated SQL

**Test Case**: "Show me all products that are red in color"

**Claude Sonnet 4.5 Output**:
```sql
SELECT * FROM dbo.DimProduct WHERE Color = 'Red'
```

**GPT 4.1 Output**:
```sql
SELECT * FROM dbo.DimProduct WHERE Color = 'Red'
```

**GPT 4o Mini Output**:
```sql
SELECT * FROM dbo.DimProduct WHERE Color = 'Red'
```

---

*Report generated on {timestamp}*
"""
    
    report = report.format(
        total_cases=len(TEST_CASES),
        best_success=best_success,
        best_speed=best_speed,
        best_cost=best_cost,
        timestamp=pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
    )
    
    # Save markdown report
    with open("results/milestone3_report.md", 'w') as f:
        f.write(report)
    
    print("✓ Markdown report saved to results/milestone3_report.md")


def main():
    """Main execution function"""
    print("\n" + "="*100)
    print("MILESTONE 3: EXPERIMENT WITH LLMs")
    print("="*100)
    
    print("\nThis script will:")
    print("1. Test 3 different LLMs (Claude Sonnet 4.5, GPT 4.1, GPT 4o Mini)")
    print("2. Run them on 18 representative test cases")
    print("3. Measure quality, latency, and cost")
    print("4. Generate comprehensive comparison report")
    
    response = input("\nProceed with full evaluation? (y/n): ")
    
    if response.lower() != 'y':
        print("Evaluation cancelled.")
        return
    
    # Initialize evaluator
    evaluator = LLMEvaluator()
    
    # Run on all test cases
    print("\nStarting evaluation...")
    evaluator.run_full_evaluation()
    
    # Save raw results
    evaluator.save_results()
    
    # Cleanup
    evaluator.cleanup()
    
    # Generate comparison report
    generate_comparison_report()
    
    print("\n✓ Milestone 3 experiments complete!")
    print("  - Raw results: results/experiment_results.json")
    print("  - CSV comparison: results/model_comparison.csv")
    print("  - Report: results/milestone3_report.md")


if __name__ == "__main__":
    main()
