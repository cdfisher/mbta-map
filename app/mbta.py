from collections import deque

# TODO this can probably be handled better
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
    'CR-NewBedford': (128, 39, 108),
}

silver_line_route_names = {
    '741': 'SL1',
    '742': 'SL2',
    '743': 'SL3',
    '751': 'SL4',
    '749': 'SL5',
    '746': 'SLW',
}

# TODO add text colors
colors = {
    'Re': (255, 0, 0),
    'Or': (237, 139, 0),
    'Bl': (0, 61, 165),
    'Gr': (0, 132, 61),
    'CR': (128, 39, 108),
    'SL': (124, 135, 142),
    'Bus': (255, 199, 44), # This case won't get hit directly but is included for reference
}

rapid_routes = ['Red', 'Blue', 'Orange', 'Green-B', 'Green-C', 'Green-D', 'Green-E']
commuter_routes = ['CR-Fairmount', 'CR-Fitchburg', 'CR-Worcester', 'CR-Franklin', 'CR-Greenbush', 'CR-Haverhill',
                   'CR-Kingston', 'CR-Lowell', 'CR-Middleborough', 'CR-Needham', 'CR-Newburyport', 'CR-Providence',
                   'CR-Foxboro', 'CR-NewBedford']
silver_line_routes = ['741', '742', '743', '746', '749', '751']
bus_routes = [] # Includes SL TODO NYI


def get_priority(line: str) -> int:
    match line:
        case 'Red':
            return 6
        case 'Orange':
            return 5
        case 'Blue':
            return 4
        case 'Green-B' | 'Green-C' | 'Green-D' | 'Green-E':
            return 3
        case _:
            if line[:2] == 'CR':
                return 2
            elif line in {'741', '742', '743', '746', '749', '751'}:
                # Silver Line route IDs
                return 1
            else:
                #Default to bus priority
                return 0


class Carriage:
    def __init__(self, c: dict):
        self.label = c['label']
        self.occupancy_status = c['occupancy_status']
        self.occupancy_percentage = c['occupancy_percentage']


class Vehicle:
    def __init__(self, r: dict, headsign=''):
        rel = r['relationships']
        attr = r['attributes']

        # TODO including route.color should be able to replace this
        # This will be set later for all rapid transit and CR vehicles, so defaults to the color for busses
        self.color = (255, 199, 44)

        # under relationships
        self.route = rel['route']['data']['id']  # for instance 'Green-B'
        if self.route[:2] in colors.keys():
            self.color = colors[self.route[:2]]
        # Handle SL route IDs just being numerical values since the short names are more helpful for those
        if self.route in silver_line_route_names.keys():
            self.route = silver_line_route_names[self.route]
            self.color = (124, 135, 142)

        self.trip_id = rel['trip']['data']['id']  # (usually?) numerical trip ID
        if rel['stop']['data'] is not None:
            self.stop = rel['stop']['data']['id']  # this is a numerical (usually?) stop ID
        else:
            self.stop = None

        # under attributes
        self.bearing = attr['bearing']
        self.carriages = [Carriage(c) for c in attr['carriages']]  # list of carriages
        self.carriage_list = [c.label for c in self.carriages]
        self.current_status = attr['current_status']
        self.direction_id = attr['direction_id']
        self.location = [attr['longitude'], attr['latitude']]
        try:
            self.revenue = attr['revenue']
        except KeyError:  # often null/not included so if this is the case set it to None
            self.revenue = None

        self.speed = attr['speed']  # in m/s, often null
        self.updated_at = attr['updated_at']

        self.headsign = headsign

        # https://api-v3.mbta.com/vehicles?fields[vehicle]=bearing,current_status,carriages,latitude,longitude,
        # direction_id,revenue_status,speed,updated_at&include=trip.headsign&filter[route]=Red

    def carriages_str(self):
        s = ''
        for v in range(len(self.carriage_list)):
            s = f'{s},{self.carriage_list[v]}'
        return s[1:]

    def build_label(self) -> str:
        return f"<h3 style=\"margin:0;padding:0;\">{self.headsign} {'train' if self.route[:2] in ('Re', 'Or', 'Bl', 'Gr', 'CR') else 'bus'}</h3>" \
               f"<h4 style=\"margin:0;padding:0;\">" \
               f"{f'Green Line {self.route[-1]}' if self.route[0:5] == 'Green' else f'{self.route} Line'}</h4><br>" \
               f"{f'<b>Carriages: </b>{self.carriages_str()}<br>' if len(self.carriages_str()) > 0 else ''}" \
               f"{f'<b>Speed (m/s) : </b>{self.speed}<br>' if self.speed is not None else ''}"

    def get_icon(self) -> dict:
        # TODO this approach is a bit messy, clean up
        c = self.color
        match c:
            case (255, 0, 0):
                color_string = 'red'
            case (237, 139, 0):
                color_string = 'orange'
            case (0, 61, 165):
                color_string = 'blue'
            case (0, 132, 61):
                color_string = 'green'
            case (128, 39, 108):
                color_string = 'purple'
            case (124, 135, 142):
                color_string = 'silver'
            case _:
                color_string = 'yellow'

        return {
            "url": f'https://raw.githubusercontent.com/cdfisher/mbta-map/refs/heads/master/app/static/arrow_{color_string}.png',
            "width": 150,
            "height": 150,
            "anchorY": 75,
        }

    # TODO this may need additional values added
    def row(self) -> list:
        return [self.build_label(), self.location, self.color, self.bearing, self.get_icon()]


class Stop:
    def __init__(self, s: dict, route=None):
        attr = s['attributes']

        self.stop_id = s['id']

        if route is not None:
            # Handle SL route IDs just being numerical values when in the case of those the short names are more helpful
            if route in silver_line_route_names.keys():
                route = silver_line_route_names[route]
            self.routes_served = deque([route])
        else:
            self.routes_served = deque([])

        self.name = attr['name']
        self.location = [attr['longitude'], attr['latitude']]

    def add_route(self, route):
        # Handle SL route IDs just being numerical values when in the case of those the short names are more helpful
        if route in silver_line_route_names.keys():
            route = silver_line_route_names[route]
        if len(self.routes_served) > 0:
            r = self.routes_served[0]
            if get_priority(route) > get_priority(r):
                self.routes_served.appendleft(route)
            else:
                self.routes_served.append(route)
        else:
            self.routes_served.append(route)

    def get_color(self):
        try:
            if self.routes_served[0][:2] in colors.keys():
                return colors[self.routes_served[0][:2]]
            else:
                # default to the color for a bus
                return (255, 199, 44)
        except IndexError:
            # If an index error is encountered it's a single-digit numbered bus route
            return (255, 199, 44)

    def row(self) -> list:
        return [self.name, f"<h3 style=\"margin:0;padding:0;\">{self.name}</h3>",
                self.stop_id, self.location, list(self.routes_served), self.get_color()]


class Station:
    def __init__(self):
        raise NotImplementedError('Station objects have not yet been implemented, use Stop objects instead')
