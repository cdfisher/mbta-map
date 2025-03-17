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


class Carriage:
    def __init__(self, c: dict):
        self.label = c['label']
        self.occupancy_status = c['occupancy_status']
        self.occupancy_percentage = c['occupancy_percentage']


class Vehicle:
    def __init__(self, r: dict, headsign=''):
        rel = r['relationships']
        attr = r['attributes']

        # under relationships
        self.route = rel['route']['data']['id']  # for instance 'Green-B'
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
        # TODO will need to be modified for non-train vehicles
        return f"<h3 style=\"margin:0;padding:0;\">{self.headsign} train</h3>" \
               f"<h4 style=\"margin:0;padding:0;\">" \
               f"{f'Green Line {self.route[-1]}' if self.route[0:5] == 'Green' else f'{self.route} Line'}</h4><br>" \
               f"{f'<b>Carriages: </b>{self.carriages_str()}<br>' if len(self.carriages_str()) > 0 else ''}" \
               f"{f'<b>Bearing: </b>{self.bearing}<br>' if self.bearing is not None else ''}" \
               f"{f'<b>Speed (m/s) : </b>{self.speed}<br>' if self.speed is not None else ''}"

    # TODO this may need additional values added
    def row(self) -> list:
        return [self.build_label(), self.location, COLORS[self.route], self.bearing]


class Stop:
    def __init__(self, s: dict, route=None):
        attr = s['attributes']

        self.stop_id = s['id']

        if route is not None:
            self.routes_served = [route]
        else:
            self.routes_served = []

        self.name = attr['name']
        self.location = [attr['longitude'], attr['latitude']]

    def add_route(self, route):
        self.routes_served.append(route)

    def row(self) -> list:
        return [self.name, f"<h3 style=\"margin:0;padding:0;\">{self.name}</h3>",
                self.stop_id, self.location, self.routes_served, COLORS[self.routes_served[0]]]


class Station:
    def __init__(self):
        raise NotImplementedError('Station objects have not yet been implemented, use Stop objects instead')
