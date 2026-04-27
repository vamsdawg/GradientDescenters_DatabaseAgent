"""
Database utilities for connecting to AdventureWorksDW2025
"""
import pyodbc
import pandas as pd
from typing import Optional, List, Dict, Tuple
import os
from dotenv import load_dotenv

# Load .env file from the same directory as this script
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))


class DatabaseManager:
    """Manages connection and queries to AdventureWorksDW2025"""
    
    def __init__(self):
        self.server = os.getenv('DB_SERVER', 'localhost')
        self.database = os.getenv('DB_NAME', 'AdventureWorksDW2025')
        self.driver = os.getenv('DB_DRIVER', 'ODBC Driver 17 for SQL Server')
        self.username = os.getenv('DB_USER')
        self.password = os.getenv('DB_PASSWORD')
        self.connection = None
        
    def connect(self) -> bool:
        """Establish database connection using Windows Authentication"""
        try:
            if self.username and self.password:
                # Use SQL authentication (required for Azure SQL)
                connection_string = (
                    f"DRIVER={{{self.driver}}};"
                    f"SERVER={self.server};"
                    f"DATABASE={self.database};"
                    f"UID={self.username};"
                    f"PWD={self.password};"
                    "Encrypt=yes;"
                    "TrustServerCertificate=no;"
                    "Connection Timeout=30;"
                )
            else:
                # Fall back to Windows Authentication for local SQL Server
                connection_string = (
                    f"DRIVER={{{self.driver}}};"
                    f"SERVER={self.server};"
                    f"DATABASE={self.database};"
                    "Trusted_Connection=yes;"
                )
            self.connection = pyodbc.connect(connection_string)
            print(f"✓ Connected to {self.database}")
            return True
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            print("✓ Database connection closed")
    
    def execute_query(self, sql: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """
        Execute SQL query and return results as DataFrame
        Returns: (DataFrame or None, error_message or None)
        """
        try:
            if not self.connection:
                self.connect()
            
            df = pd.read_sql(sql, self.connection)
            return df, None
        except Exception as e:
            return None, str(e)
    
    def get_schema_info(self) -> pd.DataFrame:
        """Retrieve database schema information"""
        schema_query = """
        SELECT 
            t.TABLE_SCHEMA,
            t.TABLE_NAME,
            c.COLUMN_NAME,
            c.DATA_TYPE,
            c.IS_NULLABLE
        FROM INFORMATION_SCHEMA.TABLES t
        JOIN INFORMATION_SCHEMA.COLUMNS c 
            ON t.TABLE_NAME = c.TABLE_NAME 
            AND t.TABLE_SCHEMA = c.TABLE_SCHEMA
        WHERE t.TABLE_TYPE = 'BASE TABLE'
        ORDER BY t.TABLE_SCHEMA, t.TABLE_NAME, c.ORDINAL_POSITION
        """
        df, error = self.execute_query(schema_query)
        if error:
            print(f"Error fetching schema: {error}")
            return pd.DataFrame()
        return df
    
    def get_table_list(self) -> List[str]:
        """Get list of all tables in the database"""
        query = """
        SELECT TABLE_SCHEMA + '.' + TABLE_NAME as FullTableName
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_SCHEMA, TABLE_NAME
        """
        df, error = self.execute_query(query)
        if error:
            return []
        return df['FullTableName'].tolist()
    
    def get_sample_data(self, table_name: str, limit: int = 5) -> Optional[pd.DataFrame]:
        """Get sample rows from a table"""
        query = f"SELECT TOP {limit} * FROM {table_name}"
        df, error = self.execute_query(query)
        if error:
            print(f"Error fetching sample data from {table_name}: {error}")
            return None
        return df
    
    def validate_sql_syntax(self, sql: str) -> Tuple[bool, Optional[str]]:
        """
        Validate SQL without executing (using SET PARSEONLY)
        Returns: (is_valid, error_message)
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("SET PARSEONLY ON")
            cursor.execute(sql)
            cursor.execute("SET PARSEONLY OFF")
            cursor.close()
            return True, None
        except Exception as e:
            return False, str(e)


def get_schema_context() -> str:
    """
    Generate a compact schema description for LLM context
    """
    db = DatabaseManager()
    if not db.connect():
        return "Error: Could not connect to database"
    
    schema_df = db.get_schema_info()
    db.disconnect()
    
    if schema_df.empty:
        return "Error: Could not retrieve schema"
    
    # Group by table and format
    schema_text = "Database Schema (AdventureWorksDW2025):\n\n"
    
    for table in schema_df['TABLE_NAME'].unique():
        table_schema = schema_df[schema_df['TABLE_NAME'] == table]
        schema_name = table_schema['TABLE_SCHEMA'].iloc[0]
        
        schema_text += f"Table: {schema_name}.{table}\n"
        
        for _, row in table_schema.iterrows():
            nullable = "NULL" if row['IS_NULLABLE'] == 'YES' else "NOT NULL"
            schema_text += f"  - {row['COLUMN_NAME']} ({row['DATA_TYPE']}) {nullable}\n"
        
        schema_text += "\n"
    
    return schema_text


if __name__ == "__main__":
    # Test database connection
    db = DatabaseManager()
    if db.connect():
        print("\nAvailable tables:")
        tables = db.get_table_list()
        for table in tables[:10]:  # Show first 10
            print(f"  - {table}")
        
        print(f"\nTotal tables: {len(tables)}")
        
        # Test a simple query
        print("\nTesting query execution...")
        df, error = db.execute_query("SELECT TOP 5 * FROM dbo.DimProduct")
        if error:
            print(f"Error: {error}")
        else:
            print(f"Query returned {len(df)} rows")
            print(df.head())
        
        db.disconnect()
