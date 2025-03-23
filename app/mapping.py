import pydeck as pdk

from datamanager import *


def build_lines_layer(route_ids: list) -> pdk.Layer:
    routes_df = fetch_shapes(route_ids)

    path_layer = pdk.Layer(
        type='PathLayer',
        data=routes_df,
        pickable=True,
        get_color='color',
        width_scale=20,
        width_min_pixels=4,
        get_path='path',
        path_type='open'
    )

    return path_layer


# TODO maybe migrate to IconLayer
def build_stops_layer(route_ids: list) -> pdk.Layer:
    stops_df = fetch_stops(route_ids)

    # previously used a label value of f"<h3 style=\"margin:0;padding:0;\">{s.name}</h3>"
    # TODO add routes served, stop info label, next trains prediction

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
        get_position='location',
        get_line_color=[0, 0, 0],
        get_fill_color='color'
    )

    return stops_layer


def build_vehicles_layer(route_ids: list) -> pdk.Layer:
    vehicles_df = build_vehicle_df(route_ids)

    vehicles_layer = pdk.Layer(
        'IconLayer',
        vehicles_df,
        get_position='location',
        get_icon='icon',
        size_min_pixels=10,
        size_scale=25,
        pickable=True,
        get_angle='360 - bearing',
    )

    return vehicles_layer

# To be replaced/removed, left as reference for now
# def build_text_layer():
#     # Transfers and termini
#     stations_to_label = {
#         # Red Line
#         'Alewife',
#         'Ashmont',
#         'Braintree',
#         'JFK/UMass',
#         'South Station',
#         'Downtown Crossing',
#         'Park Street',
#         # Orange Line
#         'Oak Grove',
#         'Forest Hills',
#         'North Station',
#         'Haymarket',
#         'State',
#         # Blue Line
#         'Wonderland',
#         'Government Center',
#         'Bowdoin',
#         # Green Line
#         'Medford/Tufts',
#         'Union Square',
#         'Heath Street',
#         'Riverside',
#         'Cleveland Circle',
#         'Boston College'
#     }
#
#     stations = []
#     for s in stations_to_label:
#         stations.append([s, subway_stop_coords[s]])
#
#     labels_df = pd.DataFrame(stations, columns=['name', 'coordinates'])
#
#     text_layer = pdk.Layer(
#         'TextLayer',
#         labels_df,
#         get_position='coordinates',
#         get_text='name',
#         get_color=(201,205,225),
#         size_max_pixels=17,
#         font_weight=900,
#         #get_alignment_baseline='bottom',
#        # get_pixel_offset=[55, -20]
#         get_pixel_offset=[0, -30]
#     )
#
#     return text_layer


def generate_map(routes: list):
    layers = [build_lines_layer(routes), build_stops_layer(routes), build_vehicles_layer(routes)]

    view = pdk.View(type="MapView", controller='true', height="80%", width="100%")

    initial_view_state = pdk.ViewState(latitude=42.34946811943323, longitude=-71.06381901438351, zoom=10, bearing=0,
                                       pitch=0)

    deck = pdk.Deck(layers=layers, views=[view], initial_view_state=initial_view_state, tooltip={"html": "{label}"},
                    height=400)
    return deck.to_html(as_string=True)
