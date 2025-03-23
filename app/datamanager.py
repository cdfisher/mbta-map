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
        'If-Modified-Since': 'Fri, 21 Mar 2025 19:59:59 GMT'
        }

    j, status = _query_api(f'/shapes?filter[route]={_list_for_url(route_ids)}', headers=_headers)

    if status == 304:
        # load from pickle
        df = pd.read_pickle('./data/shapes.pkl')
    else:
        df = build_shape_df(j)

    # filter just the routes passed as an argument
    # todo sort df to order based on draw priority I want to use
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
        rows.append([r, shapes[i], COLORS[r]])

    df = pd.DataFrame(rows, columns=['label', 'path', 'color'])

    # write pickle for all routes, since if this is running, all the cached data should be updated
    df.to_pickle('./data/shapes.pkl')

    return df


def fetch_stops(route_ids: list) -> pd.DataFrame:
    # there might be a better way to do this but it's still a significant improvement I think
    # todo update dynamically, will implement once I have a middleman server or a service updating this csv in a bucket
    _headers = {
        'User-Agent': USER_AGENT,
        'x-api-key': MBTA_API_KEY,
        'If-Modified-Since': 'Fri, 21 Mar 2025 19:59:59 GMT'
        }

    j, status = _query_api(f'/stops?filter[route]={_list_for_url(route_ids)}', headers=_headers)
    if status == 304:
        # load from pickle
        df = pd.read_pickle('./data/stops.pkl')
    else:
        df = build_stop_df(j)

    with open('./data/route-to-stops.json', 'r') as inf:
        route_to_stops = json.load(inf)

    # filter just the routes passed as an argument
    r = set(route_ids)
    stops = set()
    for s in r:
        stops = stops.union(set(route_to_stops[s]))

    # todo df.apply to filter routes_served and update color value based on this
    return df[df['id'].isin(stops)]


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
    df.to_pickle('./data/stops.pkl')
    return df


def build_vehicle_df(route_ids: list) -> pd.DataFrame:
    vehicle_dict = {}
    jdata, _ = _query_api(f'/vehicles?fields[vehicle]=bearing,current_status,carriages,'
                               f'latitude,longitude,direction_id,revenue_status,speed,updated_at'
                               f'&include=trip.headsign&filter[route]={_list_for_url(route_ids)}')

    headsigns = {}
    for d in jdata['included']:
        headsigns[d['id']] = d['attributes']['headsign']

    for v in jdata['data']:
        try:
            headsign = headsigns[v['relationships']['trip']['data']['id']]
        except KeyError:
            # if trip doesn't exist in the included data (which seems to happen for a small number of IDs,
            # set it to None
            headsign = None

        vehicle_dict[v['id']] = Vehicle(v, headsign=headsign)

    # TODO implement predictions for next stop
    # vehicles are in a dict so a lookup can be done for predictions

    rows = [v.row() for v in vehicle_dict.values()]
    return pd.DataFrame(rows, columns=['label', 'location', 'color', 'bearing', 'icon'])
