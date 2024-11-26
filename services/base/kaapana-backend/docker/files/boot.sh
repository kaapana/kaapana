if [ ! -d "/kaapana/app/alembic" ]; then
    alembic init alembic
    cp env.py /kaapana/app/alembic/env.py
fi
# Apply existing migrations
alembic upgrade head
alembic revision --autogenerate -m "Automated Migration"
# Apply the new migration
alembic upgrade head

# Trying to handle multiple heads if they exist
if [ $(alembic heads | wc -l) -gt 1 ]; then
    echo "Multiple heads detected, trying to automaticly merge."
    alembic merge $(alembic heads | awk '{print $1}')
    alembic upgrade head
fi


export PYTHONPATH="$PWD" 

if [ "$BACKEND_TYPE" = "backend" ]; then
    python3 scripts/create_kaapana_instance.py
fi

# # Production
# echo "Running at $APPLICATION_ROOT"
SCRIPT_NAME=/kaapana-$BACKEND_TYPE gunicorn app.$BACKEND_TYPE:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:5000 --access-logfile - --error-logfile - 

# Development
# uvicorn app.main:app --reload --host 0.0.0.0 --port 5000 --workers 4 --root-path $APPLICATION_ROOT
