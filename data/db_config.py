import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_db_connection():
    """Create and return a database connection using env vars."""
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5430"),
        database=os.getenv("DB_NAME", "happy-machine"),
        user=os.getenv("DB_USER", "benny"),
        password=os.getenv("DB_PASSWORD", "nipa")
    )

def get_migration_db_connection():
    """Create and return a connection to the migration/secondary DB."""
    return psycopg2.connect(
        host=os.getenv("DB_MIGRATION_HOST", "localhost"),
        port=os.getenv("DB_MIGRATION_PORT", "5436"),
        database=os.getenv("DB_MIGRATION_NAME", "postgres"),
        user=os.getenv("DB_MIGRATION_USER", "postgres"),
        password=os.getenv("DB_MIGRATION_PASSWORD", "password")
    )

def get_source_db_connection():
    """Create and return a connection to the source DB for migration."""
    return psycopg2.connect(
        host=os.getenv("DB_SOURCE_HOST", "localhost"),
        port=os.getenv("DB_SOURCE_PORT", "5432"),
        database=os.getenv("DB_SOURCE_NAME", "postgres"),
        user=os.getenv("DB_SOURCE_USER", "postgres"),
        password=os.getenv("DB_SOURCE_PASSWORD", "password")
    )
