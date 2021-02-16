"""Flask App Project."""

from flask import Flask, jsonify
from flask import render_template
from markupsafe import escape
import os
import psycopg2

from functools import wraps
import json
from os import environ as env
from werkzeug.exceptions import HTTPException

from dotenv import load_dotenv, find_dotenv
from flask import Flask
from flask import jsonify
from flask import redirect
from flask import render_template
from flask import session
from flask import url_for
from authlib.integrations.flask_client import OAuth
from six.moves.urllib.parse import urlencode

app = Flask(__name__, static_url_path='/public', static_folder='./public')
app.secret_key = os.environ['AUTH0_CLIENT_SECRET']

@app.errorhandler(Exception)
def handle_auth_error(ex):
    response = jsonify(message=str(ex))
    response.status_code = (ex.code if isinstance(ex, HTTPException) else 500)
    return response

oauth = OAuth(app)

AUTH0_CLIENT_ID = os.environ['AUTH0_CLIENT_ID']
AUTH0_CLIENT_SECRET = os.environ['AUTH0_CLIENT_SECRET']
AUTH0_DOMAIN = os.environ['AUTH0_DOMAIN']
AUTH0_BASE_URL = 'https://' + AUTH0_DOMAIN
AUTH0_ACCESS_TOKEN_URL = AUTH0_BASE_URL + '/oauth/token'
AUTH0_AUTHORIZE_URL = AUTH0_BASE_URL + '/authorize'
APP_BASE_URL = os.environ['APP_BASE_URL']

auth0 = oauth.register(
    'auth0',
    client_id=AUTH0_CLIENT_ID,
    client_secret=AUTH0_CLIENT_SECRET,
    api_base_url=AUTH0_DOMAIN,
    access_token_url=AUTH0_ACCESS_TOKEN_URL,
    authorize_url=AUTH0_AUTHORIZE_URL,
    client_kwargs={
        'scope': 'openid profile email',
    },
)

DATABASE_URL = os.environ['DATABASE_URL']

def requires_auth(f):
  @wraps(f)
  def decorated(*args, **kwargs):
    if 'profile' not in session:
      # Redirect to Login page here
      return redirect('/')
    return f(*args, **kwargs)

  return decorated

@app.route('/callback')
def callback_handling():
    # Handles response from token endpoint
    auth0.authorize_access_token()
    resp = auth0.get(AUTH0_BASE_URL + '/userinfo')
    userinfo = resp.json()

    # Store the user information in flask session.
    session['jwt_payload'] = userinfo
    session['profile'] = {
        'user_id': userinfo['sub'],
        'name': userinfo['name'],
        'picture': userinfo['picture']
    }
    return redirect('/dashboard')

@app.route('/login')
def login():
    return auth0.authorize_redirect(redirect_uri=APP_BASE_URL + '/callback')

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/logout')
def logout():
    # Clear session stored data
    session.clear()
    # Redirect user to logout endpoint
    params = {'returnTo': url_for('home', _external=True), 'client_id': AUTH0_CLIENT_ID}
    return redirect(auth0.api_base_url + '/v2/logout?' + urlencode(params))

@app.route('/dashboard')
@requires_auth
def index():
    return render_template('dashboard.html',
                           userinfo=session['profile'],
                           userinfo_pretty=json.dumps(session['jwt_payload'], indent=4))

@app.route('/chores')
@requires_auth
def chores():
    json_data = []
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cursor = conn.cursor()
        postgreSQL_select_Query = "select * from choremate.chores"

        cursor.execute(postgreSQL_select_Query)
        print("Selecting rows from chores table using cursor.fetchall")
        chores_records = cursor.fetchall() 
        
        for row in chores_records:
            json_data.append({'Id':row[0],'Name':row[1],'Description':row[2],'Score':row[3]})

    except (Exception, psycopg2.Error) as error :
        print ("Error while fetching data from PostgreSQL", error)

    finally:
        #closing database connection.
        if(conn):
            cursor.close()
            conn.close()
            print("PostgreSQL connection is closed")

    return jsonify(json_data)

@app.route('/chores/<int:id>')
@requires_auth
def chore(id):
    json_data = None
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cursor = conn.cursor()
        postgreSQL_select_Query = "select * from choremate.chores where chore_id = %s"

        cursor.execute(postgreSQL_select_Query, (id,))
        print("Selecting row from chores table using cursor.fetchall")
        chores_records = cursor.fetchall() 
        
        row = chores_records[0]
        json_data = ({'Id':row[0],'Name':row[1],'Description':row[2],'Score':row[3]})

    except (Exception, psycopg2.Error) as error :
        print ("Error while fetching data from PostgreSQL", error)

    finally:
        #closing database connection.
        if(conn):
            cursor.close()
            conn.close()
            print("PostgreSQL connection is closed")
    return jsonify(json_data)


if __name__ == '__main__':
    app.run()
