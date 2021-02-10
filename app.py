"""Flask App Project."""

from flask import Flask, jsonify
from flask import render_template
from markupsafe import escape
app = Flask(__name__)


@app.route('/')
@app.route('/<name>')
def index(name=None):
    return render_template('index.html', name=escape(name))

@app.route('/chores')
def chores():
    json_data = {'Hello': 'Chores!'}
    return jsonify(json_data)

@app.route('/chores/<int:id>')
def chore(id):
    json_data = {'Hello': 'Chore %d!' % id}
    return jsonify(json_data)


if __name__ == '__main__':
    app.run()
