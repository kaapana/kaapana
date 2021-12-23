from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
import datetime
import os
#engine = create_engine('postgresql://postgres:1234@localhost:5432/postgres')
engine = create_engine(os.getenv("DATAMODEL_DATABASE"))
#for testing in memory db
#engine = create_engine('sqlite:////tmp/db.sqlite', echo=True)
# use session_factory() to get a new Session
#_SessionFactory = sessionmaker(bind=engine)
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))

Base = declarative_base()
Base.query = db_session.query_property()
from unittest import mock


 # https://docs.graphene-python.org/projects/sqlalchemy/en/latest/tutorial/

# engine = create_engine('sqlite:///database.sqlite3', convert_unicode=True)
# db_session = scoped_session(sessionmaker(autocommit=False,
#                                          autoflush=False,
#                                          bind=engine))
#
# Base = declarative_base()
# # We will need this for querying
# Base.query = db_session.query_property()


def add_to_session(node):
    db_session.add(node)

def add_and_commit_to_session(node):
    add_to_session(node)
    commit_to_db()
def commit_to_db():
    db_session.commit()

def refresh():
    db_session.flush()
    db_session.expire_all()

def init_db():
    # import all modules here that might define models so that
    # they will be registered properly on the metadata.  Otherwise
    # you will have to import them first before calling init_db()
    from .model_dicom import DicomPatient
    from datamodel.database.model import KaapanaNode
    #Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # Create the fixtures
    main_node = KaapanaNode(name='MainNode')
    db_session.add(main_node)

    # db_session.add(patient)
    # roy = Patient(name='Roy', birthday=datetime.date.fromisocalendar(1950, 22, 5))
    # db_session.add(roy)
    db_session.commit()


def session():
    return db_session
