from arcgis.features import GeoAccessor, FeatureLayer
from arcgis.geometry import Geometry
from arcgis.gis import GIS
import pandas as pd
import os
import re


def get_dataframe(in_features, gis=None):
    """
    Get a spatially enabled dataframe from the input features provided.
    :param in_features: Spatially Enabled Dataframe | String path to Feature Class | String url to Feature Service
        | String Web GIS Item ID
        Resource to be evaluated and converted to a Spatially Enabled Dataframe.
    :param gis: Optional GIS object instance for connecting to resources.
    """
    # if already a Spatially Enabled Dataframe, mostly just pass it straight through
    if isinstance(in_features, pd.DataFrame) and in_features.spatial.validate() == True:
        df = in_features

    # if a csv previously exported from a Spatially Enabled Dataframe, get it in
    elif isinstance(in_features, str) and os.path.exists(in_features) and in_features.endswith('.csv'):
        df = pd.read_csv(in_features)
        df['SHAPE'] = df['SHAPE'].apply(lambda geom: Geometry(eval(geom)))

        # this almost always is the index written to the csv, so taking care of this
        if df.columns[0] == 'Unnamed: 0':
            df = df.set_index('Unnamed: 0')
            del (df.index.name)

    # create a Spatially Enabled Dataframe from the direct url to the Feature Service
    elif isinstance(in_features, str) and in_features.startswith('http'):

        # submitted urls can be lacking a few essential pieces, so handle some contingencies with some regex matching
        regex = re.compile(r'((^https?://.*?)(/\d{1,3})?)\?')
        srch = regex.search(in_features)

        # if the layer index is included, still clean by dropping any possible trailing url parameters
        if srch.group(3):
            in_features = f'{srch.group(1)}'

        # ensure at least the first layer is being referenced if the index was forgotten
        else:
            in_features = f'{srch.group(2)}/0'

            # if the layer is unsecured, a gis is not needed, but we have to handle differently
        if gis is not None:
            df = FeatureLayer(in_features, gis).query(out_sr=4326, as_df=True)
        else:
            df = FeatureLayer(in_features).query(out_sr=4326, as_df=True)

    # create a Spatially Enabled Dataframe from a Web GIS Item ID
    elif isinstance(in_features, str) and len(in_features) == 32:

        # if publicly shared on ArcGIS Online this anonymous gis can be used to access the resource
        if gis is None:
            gis = GIS()
        itm = gis.content.get(in_features)
        df = itm.layers[0].query(out_sr=4326, as_df=True)

    # create a Spatially Enabled Dataframe from a local feature class
    elif isinstance(in_features, str):
        df = GeoAccessor.from_featureclass(in_features)

    else:
        raise Exception('Could not process input features for get_dataframe function.')

    # ensure the universal spatial column is correctly being recognized
    df.spatial.set_geometry('SHAPE')

    # index the spatial data for faster subsequnet analyses
    # df.spatial.sindex()

    return df
