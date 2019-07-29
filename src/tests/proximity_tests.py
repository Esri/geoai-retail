import os
import sys
import tempfile
import pandas as pd

import arcpy
import pytest
from arcgis import GeoAccessor

import geoai_retail.proximity_local as proximity

network_dataset = r'D:\arcgis\ba_data\Data\Streets Data\NorthAmerica.gdb\Routing\Routing_ND'

arcpy.env.overwriteOutput = True


@pytest.fixture
def dest_df():
    return GeoAccessor.from_featureclass('./test_data.gdb/coffee_pdx')


@pytest.fixture
def study_dest(dest_df):
    return dest_df[dest_df['LOCNUM'] == '405004979']


@pytest.fixture
def origin_df():
    return GeoAccessor.from_featureclass('./test_data.gdb/block_groups')


@pytest.fixture
def study_origin(origin_df):
    return origin_df[origin_df['ID'] == '410670310043']


@pytest.fixture
def weighting_points():
    return './test_data.gdb/block_points'


def test_prep_sdf_for_nearest_no_weighting(origin_df):
    output = proximity.prep_sdf_for_nearest(origin_df, 'ID')
    assert((output.columns == ['ID', 'Name', 'SHAPE']).all() and len(output.index))


def test_get_closest_df(origin_df, dest_df):

    destination_count = 4

    origin_df = proximity.prep_sdf_for_nearest(origin_df, 'ID')
    dest_df = proximity.prep_sdf_for_nearest(dest_df, 'LOCNUM')

    closest_df = proximity._get_closest_df_arcpy(origin_df, dest_df, dest_count=destination_count,
                                                 network_dataset=network_dataset)

    assert(isinstance(closest_df, pd.DataFrame))


def test_closest_dataframe_from_origins_destinations(origin_df, dest_df):

    destination_count = 4

    closest_df = proximity.closest_dataframe_from_origins_destinations(origin_df, 'ID', dest_df, 'LOCNUM',
                                                                       network_dataset=network_dataset,
                                                                       destination_count=destination_count)

    assert (isinstance(closest_df, pd.DataFrame))
