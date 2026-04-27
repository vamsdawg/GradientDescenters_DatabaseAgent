"""
Generate schema documentation for RAG content
Extracts table schemas from database and creates formatted text files
"""
import sys
from pathlib import Path
_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT / '_prod'))
sys.path.insert(0, str(Path(__file__).parent))

from database_utils import DatabaseManager
import os

# Key tables to document (most important for RAG)
KEY_TABLES = [
    'dbo.FactInternetSales',
    'dbo.FactResellerSales',
    'dbo.FactProductInventory',
    'dbo.FactSalesQuota',
    'dbo.DimProduct',
    'dbo.DimCustomer',
    'dbo.DimDate',
    'dbo.DimGeography',
    'dbo.DimProductCategory',
    'dbo.DimProductSubcategory',
    'dbo.DimSalesTerritory',
    'dbo.DimReseller',
    'dbo.DimEmployee',
    'dbo.DimPromotion',
]

# Table descriptions from AdventureWorksDW documentation
TABLE_DESCRIPTIONS = {
    'FactInternetSales': 'Online/internet sales transactions (B2C). Each row represents one line item from a customer order. Primary fact table for direct-to-consumer sales analysis.',
    'FactResellerSales': 'Wholesale/reseller sales transactions (B2B). Each row represents one line item sold to business resellers who then sell to end consumers.',
    'FactProductInventory': 'Product inventory levels over time. Tracks stock quantities at different points in time. Used for inventory analysis and stock management.',
    'FactSalesQuota': 'Sales targets assigned to sales employees by time period. Contains quota amounts by employee and date. Considered confidential data.',
    'DimProduct': 'Product master dimension. Contains all product details including name, category, color, size, cost, and price information.',
    'DimCustomer': 'Customer master dimension. Stores customer demographic and profile information. Links to DimGeography for location.',
    'DimDate': 'Date dimension with calendar and fiscal date attributes. Essential for all time-based analysis. Pre-populated with dates.',
    'DimGeography': 'Geographic location dimension containing countries, states/provinces, and cities. Used for customer and reseller locations.',
    'DimProductCategory': 'Top-level product categories (Bikes, Accessories, Clothing, Components). Part of product hierarchy.',
    'DimProductSubcategory': 'Mid-level product groupings under categories (e.g., Mountain Bikes, Road Bikes, Helmets). Links categories to products.',
    'DimSalesTerritory': 'Sales territory dimension defining geographic sales regions. Different from customer location - represents assigned sales area.',
    'DimReseller': 'Reseller/wholesale customer master. Contains business customer information including business type and size.',
    'DimEmployee': 'Employee master dimension. Contains employee profile information. Links to sales and organizational hierarchies.',
    'DimPromotion': 'Marketing promotion dimension. Tracks promotional campaigns and discount programs applied to sales.',
}


def get_foreign_keys(db: DatabaseManager):
    """Get foreign key relationships"""
    query = """
    SELECT 
        OBJECT_SCHEMA_NAME(fk.parent_object_id) + '.' + OBJECT_NAME(fk.parent_object_id) AS ParentTable,
        COL_NAME(fkc.parent_object_id, fkc.parent_column_id) AS ParentColumn,
        OBJECT_SCHEMA_NAME(fk.referenced_object_id) + '.' + OBJECT_NAME(fk.referenced_object_id) AS ReferencedTable,
        COL_NAME(fkc.referenced_object_id, fkc.referenced_column_id) AS ReferencedColumn
    FROM sys.foreign_keys AS fk
    INNER JOIN sys.foreign_key_columns AS fkc 
        ON fk.object_id = fkc.constraint_object_id
    ORDER BY ParentTable, ParentColumn
    """
    df, error = db.execute_query(query)
    if error:
        print(f"Error fetching foreign keys: {error}")
        return {}
    
    # Group by table
    fk_dict = {}
    for _, row in df.iterrows():
        table = row['ParentTable']
        if table not in fk_dict:
            fk_dict[table] = []
        fk_dict[table].append({
            'column': row['ParentColumn'],
            'references': f"{row['ReferencedTable']}.{row['ReferencedColumn']}"
        })
    
    return fk_dict


def generate_table_doc(db: DatabaseManager, table_name: str, fk_dict: dict, output_dir: str):
    """Generate documentation for a single table"""
    
    # Get schema info
    schema_query = f"""
    SELECT 
        c.COLUMN_NAME,
        c.DATA_TYPE,
        c.CHARACTER_MAXIMUM_LENGTH,
        c.IS_NULLABLE,
        CASE 
            WHEN pk.COLUMN_NAME IS NOT NULL THEN 'YES'
            ELSE 'NO'
        END AS IS_PRIMARY_KEY
    FROM INFORMATION_SCHEMA.COLUMNS c
    LEFT JOIN (
        SELECT ku.TABLE_SCHEMA, ku.TABLE_NAME, ku.COLUMN_NAME
        FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS AS tc
        INNER JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE AS ku
            ON tc.CONSTRAINT_TYPE = 'PRIMARY KEY' 
            AND tc.CONSTRAINT_NAME = ku.CONSTRAINT_NAME
    ) pk ON c.TABLE_SCHEMA = pk.TABLE_SCHEMA 
        AND c.TABLE_NAME = pk.TABLE_NAME 
        AND c.COLUMN_NAME = pk.COLUMN_NAME
    WHERE c.TABLE_SCHEMA + '.' + c.TABLE_NAME = '{table_name}'
    ORDER BY c.ORDINAL_POSITION
    """
    
    df, error = db.execute_query(schema_query)
    if error:
        print(f"Error fetching schema for {table_name}: {error}")
        return
    
    # Get sample data (skip for now to avoid encoding issues)
    sample_df = None  # Will get minimal samples using safer method
    
    # Build documentation
    table_short_name = table_name.split('.')[-1]
    description = TABLE_DESCRIPTIONS.get(table_short_name, 'No description available')
    
    doc = f"TABLE: {table_name}\n"
    doc += "=" * 70 + "\n\n"
    doc += f"DESCRIPTION:\n{description}\n\n"
    doc += f"TYPE: {'Fact Table' if table_short_name.startswith('Fact') else 'Dimension Table'}\n\n"
    doc += "=" * 70 + "\n"
    doc += "COLUMNS:\n"
    doc += "=" * 70 + "\n\n"
    
    # Document each column
    for _, row in df.iterrows():
        col_name = row['COLUMN_NAME']
        data_type = row['DATA_TYPE']
        
        # Add length for string types
        if row['CHARACTER_MAXIMUM_LENGTH'] and row['CHARACTER_MAXIMUM_LENGTH'] > 0:
            data_type += f"({row['CHARACTER_MAXIMUM_LENGTH']})"
        
        nullable = "NULL" if row['IS_NULLABLE'] == 'YES' else "NOT NULL"
        pk = " [PRIMARY KEY]" if row['IS_PRIMARY_KEY'] == 'YES' else ""
        
        # Check if foreign key
        fk_info = ""
        if table_name in fk_dict:
            for fk in fk_dict[table_name]:
                if fk['column'] == col_name:
                    fk_info = f" [FK → {fk['references']}]"
                    break
        
        doc += f"{col_name}\n"
        doc += f"  Type: {data_type} {nullable}{pk}{fk_info}\n"
        
        # Try to get sample values (safely handle encoding issues)
        try:
            if data_type.startswith(('int', 'bigint', 'smallint', 'tinyint', 'decimal', 'numeric', 'money', 'bit')):
                # Numeric columns - safe to sample
                sample_query = f"SELECT TOP 3 DISTINCT [{col_name}] FROM {table_name} WHERE [{col_name}] IS NOT NULL"
                sample_result, sample_error = db.execute_query(sample_query)
                if not sample_error and sample_result is not None and len(sample_result) > 0:
                    samples = ", ".join([str(v) for v in sample_result[col_name].tolist()[:3]])
                    doc += f"  Sample: {samples}\n"
            elif col_name.lower().endswith(('key', 'id')):
                # ID/Key columns - show just structure
                doc += f"  Sample: (numeric keys)\n"
            elif data_type.startswith(('nvarchar', 'varchar', 'nchar', 'char')):
                # String columns - try but handle encoding errors
                sample_query = f"SELECT TOP 3 DISTINCT [{col_name}] FROM {table_name} WHERE [{col_name}] IS NOT NULL AND LEN([{col_name}]) > 0"
                try:
                    sample_result, sample_error = db.execute_query(sample_query)
                    if not sample_error and sample_result is not None and len(sample_result) > 0:
                        sample_vals = []
                        for val in sample_result[col_name].tolist()[:3]:
                            try:
                                # Try to encode/decode safely
                                safe_val = str(val).encode('ascii', 'replace').decode('ascii')[:30]
                                sample_vals.append(f"'{safe_val}...'")
                            except:
                                sample_vals.append("'<text>'")
                        if sample_vals:
                            samples = ", ".join(sample_vals)
                            doc += f"  Sample: {samples}\n"
                except:
                    doc += f"  Sample: (text values)\n"
        except Exception as e:
            # Skip sample if any error
            pass
        
        doc += "\n"
    
    # Add foreign key summary
    if table_name in fk_dict and fk_dict[table_name]:
        doc += "=" * 70 + "\n"
        doc += "FOREIGN KEY RELATIONSHIPS:\n"
        doc += "=" * 70 + "\n\n"
        for fk in fk_dict[table_name]:
            doc += f"  {fk['column']} → {fk['references']}\n"
        doc += "\n"
    
    # Add common usage notes
    doc += "=" * 70 + "\n"
    doc += "USAGE NOTES:\n"
    doc += "=" * 70 + "\n\n"
    
    # Add table-specific notes
    if table_short_name == 'FactInternetSales':
        doc += "- Primary fact table for internet/online sales analysis\n"
        doc += "- Join to DimProduct, DimCustomer, DimDate for complete analysis\n"
        doc += "- OrderDateKey is primary date for sales (not ShipDateKey)\n"
        doc += "- SalesAmount includes tax and freight\n"
        doc += "- Use DISTINCT on SalesOrderNumber for order counting\n"
    elif table_short_name == 'DimProduct':
        doc += "- Use EnglishProductName for display purposes\n"
        doc += "- Filter by FinishedGoodsFlag = 1 for saleable products\n"
        doc += "- Links to subcategory/category through ProductSubcategoryKey\n"
        doc += "- ListPrice is MSRP, StandardCost is manufacturing cost\n"
    elif table_short_name == 'DimCustomer':
        doc += "- NEVER include EmailAddress, Phone, AddressLine* (confidential)\n"
        doc += "- Join to DimGeography for location information\n"
        doc += "- YearlyIncome useful for customer segmentation\n"
        doc += "- Use FirstName + ' ' + LastName for full name\n"
    elif table_short_name == 'DimDate':
        doc += "- Essential for all time-based analysis\n"
        doc += "- Contains calendar and fiscal date attributes\n"
        doc += "- Use OrderDateKey from fact tables to join\n"
        doc += "- CalendarYear, CalendarQuarter for grouping\n"
        doc += "- Data range typically 2010-2014\n"
    
    doc += "\n"
    doc += "=" * 70 + "\n"
    doc += f"END OF {table_name} DOCUMENTATION\n"
    doc += "=" * 70 + "\n"
    
    # Write to file with error handling
    filename = f"{table_short_name}.txt"
    filepath = os.path.join(output_dir, filename)
    
    try:
        with open(filepath, 'w', encoding='utf-8', errors='replace') as f:
            f.write(doc)
        print(f"✓ Generated documentation for {table_name}")
    except Exception as e:
        # Try with ASCII if UTF-8 fails
        try:
            with open(filepath, 'w', encoding='ascii', errors='replace') as f:
                f.write(doc)
            print(f"✓ Generated documentation for {table_name} (ASCII fallback)")
        except Exception as e2:
            print(f"✗ Failed to write documentation for {table_name}: {e2}")


def main():
    """Generate schema documentation for all key tables"""
    
    print("Generating schema documentation for RAG content...")
    print("=" * 70)
    
    # Setup
    db = DatabaseManager()
    if not db.connect():
        print("Failed to connect to database")
        return
    
    output_dir = os.path.join(os.path.dirname(__file__), 'rag_content', 'schemas')
    os.makedirs(output_dir, exist_ok=True)
    
    # Get foreign key relationships
    print("\nFetching foreign key relationships...")
    fk_dict = get_foreign_keys(db)
    print(f"✓ Found foreign keys for {len(fk_dict)} tables")
    
    # Generate documentation for each key table
    print(f"\nGenerating documentation for {len(KEY_TABLES)} key tables...")
    print("=" * 70)
    
    for table in KEY_TABLES:
        try:
            generate_table_doc(db, table, fk_dict, output_dir)
        except Exception as e:
            print(f"✗ Error generating doc for {table}: {e}")
    
    db.disconnect()
    
    print("\n" + "=" * 70)
    print(f"✓ Schema documentation complete!")
    print(f"✓ Files saved to: {output_dir}")
    print("=" * 70)


if __name__ == "__main__":
    main()
