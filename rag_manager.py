"""
RAG Manager for AdventureWorksDW Database Agent
Handles document processing, embeddings, vector storage, and retrieval
"""
import os
import json
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import chromadb
from chromadb.config import Settings
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class RAGManager:
    """Manages RAG pipeline: document loading, embedding, and retrieval"""
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        """Initialize RAG manager with vector database"""
        self.persist_directory = persist_directory
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Initialize ChromaDB with persistence
        self.chroma_client = chromadb.Client(Settings(
            persist_directory=persist_directory,
            anonymized_telemetry=False
        ))
        
        # Create or get collections
        self.collection_examples = self._get_or_create_collection("sql_examples")
        self.collection_patterns = self._get_or_create_collection("join_patterns")
        self.collection_schemas = self._get_or_create_collection("table_schemas")
        self.collection_business = self._get_or_create_collection("business_rules")
        
        print(f"✓ RAG Manager initialized with persist directory: {persist_directory}")
    
    def _get_or_create_collection(self, name: str):
        """Get existing or create new collection"""
        try:
            return self.chroma_client.get_collection(name=name)
        except:
            return self.chroma_client.create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"}  # Use cosine similarity
            )
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI"""
        response = self.openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    
    def load_sql_examples(self, examples_file: str) -> int:
        """Load SQL query examples from JSON file"""
        with open(examples_file, 'r', encoding='utf-8') as f:
            examples = json.load(f)
        
        documents = []
        embeddings = []
        metadatas = []
        ids = []
        
        for example in examples:
            # Create searchable document from natural language + context
            doc_text = f"""
            Question: {example['natural_language']}
            Category: {example['category']}
            Difficulty: {example['difficulty']}
            Tables: {', '.join(example['expected_tables'])}
            SQL Query: {example['sql']}
            """
            
            documents.append(doc_text.strip())
            embeddings.append(self.generate_embedding(example['natural_language']))
            metadatas.append({
                'type': 'sql_example',
                'category': example['category'],
                'difficulty': example['difficulty'],
                'fact_table': example['fact_table']
            })
            ids.append(f"example_{example['id']}")
        
        # Add to collection
        self.collection_examples.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        
        print(f"✓ Loaded {len(documents)} SQL examples")
        return len(documents)
    
    def load_join_patterns(self, patterns_dir: str) -> int:
        """Load join pattern documents"""
        pattern_files = Path(patterns_dir).glob("*.txt")
        
        documents = []
        embeddings = []
        metadatas = []
        ids = []
        
        for pattern_file in pattern_files:
            with open(pattern_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract pattern name from filename
            pattern_name = pattern_file.stem.replace('_', ' ').title()
            
            # Create embedding from first part (when to use + description)
            first_lines = '\n'.join(content.split('\n')[:20])  # First 20 lines for embedding
            
            documents.append(content)
            embeddings.append(self.generate_embedding(first_lines))
            metadatas.append({
                'type': 'join_pattern',
                'pattern_name': pattern_name
            })
            ids.append(f"pattern_{pattern_file.stem}")
        
        self.collection_patterns.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        
        print(f"✓ Loaded {len(documents)} join patterns")
        return len(documents)
    
    def load_table_schemas(self, schemas_dir: str) -> int:
        """Load table schema documents"""
        schema_files = Path(schemas_dir).glob("*.txt")
        
        documents = []
        embeddings = []
        metadatas = []
        ids = []
        
        for schema_file in schema_files:
            with open(schema_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            table_name = schema_file.stem
            
            # Create embedding from table description + key columns
            lines = content.split('\n')
            embedding_text = '\n'.join(lines[:30])  # First 30 lines
            
            documents.append(content)
            embeddings.append(self.generate_embedding(embedding_text))
            metadatas.append({
                'type': 'table_schema',
                'table_name': table_name,
                'table_type': 'fact' if table_name.startswith('Fact') else 'dimension'
            })
            ids.append(f"schema_{table_name}")
        
        self.collection_schemas.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        
        print(f"✓ Loaded {len(documents)} table schemas")
        return len(documents)
    
    def load_business_rules(self, business_dir: str) -> int:
        """Load business rules and glossary documents"""
        rule_files = Path(business_dir).glob("*.txt")
        
        documents = []
        embeddings = []
        metadatas = []
        ids = []
        
        for rule_file in rule_files:
            with open(rule_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            doc_type = rule_file.stem
            
            # For business rules, chunk into sections
            if doc_type == 'business_rules':
                sections = content.split('=' * 47)  # Split by section dividers
                for i, section in enumerate(sections):
                    if section.strip():
                        documents.append(section.strip())
                        embeddings.append(self.generate_embedding(section[:500]))  # First 500 chars
                        metadatas.append({
                            'type': 'business_rule',
                            'section': i
                        })
                        ids.append(f"rule_{i}")
            else:
                # Glossary or other files - add as single document
                documents.append(content)
                embeddings.append(self.generate_embedding(content[:500]))
                metadatas.append({
                    'type': doc_type
                })
                ids.append(f"business_{doc_type}")
        
        self.collection_business.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        
        print(f"✓ Loaded {len(documents)} business rule documents")
        return len(documents)
    
    def retrieve_similar_examples(self, query: str, k: int = 3) -> List[Dict]:
        """Retrieve k most similar SQL examples for a query"""
        query_embedding = self.generate_embedding(query)
        
        results = self.collection_examples.query(
            query_embeddings=[query_embedding],
            n_results=k
        )
        
        retrieved = []
        if results['documents'] and results['documents'][0]:
            for i in range(len(results['documents'][0])):
                retrieved.append({
                    'document': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if 'distances' in results else None
                })
        
        return retrieved
    
    def retrieve_relevant_patterns(self, query: str, k: int = 2) -> List[Dict]:
        """Retrieve relevant join patterns for a query"""
        query_embedding = self.generate_embedding(query)
        
        results = self.collection_patterns.query(
            query_embeddings=[query_embedding],
            n_results=k
        )
        
        retrieved = []
        if results['documents'] and results['documents'][0]:
            for i in range(len(results['documents'][0])):
                retrieved.append({
                    'document': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if 'distances' in results else None
                })
        
        return retrieved
    
    def retrieve_relevant_schemas(self, query: str, k: int = 5) -> List[Dict]:
        """Retrieve relevant table schemas for a query"""
        query_embedding = self.generate_embedding(query)
        
        results = self.collection_schemas.query(
            query_embeddings=[query_embedding],
            n_results=k
        )
        
        retrieved = []
        if results['documents'] and results['documents'][0]:
            for i in range(len(results['documents'][0])):
                retrieved.append({
                    'document': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if 'distances' in results else None
                })
        
        return retrieved
    
    def retrieve_business_rules(self, query: str, k: int = 2) -> List[Dict]:
        """Retrieve relevant business rules for a query"""
        query_embedding = self.generate_embedding(query)
        
        results = self.collection_business.query(
            query_embeddings=[query_embedding],
            n_results=k
        )
        
        retrieved = []
        if results['documents'] and results['documents'][0]:
            for i in range(len(results['documents'][0])):
                retrieved.append({
                    'document': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if 'distances' in results else None
                })
        
        return retrieved
    
    def retrieve_all_context(
        self, 
        query: str, 
        k_examples: int = 3,
        k_patterns: int = 2,
        k_schemas: int = 5,
        k_business: int = 2
    ) -> Dict[str, List[Dict]]:
        """Retrieve relevant context from all sources"""
        return {
            'examples': self.retrieve_similar_examples(query, k_examples),
            'patterns': self.retrieve_relevant_patterns(query, k_patterns),
            'schemas': self.retrieve_relevant_schemas(query, k_schemas),
            'business_rules': self.retrieve_business_rules(query, k_business)
        }
    
    def get_collection_stats(self) -> Dict[str, int]:
        """Get statistics about loaded collections"""
        return {
            'sql_examples': self.collection_examples.count(),
            'join_patterns': self.collection_patterns.count(),
            'table_schemas': self.collection_schemas.count(),
            'business_rules': self.collection_business.count(),
            'total': (
                self.collection_examples.count() +
                self.collection_patterns.count() +
                self.collection_schemas.count() +
                self.collection_business.count()
            )
        }


def initialize_rag_system(force_reload: bool = False) -> RAGManager:
    """Initialize RAG system by loading all documents"""
    
    project_dir = Path(__file__).parent
    rag_content_dir = project_dir / 'rag_content'
    
    # Initialize manager
    rag = RAGManager()
    
    # Check if already loaded
    stats = rag.get_collection_stats()
    if stats['total'] > 0 and not force_reload:
        print(f"✓ RAG system already loaded with {stats['total']} documents")
        print(f"  - SQL Examples: {stats['sql_examples']}")
        print(f"  - Join Patterns: {stats['join_patterns']}")
        print(f"  - Table Schemas: {stats['table_schemas']}")
        print(f"  - Business Rules: {stats['business_rules']}")
        return rag
    
    print("Loading documents into RAG system...")
    print("=" * 70)
    
    # Load all content
    examples_file = rag_content_dir / 'examples' / 'test_cases_with_sql.json'
    patterns_dir = rag_content_dir / 'patterns'
    schemas_dir = rag_content_dir / 'schemas'
    business_dir = rag_content_dir / 'business_rules'
    
    rag.load_sql_examples(str(examples_file))
    rag.load_join_patterns(str(patterns_dir))
    rag.load_table_schemas(str(schemas_dir))
    rag.load_business_rules(str(business_dir))
    
    print("=" * 70)
    print("✓ RAG system fully initialized!")
    
    stats = rag.get_collection_stats()
    print(f"✓ Total documents loaded: {stats['total']}")
    print(f"  - SQL Examples: {stats['sql_examples']}")
    print(f"  - Join Patterns: {stats['join_patterns']}")
    print(f"  - Table Schemas: {stats['table_schemas']}")
    print(f"  - Business Rules: {stats['business_rules']}")
    
    return rag


if __name__ == "__main__":
    # Test RAG system
    print("Testing RAG System")
    print("=" * 70)
    
    rag = initialize_rag_system(force_reload=True)
    
    # Test retrieval
    print("\n" + "=" * 70)
    print("Testing retrieval with sample query...")
    print("=" * 70)
    
    test_query = "Show me total sales by product category"
    print(f"\nQuery: '{test_query}'\n")
    
    context = rag.retrieve_all_context(test_query, k_examples=2, k_patterns=1, k_schemas=3, k_business=1)
    
    print(f"Retrieved Examples: {len(context['examples'])}")
    for i, ex in enumerate(context['examples'], 1):
        print(f"  {i}. {ex['metadata']['category']} - Distance: {ex['distance']:.4f}")
    
    print(f"\nRetrieved Patterns: {len(context['patterns'])}")
    for i, pat in enumerate(context['patterns'], 1):
        print(f"  {i}. {pat['metadata']['pattern_name']} - Distance: {pat['distance']:.4f}")
    
    print(f"\nRetrieved Schemas: {len(context['schemas'])}")
    for i, schema in enumerate(context['schemas'], 1):
        print(f"  {i}. {schema['metadata']['table_name']} - Distance: {schema['distance']:.4f}")
    
    print("\n" + "=" * 70)
    print("✓ RAG system test complete!")
