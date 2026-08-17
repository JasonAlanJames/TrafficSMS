from sqlalchemy import create_engine, text

from app.core.config import settings

print(settings.DATABASE_SYNC_URL)

engine = create_engine(settings.DATABASE_SYNC_URL)

with engine.connect() as connection:
    print(connection.execute(text("SELECT current_user")).scalar())

print("SUCCESS")
