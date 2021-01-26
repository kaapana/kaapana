# from keycloak import KeycloakOpenID
from flask import Flask, redirect,request,make_response
import collections
import requests
import json
import urllib
import os

app = Flask(__name__)


@app.route('/')
@app.route('/debug')
def hello_world():
    ordered_headers = collections.OrderedDict(sorted(request.headers.items()))
    headers = ''
    referer=''
    host=''
    headers = headers+"<br><br>###################################  COOKIE CONTENT  ###################################<br><br>"
    for cookie in request.cookies:
        print("cookie: "+cookie)
        headers = headers+"cookie: "+cookie+"<br><br>"

    headers = headers+"<br><br>###################################  JIP HEADERS   ###################################<br><br>"
    for key, val in ordered_headers.items():
        if "Jip" in key:
            headers = headers+key+":        " + \
                str(val)+"<br><br>"
            print(key + ": "+key+"\n value: " + str(val+"\n\n"))


    headers = headers+"<br><br>###################################  OTHER HEADERS  ###################################<br><br>"
    for key, val in ordered_headers.items():
        if "Jip" not in key:
            headers = headers+key+":        " + \
                str(val)+"<br><br>"
            print(key + ": "+key+"\n value: " + str(val+"\n\n"))

    return headers



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
