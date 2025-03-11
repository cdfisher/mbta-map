import os
import json
import requests
import polyline
import pydeck as pdk
import pandas as pd

from dotenv import load_dotenv

from utils import *

load_dotenv()
USER_AGENT = os.getenv('USER_AGENT')
MBTA_API_KEY = os.getenv('MBTA_API_KEY')

HEADERS = {
    'User-Agent': USER_AGENT,
    'x-api-key': MBTA_API_KEY
}

BASE_URL = 'https://api-v3.mbta.com/'

COLORS = {
    'Red': (255, 0, 0),
    'Orange': (237, 139, 0),
    'Blue': (0, 61, 165),
    'Green-B': (0, 132, 61),
    'Green-C': (0, 132, 61),
    'Green-D': (0, 132, 61),
    'Green-E': (0, 132, 61),
    'CR-Fairmount': (128, 39, 108),
    'CR-Fitchburg': (128, 39, 108),
    'CR-Worcester': (128, 39, 108),
    'CR-Franklin': (128, 39, 108),
    'CR-Greenbush': (128, 39, 108),
    'CR-Haverhill': (128, 39, 108),
    'CR-Kingston': (128, 39, 108),
    'CR-Lowell': (128, 39, 108),
    'CR-Middleborough': (128, 39, 108),
    'CR-Needham': (128, 39, 108),
    'CR-Newburyport': (128, 39, 108),
    'CR-Providence': (128, 39, 108),
    'CR-Foxboro': (128, 39, 108),
    'CR-NewBedford': (128, 39, 108)
}

extra_tracks = {
    ('Red', 8),
    ('Red', 9),
    ('Orange', 2),
    ('Orange', 8),
    ('Orange', 12),
    ('Orange', 13),
    ('Orange', 16),
    ('Orange', 17),
}


def _query_api(route: str) -> (dict, int):
    """Returns a (dict, int) tuple with the decoded response JSON and
        the response status code.

        :param route: The API route to query
        :type route: str

        :raises requests.Exception.HTTPError

        :return: tuple with decoded JSON and request status code
        :rtype (dict, int) tuple

        """
    try:
        r = requests.get(f"{BASE_URL}{route}", headers=HEADERS)
        r.raise_for_status()
    except requests.exceptions.HTTPError as err:
        raise err

    return json.loads(r.content.decode()), r.status_code


def _get_shapes(route_id: str) -> list:
    jdata, status = _query_api(f"shapes?filter[route]={route_id}")
    if status > 399:
        raise requests.exceptions.HTTPError(f"Encountered HTTP error, status {status}")

    shapes = []
    for d in jdata['data']:
        shapes.append(_polyline_to_coords(d['attributes']['polyline']))

    return shapes


def _get_stops(route_id: str) -> list:
    jdata, status = _query_api(f"stops?filter[route]={route_id}")
    if status > 399:
        raise requests.exceptions.HTTPError(f"Encountered HTTP error, status {status}")

    stops = []
    for d in jdata['data']:
        attrs = d['attributes']
        stops.append(Stop(attrs['name'], attrs['latitude'], attrs['longitude']))
    return stops


def _get_vehicles(route_id: str) -> list:
    jdata, status = _query_api(f"vehicles?filter[route]={route_id}")
    if status > 399:
        raise requests.exceptions.HTTPError(f"Encountered HTTP error, status {status}")

    vehicles = []
    trips = []
    for d in jdata['data']:
        attrs = d['attributes']
        trip_id = d['relationships']['trip']['data']['id']

        vehicles.append(Vehicle(attrs['label'], attrs['latitude'], attrs['longitude'], attrs['bearing'],
                                attrs['direction_id'], attrs['speed'],
                                (True if attrs['revenue'] == 'REVENUE' else False),
                                trip_id))
        trips.append(trip_id)

    filter_str = ''
    for t in range(len(trips)-1):
        filter_str = f"{filter_str}{trips[t]},"

    filter_str = f"{filter_str}{trips[-1]}"

    # query api
    jdata, status = _query_api(f"trips?filter[id]={filter_str}")
    if status > 399:
        raise requests.exceptions.HTTPError(f"Encountered HTTP error, status {status}")

    # for each in response add trip_id:headsign to a dict
    headsigns = {}
    for d in jdata['data']:
        h = d['attributes']['headsign']
        _id = d['id']
        headsigns[_id] = h

    # for v in vehicles
    # v.set_headsign(headsigns[trip_id])
    for v in vehicles:
        try:
            v.set_headsign(headsigns[v.trip_id])
        except KeyError:
            v.set_headsign(None)

    return vehicles


# TODO potentially migrate to IconLayer
def build_stops_layer(routes: list) -> pdk.Layer:
    rows = []
    for route in routes:
        stops = _get_stops(route)
        for s in stops:
            rows.append([s.name, f"<h3 style=\"margin:0;padding:0;\">{s.name}</h3>", s.location, COLORS[route]])

    cols = ['name', 'label', 'coordinates', 'color']
    stops_df = pd.DataFrame(rows, columns=cols)

    stops_layer = pdk.Layer(
        'ScatterplotLayer',
        stops_df,
        pickable=True,
        opacity=1,
        stroked=True,
        filled=True,
        radius_scale=15,
        radius_min_pixels=8,
        radius_max_pixels=50,
        line_width_min_pixels=1,
        get_position="coordinates",
        get_line_color=[0, 0, 0],
        get_fill_color="color"
    )

    stops_df.to_csv('stops.csv', columns=['name', 'coordinates'])

    return stops_layer


def _polyline_to_coords(poly: str) -> list:
    line = polyline.decode(poly)
    # coords is a list of points like [[lng, lat], [lng, lat]]
    # transform from list of tuples to list of lists
    coords = []
    for l in line:
        coords.append([l[1], l[0]])
    return coords


def build_lines_layer(routes: list) -> pdk.Layer:
    rows = []
    for route in routes:
        shapes = _get_shapes(route)
        i = 0
        for s in shapes:
            if (route, i) not in extra_tracks:
                rows.append([f"{route}", s, COLORS[route]])
                i += 1

    cols = ['label', 'path', 'color']
    routes_df = pd.DataFrame(rows, columns=cols)

    path_layer = pdk.Layer(
        type="PathLayer",
        data=routes_df,
        pickable=True,
        get_color="color",
        width_scale=20,
        width_min_pixels=4,
        get_path="path",
        path_type='open'
    )

    return path_layer


# TODO potentially migrate to IconLayer
def build_vehicles_layer(routes: list) -> pdk.Layer:
    rows = []
    for route in routes:
        vehicles = _get_vehicles(route)
        for v in vehicles:
            # TODO add carriages list to tooltip
            label = f"<h3 style=\"margin:0;padding:0;\">{v.headsign} train</h3>" \
                    f"<h4 style=\"margin:0;padding:0;\">{f'Green Line {route[-1]}' if route[0:5] == 'Green' else f'{route} Line'}</h4><br>" \
                    f"<b>Bearing: </b>{v.bearing}<br>" \
                    f"{f'<b>Speed: </b>{v.speed}<br>' if v.speed is not None else ''}" \
                    # f"<b>Revenue?: </b>{'Yes' if v.is_revenue else 'No'}"
            rows.append([label, v.location, COLORS[route], v.bearing, v.direction, v.speed, v.is_revenue])

    cols = ['label', 'coordinates', 'color', 'bearing', 'direction', 'speed', 'is_revenue']
    vehicles_df = pd.DataFrame(rows, columns=cols)

    vehicles_layer = pdk.Layer(
        'ScatterplotLayer',
        vehicles_df,
        pickable=True,
        opacity=1,
        stroked=True,
        filled=True,
        radius_scale=10,
        radius_min_pixels=6,
        radius_max_pixels=400,
        line_width_min_pixels=6,
        get_position="coordinates",
        get_line_color="color",
        get_fill_color=[255, 255, 255]
    )

    return vehicles_layer


def build_text_layer():
    # Transfers and termini
    stations_to_label = {
        # Red Line
        'Alewife',
        'Ashmont',
        'Braintree',
        'JFK/UMass',
        'South Station',
        'Downtown Crossing',
        'Park Street',
        # Orange Line
        'Oak Grove',
        'Forest Hills',
        'North Station',
        'Haymarket',
        'State',
        # Blue Line
        'Wonderland',
        'Government Center',
        'Bowdoin',
        # Green Line
        'Medford/Tufts',
        'Union Square',
        'Heath Street',
        'Riverside',
        'Cleveland Circle',
        'Boston College'
    }

    stations = []
    for s in stations_to_label:
        stations.append([s, subway_stop_coords[s]])

    labels_df = pd.DataFrame(stations, columns=['name', 'coordinates'])

    text_layer = pdk.Layer(
        'TextLayer',
        labels_df,
        get_position='coordinates',
        get_text='name',
        get_color=(201,205,225),
        size_max_pixels=17,
        font_weight=900,
        #get_alignment_baseline='bottom',
       # get_pixel_offset=[55, -20]
        get_pixel_offset=[0, -30]
    )

    return text_layer


def construct_map(routes: list):
    layers = [build_lines_layer(routes), build_stops_layer(routes), build_vehicles_layer(routes), build_text_layer()]

    view = pdk.View(type="MapView", controller='true', height="80%", width="100%")

    initial_view_state = pdk.ViewState(latitude=42.34946811943323, longitude=-71.06381901438351, zoom=10, bearing=0,
                                       pitch=0)

    deck = pdk.Deck(layers=layers, views=[view], initial_view_state=initial_view_state, tooltip={"html": "{label}"},
                    height=400)
    return deck.to_html(as_string=True)
