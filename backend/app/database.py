from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import settings

class Base(DeclarativeBase):
    pass

engine = create_engine(settings.database_url, pool_pre_ping=True)
Session = sessionmaker(engine, expire_on_commit=False)

def get_db():
    with Session() as db:
        with db.begin():
            yield db
