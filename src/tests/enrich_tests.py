import os
import arcpy
from src.geoai_retail import enrich
import pandas as pd

test_dir = os.path.abspath('../ba_data/test')
test_gdb = os.path.join(test_dir, 'test.gdb')
zip_fc = os.path.join(test_gdb, 'zip_three_test')
zip_6k_fc = os.path.join(test_gdb, 'zip_6k_test')
zip_enriched_fc = os.path.join(test_gdb, 'zip_three_enriched')
enrich_vars_csv = os.path.join(test_dir, 'enrichment_variables.csv')

arcpy.env.overwriteOutput = True


def test_enrich_from_csv_feature_class():
    test_out_fc = 'memory/test_zip_enrich_fc'
    enriched_fc = enrich.using_csv_variable_file(zip_fc, enrich_vars_csv, test_out_fc)
    assert arcpy.Exists(enriched_fc)


def test_enrich_from_csv_layer():
    in_lyr = arcpy.management.MakeFeatureLayer(zip_fc)[0]
    test_out_fc = 'memory/test_zip_enrich_fc'
    enriched_fc = enrich.using_csv_variable_file(in_lyr, enrich_vars_csv, test_out_fc)
    assert arcpy.Exists(enriched_fc)


def test_get_enrich_dataframe_from_enriched_feature_class():
    df = enrich._get_enrich_dataframe_from_enriched_feature_class(zip_enriched_fc)
    assert isinstance(df, pd.DataFrame)


def test_enrich_using_existing_enriched_feature_class_as_template():
    template_fc = zip_enriched_fc
    in_fc = zip_fc
    out_fc = 'memory/enriched'
    enriched_fc = enrich.using_existing_enriched_feature_class_as_template(template_fc, in_fc, out_fc)
    assert arcpy.Exists(enriched_fc)


def test_enrich_from_csv_6k():
    test_out_fc = 'memory/test_zip_enrich_6k'
    enriched_fc = enrich.using_csv_variable_file(zip_6k_fc, enrich_vars_csv, test_out_fc)
    assert arcpy.Exists(enriched_fc)
