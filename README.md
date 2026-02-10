# AdventureWorksDW2025 Database Agent Project

## Overview
This project develops an AI-powered database agent that converts natural language queries to SQL for the AdventureWorksDW2025 database. The system uses large language models (LLMs) to generate secure, optimized T-SQL queries with built-in privacy controls.

## Milestones Completed

### Milestone 3: LLM Experimentation
- Tested 3 LLMs (Claude Sonnet 4.5, GPT-4.1, GPT-4o-mini) for text-to-SQL generation
- Evaluated 18 test cases across different complexity levels
- Measured performance metrics: accuracy, cost, latency, consistency

### Milestone 4: Prompt Design and Testing
- Developed 5 prompt templates using different techniques (instruction-based, few-shot, chain-of-thought)
- Implemented comprehensive privacy controls to protect sensitive data:
  - Customer: EmailAddress, Phone, Address
  - Sales: SalesQuota information
- Tested on 10 representative, edge-case, and complex queries
- Selected best-performing prompt (Advanced + Privacy) for production use

## Quick Start

### Prerequisites
- Python 3.8+
- SQL Server with AdventureWorksDW2025 database
- OpenAI API key (for GPT-4o-mini)

### Setup

1. **Install dependencies**
```bash
pip install -r requirements.txt
```

2. **Configure environment**
Create a `.env` file:
```
OPENAI_API_KEY=your_key_here
DB_SERVER=localhost
DB_NAME=AdventureWorksDW2025
DB_DRIVER=ODBC Driver 17 for SQL Server
```

### Running the Project

**Option 1: Jupyter Notebooks (Recommended)**
```bash
jupyter notebook
```
Then run notebooks in order:
- `01_setup_verification.ipynb` - Verify environment
- `02_llm_experimentation.ipynb` - Quick test (5 cases)
- `03_full_evaluation.ipynb` - Full evaluation (18 cases)
- `04_prompt_testing.ipynb` - Prompt comparison and testing

**Option 2: Python Scripts**
```bash
# Quick test
python llm_evaluator.py

# Full evaluation
python run_experiments.py
```

## Project Structure
```
final_project/
├── README.md                        # Project documentation
├── requirements.txt                 # Python dependencies
├── .env                             # API keys and database config
│
├── notebooks/                       # Jupyter notebooks
│   ├── 01_setup_verification.ipynb  # Environment verification
│   ├── 02_llm_experimentation.ipynb # Quick test (5 cases)
│   ├── 03_full_evaluation.ipynb     # Full evaluation (18 cases)
│   └── 04_prompt_testing.ipynb      # Prompt design & testing
│
├── database_utils.py                # Database connection & utilities
├── test_cases.py                    # Test query definitions
├── llm_evaluator.py                 # LLM evaluation framework
├── run_experiments.py               # Full evaluation runner
│
└── results/                         # Output directory (auto-created)
    ├── experiment_results.json      # Detailed results
    ├── prompt_testing_results_*.json # Prompt test results
    └── *.csv                        # Summary statistics
```

## Key Features

**Privacy-First Design**
- Automatically excludes sensitive customer data (email, phone, addresses)
- Protects employee contact information
- Hides sales quota data
- Uses only approved fields for identification

**Optimized Prompt Engineering**
- Advanced prompt template with explicit privacy rules
- Schema-aware query generation
- Validation checklist for quality assurance
- Tested across multiple prompting techniques

**Comprehensive Testing**
- 18 test cases covering simple to complex queries
- Representative queries, edge cases, and complex analytical queries
- Privacy-sensitive test scenarios
- Performance metrics: accuracy, latency, cost

## Results

The current system uses GPT-4o-mini with the Advanced + Privacy prompt template, which provides:
- High query accuracy
- Strong privacy compliance
- Low cost per query
- Fast response times

All evaluation results are saved in the `results/` directory with timestamps for tracking improvements over time.
