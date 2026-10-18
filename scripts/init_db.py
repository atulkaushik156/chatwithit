import os
import sys
import psycopg
from dotenv import load_dotenv
from langgraph.checkpoint.postgres import PostgresSaver

load_dotenv()

def run_migrations():
    db_uri = os.getenv("DATABASE_URL")
    if not db_uri:
        print("❌ ERROR: DATABASE_URL environment variable is missing.")
        sys.exit(1)

    print("⏳ Connecting to Neon Postgres to run migrations...")
    try:
        # autocommit=True is required by PostgresSaver.setup()
        with psycopg.connect(db_uri, autocommit=True) as conn:
            # 1. Create LangGraph's internal state persistence tables
            checkpointer = PostgresSaver(conn)
            checkpointer.setup()
            print("✅ LangGraph checkpoint tables verified/created.")

            # 2. Create custom table mapping user_ids to thread_ids
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_threads (
                    thread_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_threads_user_id 
                ON user_threads(user_id);
            """)
            print("✅ 'user_threads' table and indexes verified/created.")

        print("🚀 Database initialization complete!")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migrations()