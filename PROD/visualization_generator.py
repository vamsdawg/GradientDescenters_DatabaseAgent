"""
Visualization Generator - Creates charts from query results
Automatically selects appropriate visualization based on data characteristics
"""
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Optional, Tuple, Dict
import io
from pathlib import Path
import os

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['font.size'] = 10


class VisualizationGenerator:
    """Automatically generates appropriate visualizations from query results"""
    
    def __init__(self, output_dir: str = "./visualizations"):
        """Initialize visualization generator"""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
    def detect_chart_type(self, df: pd.DataFrame, query_context: str = "") -> str:
        """
        Automatically detect the most appropriate chart type based on data characteristics
        
        Returns: 'line', 'bar', 'horizontal_bar', 'pie', 'scatter', 'heatmap', or 'table'
        """
        if df.empty or len(df) == 0:
            return 'table'
        
        num_rows = len(df)
        num_cols = len(df.columns)
        
        # Check column types
        numeric_cols = df.select_dtypes(include=['int64', 'float64', 'int32', 'float32']).columns
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns
        datetime_cols = df.select_dtypes(include=['datetime64']).columns
        
        # Detect time series data
        time_indicators = ['year', 'month', 'day', 'date', 'quarter', 'week']
        has_time_column = any(
            any(indicator in col.lower() for indicator in time_indicators)
            for col in df.columns
        )
        
        # Query context hints
        context_lower = query_context.lower()
        
        # Decision tree for chart selection
        if has_time_column or len(datetime_cols) > 0 or 'trend' in context_lower or 'over time' in context_lower:
            return 'line'
        
        elif 'compare' in context_lower or 'versus' in context_lower or 'vs' in context_lower:
            if num_rows > 10:
                return 'horizontal_bar'
            return 'bar'
        
        elif ('top' in context_lower or 'bottom' in context_lower) and num_rows <= 20:
            if num_rows > 10:
                return 'horizontal_bar'
            return 'bar'
        
        elif 'distribution' in context_lower or 'breakdown' in context_lower:
            if num_rows <= 8 and len(numeric_cols) > 0:
                return 'pie'
            return 'bar'
        
        elif 'category' in context_lower or 'by category' in context_lower:
            return 'bar'
        
        elif len(numeric_cols) >= 2 and num_rows <= 100:
            return 'scatter'
        
        # Default heuristics based on data shape
        elif num_rows <= 8 and len(numeric_cols) == 1:
            return 'pie'
        
        elif num_rows <= 30:
            return 'bar'
        
        elif num_rows > 30:
            return 'horizontal_bar'
        
        else:
            return 'table'
    
    def create_visualization(
        self, 
        df: pd.DataFrame, 
        query_context: str = "",
        chart_type: Optional[str] = None,
        title: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Create visualization and save to file
        
        Args:
            df: DataFrame with query results
            query_context: The original natural language query
            chart_type: Force specific chart type (optional)
            title: Custom title (optional)
        
        Returns:
            (file_path, chart_type_used)
        """
        if df.empty:
            print("⚠️  No data to visualize")
            return None, 'empty'
        
        # Auto-detect chart type if not specified
        if chart_type is None:
            chart_type = self.detect_chart_type(df, query_context)
        
        # Generate title if not provided
        if title is None:
            title = query_context if query_context else "Query Results"
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 6))
        
        try:
            if chart_type == 'line':
                self._create_line_chart(df, ax, title)
            
            elif chart_type == 'bar':
                self._create_bar_chart(df, ax, title)
            
            elif chart_type == 'horizontal_bar':
                self._create_horizontal_bar_chart(df, ax, title)
            
            elif chart_type == 'pie':
                self._create_pie_chart(df, ax, title)
            
            elif chart_type == 'scatter':
                self._create_scatter_plot(df, ax, title)
            
            elif chart_type == 'heatmap':
                self._create_heatmap(df, ax, title)
            
            else:
                # No chart, return None
                plt.close(fig)
                return None, 'table'
            
            # Save figure
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            filename = f"chart_{chart_type}_{timestamp}.png"
            filepath = self.output_dir / filename
            
            plt.tight_layout()
            plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white')
            plt.close(fig)
            
            print(f"✓ Visualization saved: {filepath}")
            return str(filepath), chart_type
            
        except Exception as e:
            print(f"✗ Error creating visualization: {e}")
            plt.close(fig)
            return None, 'error'
    
    def _create_line_chart(self, df: pd.DataFrame, ax: plt.Axes, title: str):
        """Create line chart for time-series or trend data"""
        # Find x and y columns
        numeric_cols = df.select_dtypes(include=['int64', 'float64', 'int32', 'float32']).columns
        non_numeric_cols = [col for col in df.columns if col not in numeric_cols]
        
        if len(non_numeric_cols) > 0 and len(numeric_cols) > 0:
            x_col = non_numeric_cols[0]
            y_cols = numeric_cols[:3]  # Up to 3 series
            
            for y_col in y_cols:
                ax.plot(df[x_col], df[y_col], marker='o', linewidth=2, label=y_col)
            
            ax.set_xlabel(x_col, fontsize=12, fontweight='bold')
            ax.set_ylabel('Value', fontsize=12, fontweight='bold')
            
            if len(y_cols) > 1:
                ax.legend()
            
            # Rotate x-axis labels if needed
            if len(df) > 10:
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        ax.grid(True, alpha=0.3)
    
    def _create_bar_chart(self, df: pd.DataFrame, ax: plt.Axes, title: str):
        """Create vertical bar chart"""
        numeric_cols = df.select_dtypes(include=['int64', 'float64', 'int32', 'float32']).columns
        categorical_cols = [col for col in df.columns if col not in numeric_cols]
        
        if len(categorical_cols) > 0 and len(numeric_cols) > 0:
            x_col = categorical_cols[0]
            y_col = numeric_cols[0]
            
            bars = ax.bar(df[x_col], df[y_col], color='steelblue', edgecolor='black', alpha=0.7)
            
            # Add value labels on top of bars
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:,.0f}',
                       ha='center', va='bottom', fontsize=9)
            
            ax.set_xlabel(x_col, fontsize=12, fontweight='bold')
            ax.set_ylabel(y_col, fontsize=12, fontweight='bold')
            
            # Rotate labels if many categories
            if len(df) > 8:
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        ax.grid(True, alpha=0.3, axis='y')
    
    def _create_horizontal_bar_chart(self, df: pd.DataFrame, ax: plt.Axes, title: str):
        """Create horizontal bar chart (better for many items or long labels)"""
        numeric_cols = df.select_dtypes(include=['int64', 'float64', 'int32', 'float32']).columns
        categorical_cols = [col for col in df.columns if col not in numeric_cols]
        
        if len(categorical_cols) > 0 and len(numeric_cols) > 0:
            y_col = categorical_cols[0]
            x_col = numeric_cols[0]
            
            # Sort by value for better visualization
            df_sorted = df.sort_values(by=x_col, ascending=True)
            
            bars = ax.barh(df_sorted[y_col], df_sorted[x_col], color='coral', edgecolor='black', alpha=0.7)
            
            # Add value labels
            for i, bar in enumerate(bars):
                width = bar.get_width()
                ax.text(width, bar.get_y() + bar.get_height()/2.,
                       f'{width:,.0f}',
                       ha='left', va='center', fontsize=9, fontweight='bold')
            
            ax.set_ylabel(y_col, fontsize=12, fontweight='bold')
            ax.set_xlabel(x_col, fontsize=12, fontweight='bold')
        
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        ax.grid(True, alpha=0.3, axis='x')
    
    def _create_pie_chart(self, df: pd.DataFrame, ax: plt.Axes, title: str):
        """Create pie chart for distribution/breakdown"""
        numeric_cols = df.select_dtypes(include=['int64', 'float64', 'int32', 'float32']).columns
        categorical_cols = [col for col in df.columns if col not in numeric_cols]
        
        if len(categorical_cols) > 0 and len(numeric_cols) > 0:
            labels_col = categorical_cols[0]
            values_col = numeric_cols[0]
            
            # Handle top N if too many slices
            if len(df) > 8:
                df_top = df.nlargest(7, values_col)
                others_sum = df[~df[labels_col].isin(df_top[labels_col])][values_col].sum()
                if others_sum > 0:
                    df_top = pd.concat([df_top, pd.DataFrame({
                        labels_col: ['Others'],
                        values_col: [others_sum]
                    })])
                df = df_top
            
            colors = sns.color_palette('Set3', len(df))
            wedges, texts, autotexts = ax.pie(
                df[values_col], 
                labels=df[labels_col],
                autopct='%1.1f%%',
                startangle=90,
                colors=colors,
                textprops={'fontsize': 10, 'fontweight': 'bold'}
            )
            
            # Make percentage text white for better contrast
            for autotext in autotexts:
                autotext.set_color('white')
        
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
    
    def _create_scatter_plot(self, df: pd.DataFrame, ax: plt.Axes, title: str):
        """Create scatter plot for correlation analysis"""
        numeric_cols = df.select_dtypes(include=['int64', 'float64', 'int32', 'float32']).columns
        
        if len(numeric_cols) >= 2:
            x_col = numeric_cols[0]
            y_col = numeric_cols[1]
            
            ax.scatter(df[x_col], df[y_col], s=100, alpha=0.6, edgecolors='black', color='teal')
            
            ax.set_xlabel(x_col, fontsize=12, fontweight='bold')
            ax.set_ylabel(y_col, fontsize=12, fontweight='bold')
        
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        ax.grid(True, alpha=0.3)
    
    def _create_heatmap(self, df: pd.DataFrame, ax: plt.Axes, title: str):
        """Create heatmap for matrix data"""
        # Select only numeric columns
        numeric_df = df.select_dtypes(include=['int64', 'float64', 'int32', 'float32'])
        
        if not numeric_df.empty:
            sns.heatmap(numeric_df, annot=True, fmt='.0f', cmap='YlOrRd', ax=ax, cbar_kws={'label': 'Value'})
        
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
    
    def create_visual_summary(self, df: pd.DataFrame, query: str, sql: str) -> Dict:
        """
        Create a comprehensive visual summary with chart + metadata
        
        Returns dictionary with:
        - chart_path: Path to saved visualization
        - chart_type: Type of chart created
        - data_summary: Summary statistics
        """
        # Create visualization
        chart_path, chart_type = self.create_visualization(df, query)
        
        # Generate data summary
        summary = {
            'rows': len(df),
            'columns': len(df.columns),
            'column_names': df.columns.tolist()
        }
        
        # Add numeric column statistics
        numeric_cols = df.select_dtypes(include=['int64', 'float64', 'int32', 'float32']).columns
        if len(numeric_cols) > 0:
            summary['numeric_summary'] = {}
            for col in numeric_cols[:3]:  # First 3 numeric columns
                summary['numeric_summary'][col] = {
                    'min': float(df[col].min()),
                    'max': float(df[col].max()),
                    'mean': float(df[col].mean()),
                    'total': float(df[col].sum()) if df[col].dtype in ['int64', 'float64'] else None
                }
        
        return {
            'chart_path': chart_path,
            'chart_type': chart_type,
            'data_summary': summary
        }


if __name__ == "__main__":
    # Test visualization generator
    from database_utils import DatabaseManager
    
    print("="*70)
    print("Visualization Generator Test")
    print("="*70)
    
    db = DatabaseManager()
    db.connect()
    
    # Test query
    test_query = """
    SELECT TOP 10 
        p.EnglishProductName,
        SUM(fis.SalesAmount) as TotalSales
    FROM dbo.FactInternetSales fis
    JOIN dbo.DimProduct p ON fis.ProductKey = p.ProductKey
    GROUP BY p.EnglishProductName
    ORDER BY TotalSales DESC
    """
    
    df, error = db.execute_query(test_query)
    
    if not error:
        print(f"\n✓ Query executed: {len(df)} rows")
        print(df.head())
        
        # Create visualization
        viz_gen = VisualizationGenerator()
        result = viz_gen.create_visual_summary(
            df, 
            "Top 10 products by sales",
            test_query
        )
        
        print(f"\n✓ Visualization created:")
        print(f"  Chart type: {result['chart_type']}")
        print(f"  Chart path: {result['chart_path']}")
        print(f"  Data summary: {result['data_summary']}")
    
    db.disconnect()
