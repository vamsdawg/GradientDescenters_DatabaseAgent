"""
Test cases for LLM evaluation - Natural language queries for AdventureWorksDW2025
"""
from typing import List, Dict

# Test cases organized by complexity level
TEST_CASES = [
    # ===== SIMPLE SELECT QUERIES =====
    {
        "id": 1,
        "category": "Simple Select",
        "natural_language": "Show me all products",
        "expected_tables": ["DimProduct"],
        "difficulty": "Easy",
        "description": "Basic SELECT with no filters"
    },
    {
        "id": 2,
        "category": "Simple Select",
        "natural_language": "List all customers with their email addresses",
        "expected_tables": ["DimCustomer"],
        "difficulty": "Easy",
        "description": "Simple SELECT with specific columns"
    },
    {
        "id": 3,
        "category": "Simple Filter",
        "natural_language": "Show me products that are red in color",
        "expected_tables": ["DimProduct"],
        "difficulty": "Easy",
        "description": "SELECT with WHERE clause"
    },
    
    # ===== AGGREGATION QUERIES =====
    {
        "id": 4,
        "category": "Aggregation",
        "natural_language": "What is the total sales amount?",
        "expected_tables": ["FactInternetSales"],
        "difficulty": "Medium",
        "description": "Simple SUM aggregation"
    },
    {
        "id": 5,
        "category": "Aggregation",
        "natural_language": "How many customers do we have?",
        "expected_tables": ["DimCustomer"],
        "difficulty": "Easy",
        "description": "COUNT aggregation"
    },
    {
        "id": 6,
        "category": "Aggregation",
        "natural_language": "What is the average order quantity for internet sales?",
        "expected_tables": ["FactInternetSales"],
        "difficulty": "Medium",
        "description": "AVG aggregation"
    },
    
    # ===== JOIN QUERIES =====
    {
        "id": 7,
        "category": "Join",
        "natural_language": "Show me all sales with product names",
        "expected_tables": ["FactInternetSales", "DimProduct"],
        "difficulty": "Medium",
        "description": "Simple JOIN between fact and dimension"
    },
    {
        "id": 8,
        "category": "Join",
        "natural_language": "List all orders with customer names and product names",
        "expected_tables": ["FactInternetSales", "DimCustomer", "DimProduct"],
        "difficulty": "Medium",
        "description": "Multiple JOINs"
    },
    {
        "id": 9,
        "category": "Join",
        "natural_language": "Show me sales by product category",
        "expected_tables": ["FactInternetSales", "DimProduct", "DimProductCategory"],
        "difficulty": "Hard",
        "description": "Multiple JOINs with aggregation"
    },
    
    # ===== DATE/TIME QUERIES =====
    {
        "id": 10,
        "category": "Date Filter",
        "natural_language": "Show me sales from the year 2023",
        "expected_tables": ["FactInternetSales", "DimDate"],
        "difficulty": "Medium",
        "description": "Date filtering with dimension table"
    },
    {
        "id": 11,
        "category": "Date Filter",
        "natural_language": "What were the total sales in December 2023?",
        "expected_tables": ["FactInternetSales", "DimDate"],
        "difficulty": "Medium",
        "description": "Date filtering with aggregation"
    },
    
    # ===== GROUP BY QUERIES =====
    {
        "id": 12,
        "category": "Group By",
        "natural_language": "Show me total sales by country",
        "expected_tables": ["FactInternetSales", "DimCustomer", "DimGeography"],
        "difficulty": "Hard",
        "description": "GROUP BY with multiple joins"
    },
    {
        "id": 13,
        "category": "Group By",
        "natural_language": "What is the average unit price by product category?",
        "expected_tables": ["DimProduct", "DimProductCategory"],
        "difficulty": "Medium",
        "description": "GROUP BY with aggregation and join"
    },
    
    # ===== TOP N QUERIES =====
    {
        "id": 14,
        "category": "Top N",
        "natural_language": "Show me the top 10 products by sales amount",
        "expected_tables": ["FactInternetSales", "DimProduct"],
        "difficulty": "Hard",
        "description": "TOP N with aggregation and sorting"
    },
    {
        "id": 15,
        "category": "Top N",
        "natural_language": "Who are the top 5 customers by total purchase amount?",
        "expected_tables": ["FactInternetSales", "DimCustomer"],
        "difficulty": "Hard",
        "description": "TOP N with customer dimension"
    },
    
    # ===== COMPLEX ANALYTICAL QUERIES =====
    {
        "id": 16,
        "category": "Complex",
        "natural_language": "Compare sales between 2023 and 2024 by quarter",
        "expected_tables": ["FactInternetSales", "DimDate"],
        "difficulty": "Very Hard",
        "description": "Year-over-year comparison with time grouping"
    },
    {
        "id": 17,
        "category": "Complex",
        "natural_language": "Show me the profit margin by product subcategory",
        "expected_tables": ["FactInternetSales", "DimProduct", "DimProductSubcategory"],
        "difficulty": "Very Hard",
        "description": "Calculated fields with multiple joins"
    },
    {
        "id": 18,
        "category": "Complex",
        "natural_language": "Which sales territory has the highest average order value?",
        "expected_tables": ["FactInternetSales", "DimSalesTerritory"],
        "difficulty": "Hard",
        "description": "Aggregation with comparison logic"
    },
]


def get_test_cases_by_difficulty(difficulty: str) -> List[Dict]:
    """Filter test cases by difficulty level"""
    return [tc for tc in TEST_CASES if tc["difficulty"] == difficulty]


def get_test_cases_by_category(category: str) -> List[Dict]:
    """Filter test cases by category"""
    return [tc for tc in TEST_CASES if tc["category"] == category]


def get_test_case_by_id(test_id: int) -> Dict:
    """Get a specific test case by ID"""
    for tc in TEST_CASES:
        if tc["id"] == test_id:
            return tc
    return None


def print_test_cases_summary():
    """Print summary of all test cases"""
    print("=" * 80)
    print("TEST CASES SUMMARY")
    print("=" * 80)
    
    # Group by category
    categories = set(tc["category"] for tc in TEST_CASES)
    
    for category in sorted(categories):
        cases = get_test_cases_by_category(category)
        print(f"\n{category} ({len(cases)} cases):")
        for tc in cases:
            print(f"  [{tc['id']:2d}] {tc['natural_language'][:60]:60s} | {tc['difficulty']}")
    
    print(f"\n{'=' * 80}")
    print(f"Total Test Cases: {len(TEST_CASES)}")
    print(f"Difficulty Distribution:")
    difficulties = [tc["difficulty"] for tc in TEST_CASES]
    for diff in ["Easy", "Medium", "Hard", "Very Hard"]:
        count = difficulties.count(diff)
        print(f"  {diff}: {count}")


if __name__ == "__main__":
    print_test_cases_summary()
