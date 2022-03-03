alembic init alembic
cp env.py /app/alembic/env.py
alembic revision --autogenerate -m "Migration"
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 3128 --workers 4 --root-path $APPLICATION_ROOT