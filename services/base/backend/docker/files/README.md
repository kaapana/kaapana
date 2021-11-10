# Backend

## How to start it

Assuming you are in files directory:

- Create a venv `python3 -m venv venv` and activate it `source venv/bin/activate`
- Install datamodel requrement `pip install -e ../../../datamodel`
- Install requirements with `pip install -r requirements.txt`
- Start the flask server by `boot.sh` also `flask run` should work
- To check if everything is working you can try `curl http://localhost:5000/api/v1/heartbeat`