# import the sqlalchemy parts
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

engine = create_engine(os.environ["DATABASE_URL"])

# each instance of class SessionLocal is a database session (SessionLocal itself not)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# create a base class from which the db models and classes inherit from
Base = declarative_base()
