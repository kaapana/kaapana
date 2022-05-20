alembic init alembic
cp env.py /app/alembic/env.py
alembic revision --autogenerate -m "Migration"
alembic upgrade head

# Production
echo "Running at $APPLICATION_ROOT"
SCRIPT_NAME=$APPLICATION_ROOT gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:5000 --access-logfile - --error-logfile - 

# Development
# SCRIPT_NAME=$APPLICATION_ROOT gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:5000 --reload
#uvicorn app.main:app --reload --host 0.0.0.0 --port 5000 --workers 4 --root-path $APPLICATION_ROOT