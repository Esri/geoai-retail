"""
Streamline the enrichment process so it can be run autonomously from ArcGIS Pro
"""
import os
import arcpy

import sys
sys.path.append('../src')
from geoai_retail import enrich

data_dir = os.path.abspath(r'D:\projects\nike-sprint4\data')
int_dir = os.path.join(data_dir, 'interim')
ext_dir = os.path.join(data_dir, 'external')
gdb = os.path.join(int_dir, 'interim.gdb')

arcpy.management.Delete(arcpy.env.scratchGDB)

input_enrich_feature_class = os.path.join(gdb, 'Blocks_analysis')
output_enrich_feature_class = os.path.join(gdb, 'Blocks_enrich')
enrichment_csv = os.path.join(ext_dir, 'enrichment_variables.csv')

enrichment_fc = enrich.using_csv_variable_file(input_enrich_feature_class, enrichment_csv, output_enrich_feature_class)
