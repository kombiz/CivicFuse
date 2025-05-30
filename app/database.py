"""Database connection and management."""
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool
from contextlib import contextmanager
from typing import Any, Dict, List, Optional
import logging
from app.config import settings

logger = logging.getLogger(__name__)

class DatabasePool:
    """Manages PostgreSQL connection pool."""
    
    def __init__(self):
        self.pool = None
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialize the connection pool."""
        try:
            self.pool = SimpleConnectionPool(
                1,  # minconn
                settings.db_pool_size,  # maxconn
                settings.database_url,
                cursor_factory=RealDictCursor
            )
            logger.info("Database connection pool initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """Get a connection from the pool."""
        conn = self.pool.getconn()
        try:
            yield conn
        finally:
            self.pool.putconn(conn)
    
    def close_all(self):
        """Close all connections in the pool."""
        if self.pool:
            self.pool.closeall()

# Global database pool instance
db_pool = DatabasePool()

@contextmanager
def get_db_connection():
    """Get database connection from pool."""
    with db_pool.get_connection() as conn:
        yield conn

@contextmanager
def get_db_cursor(commit: bool = True):
    """Get database cursor with automatic commit/rollback."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            yield cursor
            if commit:
                conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database operation failed: {e}")
            raise
        finally:
            cursor.close()

def execute_query(
    query: str, 
    params: Optional[tuple] = None, 
    fetch_one: bool = False
) -> Optional[Any]:
    """Execute a query and return results."""
    with get_db_cursor() as cursor:
        cursor.execute(query, params)
        if cursor.description:  # Query returns data
            return cursor.fetchone() if fetch_one else cursor.fetchall()
        return None

def execute_many(query: str, params_list: List[tuple]) -> None:
    """Execute a query with multiple parameter sets."""
    with get_db_cursor() as cursor:
        cursor.executemany(query, params_list)

def test_connection() -> bool:
    """Test database connectivity and schema existence."""
    try:
        # Test basic connection
        result = execute_query("SELECT 1 as test", fetch_one=True)
        if not result or result['test'] != 1:
            raise Exception("Basic connectivity test failed")
        
        # Check if schema exists
        schema_check = execute_query(
            "SELECT COUNT(*) as count FROM information_schema.schemata WHERE schema_name = 'cms_core'",
            fetch_one=True
        )
        
        if schema_check['count'] == 0:
            logger.warning("Schema cms_core does not exist")
            return False
        
        # Check required tables
        tables_check = execute_query("""
            SELECT COUNT(*) as count 
            FROM information_schema.tables 
            WHERE table_schema = 'cms_core' 
            AND table_name IN ('contacts', 'groups', 'contact_group_memberships', 
                               'social_profiles', 'shared_content_log')
        """, fetch_one=True)
        
        if tables_check['count'] < 5:
            logger.warning(f"Missing tables in cms_core schema (found {tables_check['count']}/5)")
            return False
        
        logger.info("✓ Database connection successful and schema verified")
        return True
        
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False

def init_database() -> None:
    """Initialize database schema if it doesn't exist."""
    try:
        with open('scripts/create_schema.sql', 'r') as f:
            schema_sql = f.read()
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(schema_sql)
            conn.commit()
            cursor.close()
        
        logger.info("Database schema initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database schema: {e}")
        raise

# Health check query
def health_check() -> Dict[str, Any]:
    """Perform database health check."""
    try:
        # Check connection
        result = execute_query("SELECT version()", fetch_one=True)
        pg_version = result['version'] if result else "Unknown"
        
        # Check schema
        schema_exists = execute_query(
            "SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name = 'cms_core')",
            fetch_one=True
        )
        
        # Count records
        counts = {}
        if schema_exists and schema_exists['exists']:
            for table in ['contacts', 'groups', 'social_profiles', 'shared_content_log']:
                count_result = execute_query(
                    f"SELECT COUNT(*) as count FROM cms_core.{table}",
                    fetch_one=True
                )
                counts[table] = count_result['count'] if count_result else 0
        
        return {
            "status": "healthy",
            "postgres_version": pg_version,
            "schema_exists": schema_exists['exists'] if schema_exists else False,
            "record_counts": counts,
            "pool_size": settings.db_pool_size
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

if __name__ == "__main__":
    # Test database connection when run directly
    import sys
    if test_connection():
        print("Database connection test passed!")
        health = health_check()
        print(f"Health check: {health}")
        sys.exit(0)
    else:
        print("Database connection test failed!")
        sys.exit(1)