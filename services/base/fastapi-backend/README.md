Kaapana Backend
===============

When the backend is running a swager frontend is accessable under `https://YOUR-INSTANCE/backend/docs`

## Structure of the code

- main.py contains the FastAPI app, all routers are registered here
- config.py holds the settings object for this app, if you want to add new configurations (even over environment variables) this is the way to go
- dependencies.py holds all the singeltons of the backend like database connections or services, thos things are available in the whole app using fastapis Depends directive
- `routers` folder containes one module per router (e.g. the actual endpoint)
- `schemas` contains one module per router containing the pydantic schemas for the return values
- `services` contains one module per endpoint

## How to develop

1. Set absolute path to `docker/files` for the `dev_files` variable in  `backend-chart/values.yaml``
2. Build the docker container (e.g.``docker build --build-arg http_proxy="http://www-int2.dkfz-heidelberg.de:80" --build-arg https_proxy="http://www-int2.dkfz-heidelberg.de:80" -t registry.hzdr.de/[YOUR-USERNAME]/kaapana/fastapi-backend:0.1.0 docker`)
3. Install the chart into your platofrm `helm install kaapana-backend backend-chart/`

Your backend pod will have the code directly mounted via a volume called `fastapi-dev-files`. Since fastapi is able to detect changes, it will reload every time you edit a file in the backend folder. To have continious logging use `kubectl logs POD-NAME -n base -f`.

**Note:** Dev mode opens a NodePort for the backend on port 5000 for direct access. Authentification is disabled here.


## Integrating new endpoints

1. Create a module in the routers folder named after you endpoint and create a router for your endpoint in there
2. Register the router object for your endpoint in `main.py``
3. Add routes to the router and write presentation logic
4. If you need singelton classes add a factory method in the `dependencies.py` and use FastAPIs dependency injection mechanisem (e.g. `Depends`)
5. Encode Business logic of your endpoint into services
6. Data Types of your enpoints should be defined as Pydantic object in the schemas object.
