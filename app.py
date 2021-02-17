"""Flask App Project."""
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
from flask import request
from authlib.integrations.flask_client import OAuth
from six.moves.urllib.parse import urlencode
from jose import jwt

from six.moves.urllib.request import urlopen

from flask import _request_ctx_stack
from flask_cors import cross_origin

app = Flask(__name__, static_url_path='/public', static_folder='./public')
app.secret_key = os.environ['AUTH0_CLIENT_SECRET']

@app.errorhandler(Exception)
def handle_auth_error(ex):
    response = jsonify(message=str(ex))
    response.status_code = (ex.code if isinstance(ex, HTTPException) else 500)
    return response

# Format error response and append status code.
class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code

@app.errorhandler(AuthError)
def handle_auth_error(ex):
    response = jsonify(ex.error)
    response.status_code = ex.status_code
    return response

oauth = OAuth(app)

AUTH0_CLIENT_ID = os.environ['AUTH0_CLIENT_ID']
AUTH0_CLIENT_SECRET = os.environ['AUTH0_CLIENT_SECRET']
AUTH0_DOMAIN = os.environ['AUTH0_DOMAIN']
AUTH0_BASE_URL = 'https://' + AUTH0_DOMAIN
AUTH0_ACCESS_TOKEN_URL = AUTH0_BASE_URL + '/oauth/token'
AUTH0_AUTHORIZE_URL = AUTH0_BASE_URL + '/authorize'
APP_BASE_URL = os.environ['APP_BASE_URL']

ALGORITHMS = ["RS256"]
API_AUDIENCE = 'https://choremate-app.herokuapp.com/api'

auth0 = oauth.register(
    'auth0',
    client_id=AUTH0_CLIENT_ID,
    client_secret=AUTH0_CLIENT_SECRET,
    api_base_url=AUTH0_DOMAIN,
    access_token_url=AUTH0_ACCESS_TOKEN_URL,
    authorize_url=AUTH0_AUTHORIZE_URL,
    client_kwargs={
        'scope': 'openid profile email read:data',
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

def requires_api_auth(f):
    """Determines if the Access Token is valid
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_auth_header()
        jsonurl = urlopen("https://"+AUTH0_DOMAIN+"/.well-known/jwks.json")
        jwks = json.loads(jsonurl.read())
        unverified_header = jwt.get_unverified_header(token)
        rsa_key = {}
        for key in jwks["keys"]:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }
        if rsa_key:
            try:
                payload = jwt.decode(
                    token,
                    rsa_key,
                    algorithms=ALGORITHMS,
                    audience=API_AUDIENCE,
                    issuer="https://"+AUTH0_DOMAIN+"/"
                )
            except jwt.ExpiredSignatureError:
                raise AuthError({"code": "token_expired",
                                "description": "token is expired"}, 401)
            except jwt.JWTClaimsError:
                raise AuthError({"code": "invalid_claims",
                                "description":
                                    "incorrect claims,"
                                    "please check the audience and issuer"}, 401)
            except Exception:
                raise AuthError({"code": "invalid_header",
                                "description":
                                    "Unable to parse authentication"
                                    " token."}, 401)

            _request_ctx_stack.top.current_user = payload
            return f(*args, **kwargs)
        raise AuthError({"code": "invalid_header",
                        "description": "Unable to find appropriate key"}, 401)
    return decorated

def requires_scope(required_scope):
    """Determines if the required scope is present in the access token
    Args:
        required_scope (str): The scope required to access the resource
    """
    token = get_token_auth_header()
    unverified_claims = jwt.get_unverified_claims(token)
    if unverified_claims.get("scope"):
        token_scopes = unverified_claims["scope"].split()
        for token_scope in token_scopes:
            if token_scope == required_scope:
                return True
    return False

def get_token_auth_header():
    """Obtains the access token from the Authorization Header
    """
    auth = request.headers.get("Authorization", None)
    if not auth:
        raise AuthError({"code": "authorization_header_missing",
                        "description":
                            "Authorization header is expected"}, 401)

    parts = auth.split()

    if parts[0].lower() != "bearer":
        raise AuthError({"code": "invalid_header",
                        "description":
                            "Authorization header must start with"
                            " Bearer"}, 401)
    elif len(parts) == 1:
        raise AuthError({"code": "invalid_header",
                        "description": "Token not found"}, 401)
    elif len(parts) > 2:
        raise AuthError({"code": "invalid_header",
                        "description":
                            "Authorization header must be"
                            " Bearer token"}, 401)

    token = parts[1]
    return token

@app.route('/callback')
def callback_handling():
    # Handles response from token endpoint
    # response = jsonify(auth0.authorize_access_token())
    # resp = auth0.get(AUTH0_BASE_URL + '/userinfo')
    # userinfo = resp.json()

    # # Store the user information in flask session.
    # session['jwt_payload'] = userinfo
    # session['profile'] = {
    #     'user_id': userinfo['sub'],
    #     'name': userinfo['name'],
    #     'picture': userinfo['picture'],
    #     'access_token':response
    # }
    return jsonify(auth0.authorize_access_token())

@app.route('/login')
def login():
    return auth0.authorize_redirect(redirect_uri=APP_BASE_URL + '/callback', audience='https://choremate-app.herokuapp.com/api')

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

@app.route('/api/chores')
@cross_origin(headers=["Content-Type", "Authorization"])
@requires_api_auth
def chores():
    if requires_scope("read:data"):
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
    raise AuthError({
        "code": "Unauthorized",
        "description": "You don't have access to this resource"
    }, 403)

@app.route('/api/chores/<int:id>')
@cross_origin(headers=["Content-Type", "Authorization"])
@requires_api_auth
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
