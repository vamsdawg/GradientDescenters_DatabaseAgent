# Quick Start Guide: Multimodal Database Agent

## Setup (5 minutes)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Verify Database Connection
```bash
python database_utils.py
```

### 3. Initialize RAG System (Optional)
```bash
python -c "from rag_manager import initialize_rag_system; initialize_rag_system()"
```

---

## Usage Options

### Option 1: Web Interface (Recommended for Demos) 🌐

```bash
streamlit run streamlit_app.py
```

Then open browser to `http://localhost:8501`

**Features:**
- Interactive query input
- Real-time visualization
- AI insights display
- Query history
- Performance metrics

---

### Option 2: Jupyter Notebook 📓

```bash
jupyter notebook notebooks/07_multimodal_capabilities_demo.ipynb
```

**Best for:**
- Step-by-step demonstration
- Understanding implementation details
- Testing individual components

---

### Option 3: Python Script 🐍

```python
from multimodal_agent import MultimodalDatabaseAgent

# Initialize
agent = MultimodalDatabaseAgent(use_rag=True, enable_vision=True)

# Process query
result = agent.process_query("Show monthly sales trends for 2013")

# Display results
agent.display_results(result)
```

---

## Example Queries to Try

### Time-Series Analysis
```
"Show monthly sales trends for 2013"
"What were sales by month in 2012?"
"Display quarterly revenue for 2011"
```

### Product Rankings
```
"Top 10 products by revenue"
"Show me the best selling bikes"
"What are the lowest performing products?"
```

### Category Analysis
```
"Sales by product category"
"Compare bikes vs accessories revenue"
"Breakdown of sales by product type"
```

### Geographic Analysis
```
"Sales by country"
"Which regions have the highest revenue?"
"Show sales distribution across territories"
```

---

## Running Evaluations

### Test Cross-Modal Consistency
```python
from multimodal_evaluator import MultimodalEvaluator
from multimodal_agent import MultimodalDatabaseAgent

agent = MultimodalDatabaseAgent()
evaluator = MultimodalEvaluator(agent)

# Run test suite
summary = evaluator.evaluate_test_suite(max_cases=5)

# Results saved to: results/multimodal_evaluation_*.json
```

---

## Troubleshooting

### Issue: "Module not found"
**Solution:** Ensure you're in the project directory
```bash
cd "c:\Users\Vamsi Chintalapati\Desktop\DSBA 6010\final_project"
python streamlit_app.py  # or your desired script
```

### Issue: Database connection failed
**Solution:** Check .env file has correct database credentials
```
DB_SERVER=localhost
DB_NAME=AdventureWorksDW2025
```

### Issue: Vision analysis not working
**Solution:** Verify OpenAI API key is set
```bash
echo %OPENAI_API_KEY%  # Windows
# Should return your API key
```

### Issue: Charts not displaying
**Solution:** Check visualizations directory exists
```bash
mkdir visualizations
```

---

## File Structure

```
final_project/
├── multimodal_agent.py           # Main orchestrator
├── visualization_generator.py     # Chart creation
├── vision_analyzer.py            # AI vision analysis
├── multimodal_evaluator.py       # Testing suite
├── streamlit_app.py              # Web interface
├── database_utils.py             # Database connector
├── rag_manager.py                # RAG system
├── notebooks/
│   └── 07_multimodal_capabilities_demo.ipynb
├── visualizations/               # Generated charts
├── results/                      # Evaluation results
└── requirements.txt              # Dependencies
```

---

## Performance Expectations

| Operation | Time | Tokens |
|-----------|------|---------|
| SQL Generation | ~0.8s | ~500 |
| Visualization | ~0.5s | 0 |
| Vision Analysis | ~1.2s | ~800 |
| **Total per Query** | **~2.7s** | **~1,300** |

### Cost per Query
- ~$0.013 using GPT-4o and GPT-4o-mini
- Approximately 75 queries per $1

---

## Demo Checklist ✓

Before presenting:

- [ ] Install all dependencies
- [ ] Test database connection
- [ ] Generate at least 3 sample visualizations
- [ ] Run evaluation suite once
- [ ] Prepare 5 example queries
- [ ] Open Streamlit app and verify it loads
- [ ] Check that visualizations director exists
- [ ] Have backup screenshots ready

---

## Tips for Best Results

1. **Use specific queries**: "Top 10 products" works better than "show products"
2. **Include time periods**: "sales in 2013" is clearer than "sales"
3. **Be explicit about metrics**: "by revenue" vs "by quantity"
4. **Try different chart types**: System auto-selects, but you can override
5. **Review vision insights**: They provide context beyond raw numbers

---

## Next Steps

After mastering the basics:

1. **Customize prompts** in `vision_analyzer.py` for your specific needs
2. **Add new chart types** in `visualization_generator.py`
3. **Expand test cases** in `multimodal_evaluator.py`
4. **Enhance UI** in `streamlit_app.py`

---

**Ready to go!** Start with the Streamlit app for the best demo experience.

```bash
streamlit run streamlit_app.py
```
