
from geopandas import gpd 
from shapely.geometry import Point, Polygon
import geojson


# paths to change:

attributes_filename = "output/"+'test_attr.json' # not important
stickers_json="output/numtest.geojson"
parcels_json="output/tab1gr_80_gen1cl.geojson"
polyidout='output/test_polyid.json' # not important
finaloutput="output/"+'test_parcels_with_attributes.json'
# get ODK Data

credentials = {'email': 'auriol.degbelo@uni-osnabrueck.de', 'password': '*UsEr*2021*'}
url_post = "https://smartlmaps.mooo.com/v1/sessions"
url_get = "https://smartlmaps.mooo.com/v1/projects/9/forms/1/submissions.csv"    # url of the form to retrieve data from
saving_path = attributes_filename

from analyzer_c_2022_10 import retrieve_odk_administrative_data, get_token

odk_data = retrieve_odk_administrative_data (url_get, get_token(url_post, credentials), saving_path)
#print(odk_data)

#join points to polys by location

from geopandas import gpd 

points = gpd.GeoDataFrame.from_file(stickers_json) # Stickers JSON  
polys = gpd.GeoDataFrame.from_file(parcels_json) # Parcels JSON
polyid = gpd.sjoin(polys, points, how='left') 
polyid.to_file(polyidout) # Polygons with ID-s output filename

print("Sticker ID successfully merged with polygons")


    # Join ODK data with polygons by sticker ID
# Before running check if data needs to be edited
import pandas as pd

odk_dataframe = pd.DataFrame.from_dict(odk_data)
odk_poly_merged = polyid.merge(odk_dataframe, left_on='Sticker_number', right_on='SpatialUnit-ID')
odk_poly_merged.to_file(finaloutput) # Parcels with all attributes from odk
