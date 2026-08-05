import sys
import os

# Add the app directory to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.db.session import engine
from sqlalchemy import text

def add_enum_value():
    try:
        with engine.connect() as conn:
            # PostgreSQL requires ALTER TYPE ADD VALUE to be executed outside of a transaction block
            conn.execution_options(isolation_level="AUTOCOMMIT").execute(text("ALTER TYPE questiontype ADD VALUE 'SINGLE_CHOICE'"))
            print("Successfully added SINGLE_CHOICE to questiontype enum")
    except Exception as e:
        print(f"Error (maybe it already exists?): {e}")

if __name__ == "__main__":
    add_enum_value()
