import arcpy
from ba_tools import data

def _get_map():
    aprx = arcpy.mp.ArcGISProject('CURRENT')
    return aprx.listMaps()[0]

def add_block_groups():
    mp = _get_map()
    lyr = data.layer_block_group
    mp.addLayer(lyr)
    return lyr

def add_cbsas():
    mp = _get_map()
    lyr = data.layer_cbsa
    mp.addLayer(lyr)
    return lyr