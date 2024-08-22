import sqlalchemy as sa
from main import SessionLocalRequests, engine_requests, BaseRequests
from main  import SessionLocalEnvironments, engine_environments, BaseEnvironments
from main  import SessionLocalProjects, engine_projects, BaseProjects
from main  import Request
from main  import Environment
from main  import Project

# Create tables if they don't exist
BaseRequests.metadata.create_all(bind=engine_requests)
BaseEnvironments.metadata.create_all(bind=engine_environments)
BaseProjects.metadata.create_all(bind=engine_projects)

# Example data for environments
environments_data = [
    {"name": "Development Environment", "project": "Project Gamma", "description": "Environment for development purposes.", "memory": 16, "storage": 256, "gpu": "yes", "owner": "owner1", "user": "user1", "status": "pending"},
    {"name": "Staging Environment", "project": "Project Alpha", "description": "Environment for staging purposes.", "memory": 32, "storage": 512, "gpu": "yes", "owner": "owner2", "user": "user2", "status": "pending"},
    {"name": "Production Environment", "project": "Project Beta", "description": "Live production environment.", "memory": 64, "storage": 1024, "gpu": "no", "owner": "owner3", "user": "user3", "status": "pending"},
    {"name": "Data Cleaning Environment", "project": "UKHD Data Analysis", "description": "Selecting valid data for analysis.", "memory": 64, "storage": 1024, "gpu": "no", "owner": "owner3", "user": "user3", "status": "accepted"},
    {"name": "nnUnet training Experiments", "project": "RACCOON pre study data comparison", "description": "Experiments with nnUnet training", "memory": 64, "storage": 1024, "gpu": "no", "owner": "owner3", "user": "user3", "status": "denied"}

]

# Example data for projects
projects_data = [
    {"name": "Project Alpha", "owner": "user1"},
    {"name": "Project Beta", "owner": "user2"},
    {"name": "Project Gamma", "owner": "user3"}
]

def populate_environments():
    db = SessionLocalEnvironments()
    try:
        # Clear the existing data
        db.query(Environment).delete()

        # Insert new environments and return their IDs
        environment_ids = []
        for data in environments_data:
            db_environment = Environment(**data)
            db.add(db_environment)
            db.commit()
            db.refresh(db_environment)
            environment_ids.append(db_environment.id)
        return environment_ids
    finally:
        db.close()

def populate_projects():
    db = SessionLocalProjects()
    try:
        # Clear the existing data
        db.query(Project).delete()

        # Insert new projects
        for data in projects_data:
            db_project = Project(**data)
            db.add(db_project)
        db.commit()
    finally:
        db.close()

def populate_requests(environment_ids):
    db = SessionLocalRequests()
    try:
        # Clear the existing data
        db.query(Request).delete()

        # Example data for requests, using the environment IDs
        requests_data = [
            {"user": "user1", "project": "Project Alpha", "memory": 16, "storage": 256, "gpu": "yes", "environment_id": environment_ids[0]},
            {"user": "user2", "project": "Project Beta", "memory": 32, "storage": 512, "gpu": "yes", "environment_id": environment_ids[1]},
            {"user": "user3", "project": "Project Gamma", "memory": 64, "storage": 1024, "gpu": "no", "environment_id": environment_ids[2]}
        ]

        # Insert new requests with environment IDs
        for data in requests_data:
            db_request = Request(**data)
            db.add(db_request)
        db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    # Populate environments and get their IDs
    environment_ids = populate_environments()
    
    # Populate projects
    populate_projects()
    
    # Populate requests using the environment IDs
    populate_requests(environment_ids)
    
    print("Databases have been populated with example data.")