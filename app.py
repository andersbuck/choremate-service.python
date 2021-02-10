"""Flask App Project."""

from flask import Flask, jsonify
from flask import render_template
from markupsafe import escape
import os
import psycopg2
app = Flask(__name__)

DATABASE_URL = os.environ['DATABASE_URL']

@app.route('/')
@app.route('/<name>')
def index(name=None):
    return render_template('index.html', name=escape(name))

@app.route('/chores')
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
def chore(id):
    json_data = null;
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cursor = conn.cursor()
        postgreSQL_select_Query = "select * from choremate.chores where chore_id = %s"

        cursor.execute(postgreSQL_select_Query, (id,))
        print("Selecting row from chores table using cursor.fetchall")
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


if __name__ == '__main__':
    app.run()
