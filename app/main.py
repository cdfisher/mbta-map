import flask
from flask import Flask, render_template, request
from markupsafe import escape
from mapping import generate_map

app = Flask(__name__)

rapid_routes = ['Red', 'Blue', 'Orange', 'Green-B', 'Green-C', 'Green-D', 'Green-E']
commuter_routes = ['CR-Fairmount', 'CR-Fitchburg', 'CR-Worcester', 'CR-Franklin', 'CR-Greenbush', 'CR-Haverhill',
                   'CR-Kingston', 'CR-Lowell', 'CR-Middleborough', 'CR-Needham', 'CR-Newburyport', 'CR-Providence',
                   'CR-Foxboro', 'CR-NewBedford']
silver_line_routes = [] # TODO NYI
bus_routes = [] # Includes SL TODO NYI

map_types = {
    'rapid',
    'commuter',
    'silver',
    'busses',
    'trains',
    'core',
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
            routes = rapid_routes
        case 'commuter':
            routes = commuter_routes
        case 'silver':
            routes = silver_line_routes
        case 'busses':
            routes = bus_routes
        case 'trains':
            routes = rapid_routes + commuter_routes
        case 'core':
            routes = rapid_routes + silver_line_routes
        case 'all':
            routes = rapid_routes + silver_line_routes + commuter_routes

        # no default since this should be unreachable

    return render_template('map.html', iframe=generate_map(routes), base_url=request.root_url)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
