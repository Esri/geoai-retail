import os

import arcpy

from geoai_retail import enrich_local as enrich

enrich_template_fc = './test_data.gdb/block_groups_enrich_template'
block_groups_fc = './test_data.gdb/block_groups'
blocks_fc = './test_data.gdb/blocks'


def test_enrich_from_enriched():

    enrich_out = enrich.enrich_from_enriched(enrich_template_fc, block_groups_fc, 'memory/test_enriched')

    enrich_fields = ['F5yearincrements_POP18UP_CY', 'F5yearincrements_MEDAGE_CY', 'F5yearincrements_MEDAGE10',
                     'clothing_X5001_X', 'hispanicorigin_HISPPOP_CY', 'householdincome_MEDHINC_CY',
                     'householdincome_PCI_CY', 'SpendingTotal_X1001_X', 'SpendingTotal_X15001_X']
    out_fields = [f.name for f in arcpy.ListFields(enrich_out)]
    contains_lst = [f in out_fields for f in enrich_fields]

    assert(all(contains_lst))


def test_enrich_from_enriched_over_1500():

    enrich_out = enrich.enrich_from_enriched(enrich_template_fc, blocks_fc, 'memory/test_enriched')

    enrich_fields = ['F5yearincrements_POP18UP_CY', 'F5yearincrements_MEDAGE_CY', 'F5yearincrements_MEDAGE10',
                     'clothing_X5001_X', 'hispanicorigin_HISPPOP_CY', 'householdincome_MEDHINC_CY',
                     'householdincome_PCI_CY', 'SpendingTotal_X1001_X', 'SpendingTotal_X15001_X']
    out_fields = [f.name for f in arcpy.ListFields(enrich_out)]
    contains_lst = [f in out_fields for f in enrich_fields]

    assert(all(contains_lst))


def test_enriched_fields_to_csv():

    enrich_csv = enrich.enriched_fields_to_csv(enrich_template_fc,
                                               os.path.join(arcpy.env.scratchFolder, 'temp_test.csv'))

    assert(os.path.exists(enrich_csv))


def test_enrich_from_fields_table():

    enrich_tbl = enrich._get_enrich_var_df(enrich_template_fc)

    enrich_out = enrich.enrich_from_fields_table(enrich_tbl, block_groups_fc, 'memory/enrich_test')

    enrich_fields = ['F5yearincrements_POP18UP_CY', 'F5yearincrements_MEDAGE_CY', 'F5yearincrements_MEDAGE10',
                     'clothing_X5001_X', 'hispanicorigin_HISPPOP_CY', 'householdincome_MEDHINC_CY',
                     'householdincome_PCI_CY', 'SpendingTotal_X1001_X', 'SpendingTotal_X15001_X']
    out_fields = [f.name for f in arcpy.ListFields(enrich_out)]
    contains_lst = [f in out_fields for f in enrich_fields]

    assert(all(contains_lst))
