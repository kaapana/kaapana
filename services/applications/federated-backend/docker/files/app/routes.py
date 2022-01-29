import os
from flask import render_template
from app import app

@app.route('/')
@app.route('/index')
def index():
    hello_world_user = os.environ['HELLO_WORLD_USER']
    return render_template('index.html', title='Home', hello_world_user=hello_world_user + 'hello')

