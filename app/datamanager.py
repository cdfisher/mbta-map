import os
import json
import requests
import polyline
import pandas as pd

from dotenv import load_dotenv

from mbta import *

load_dotenv()
USER_AGENT = os.getenv('USER_AGENT')
MBTA_API_KEY = os.getenv('MBTA_API_KEY')

HEADERS = {
    'User-Agent': USER_AGENT,
    'x-api-key': MBTA_API_KEY
}

BASE_URL = 'https://api-v3.mbta.com/'

all_routes = commuter_routes + silver_line_routes + rapid_routes


def _list_for_url(values: list) -> str:
    s = ''
    for v in range(len(values)):
        s = f'{s},{values[v]}'
    return s[1:]


def _query_api(route: str, headers=HEADERS) -> (dict, int):
    """Returns a (dict, int) tuple with the decoded response JSON and
        the response status code.

        :param route: The API route to query
        :type route: str

        :raises requests.Exception.HTTPError

        :return: tuple with decoded JSON and request status code
        :rtype (dict, int) tuple

        """
    try:
        r = requests.get(f"{BASE_URL}{route}", headers=headers)
        r.raise_for_status()
    except requests.exceptions.HTTPError as err:
        raise err

    status = r.status_code
    if status > 399:
        raise requests.exceptions.HTTPError(f'Encountered HTTP error, status {status}')

    # Necessary to play nicely with 304, etc.
    if len(r.content) > 0:
        return json.loads(r.content.decode()), status
    else:
        return {}, r.status_code


def _polyline_to_coords(poly: str) -> list:
    line = polyline.decode(poly)
    # coords is a list of points like [[lng, lat], [lng, lat]]
    # transform from list of tuples to list of lists
    coords = []
    for l in line:
        coords.append([l[1], l[0]])
    return coords


def _filter_deque(d: deque, included_elements: set) -> deque:
    # filters deque to include only the elements in a set, while maintaining relative positions in the deque
    d_prime = deque([])
    d.reverse()
    while len(d) > 0:
        e = d.pop()
        if e in included_elements:
            d_prime.append(e)

    return d_prime


def build_route_df(route_ids: list):
    # TODO NYI
    # use /routes?filter[type]=<routes> to get name, route_id, color, text_color, direction names,
    # direction destinations

    # This will be helpful to get the next couple trains in each direction for each line at a given station
    raise NotImplementedError


def fetch_shapes(route_ids: list) -> pd.DataFrame:
    # there might be a better way to do this but it's still a significant improvement I think
    # todo update dynamically, will implement once I have a middleman server or a service updating this csv in a bucket
    _headers = {
        'User-Agent': USER_AGENT,
        'x-api-key': MBTA_API_KEY,
        'If-Modified-Since': 'Thu, 27 Mar 2025 15:46:06 GMT'
        }

    j, status = _query_api(f'/shapes?filter[route]={_list_for_url(route_ids)}', headers=_headers)

    if status == 304:
        # load from pickle
        df = pd.read_pickle('./data/shapes.pkl')
    else:
        df = build_shape_df(j)

    # Sort df based on color values to follow draw order priority
    color_sorter = dict(zip(df_color_sort_order, range(len(df_color_sort_order))))
    df['sort_order'] = df['color'].map(color_sorter)
    df.sort_values('sort_order', inplace=True)
    df.drop('sort_order', axis='columns', inplace=True)

    # filter just the routes passed as an argument
    return df[df['label'].isin(route_ids)]


def build_shape_df(jdata: dict) -> pd.DataFrame:
    rows, shapes, shape_ids = [], [], []

    with open('./data/shape-to-route.json', 'r') as inf:
        shape_to_route = json.load(inf)

    for d in jdata['data']:
        if 'canonical' in d['id']:
            shapes.append(_polyline_to_coords(d['attributes']['polyline']))
            shape_ids.append(d['id'])

    for i in range(len(shape_ids)):
        r = shape_to_route[shape_ids[i]]
        rows.append([r, shapes[i], get_color(r)])

    df = pd.DataFrame(rows, columns=['label', 'path', 'color'])

    # write pickle for all routes, since if this is running, all the cached data should be updated
    #df.to_pickle('./data/shapes.pkl')

    return df


def fetch_stops(route_ids: list) -> pd.DataFrame:
    # there might be a better way to do this but it's still a significant improvement I think
    # todo update dynamically, will implement once I have a middleman server or a service updating this csv in a bucket
    _headers = {
        'User-Agent': USER_AGENT,
        'x-api-key': MBTA_API_KEY,
        'If-Modified-Since': 'Thu, 27 Mar 2025 15:46:06 GMT'
        }

    j, status = _query_api(f'/stops?filter[route]={_list_for_url(route_ids)}', headers=_headers)
    if status == 304:
        # load from pickle
        df = pd.read_pickle('./data/stops.pkl')
    else:
        df = build_stop_df(j)

    # If SL stops stop loading again, add the 'SL'- route names back to this as copies of the numerical k-v pairs
    with open('./data/route-to-stops.json', 'r') as inf:
        route_to_stops = json.load(inf)

    # filter just the routes passed as an argument
    r = set(route_ids)

    # TODO get rid of this and rename SL routes later down the line rather than when building the DF
    # hacky fix for silver line stops being filtered accidentally
    if not r.isdisjoint({'741', '742', '734', '746', '749', '751'}):
        r = r.union({'SL1', 'SL2', 'SL3', 'SL4', 'SL5', 'SLW'})
    stops = set()
    for s in r:
        stops = stops.union(set(route_to_stops[s]))

    # Filter the routes_served for each stop to only include routes in route_ids and
    # update the color to be based on this new filtered group of routes
    df = df[df['id'].isin(stops)]
    # filter routes_served to only include those in route_types
    df['routes_served'] = df['routes_served'].apply(lambda x: list(_filter_deque(x, r)))
    df = df[df.routes_served.astype(bool)]
    # update color
    df['color'] = df['routes_served'].apply(update_color)

    return df


def build_stop_df(jdata: dict) -> pd.DataFrame:
    stop_dict = {}

    with open('./data/route-to-stops.json', 'r') as inf:
        rts = json.load(inf)

    route_to_stops = {}

    for k in rts.keys():
        route_to_stops[k] = set(rts[k])

    for d in jdata['data']:
        _id = d['id']
        stop_dict[_id] = Stop(d)
        for r in route_to_stops.keys():
            if _id in route_to_stops[r]:
                stop_dict[_id].add_route(r)

    rows = [v.row() for v in stop_dict.values()]
    df = pd.DataFrame(rows, columns=['name', 'label', 'id', 'location', 'routes_served', 'color'])
    #df.to_pickle('./data/stops.pkl')
    return df


def build_vehicle_df(route_ids: list) -> pd.DataFrame:
    vehicle_dict = {}
    jdata, _ = _query_api(f'/vehicles?fields[vehicle]=bearing,current_status,carriages,'
                               f'latitude,longitude,direction_id,revenue_status,speed'
                               f'&include=trip,route&filter[route]={_list_for_url(route_ids)}')

    headsigns = {}
    route_colors = {}
    for d in jdata['included']:
        if 'headsign' in d['attributes'].keys():
            headsigns[d['id']] = d['attributes']['headsign']
        elif 'color' in d['attributes'].keys():
            route_colors[d['id']] = parse_color(d['attributes']['color'])

    for v in jdata['data']:
        try:
            headsign = headsigns[v['relationships']['trip']['data']['id']]
        except KeyError:
            # if trip doesn't exist in the included data (which seems to happen for a small number of IDs,
            # set it to None
            headsign = None

        try:
            color = route_colors[v['relationships']['route']['data']['id']]
        except KeyError:
            # if trip doesn't exist in the included data (which seems to happen for a small number of IDs,
            # set it to None
            color = None

        vehicle_dict[v['id']] = Vehicle(v, headsign=headsign, color=color)

    rows = [v.row() for v in vehicle_dict.values()]
    return pd.DataFrame(rows, columns=['label', 'location', 'color', 'bearing', 'icon', 'trip_id', 'vehicle_id'])


def get_predictions(df: pd.DataFrame):
    # https://api-v3.mbta.com/predictions?sort=arrival_time&include=vehicle.status&filter[trip]=TRIPS
    trip_ids = df['trip_id'].unique()
    j, _ = _query_api(f'/predictions?sort=arrival_time&include=vehicle.status&filter[trip]={_list_for_url(trip_ids)}')
    predictions_dict = {}

    with open('./data/stop-id-to-name.json', 'r') as inf:
        stop_lookup = json.load(inf)

    for d in j['data']:
        if d['relationships']['vehicle']['data'] is None:
            continue
        v = d['relationships']['vehicle']['data']['id']
        if v not in predictions_dict:
            predictions_dict[v] = Prediction(d, j['included'])
        else:
            predictions_dict[v].update_time_and_stop(d)

    for k in predictions_dict.keys():
        # get vehicle ID
        p = predictions_dict[k]

        # for the row in vehicles_df where trip ids match:
        idx = df.index[df['vehicle_id'] == p.vehicle][0]
        df.at[idx, 'label'] = f"{df.at[idx, 'label']}<br><b>Next stop: </b>{stop_lookup[p.stop_id]}: {p.get_countdown_string()}"

    return df
