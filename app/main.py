from flask import Flask, render_template, request
from mapping import construct_map

app = Flask(__name__)

main_routes = ['Red', 'Blue', 'Orange', 'Green-B', 'Green-C', 'Green-D', 'Green-E']
layers = ['lines', 'stops', 'vehicles']


@app.route('/')
def index():
    return render_template('index.html', iframe=construct_map(main_routes))

# @app.route('/map/')
# def build_map():
#     return render_template('map.html', iframe=construct_map(main_routes))


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)