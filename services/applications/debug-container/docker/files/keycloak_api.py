# from keycloak import KeycloakOpenID
from flask import Flask, redirect,request,make_response
import requests
import json
import urllib
import os

app = Flask(__name__)


@app.route('/')
@app.route('/logout')
def hello_world():
    realm=os.getenv('REALM', 'jipdktk')
    client=os.getenv('CLIENT', 'jip')
    auth_url=os.getenv('AUTHURL', 'https://jip-dktk/auth')
    headers = ''
    referer=''
    host=''

    url = auth_url+"/realms/"+realm+"/protocol/openid-connect/token"
    print("Auth-url"+url)
    access_token = "eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJkaFB1M21VTS1ObEdMZ3hJbnBEX3R5YXRzS2VUMDFhQjFPVmxTSXk4V3I0In0.eyJqdGkiOiJkM2QwNTIxZi01ZGVhLTQxMWMtODE1ZS1kNzk2NWQzN2NmNjMiLCJleHAiOjE1NDM1Nzc3MzYsIm5iZiI6MCwiaWF0IjoxNTQzNTc3NDM2LCJpc3MiOiJodHRwczovL2ppcC1ka3RrL2F1dGgvcmVhbG1zL2ppcGRrdGsiLCJhdWQiOiJhY2NvdW50Iiwic3ViIjoiODQxYmYzODUtMDQ4Ni00NzU0LThjMTAtZTI0YjIyZmE5MTkzIiwidHlwIjoiQmVhcmVyIiwiYXpwIjoiamlwIiwiYXV0aF90aW1lIjoxNTQzNTcxNDI5LCJzZXNzaW9uX3N0YXRlIjoiZWYxMWY2MWUtN2QwMy00OTdjLTg1M2YtY2ZhNzA3OWY1MDFiIiwiYWNyIjoiMCIsImFsbG93ZWQtb3JpZ2lucyI6WyIqIl0sInJlYWxtX2FjY2VzcyI6eyJyb2xlcyI6WyJvZmZsaW5lX2FjY2VzcyIsImFkbWluIiwidW1hX2F1dGhvcml6YXRpb24iLCJ1c2VyIl19LCJyZXNvdXJjZV9hY2Nlc3MiOnsiYWNjb3VudCI6eyJyb2xlcyI6WyJtYW5hZ2UtYWNjb3VudCIsIm1hbmFnZS1hY2NvdW50LWxpbmtzIiwidmlldy1wcm9maWxlIl19fSwic2NvcGUiOiJvcGVuaWQgZW1haWwgcHJvZmlsZSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwicHJlZmVycmVkX3VzZXJuYW1lIjoiamlwdXNlciJ9.u0CoysZAAwX5_6HE1dkILRpWrFmO_FTIXDZ3JuYTsiQNuxoJLfBeN59Yoe4AXBy9H9EFbuO6AxaeXndN30A7rtkE6larWksLTY7hd0D28J-nDrSZSNxSLsRNfsh_Kgu865Mke7RnR-jt2I2zfL5m85k_qtqO4ae-xVvFTGyxhldlK3GuIm1R65KuVaYNVahJimkqd9iW6l2hwUZoFgi6gDxQcF2JinmZEe2gsIsF1WJAZkByiTK-QgNEz219eDEAoKKyzJAF-7W0wXhRGSmSeDYMAM5uvLKXB6EpC7Xo-J7lIvJ_k_boPwXQtFWi7fDbzm_GJTApNO4rBTQv4uSfDw"


    if 'Jip-Access-Token' in request.headers:
        access_token = request.headers['Jip-Access-Token']
    if 'Host' in request.headers:
        host='https://'+request.headers['Host']+'/'
    else:
        host=''

    data = [
        ('client_id', client),
        ('subject_token', access_token),
        ('requested_token_type', 'urn:ietf:params:oauth:token-type:refresh_token'),
        ('grant_type', 'urn:ietf:params:oauth:grant-type:token-exchange'),
        ('subject_token', access_token),
    ]

    response = requests.post(url, data=data,verify=False)
    print(response)

    headers = headers+"<br><br>###################################  GOT REFRESH TOKEN!  ###################################br><br>"


    print("############################################################################################ RESPONSE")
    print(str(response.content))
    print("############################################################################################ ")
    response = response.json()
    for key in response.keys():
        headers = headers+key+":        " + str(response[key])+"<br><br>"

    refresh_token = ""
    if 'refresh_token' in response:
        refresh_token = response['refresh_token']
        access_token = response['access_token']

    url = auth_url+"/realms/"+realm+"/protocol/openid-connect/logout"

    data = [
        ('client_id', client),
        ('subject_token', access_token),
        ('refresh_token', refresh_token),
        ('requested_token_type', 'urn:ietf:params:oauth:token-type:refresh_token'),
        ('grant_type', 'urn:ietf:params:oauth:grant-type:token-exchange'),
        ('subject_token', access_token),
    ]

    response = requests.post(url, data=data,verify=False)

    answer = str(response.content)
    print(answer)
    text_file = open("Output.txt", "w")
    text_file.write("Server answer: %s" % answer)
    text_file.close()

    headers = headers+"<br><br>###################################  LOGOUT:  ###################################<br><br>"

    if response.content != b'':
        response = response.json()
        for key in response.keys():
            headers = headers+key+":        " + str(response[key])+"<br><br>"
    else:
        headers = headers+"NO SERVER RESPONSE (OK)<br><br>"
    html_response=headers
    resp=make_response(html_response,200)
    if "keycloak."+client+".session" in request.cookies:
        resp.set_cookie("keycloak."+client+".session", '', expires=0)
    return headers
    
    # else:
    #     html_response = "<html><header><title>DKTK Joint Imaging Platform</title></header><body><h1>Welcome to DKTK Joint Imaging Platform <br></h1><h2><a href=%s>continue to BASE...</a></h2></body></html>"%host
    #     headers = headers+"<br><br>###################################  FROM LOGIN  ###################################<br><br>"

    #     return html_response



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
