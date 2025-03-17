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


def _list_for_url(values: list) -> str:
    s = ''
    for v in range(len(values)):
        s = f'{s},{values[v]}'
    return s[1:]


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


def build_shape_df(route_ids: list) -> pd.DataFrame:
    # TODO this probably isn't the most efficient way, and I'd like to cache it (once a day maybe?)

    rows = []
    for route in route_ids:
        jdata, status = _query_api(f'/shapes?filter[route]={route}')
        if status > 399:
            raise requests.exceptions.HTTPError(f"Encountered HTTP error, status {status}")

        shapes = []
        for d in jdata['data']:
            shapes.append(_polyline_to_coords(d['attributes']['polyline']))

        i = 0
        for s in shapes:
            # TODO this can likely filter based on id rather than a (not super robust) numbered list
            if (route, i) not in extra_tracks:
                rows.append([f"{route}", s, COLORS[route]])
                i += 1

    return pd.DataFrame(rows, columns=['label', 'path', 'color'])


def build_stop_df(route_ids: list) -> pd.DataFrame:
    stop_dict = {}
    for route in route_ids:
        jdata, status = _query_api(f'/stops?filter[route]={route}')
        if status > 399:
            raise requests.exceptions.HTTPError(f'Encountered HTTP error, status {status}')

        for d in jdata['data']:
            if d['id'] not in stop_dict:
                stop_dict[d['id']] = Stop(d, route=route)
            else:
                stop_dict[d['id']].add_route(route)

    rows = [v.row() for v in stop_dict.values()]

    return pd.DataFrame(rows, columns=['name', 'label', 'id', 'location', 'routes_served', 'color'])


def build_vehicle_df(route_ids: list) -> pd.DataFrame:
    vehicle_dict = {}
    jdata, status = _query_api(f'/vehicles?fields[vehicle]=bearing,current_status,carriages,'
                               f'latitude,longitude,direction_id,revenue_status,speed,updated_at'
                               f'&include=trip.headsign&filter[route]={_list_for_url(route_ids)}')

    if status > 399:
        raise requests.exceptions.HTTPError(f'Encountered HTTP error, status {status}')

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
    return pd.DataFrame(rows, columns=['label', 'location', 'color', 'bearing'])
