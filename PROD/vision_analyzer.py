"""
Vision Analyzer - Uses GPT-4o vision to analyze charts and extract insights
Implements multimodal image understanding capability
"""
import base64
import os
from typing import Dict, Optional, List
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path
import pandas as pd

load_dotenv()


class VisionAnalyzer:
    """Analyzes visualizations using GPT-4o vision model to extract insights"""
    
    def __init__(self, model: str = "gpt-4o"):
        """
        Initialize vision analyzer
        
        Args:
            model: Vision-capable model (gpt-4o, gpt-4o-mini, or gpt-4-turbo)
        """
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model = model
        self.analysis_history = []
    
    def encode_image(self, image_path: str) -> str:
        """Encode image to base64 for API transmission"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def create_analysis_prompt(
        self, 
        chart_type: str,
        query_context: str,
        data_summary: Dict
    ) -> str:
        """
        Create tailored prompt for vision model based on chart type
        
        This implements modality-specific prompt strategies (Requirement 4)
        """
        base_prompt = f"""You are analyzing a data visualization from a sales analytics dashboard for AdventureWorks company (bike/cycling products).

**Context:**
- Original Query: "{query_context}"
- Chart Type: {chart_type}
- Data Points: {data_summary.get('rows', 'Unknown')} rows
- Metrics: {', '.join(data_summary.get('column_names', []))}

**Your Task:**
Analyze this visualization and provide business insights. Focus on:

"""
        
        # Chart-type-specific analysis instructions
        if chart_type == 'line':
            prompt = base_prompt + """1. **Trend Analysis:** Identify overall trends (upward, downward, flat, seasonal)
2. **Pattern Recognition:** Spot recurring patterns, cycles, or anomalies
3. **Key Moments:** Highlight peaks, troughs, or inflection points
4. **Growth Metrics:** Estimate growth rates or changes between periods
5. **Business Insights:** What do these trends mean for business decisions?

**Format:**
- Trends: [Describe overall direction]
- Patterns: [Note any repeating patterns or seasonality]
- Key Points: [Identify significant data points]
- Insights: [Provide actionable business insights]
"""
        
        elif chart_type in ['bar', 'horizontal_bar']:
            prompt = base_prompt + """1. **Ranking Analysis:** Identify top and bottom performers
2. **Comparative Insights:** Compare relative performance across categories
3. **Distribution:** Analyze how values are distributed (concentrated vs. spread)
4. **Outliers:** Spot any unusual performers (exceptionally high or low)
5. **Market Share:** Estimate contribution of top performers to total
6. **Business Insights:** Recommendations based on performance gaps

**Format:**
- Leaders: [Identify top performers]
- Laggards: [Identify underperformers]
- Distribution: [Describe how values are spread]
- Insights: [Actionable business recommendations]
"""
        
        elif chart_type == 'pie':
            prompt = base_prompt + """1. **Market Share:** Calculate percentage contributions of each segment
2. **Dominance:** Identify which segments dominate and which are marginal
3. **Balance:** Assess whether distribution is balanced or concentrated
4. **Opportunities:** Spot segments with growth potential
5. **Business Insights:** Strategic recommendations based on distribution

**Format:**
- Dominant Segments: [Which segments lead?]
- Distribution: [Balanced or concentrated?]
- Small Segments: [Minor contributors worth noting]
- Insights: [Strategic recommendations]
"""
        
        elif chart_type == 'scatter':
            prompt = base_prompt + """1. **Correlation:** Identify relationship between variables (positive, negative, none)
2. **Clusters:** Spot groupings or clusters in the data
3. **Outliers:** Identify data points that don't fit the pattern
4. **Strength:** Assess how strong the relationship is
5. **Business Insights:** What does this relationship mean for operations?

**Format:**
- Correlation: [Describe relationship]
- Patterns: [Note clusters or groupings]
- Outliers: [Identify unusual points]
- Insights: [Business implications]
"""
        
        else:
            # Generic analysis for other chart types
            prompt = base_prompt + """1. **Key Observations:** What stands out visually in this chart?
2. **Data Patterns:** Identify any clear patterns or structures
3. **Notable Values:** Highlight extreme or interesting values
4. **Comparisons:** Compare different elements shown
5. **Business Insights:** What actions should be taken based on this data?

**Format:**
- Observations: [Key visual findings]
- Patterns: [Any clear patterns]
- Insights: [Business recommendations]
"""
        
        # Add data context if available
        if 'numeric_summary' in data_summary:
            prompt += f"\n**Data Context:**\n"
            for col, stats in data_summary['numeric_summary'].items():
                if stats.get('total'):
                    prompt += f"- {col}: Min={stats['min']:,.0f}, Max={stats['max']:,.0f}, Avg={stats['mean']:,.0f}, Total={stats['total']:,.0f}\n"
        
        prompt += "\n**Important:** Be specific with values you see in the chart. Provide actionable insights, not just descriptions."
        
        return prompt
    
    def analyze_visualization(
        self,
        image_path: str,
        chart_type: str,
        query_context: str,
        data_summary: Dict,
        detail_level: str = "high"
    ) -> Dict:
        """
        Analyze visualization using vision model
        
        Args:
            image_path: Path to chart image
            chart_type: Type of chart (line, bar, pie, etc.)
            query_context: Original natural language query
            data_summary: Summary statistics about the data
            detail_level: Vision detail level ("low", "high", "auto")
        
        Returns:
            Dictionary with analysis results and metadata
        """
        if not Path(image_path).exists():
            return {
                'success': False,
                'error': f"Image file not found: {image_path}"
            }
        
        try:
            # Encode image
            base64_image = self.encode_image(image_path)
            
            # Create tailored prompt
            prompt = self.create_analysis_prompt(chart_type, query_context, data_summary)
            
            # Call vision model
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}",
                                    "detail": detail_level
                                }
                            }
                        ]
                    }
                ],
                max_tokens=800,
                temperature=0.3  # Low temperature for more focused analysis
            )
            
            # Extract analysis
            analysis_text = response.choices[0].message.content
            
            # Store analysis result
            result = {
                'success': True,
                'analysis': analysis_text,
                'chart_type': chart_type,
                'query_context': query_context,
                'model': self.model,
                'tokens': {
                    'prompt': response.usage.prompt_tokens,
                    'completion': response.usage.completion_tokens,
                    'total': response.usage.total_tokens
                }
            }
            
            # Save to history
            self.analysis_history.append(result)
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'chart_type': chart_type
            }
    
    def compare_visualizations(
        self,
        image_paths: List[str],
        comparison_context: str,
        chart_descriptions: List[str]
    ) -> Dict:
        """
        Compare multiple visualizations to find cross-cutting insights
        
        This demonstrates advanced multimodal analysis
        """
        if len(image_paths) < 2:
            return {'success': False, 'error': 'Need at least 2 images to compare'}
        
        try:
            # Encode all images
            encoded_images = [self.encode_image(path) for path in image_paths]
            
            # Create comparison prompt
            prompt = f"""You are comparing multiple data visualizations from AdventureWorks sales analytics.

**Context:** {comparison_context}

**Charts:**
"""
            for i, desc in enumerate(chart_descriptions, 1):
                prompt += f"{i}. {desc}\n"
            
            prompt += """
**Your Task:**
Compare these visualizations and provide:
1. **Common Patterns:** Insights that appear across multiple charts
2. **Contrasts:** Differences or contradictions between charts
3. **Cross-Analysis:** Insights that emerge only when viewing charts together
4. **Integrated Insights:** Overall conclusions from all visualizations
5. **Recommendations:** Strategic actions based on the complete picture

Be specific and reference which charts show which patterns.
"""
            
            # Build content with all images
            content = [{"type": "text", "text": prompt}]
            for encoded_image in encoded_images:
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{encoded_image}",
                        "detail": "high"
                    }
                })
            
            # Call vision model
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": content}],
                max_tokens=1000,
                temperature=0.3
            )
            
            return {
                'success': True,
                'comparative_analysis': response.choices[0].message.content,
                'num_charts': len(image_paths),
                'tokens': {
                    'prompt': response.usage.prompt_tokens,
                    'completion': response.usage.completion_tokens,
                    'total': response.usage.total_tokens
                }
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def extract_values_from_chart(self, image_path: str, chart_type: str) -> Dict:
        """
        Attempt to extract specific numeric values visible in the chart
        
        This tests cross-modal consistency (Requirement 3) - do extracted values match the data?
        """
        if not Path(image_path).exists():
            return {'success': False, 'error': 'Image not found'}
        
        try:
            base64_image = self.encode_image(image_path)
            
            prompt = f"""Analyze this {chart_type} chart and extract the specific numeric values you can see.

**Task:**
1. Read labels and values from the chart
2. Extract specific numbers (sales amounts, quantities, percentages, etc.)
3. List the top 3-5 data points with their exact values
4. Format as: "Label: Value"

**Example Output:**
- Mountain-200 Black: $450,234
- Road-150 Red: $380,567
- Touring-1000 Blue: $295,123

Be precise with numbers. If percentages are shown, include them. If you cannot read a value clearly, note "unclear".
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}",
                                "detail": "high"
                            }
                        }
                    ]
                }],
                max_tokens=400,
                temperature=0
            )
            
            return {
                'success': True,
                'extracted_values': response.choices[0].message.content,
                'chart_type': chart_type
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_analysis_summary(self) -> Dict:
        """Get summary of all analyses performed"""
        if not self.analysis_history:
            return {'total_analyses': 0}
        
        total_tokens = sum(a['tokens']['total'] for a in self.analysis_history if a['success'])
        
        return {
            'total_analyses': len(self.analysis_history),
            'successful': sum(1 for a in self.analysis_history if a['success']),
            'failed': sum(1 for a in self.analysis_history if not a['success']),
            'total_tokens_used': total_tokens,
            'chart_types_analyzed': list(set(a['chart_type'] for a in self.analysis_history if a['success']))
        }


if __name__ == "__main__":
    # Test vision analyzer
    import sys
    
    print("="*70)
    print("Vision Analyzer Test")
    print("="*70)
    
    # Check if we have any test images
    viz_dir = Path("./visualizations")
    if viz_dir.exists():
        images = list(viz_dir.glob("*.png"))
        if images:
            print(f"\n✓ Found {len(images)} visualization(s) to analyze\n")
            
            analyzer = VisionAnalyzer()
            
            # Analyze first image
            test_image = str(images[0])
            print(f"Analyzing: {test_image}")
            
            result = analyzer.analyze_visualization(
                image_path=test_image,
                chart_type="bar",
                query_context="Top 10 products by sales",
                data_summary={'rows': 10, 'column_names': ['Product', 'Sales']}
            )
            
            if result['success']:
                print("\n" + "="*70)
                print("VISION ANALYSIS RESULT")
                print("="*70)
                print(result['analysis'])
                print("\n" + "="*70)
                print(f"Tokens used: {result['tokens']['total']}")
            else:
                print(f"\n✗ Analysis failed: {result.get('error')}")
        else:
            print("\n⚠️  No visualizations found. Run visualization_generator.py first.")
    else:
        print("\n⚠️  Visualizations directory not found. Run visualization_generator.py first.")
