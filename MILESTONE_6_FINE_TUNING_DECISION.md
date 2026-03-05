# Milestone 6: Fine-Tuning Decision

## What is Fine-Tuning?

Fine-tuning means taking a pre-trained language model and training it further on your specific dataset to specialize it for your task. Think of it like teaching a chef who already knows how to cook (the base model) your particular recipes and preferences (your custom data). The model learns patterns specific to your use case by adjusting its internal weights based on hundreds or thousands of your examples.

## Why Fine-Tuning Doesn't Make Sense for Our Database Agent

Our application converts natural language to SQL queries for the AdventureWorksDW2025 database. Fine-tuning doesn't fit because:

**The base model already knows SQL.** GPT-4o-mini understands SQL syntax, joins, aggregations, and query structure out of the box. We're not teaching it a new language or specialized domain—we're just telling it which tables and rules to follow.

**Our needs change too quickly.** Database schemas evolve. Privacy rules get updated. New tables get added. With fine-tuning, every change means collecting new training data and retraining the model. With prompts, we just update a few lines of text.

**We don't have unique patterns.** Fine-tuning makes sense when you have specialized terminology or unique patterns that standard models don't understand. Our SQL queries are standard T-SQL—nothing proprietary or unusual that requires model-level learning.

## Decision: Prompting is Sufficient

Our current approach using detailed prompts already delivers strong results:
- **90% success rate** on generating executable queries
- **100% valid SQL syntax**
- **1.95 second** average response time
- Privacy rules enforced through explicit prompt instructions

## Why This Makes Sense

**Performance**: The model already handles our test cases well. The few failures we see are edge cases that we can address by refining the prompt, not by retraining the entire model.

**Cost**: We're paying about $0.0015 per query right now, which is cheap. Fine-tuning would add training costs, storage costs for custom models, and potentially higher inference costs—without meaningful performance gains.

**Maintenance**: When something breaks or needs to change, we can fix the prompt in minutes. With a fine-tuned model, we'd need to collect new training examples, retrain, test, and deploy—that could take days or weeks.

**Flexibility**: We can easily switch between models (GPT-4o-mini, Claude, etc.) or update our privacy rules instantly. A fine-tuned model locks us into one provider and requires retraining for updates.

## Further Optimization: Prompt Design and Few-Shot Examples

Since we're not using fine-tuning, we're focusing on optimizing our prompt engineering approach:

### Enhanced Prompt Design
- **Schema context**: Including table structures and relationships directly in the prompt so the model knows exactly what's available
- **Explicit privacy rules**: Clear lists of forbidden fields (EmailAddress, Phone, etc.) that should never appear in queries
- **Validation checklists**: Built-in reminders for the model to check its work before returning a query
- **Output formatting**: Specific instructions for how to structure the SQL (indentation, JOIN types, etc.)

### Few-Shot Examples
Our testing showed that few-shot learning dramatically improved performance. We're expanding this by:
- **Common patterns**: Including 2-3 examples of typical queries (simple selects, aggregations, joins)
- **Privacy-compliant transformations**: Showing how to rewrite queries that ask for sensitive data using allowed alternatives
- **Edge cases**: Demonstrating how to handle complex scenarios like multi-table joins or date filtering

For example, instead of just telling the model "don't use EmailAddress," we can show it:
```
User asks: "Show me customer emails"
Good response: SELECT CustomerKey, FirstName, LastName FROM dbo.DimCustomer
(Email excluded for privacy)
```

### Continuous Improvement
We're also implementing:
- Query validation before execution to catch errors
- Logging of failed queries to identify patterns
- Regular prompt updates based on real usage

This iterative approach lets us improve performance without the complexity of model retraining.
