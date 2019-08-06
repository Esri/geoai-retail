"""
name:       TAZ API - Utilities
date:       18 Jan 2018
purpose:    Provide a wrapper to more easily access the
"""
import requests
import re
import pandas as pd
from arcgis.features import GeoAccessor
from arcgis.geometry import Point
from arcgis.geometry import SpatialReference


def _underscore_to_camelcase(s):
    return re.sub(r'(?!^)_([a-zA-Z])', lambda m: m.group(1).upper(), s)


class TAZ(object):

    def __init__(self, app_id, hash_token):
        self._token = self._get_token(app_id, hash_token)
        self.session = requests.Session()
        self.session.headers.update({'Authorization': self._authorization})

    @staticmethod
    def _get_token(app_id, hash_token):
        hash_url = 'https://uas-api.inrix.com/v1/appToken?appId={}&hashToken={}'.format(app_id, hash_token)
        resp = requests.get(hash_url)
        if resp.status_code == 200:
            return resp.json()['result']['token']
        else:
            raise Exception('Cannot secure token.')

    @property
    def _authorization(self):
        return 'Bearer {}'.format(self._token)

    def get_trips_dataframe(self, od, geo_filter_type, points, limit=10000, radius=None, device_ids=None,
                            start_date_time=None, end_date_time=None, provider_type=None):
        """
        Wrapper around TAZ API origin/destination endpoint.
        :param od: Origin or destination explicitly specified as "origin" or "destination".
        :param geo_filter_type: Type of geometry to search for as the origin or destination, either explicitly "circle',
            "bbox", or "polygon".
        :param points: Points defining the origin or destination geometry. If the geo_filter_type is a point, then
            this is just a longitude (y), latitude (x) pair separated by a comma. If bbox, a bounding box, this is a
            pair of points delineating the top left and bottom right corners separated by a pipe (|) symbol. If a
            polygon, the points will be listed as comma separated pairs tracing the geometry in a counter clockwise
            direction, again with the points separate by a pipe.
        :param limit: Limit for pagnation results, defaults to 10,000.
        :param radius: If the circle geo_filter_type is specified, it is required to use this parameter to
            explicityly specify the buffered area around point to search as the origin or destination.
        :param device_ids: If searching for specific devices, specify device ids separated by commas.
        :param start_date_time: Starting datetime specified as yyyy-MM-ddTHH:mm in UTC or zulu.
        :param end_date_time: Ending datetime specified as yyyy-MM-ddTHH:mm in UTC or zulu.
        :param provider_type: Type of ba_data to filter, either explicitly "consumer" or "fleet".
        :return: Pandas ba_data frame with all the trips either starting or ending in the specified geometry.
        """

        resp = self.session.get(
            url='https://trade-areas-api.inrix.com/v1/trips',
            params={_underscore_to_camelcase(key): value for key, value in locals().items() if value is not None}
        )

        if resp.status_code == 200:
            json_data = resp.json()['ba_data']
            df = pd.DataFrame(json_data)
        else:
            raise Exception('Request error: {}'.format(resp.json()['description']))

        while resp.json()['paging']['nextCursor'] is not None:
            resp = self.session.get(resp.json()['paging']['nextCursor'])
            sdf_page = pd.DataFrame(resp.json()['ba_data'])
            df = pd.concat([df, sdf_page])

        if len(df.index):

            df['travelTimeMinutes'] = df.apply(
                lambda row: (pd.Timestamp(row.endDateTime) - pd.Timestamp(row.startDateTime)).seconds / 60,
                axis=1
            )
            df['travelDistanceMiles'] = df.tripDistanceMeters.apply(lambda value: float(value) * 0.000621371)

            return df

        else:
            return None

    @staticmethod
    def _loc_to_shape(loc):
        backwards_coordinates = loc.split(',')
        return Point({
            'x': float(backwards_coordinates[1]),
            'y': float(backwards_coordinates[0]),
            'spatialReference': {'wkid': 4326}
        })

    def set_start_as_geometry(self, df):
        df['SHAPE'] = df.startLoc.apply(lambda start_loc: self._loc_to_shape(start_loc))
        df.spatial.set_geometry('SHAPE')
        return df

    def set_end_as_geometry(self, df):
        df['SHAPE'] = df.endLoc.apply(lambda end_loc: self._loc_to_shape(end_loc))
        df.spatial.set_geometry('SHAPE')
        return df

    def get_trip_destination_spatial_dataframe(self, latitude, longitude, destination_radius='100m'):
        """
        Given a provided points input ba_data frame, return a spatial ba_data frame with all contributing trips.
        :param longitude: X coordinate for the point descrbing the destination location.
        :param latitude: Y coordinate for the point describing the destination location.
        :param destination_radius: Radius to search around the destination coordinates for trips.
        :return: Spatial dataframe with all trips ending in the location specified.
        """
        trips_df = self.get_trips_dataframe(
            od='destination',
            points='{}|{}'.format(latitude, longitude),
            geo_filter_type='circle',
            provider_type='consumer',
            radius=destination_radius
        )
        if trips_df is not None:
            return self.set_start_as_geometry(trips_df)
        else:
            return None
