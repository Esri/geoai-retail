"""
Methods to analyze hypotehtical scenarios.
"""

from arcgis.geometry import Point
import pandas as pd

from ba_data_paths import ba_data
from geoai_retail import proximity_local as proximity
from geoai_retail.utils import get_dataframe


def _get_min_uid(df, uid_field, start_value=None):
    match = False
    idx = start_value if start_value else 1
    while match == False:
        if idx not in df[uid_field].astype('int64').values:
            uid = idx
            match = True
        elif idx >= df[uid_field].astype('int64').max():
            idx = idx + 1000
        else:
            idx = idx + 1
    return uid


def get_add_new_closest_dataframe(origins:[str, pd.DataFrame], origin_id_field:str, destinations:[str, pd.DataFrame],
                                  destination_id_field:str,  closest_table:[str, pd.DataFrame], new_destination:Point,
                                  origin_weighting_points:[str, pd.DataFrame]=None) -> pd.DataFrame:
    """
    Calculate the impact of a location being added to the retail landscape.
    :param origins: Polygons in a Spatially Enabled Dataframe or string path to Feature Class delineating starting
        locations for closest analysis.
    :param origin_id_field: Field or column name used to uniquely identify each origin.
    :param destinations: Spatially Enabled Dataframe or string path to Feature Class containing all destinations.
    :param destination_id_field: Field or column name used to uniquely identify each destination location.
    :param closest_table: Path to CSV, table, or Dataframe containing solution for nearest locations.
    :param new_destination: Geometry of new location being added to the retail landscape.
    :param origin_weighting_points: Points potentially used to calculate a centroid based on population density
        represented by the weighting points instead of simply the geometric centroid.
    :return: Data frame with rebalanced closest table only for affected origins.
    """
    # read in the existing closest table solution
    closest_orig_df = pd.read_csv(closest_table)

    # get a list of the destination columns from the existing closest table
    dest_cols = [col for col in closest_orig_df.columns if col.startswith('destination_id')]

    # get a count of the nth number of locations solved for
    dest_count = len(dest_cols)

    # load the original origins into a dataframe and format it for analysis
    origin_df = get_dataframe(origins)
    origin_df = proximity.prep_sdf_for_nearest(origin_df, origin_id_field, origin_weighting_points)

    # load the original destinations into a dataframe and format it for analysis
    dest_df = get_dataframe(destinations)
    dest_df = proximity.prep_sdf_for_nearest(dest_df, destination_id_field)

    # create new destination dataframe for analysis
    new_id = _get_min_uid(origin_df, 'ID')  # creates lowest numbered id available, or 1000 higher than top value
    new_df = pd.DataFrame([[new_id, new_id, new_destination]], columns=['ID', 'Name', 'SHAPE'])
    new_df.spatial.set_geometry('SHAPE')

    # get the nth closest destination locations to the new destination location
    closest_dest_df = proximity.get_closest_solution(new_df, 'ID', dest_df, 'ID',
                                                     network_dataset=ba_data.usa_network_dataset,
                                                     destination_count=dest_count)

    # get the destination ids of the existing nth closest destinations
    dest_subset_ids = closest_dest_df['destination_id'].values

    # by cross referencing from the destination ids, get the origin ids allocated to the exiting locations
    subset_origin_ids = pd.concat([closest_orig_df[closest_orig_df[dest_col].isin(dest_subset_ids)]['origin_id']
                                   for dest_col in dest_cols]).unique()

    # get a subset dataframe of the origins allocated to the closest nth locations
    subset_origin_df = origin_df[origin_df['ID'].astype('int64').isin(subset_origin_ids)].copy()

    # add the new location to the destination dataframe
    dest_analysis_df = pd.concat([dest_df, new_df], sort=False)
    dest_analysis_df.spatial.set_geometry('SHAPE')
    dest_analysis_df.reset_index(inplace=True, drop=True)

    # solve for the closest destination to the affected area
    closest_subset_df = proximity.closest_dataframe_from_origins_destinations(subset_origin_df, 'ID', dest_analysis_df,
                                                                              'ID',
                                                                              network_dataset=ba_data.usa_network_dataset,
                                                                              destination_count=dest_count)
    return closest_subset_df


def get_remove_existing_closest_dataframe(origins: [str, pd.DataFrame], origin_id_field: str,
                                          destinations: [str, pd.DataFrame],
                                          destination_id_field: str, closest_table: [str, pd.DataFrame],
                                          remove_destination_id: str,
                                          origin_weighting_points: [str, pd.DataFrame] = None) -> pd.DataFrame:
    """
    Calculate the impact of a location being removed from the retail landscape.
    :param origins: Polygons in a Spatially Enabled Dataframe or string path to Feature Class delineating starting
        locations for closest analysis.
    :param origin_id_field: Field or column name used to uniquely identify each origin.
    :param destinations: Spatially Enabled Dataframe or string path to Feature Class containing all destinations.
    :param destination_id_field: Field or column name used to uniquely identify each destination location.
    :param closest_table: Path to CSV, table, or Dataframe containing solution for nearest locations.
    :param remove_destination_id: Unique ID of location being removed from the retail landscape.
    :param origin_weighting_points: Points potentially used to calculate a centroid based on population density
        represented by the weighting points instead of simply the geometric centroid.
    :return: Data frame with rebalanced closest table only for affected origins.
    """
    # read in the existing closest table solution
    closest_orig_df = pd.read_csv(closest_table)

    # get a list of the destination columns from the existing closest table
    dest_cols = [col for col in closest_orig_df.columns if col.startswith('destination_id')]

    # get a count of the nth number of locations solved for
    dest_count = len(dest_cols)

    # load the original origins into a dataframe and format it for analysis
    origin_df = get_dataframe(origins)
    origin_df = proximity.prep_sdf_for_nearest(origin_df, origin_id_field, origin_weighting_points)

    # load the original destinations into a dataframe and format it for analysis
    dest_df = get_dataframe(destinations)
    dest_df = proximity.prep_sdf_for_nearest(dest_df, destination_id_field)

    # extract the location from the destinations to be removed and put it in a separate dataframe
    new_df = dest_df[dest_df['ID'] == str(remove_destination_id)].copy()

    # remove the location from the destinations
    dest_df = dest_df[dest_df['ID'] != str(remove_destination_id)].copy()

    # get the nth closest destination locations to the new destination location
    closest_dest_df = proximity.get_closest_solution(new_df, 'ID', dest_df, 'ID',
                                                     network_dataset=ba_data.usa_network_dataset,
                                                     destination_count=dest_count)

    # get the destination ids of the existing nth closest destinations
    dest_subset_ids = closest_dest_df['destination_id'].values

    # by cross referencing from the destination ids, get the origin ids allocated to the exiting locations
    subset_origin_ids = pd.concat([closest_orig_df[closest_orig_df[dest_col].isin(dest_subset_ids)]['origin_id']
                                   for dest_col in dest_cols]).unique()

    # get a subset dataframe of the origins allocated to the closest nth locations
    subset_origin_df = origin_df[origin_df['ID'].astype('int64').isin(subset_origin_ids)].copy()

    # solve for the closest destination to the affected area
    closest_subset_df = proximity.closest_dataframe_from_origins_destinations(subset_origin_df, 'ID', dest_df,
                                                                              'ID',
                                                                              network_dataset=ba_data.usa_network_dataset,
                                                                              destination_count=dest_count)

    return closest_subset_df

