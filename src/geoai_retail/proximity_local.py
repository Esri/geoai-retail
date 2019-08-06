import math
import os
import tempfile
import uuid

from arcgis.features import GeoAccessor
from arcgis.geometry import Geometry
import arcpy
import pandas as pd

import geoai_retail.utils as utils

# location to store temp files if necessary
csv_file_prefix = 'temp_closest'
temp_file_root = os.path.join(tempfile.gettempdir(), csv_file_prefix)

# ensure previous runs do not interfere
arcpy.env.overwriteOutput = True


def weighted_polygon_centroid(poly_df, wgt_df, poly_id_fld='ID'):
    # create a spatial index for both spatially enabled dataframes to speed up the join
    poly_df.spatial.sindex()
    wgt_df.spatial.sindex()

    # perform a spatial join between the points and the containing polygons
    join_df = wgt_df.spatial.join(poly_df)

    # extract the respective coordinates out of the geometry
    join_df['x'] = join_df['SHAPE'].apply(lambda geom: geom.centroid[0])
    join_df['y'] = join_df['SHAPE'].apply(lambda geom: geom.centroid[1])

    # get the id field following the join
    join_id_fld = poly_id_fld if poly_id_fld in join_df.columns else f'{poly_id_fld}_right'

    # calcuate the weighted centroid coordinates for each polygon and create geometries using these
    mean_df = join_df[[join_id_fld, 'x', 'y']].groupby(join_id_fld).mean()
    mean_df['SHAPE'] = mean_df.apply(
        lambda row: Geometry({'x': row['x'], 'y': row['y'], 'spatialReference': {'wkid': 4326}}), axis=1)

    # clean up the columns to a standard output schema
    mean_df.reset_index(inplace=True)
    mean_df = mean_df[[join_id_fld, 'SHAPE']].copy()
    mean_df.spatial.set_geometry('SHAPE')
    mean_df.columns = ['ID', 'SHAPE']

    return mean_df


def prep_sdf_for_nearest(df, id_fld, weighting_points=None):
    """
    Given an input Spatially Enabled Dataframe, prepare it to work well with the nearest solver.
    :param df: Spatially Enabled Dataframe with really any geometry.
    :param id_fld: Field uniquely identifying each of location to be used for routing to nearest.
    :param weighting_points: Spatially Enabled Dataframe of points for calculating weighted centroids.
    :return: Spatially Enabled Dataframe of points with correct columns for routing to nearest.
    """
    # par down the input dataframe to just the columns needed
    df = df[[id_fld, 'SHAPE']].copy()

    # rename the columns to follow the schema needed for routing
    df.columns = ['ID', 'SHAPE']

    # if the geometry is polygons and there is a weighting points spatially enabled dataframe
    if df.spatial.geometry_type == ['polygon'] and weighting_points is not None:

        # calculate the weighted centroid for the polygons
        df = weighted_polygon_centroid(df, weighting_points)

    # otherwise, if the geometry is not points, we still need points, so just get the geometric centroids
    # TODO: Account for polygons NOT always being in WGS 84
    elif df.spatial.geometry_type != ['point'] and weighting_points is None:
        df['SHAPE'] = df['SHAPE'].apply(
            lambda geom: Geometry({'x': geom.centroid[0], 'y': geom.centroid[1], 'spatialReference': {'wkid': 4326}}))

    # add a second column for the ID as Name
    df['Name'] = df['ID']

    # ensure the geometry is correctly being recognized
    df.spatial.set_geometry('SHAPE')

    # set the order of the columns and return
    return df[['ID', 'Name', 'SHAPE']].copy()


def prep_feature_service_for_nearest(item_id, id_fld, gis):
    """
    Using a feature service as the input, format the schema for closest routing and return as a Spatially Enabled
        Dataframe.
    :param item_id: The item ID in the Web GIS the feature service can be found at.
    :param id_fld: The ID field uniquely identifying each resource.
    :param gis: The Web GIS object instance to use for connecting to get the ba_data.
    :return: Spatially Enabled Dataframe with correct schema for closest network analysis.
    """
    df = gis.content.get(item_id).layers[0].query(out_sr=4326, as_df=True)
    return prep_sdf_for_nearest(df, id_fld)


def _get_max_near_dist_arcpy(origin_lyr):
    """
    Get the maximum geodesic distance between stores.
    """
    # create a location for temporary ba_data
    temp_table = r'in_memory\near_table_{}'.format(uuid.uuid4().hex)

    # if only one location, cannot generate a near table, and default to 120 miles
    if int(arcpy.management.GetCount(origin_lyr)[0]) <= 1:
        max_near_dist = 120 * 1609.34

    else:
        # use arcpy to get a table of all distances between stores
        near_tbl = arcpy.analysis.GenerateNearTable(
            in_features=origin_lyr,
            near_features=origin_lyr,
            out_table=temp_table,
            method="GEODESIC"
        )[0]

        # get the maximum near distance, which will be in meters
        meters = max([row[0] for row in arcpy.da.SearchCursor(near_tbl, 'NEAR_DIST')])

        # remove the temporty table to ensure not stuff lying around and consuming RAM
        arcpy.management.Delete(temp_table)

        # get the maximum near distance (in meters)
        max_near_dist = meters * 0.00062137

    return max_near_dist


def _get_closest_df_arcpy(origin_df, dest_df, dest_count, network_dataset, max_dist=None):
    """
    Succinct function wrapping find_closest_facilities with a little ability to handle network and server hiccups
    :param origin_df: Origin points Spatially Enabled Dataframe
    :param dest_df: Destination points Spatially Enabled Dataframe
    :param dest_count: Destination points Spatially Enabled Dataframe
    :param network_dataset: Path to ArcGIS Network dataset.
    :param max_dist: Maximum nearest routing distance in miles.
    :return: Spatially Enabled Dataframe of solved closest facility routes.
    """
    # set the workspace so networking has a place to save results
    temp_dir = tempfile.gettempdir()
    temp_gdb = os.path.join(temp_dir, 'temp.gdb')
    if not arcpy.Exists(temp_gdb):
        arcpy.management.CreateFileGDB(temp_dir, 'temp.gdb')
    arcpy.env.workspace = temp_gdb

    # save the spatially enabled dataframes as feature classes for routing analysis
    origin_fc = origin_df.spatial.to_featureclass(os.path.join(temp_gdb, f'origin_fc_{uuid.uuid4().hex}'))
    dest_fc = dest_df.spatial.to_featureclass(os.path.join(temp_gdb, f'dest_fc_{uuid.uuid4().hex}'))

    # convert to a layer
    origin_lyr = arcpy.management.MakeFeatureLayer(origin_fc)[0]

    # if the maximum near distance is desired
    if max_dist:

        # get the maximum near distance
        max_dist = _get_max_near_dist_arcpy(dest_fc)

        # create the network analysis layer
        na_lyr = arcpy.na.MakeClosestFacilityAnalysisLayer(
                network_data_source=network_dataset,
                layer_name=None,
                travel_mode="Driving Distance",
                travel_direction="TO_FACILITIES",
                cutoff=max_dist,
                number_of_facilities_to_find=dest_count,
                line_shape="ALONG_NETWORK",
                accumulate_attributes="Miles;TravelTime"
        )[0]

        # select the contributing geographies only within the search distance to speed up add locations
        arcpy.management.SelectLayerByLocation(
            in_layer=origin_lyr,
            overlap_type='WITHIN_A_DISTANCE',
            select_features=dest_fc,
            search_distance='{} miles'.format(max_dist)
        )

    # if no max near dist
    else:

        # create the network analysis layer
        na_lyr = arcpy.na.MakeClosestFacilityAnalysisLayer(
            network_data_source=network_dataset,
            layer_name=None,
            travel_mode="Driving Distance",
            travel_direction="TO_FACILITIES",
            number_of_facilities_to_find=dest_count,
            line_shape="ALONG_NETWORK",
            accumulate_attributes="Miles;TravelTime"
        )[0]

        # ensure nothing is selected in the contributing areas
        arcpy.SelectLayerByAttribute_management(origin_lyr, "CLEAR_SELECTION")

    # get a dictionary of all the layer resource names
    na_lyr_dict = arcpy.na.GetNAClassNames(na_lyr)

    # add the stores as destinations to the analysis layer
    arcpy.na.AddLocations(
            in_network_analysis_layer=na_lyr,
            sub_layer=na_lyr_dict['Facilities'],
            in_table=dest_fc,
            search_tolerance="5000 Meters",
            match_type="MATCH_TO_CLOSEST",
            append=False
    )

    # now, add area centroids to the analysis layer
    arcpy.na.AddLocations(
        in_network_analysis_layer=na_lyr,
        sub_layer=na_lyr_dict['Incidents'],
        in_table=origin_lyr,
        search_tolerance="5000 Meters",
        match_type="MATCH_TO_CLOSEST",
        append=False
    )

    # run the solve, and get comfortable
    arcpy.na.Solve(na_lyr)

    # convert the routes to a spatially enabled dataframe to send back
    closest_fc = arcpy.Describe(na_lyr_dict['CFRoutes']).catalogPath
    closest_df = GeoAccessor.from_featureclass(closest_fc)

    # get rid of the extra empty columns the local network solve adds
    closest_df.dropna(axis=1, how='all', inplace=True)

    # populate the origin and destination fields so the schema matches what online solve returns
    name_srs = closest_df.Name.str.split(' - ')
    closest_df.IncidentID = name_srs.apply(lambda val: val[0])
    closest_df.FacilityID = name_srs.apply(lambda val: val[1])

    return closest_df


def _get_closest_csv(origin_df, dest_df, dest_count, gis, max_dist=None):
    """
    Enables batch processing of get closest by saving iterative results to a temp csv file to avoid memory overruns.
    :param origin_df: Origin points Spatially Enabled Dataframe
    :param dest_df: Destination points Spatially Enabled Dataframe
    :param dest_count: Destination points Spatially Enabled Dataframe
    :param gis: ArcGIS Web GIS object instance with networking configured.
    :param max_dist: Maximum nearest routing distance in miles.
    :return: String path to CSV of solved closest facility routes.
    """
    out_csv_path = f'{temp_file_root}_{uuid.uuid4().hex}.csv'
    closest_df = _get_closest_df_arcpy(origin_df, dest_df, dest_count, gis, max_dist)
    closest_df.to_csv(out_csv_path)
    return out_csv_path


def reformat_closest_result_dataframe(closest_df):
    """
    Reformat the schema, dropping unneeded coluns and renaming those kept to be more in line with this workflow.
    :param closest_df: Dataframe of the raw output routes from the find closest analysis.
    :return: Spatially Enabled Dataframe reformatted.
    """
    # create a list of columns containing proximity metrics
    proximity_src_cols = [col for col in closest_df.columns if col.startswith('Total_')]

    # if both miles and kilometers, drop miles, and keep kilometers
    miles_lst = [col for col in proximity_src_cols if 'miles' in col.lower()]
    kilometers_lst = [col for col in proximity_src_cols if 'kilometers' in col.lower()]
    if len(miles_lst) and len(kilometers_lst):
        proximity_src_cols = [col for col in proximity_src_cols if col != miles_lst[0]]

    # filter the dataframe to just the columns we need
    src_cols = ['IncidentID', 'FacilityRank', 'FacilityID'] + proximity_src_cols + ['SHAPE']
    closest_df = closest_df[src_cols].copy()

    # replace total in proximity columns for naming convention
    proximity_out_cols = [col.lower().replace('total', 'proximity') for col in proximity_src_cols]

    # rename the columns for the naming convention
    out_cols = ['origin_id', 'destination_rank', 'destination_id'] + proximity_out_cols + ['SHAPE']
    closest_df.columns = out_cols

    return closest_df


def explode_closest_rank_dataframe(closest_df, origin_id_col='origin_id', rank_col='destination_rank',
                                   dest_id_col='destination_id'):
    """
    Effectively explode out or pivot the ba_data so there is only a single record for each origin.
    :param closest_df: Spatially Enabled Dataframe reformatted from the raw output of find nearest.
    :param origin_id_col: Column uniquely identifying each origin - default 'origin_id'
    :param rank_col: Column identifying the rank of each destination - default 'destination_rank'
    :param dest_id_col: Column uniquely identifying each destination - default 'destination_id'
    :return: Dataframe with a single row for each origin with multiple destination metrics for each.
    """
    # create a dataframe to start working with comprised of only the unique origins to start with
    origin_dest_df = pd.DataFrame(closest_df[origin_id_col].unique(), columns=[origin_id_col])

    # get a list of the proximity columns
    proximity_cols = [col for col in closest_df.columns if col.startswith('proximity_')]

    # iterate the closest destination ranking
    for rank_val in closest_df[rank_col].unique():

        # filter the dataframe to just the records with this destionation ranking
        rank_df = closest_df[closest_df[rank_col] == rank_val]

        # create a temporary dataframe to begin building the columns onto
        df_temp = rank_df[origin_id_col].to_frame()

        # iterate the relevant columns
        for col in [dest_id_col] + proximity_cols:
            # create a new column name from the unique value and the original row name
            new_name = f'{col}_{rank_val:02d}'

            # filter the ba_data in the column with the unique value
            df_temp[new_name] = rank_df[col].values

        # set the index to the origin id for joining
        df_temp.set_index(origin_id_col, inplace=True)

        # join the temporary dataframe to the master
        origin_dest_df = origin_dest_df.join(df_temp, on=origin_id_col)

    return origin_dest_df


def get_closest_solution(origins, origin_id_fld, destinations, dest_id_fld, gis=None,
                                                network_dataset=None, destination_count=4):
    """
    Create a closest destination dataframe using origin and destination Spatially Enabled Dataframes, but keep
        each origin and destination still in a discrete row instead of collapsing to a single row per origin. The main
        reason to use this is if needing the geometry for visualization.
    :param origins: Spatially Enabled Dataframe | String path to Feature Class | String url to Feature Service |
        String Web GIS Item ID
        Origins in one of the supported input formats.
    :param origin_id_fld: Column in the origin points Spatially Enabled Dataframe uniquely identifying each feature
    :param destinations: Spatially Enabled Dataframe | String path to Feature Class | String url to Feature Service |
        String Web GIS Item ID
        Destination points in one of the supported input formats.
    :param dest_id_fld: Column in the destination points Spatially Enabled Dataframe uniquely identifying each feature
    :param gis: ArcGIS Web GIS object instance with networking configured.
    :param network_dataset: Path to ArcGIS Network dataset.
    :param destination_count: Integer number of destinations to search for from every origin point.
    :return: Spatially Enabled Dataframe with a row for each origin id, and metrics for each nth destinations.
    """
    # check to environment against inputs to determine if networking locally or remotely
    if gis is not None and network_dataset is not None:
        raise Exception('You can either specify a GIS object instance OR a Network Dataset, but not both.')

    # ensure the inputs are a spatially enabled dataframe
    origin_df = utils.get_dataframe(origins, gis)
    dest_df = utils.get_dataframe(destinations, gis)

    # ensure the dataframes are in the right schema and have the right geometry
    origin_df = prep_sdf_for_nearest(origin_df, origin_id_fld)
    dest_df = prep_sdf_for_nearest(dest_df, dest_id_fld)

    # create an environment object instance for checking settings later
    env = utils.Environment(gis)

    if gis is not None:

        raise Exception('Using remote network routing is not yet implemented.')

        # # get the limitations on the networking rest endpoint, and scale the analysis based on this
        # max_records = gis._con.get(gis.properties.helperServices.asyncClosestFacility.url.rpartition('/')[0])[
        #     'maximumRecords']
        # max_origin_cnt = math.floor(max_records / destination_count)
        #
        # # if necessary, batch the analysis based on the size of the input ba_data, and the number of destinations per origin
        # if len(origin_df.index) > max_origin_cnt:
        #
        #     # process each batch, and save the results to a temp file in the temp directory
        #     closest_csv_list = [_get_closest_csv(origin_df.iloc[idx:idx + max_origin_cnt], dest_df, destination_count, gis)
        #                         for idx in range(0, len(origin_df.index), max_origin_cnt)]
        #
        #     # load all the temporary files into dataframes and combine them into a single dataframe
        #     closest_df = pd.concat([pd.read_csv(closest_csv) for closest_csv in closest_csv_list])
        #
        #     # clean up the temp files
        #     for csv_file in closest_csv_list:
        #         os.remove(csv_file)
        #
        # else:
        #     closest_df = _get_closest_df(origin_df, dest_df, destination_count, gis)

    elif network_dataset is not None:

        if 'Network' in env.arcpy_extensions:
            env.arcpy_checkout_extension('Network')
        else:
            raise Exception('To perform network routing locally you must have access to the ArcGIS Network Analyst '
                            'extension. It appears this extension is either not installed or not licensed.')

        # run the closest analysis locally
        closest_df = _get_closest_df_arcpy(origin_df, dest_df, destination_count, network_dataset)

    # reformat the results to be a single row for each origin
    closest_df = reformat_closest_result_dataframe(closest_df)

    return closest_df


def closest_dataframe_from_origins_destinations(origins, origin_id_fld, destinations, dest_id_fld, gis=None,
                                                network_dataset=None, destination_count=4):
    """
    Create a closest destination dataframe using origin and destination Spatially Enabled Dataframes.
    :param origins: Spatially Enabled Dataframe | String path to Feature Class | String url to Feature Service |
        String Web GIS Item ID
        Origins in one of the supported input formats.
    :param origin_id_fld: Column in the origin points Spatially Enabled Dataframe uniquely identifying each feature
    :param destinations: Spatially Enabled Dataframe | String path to Feature Class | String url to Feature Service |
        String Web GIS Item ID
        Destination points in one of the supported input formats.
    :param dest_id_fld: Column in the destination points Spatially Enabled Dataframe uniquely identifying each feature
    :param gis: ArcGIS Web GIS object instance with networking configured.
    :param network_dataset: Path to ArcGIS Network dataset.
    :param destination_count: Integer number of destinations to search for from every origin point.
    :return: Spatially Enabled Dataframe with a row for each origin id, and metrics for each nth destinations.
    """
    # get a closest dataframe with all the origin and destination pairs in a discrete row
    closest_df = get_closest_solution(origins, origin_id_fld, destinations, dest_id_fld, gis=gis,
                                      network_dataset=network_dataset, destination_count=destination_count)

    # collapse the solutions to a single record for each origin location
    origin_dest_df = explode_closest_rank_dataframe(closest_df)

    return origin_dest_df
