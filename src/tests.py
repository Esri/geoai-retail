import unittest

import sys
from arcgis.features import GeoAccessor

sys.path.append('../src')
from inrix import TAZ

app_id = 'c9fa4c15-b9ab-46d4-bcd9-a3eb33dd0ff8'
hash_token = '919745fda981ddccb3ffc4f07863480e624cfa3d'
bg_pop_cent_path = 'D:\\projects\\geoai_retail\\data\\interim\\interim.gdb\\bg_pop_cent'
coffee_path = 'D:\\projects\\geoai_retail\\data\\raw\\raw.gdb\\coffee'


class TazTest(unittest.TestCase):

    def test_first_record(self):
        taz = TAZ(app_id, hash_token)
        df_pop_cent = GeoAccessor.from_featureclass(coffee_path)
        geom = df_pop_cent.iloc[0].SHAPE
        dest_df = taz.get_trip_destination_spatial_dataframe(geom.y, geom.x, '100m')
        self.assertTrue(len(dest_df.index))

if __name__ == '__main__':
    unittest.main()
