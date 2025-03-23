import sys
import flask
from flask import Flask, render_template, request
from markupsafe import escape
from mapping import generate_map
from mbta import rapid_routes, commuter_routes, silver_line_routes, bus_routes

app = Flask(__name__)


map_types = {
    'rapid',
    'commuter',
    'silver',
    'busses',
    'trains',
    'all',
}


@app.route('/')
def index():
    return render_template('index.html', base_url=request.root_url)


@app.route('/map/<map_type>')
def map_page(map_type: str):
    map_type = escape(map_type).lower()
    if map_type not in map_types:
        # invalid type, redirect home
        flask.redirect(flask.url_for('index'), base_url=request.root_url)

    match map_type:
        case 'rapid':
            routes = silver_line_routes + rapid_routes
        case 'commuter':
            routes = commuter_routes
        case 'silver':
            routes = silver_line_routes
        case 'busses':
            routes = bus_routes
        case 'trains':
            routes = commuter_routes + rapid_routes
        case 'all':
            routes = commuter_routes + silver_line_routes + rapid_routes

        # no default since this should be unreachable

    return render_template('map.html', iframe=generate_map(routes), base_url=request.root_url)


if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] == '--debug':
        debug = True
    else:
        debug = False
    app.run(host='127.0.0.1', port=8080, debug=debug)
