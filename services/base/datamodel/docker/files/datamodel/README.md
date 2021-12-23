# Kaapana datamodel

This Python package implements the Kaapana datamodel.


## Install for developement

In the project root of the datamodel:

1. Create a virtual environment `python3 -m venv venv`
2. Activate it `source venv/bin/activate`
3. Install in editable mode `pip install -e .`

## Running tests

```
python -m unittest
```

## Example

```
from datamodel import DM

print(dm.fancy_stuff())
```

## Test Container:
```
docker run --rm -P -p 127.0.0.1:5432:5432 -e POSTGRES_PASSWORD="1234" --name pg postgres:alpine
```
GraphQL
http://127.0.0.1:5000/graphql?query=query%7B%0A%20%20getStudies(access%3A%20%22kaapana%22)%7B%0A%20%20%20%20name%0A%20%20%7D%0A%7D&operationName=undefined&variables=null


run pgaadmin
```
docker run -p 5050:80  -e "PGADMIN_DEFAULT_EMAIL=name@example.com" -e "PGADMIN_DEFAULT_PASSWORD=admin"  -d dpage/pgadmin4
docker ps
docker inspect ---  | grep IPAddress ## ip adress of postgres
```
http://127.0.0.1:5050

