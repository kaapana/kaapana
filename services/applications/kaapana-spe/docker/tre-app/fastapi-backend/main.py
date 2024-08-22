from fastapi import FastAPI, HTTPException
from fastapi import Depends, status
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import Column, Integer, String
# from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, Enum
# from app.db.environments_db import BaseEnvironments
import enum
# from app.db.requests_db import BaseRequests
from typing import Optional

app = FastAPI()


origins = [
    "http://localhost:3000",  # Your Vue.js frontend during development
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allow these origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Database 1: Requests (Assume you have this from the earlier example)
DATABASE_URL_REQUESTS = "sqlite:///./requests.db"

# Database 2: TRE Environments
DATABASE_URL_ENVIRONMENTS = "sqlite:///./environments.db"

# Database 3: Projects
DATABASE_URL_PROJECTS = "sqlite:///./projects.db"

# SQLAlchemy setup for Requests Database
engine_requests = create_engine(DATABASE_URL_REQUESTS)
SessionLocalRequests = sessionmaker(autocommit=False, autoflush=False, bind=engine_requests)
BaseRequests = declarative_base()

# SQLAlchemy setup for TRE Environments Database
engine_environments = create_engine(DATABASE_URL_ENVIRONMENTS)
SessionLocalEnvironments = sessionmaker(autocommit=False, autoflush=False, bind=engine_environments)
BaseEnvironments = declarative_base()

# SQLAlchemy setup for Projects Database
engine_projects = create_engine(DATABASE_URL_PROJECTS)
SessionLocalProjects = sessionmaker(autocommit=False, autoflush=False, bind=engine_projects)
BaseProjects = declarative_base()

# Model for the Requests table


class Request(BaseRequests):
    __tablename__ = "requests"

    id = Column(Integer, primary_key=True, index=True)
    user = Column(String, index=True)
    project = Column(String, index=True)
    memory = Column(Integer)
    storage = Column(Integer)
    gpu = Column(String)
    environment_id = Column(Integer, nullable=True)

# Enum for status field
class StatusEnum(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    denied = "denied"

class Environment(BaseEnvironments):
    __tablename__ = "environments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)
    memory = Column(Integer)
    storage = Column(Integer)
    gpu = Column(String)
    owner = Column(String, index=True)
    user = Column(String, index=True)
    status = Column(Enum(StatusEnum), default=StatusEnum.pending, index=True)
    project = Column(String)



class Project(BaseProjects):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    owner = Column(String, index=True)



# Create the tables
BaseRequests.metadata.create_all(bind=engine_requests)
BaseEnvironments.metadata.create_all(bind=engine_environments)
BaseProjects.metadata.create_all(bind=engine_projects)


# Pydantic schemas

# Enum for status field
class StatusEnum(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    denied = "denied"

class EnvironmentCreate(BaseModel):
    name: str
    description: str
    memory: int
    storage: int
    gpu: str
    owner: str
    user: str
    status: Optional[StatusEnum] = StatusEnum.pending  # Default to 'pending'
    project: str

class EnvironmentResponse(EnvironmentCreate):
    id: int

    class Config:
        from_attributes = True  # Use `from_attributes` instead of `orm_mode`


# Note that request means user-requests for new TRE's but not http requests here
class RequestCreate(BaseModel):
    user: str
    project: str
    memory: int
    storage: int
    gpu: str
    environment_id: Optional[int] = None  # Optional integer field

class RequestResponse(RequestCreate):
    id: int

    class Config:
        from_attributes = True 

class ProjectCreate(BaseModel):
    name: str
    owner: str

class ProjectResponse(ProjectCreate):
    id: int

    class Config:
        from_attributes = True 


class RequestEnvironmentCreate(BaseModel):
    user: str
    project: str
    memory: int
    storage: int
    gpu: str
    name: str
    description: str
    owner: str

class RequestEnvironmentResponse(BaseModel):
    request_id: int
    environment_id: int
    status: StatusEnum

    class Config:
        from_attributes = True  # Use `from_attributes`



# Dependency for Requests DB
def get_db_requests():
    db = SessionLocalRequests()
    try:
        yield db
    finally:
        db.close()

# Dependency for Environments DB
def get_db_environments():
    db = SessionLocalEnvironments()
    try:
        yield db
    finally:
        db.close()

# Dependency for Projects DB
def get_db_projects():
    db = SessionLocalProjects()
    try:
        yield db
    finally:
        db.close()

# CRUD finctions for database interaction
def get_projects(db: Session, skip: int = 0, limit: int = 10):
    return db.query(Project).offset(skip).limit(limit).all()

def create_project(db: Session, project: ProjectCreate):
    db_project = Project(**project.dict())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

def get_project(db: Session, project_id: int):
    return db.query(Project).filter(Project.id == project_id).first()

def delete_project(db: Session, project_id: int):
    db_project = get_project(db, project_id)
    if db_project:
        db.delete(db_project)
        db.commit()
    return db_project

def create_request_environment(req_env: RequestEnvironmentCreate):
    # Session for Requests DB
    db_requests = SessionLocalRequests()
    
    # Session for Environments DB
    db_environments = SessionLocalEnvironments()

    try:
        # Create the Environment
        db_environment = Environment(
            name=req_env.name,
            project=req_env.project,
            description=req_env.description,
            memory=req_env.memory,
            storage=req_env.storage,
            gpu=req_env.gpu,
            owner=req_env.owner,
            user=req_env.user,
            status=StatusEnum.pending
        )
        db_environments.add(db_environment)
        db_environments.commit()
        db_environments.refresh(db_environment)

        # Create the Request with a reference to the environment
        db_request = Request(
            user=req_env.user,
            project=req_env.project,
            memory=req_env.memory,
            storage=req_env.storage,
            gpu=req_env.gpu,
            environment_id=db_environment.id
        )
        db_requests.add(db_request)
        db_requests.commit()
        db_requests.refresh(db_request)

        return db_request, db_environment

    except Exception as e:
        db_requests.rollback()
        db_environments.rollback()
        raise e
    finally:
        db_requests.close()
        db_environments.close()

def answer_request(db_requests: Session, db_environments: Session, request_id: int, is_accepted: bool):
    # Retrieve the request by ID from the Requests database
    db_request = db_requests.query(Request).filter(Request.id == request_id).first()
    if not db_request:
        return None, None

    # Retrieve the associated environment by environment_id from the Environments database
    db_environment = db_environments.query(Environment).filter(Environment.id == db_request.environment_id).first()
    if not db_environment:
        return None, None

    # Update the environment status based on the boolean value
    if is_accepted:
        db_environment.status = StatusEnum.accepted
    else:
        db_environment.status = StatusEnum.denied

    db_environments.commit()

    # Delete the request from the Requests database
    db_requests.delete(db_request)
    db_requests.commit()

    return db_environment, db_request

def get_requests(db: Session, skip: int = 0, limit: int = 10):
    return db.query(Request).offset(skip).limit(limit).all()

def create_request(db: Session, request: RequestCreate):
    db_request = Request(**request.dict())
    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    return db_request

def get_request(db: Session, request_id: int):
    return db.query(Request).filter(Request.id == request_id).first()

def delete_request(db: Session, request_id: int):
    db_request = get_request(db, request_id)
    if db_request:
        db.delete(db_request)
        db.commit()
    return db_request

# Basic CRUD API endpoints. 
@app.post("/api/environments/", response_model=EnvironmentResponse, status_code=status.HTTP_201_CREATED)
async def create_environment(environment: EnvironmentCreate, db: Session = Depends(get_db_environments)):
    db_environment = Environment(**environment.dict())
    db.add(db_environment)
    db.commit()
    db.refresh(db_environment)
    return db_environment

@app.get("/api/environments/", response_model=list[EnvironmentResponse])
async def read_environments(skip: int = 0, limit: int = 10, db: Session = Depends(get_db_environments)):
    environments = db.query(Environment).offset(skip).limit(limit).all()
    return environments

@app.get("/api/environments/{environment_id}", response_model=EnvironmentResponse)
async def read_environment(environment_id: int, db: Session = Depends(get_db_environments)):
    environment = db.query(Environment).filter(Environment.id == environment_id).first()
    if environment is None:
        raise HTTPException(status_code=404, detail="Environment not found")
    return environment

@app.delete("/api/environments/{environment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_environment(environment_id: int, db: Session = Depends(get_db_environments)):
    environment = db.query(Environment).filter(Environment.id == environment_id).first()
    if environment is None:
        raise HTTPException(status_code=404, detail="Environment not found")
    db.delete(environment)
    db.commit()
    return {"message": "Environment deleted successfully"}


@app.get("/api/projects", response_model=list[ProjectResponse])
async def read_projects(skip: int = 0, limit: int = 10, db: Session = Depends(get_db_projects)):
    projects = get_projects(db)
    return projects

@app.get("/api/requests", response_model=list[RequestResponse])
async def read_requests(skip: int = 0, limit: int = 10, db: Session = Depends(get_db_requests)):
    requests = db.query(Request).offset(skip).limit(limit).all()
    return requests

@app.post("/api/requests", response_model=RequestResponse)
async def create_request(request: RequestCreate, db: Session = Depends(get_db_requests)):
    db_request = Request(**request.dict())
    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    return db_request

# Actual transaction endpoints
@app.post("/request-new-environment", response_model=RequestEnvironmentResponse)
async def request_new_environment(req_env: RequestEnvironmentCreate, db: Session = Depends(get_db_requests)):
    db_request, db_environment = create_request_environment(req_env=req_env)
    return RequestEnvironmentResponse(
        request_id=db_request.id,
        environment_id=db_environment.id,
        status=db_environment.status
    )

@app.post("/api/answer-request", response_model=EnvironmentResponse)
async def answer_request_endpoint(
    request_id: int,
    is_accepted: bool,
    db_requests: Session = Depends(get_db_requests),
    db_environments: Session = Depends(get_db_environments)
):
    db_environment, db_request = answer_request(
        db_requests=db_requests,
        db_environments=db_environments,
        request_id=request_id,
        is_accepted=is_accepted
    )
    
    if not db_request:
        raise HTTPException(status_code=404, detail="Request not found")
        
    if not db_environment:
        raise HTTPException(status_code=404, detail="Associated environment not found")

    return db_environment
