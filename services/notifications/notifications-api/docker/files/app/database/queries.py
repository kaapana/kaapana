from app.database.connections import engine
from sqlalchemy import text
from sqlalchemy.exc import OperationalError


async def verify_postgres_conn(debug_outputs=False):
    try:
        with engine.connect() as connection:
            available_db = connection.execute(
                text("SELECT datname FROM pg_database;")
            ).fetchall()
            if debug_outputs:
                print(available_db)
        return True, ""
    except OperationalError as e:
        return False, str(e)
