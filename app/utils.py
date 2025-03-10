class Stop:
    def __init__(self, name, latitude, longitude):
        self.name = name
        self.location = [longitude, latitude]


class Vehicle:
    def __init__(self, name, latitude, longitude, bearing, direction, speed, is_revenue):
        self.name = name
        self.location = [longitude, latitude]
        self.bearing = bearing
        self.direction = direction
        self.speed = speed
        self.is_revenue = is_revenue
