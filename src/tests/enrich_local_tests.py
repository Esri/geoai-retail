import logging
import os

import arcpy
import pandas as pd
import pytest

from geoai_retail import enrich_local as enrich

enrich_template_fc = './test_data.gdb/block_groups_enrich_template'
block_groups_fc = './test_data.gdb/block_groups'
block_groups_big_fc = './test_data.gdb/block_groups_big'
blocks_fc = './test_data.gdb/blocks'
collection = 'KeyUSFacts'

test_enrich_fields = ['F5yearincrements_POP18UP_CY', 'F5yearincrements_MEDAGE_CY', 'F5yearincrements_MEDAGE10',
                      'clothing_X5001_X', 'hispanicorigin_HISPPOP_CY', 'householdincome_MEDHINC_CY',
                      'householdincome_PCI_CY', 'SpendingTotal_X1001_X', 'SpendingTotal_X15001_X']


@pytest.fixture
def single_feature():
    fc = block_groups_fc
    first_oid = [val for val in arcpy.da.SearchCursor(fc, 'OID@')][0][0]
    sql_str = f'{arcpy.Describe(fc).OIDFieldName} = {first_oid}'
    return arcpy.analysis.Select(fc, 'memory/first_feature', sql_str)[0]


def test_enrich_from_enriched():
    enrich_df = enrich.enrich_from_enriched(enrich_template_fc, block_groups_fc, 'ID')
    contains_lst = [f in enrich_df.columns for f in test_enrich_fields]
    assert(all(contains_lst))


def test_enrich_from_enriched_over_1500():
    enrich_df = enrich.enrich_from_enriched(enrich_template_fc, blocks_fc)
    contains_lst = [f in enrich_df.columns for f in test_enrich_fields]
    assert(all(contains_lst))


def test_enriched_fields_to_csv():
    enrich_csv = enrich.enriched_fields_to_csv(enrich_template_fc,
                                               os.path.join(arcpy.env.scratchFolder, 'temp_test.csv'))
    enrich_df = pd.read_csv(enrich_csv)
    out_fields = enrich_df['enrich_field_name'].values
    contains_lst = [f in out_fields for f in test_enrich_fields]
    os.remove(enrich_csv)
    assert (all(contains_lst))


def test_enrich_from_fields_table():
    enrich_tbl = enrich._get_enrich_var_df(enrich_template_fc)
    enrich_df = enrich.enrich_from_fields_table(enrich_tbl, block_groups_fc)
    contains_lst = [f in enrich_df.columns for f in test_enrich_fields]
    assert(all(contains_lst))


def test_enrich_all_single_feature(single_feature):
    enrich_df = enrich.enrich_all(single_feature, id_field='ID')
    assert isinstance(enrich_df, pd.DataFrame)


def test_enrich_all_small():
    enrich_df = enrich.enrich_all(block_groups_fc, id_field='ID')
    assert isinstance(enrich_df, pd.DataFrame)


def test_enrich_all_over_1500():
    enrich_df = enrich.enrich_all(blocks_fc, id_field='ID')
    assert isinstance(enrich_df, pd.DataFrame)


def test_enrich_all_big():
    enrich_df = enrich.enrich_all(block_groups_big_fc, id_field='ID')
    assert isinstance(enrich_df, pd.DataFrame)


def test_enrich_collection_small():
    enrich_df = enrich.enrich_by_collection(collection, block_groups_fc, id_field='ID')
    assert isinstance(enrich_df, pd.DataFrame)


def test_enrich_collection_over_1500():
    enrich_df = enrich.enrich_by_collection(collection, blocks_fc, id_field='ID')
    assert isinstance(enrich_df, pd.DataFrame)


def test_enrich_collection_big():
    enrich_df = enrich.enrich_by_collection(collection, block_groups_big_fc, id_field='ID')
    assert isinstance(enrich_df, pd.DataFrame)
