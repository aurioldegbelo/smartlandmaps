# -*- coding: utf-8 -*-
"""
Created on January 20, 2022; last modified on February 02, 2023.

@author: Auriol Degbelo and Gergely Vassányi

Note: the entry function, if any, is specified last. The keyword (ENTRY) is mentioned in the comments
describing that function. The entry function is the one that is called first among all functions.
All other functions are listed in the alphabetical order

Variables of the approach
-----



Steps
-----
generate contours (e.g. only the extreme outer contours, or contours with inner polygons)
skeletonize the contours
georeference the polygons
convert the utm coordinates to wgs84
generate geojson files
-----
"""


import cv2 # read image, create contours
import geojson
import numpy as np # mathematical functions on multi-dimensional arrays and matrices
import pyproj
import shapely.geometry

from geojson import dump # write a geojson file
from osgeo import gdal
from pyproj import Geod
from shapely.geometry import Polygon # create a polygon
from shapely.geometry import shape
from shapely.ops import transform # coordinate conversion
from shapely.validation import make_valid

from skimage.morphology import skeletonize # skeletonize a binary image
import os


import time 
# starting time
start = time.time()


# generate contours from masks
def contours_from_mask (image):     
    # we are interested in the contours of the inner polygons only. for this, we generate both outer and inner contours and remove the outer ones through filtering
    # RETR_EXTERNAL, see doc at https://docs.opencv.org/4.x/d9/d8b/tutorial_py_contours_hierarchy.html
    # https://docs.opencv.org/2.4/modules/imgproc/doc/structural_analysis_and_shape_descriptors.html?highlight=findcontours#findcontours
    
    inner_polygons = []

    # generate inner+outer contours
    contours_ei, hierarchy_ei = cv2.findContours(image, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    contours_ei = map(np.squeeze, contours_ei)  # removing redundant dimensions
    li_contours_ei = list(contours_ei) # convert to list

    # generate outer contours only
    contours_e, hierarchy_e = cv2.findContours(image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours_e = map(np.squeeze, contours_e)  # removing redundant dimensions
    li_contours_e = list(contours_e)  # convert to list

    # go through all inner+outer contours
    for item in li_contours_ei:
        
        if (is_relevant_contour(item, li_contours_e)): # keep only those that are relevant (i.e. number of points > 3 and no outer contour)
            inner_polygons.append(item)
                
    return inner_polygons

# georeference pixel coordinates, formula from https://gdal.org/tutorials/geotransforms_tut.html
def georeference (contour, gt): 
    georef =  []
    for point in contour: 
        x_geo = gt[0] + point[0] * gt[1] + point[1] * gt[2]
        y_geo = gt[3] + point[0] * gt[4] + point[1] * gt[5]
        georef.append([x_geo, y_geo])
    return georef

# check if the file provided as input is of a given format
def of_format(data_format, source_file): 
    
    file_format = source_file.rsplit(".", 1)[1]
    
    if (file_format == data_format): 
        return True
    else:
        return False

# keep only polygons that have an area greater than a threshold
def filter_by_geodesic_area (threshold, polygons):
    
    # use the WGS84 ellipsoid to calculate the geodesic area
    geod = Geod(ellps="WGS84")

    filtered_polygons = [poly for poly in polygons 
                         if abs(geod.geometry_area_perimeter(poly)[0]) >= threshold]
    
    return filtered_polygons


# check if the contour is relevant for further processing
def is_relevant_contour (item, all_external_contours): 
    # remove contours (i.e. polygons) that have only two points    
    if (len(item)) < 3: 
        return False
    else:
        for i in all_external_contours: # remove external contours
            if np.array_equal(item, i): 
                return False
        return True

def parcel_ID(parcel): 

    return parcel['properties']['parcelID']   


# permute coordinate of polygons (if needed)
def permute_coordinates (x):
    # map_tuples executes a function over all coordinates: https://geojson.readthedocs.io/en/latest/#map-tuples
    return geojson.utils.map_tuples(lambda c: (c[1], c[0]), x)

# convert from utm coordinate to wgs84
def towgs84 (x, source_epsg): 
    utm = pyproj.CRS(source_epsg)
    wgs84 = pyproj.CRS('EPSG:4326')
    project = pyproj.Transformer.from_crs(utm, wgs84).transform
    poly = transform(project, x)
    return poly

def postprocess (runs_num, raw_path, douglas_thresh): 
    # Postprocessing : import the raw polygons geojson, perform generalization, 
    # clean polygons without attributes and export as geojson using GRASS GIS 7.8.
    
    print("Post-processing...") 
    ctstr=str(runs_num)
    out_path=raw_path[:-12]+".geojson"

    mygisdb = '/tmp/grassdata'+ctstr
    mylocation = 'world'+ctstr
    mymapset = 'user'+ctstr

    from grass_session import Session
    from grass.script import core as gcore
    import grass.script as gscript
    import grass.script.setup as gsetup
    # import grass python libraries
    from grass.pygrass.modules.shortcuts import vector as v

    # create a PERMANENT mapset object: create a Session instance
    PERMANENT = Session()
    PERMANENT.open(gisdb=mygisdb, location=mylocation, create_opts='EPSG:4326')
    # exit from PERMANENT right away in order to perform analysis in our own mapset
    PERMANENT.close()
    # create a new mapset in the same location
    user = Session()
    user.open(gisdb=mygisdb, location=mylocation, mapset=mymapset, create_opts='')

    #GRASS CAN'T REPLACE EXISTING NAMES, ALWAYS NEED TO USE NEW ONES FOR EVERY STEP
    #FOR THIS REASON I INTRODUCE A COUNTER TO BE USED IN NAMES
    #Use underscores in tool names
    v.in_ogr(input=raw_path, output="read"+ctstr, overwrite = True, snap=1e-10)
    v.generalize(input='read'+ctstr, method='douglas', threshold=1e-6, output='gen'+ctstr, overwrite = True)
    v.clean(input='gen'+ctstr, tool='rmarea', threshold=1, output='cl'+ctstr)
    v.generalize(input='cl'+ctstr, method='douglas', threshold=5e-6, output='gfin'+ctstr, overwrite = True)
    v.out_ogr(input='gfin'+ctstr, output=out_path, format='GeoJSON')
    
    print("Post-processing finished, output is exported at: ", out_path) 

    

# (ENTRY) function to generate polygons as geojson files - it reuses the functions defined above
def generate_polygons (geotiff_path, boundaries_path, source_epsg, geojson_path, 
            area_thresh, runs_num, douglas_thresh, delraw): 
    
    raw_path=geojson_path[:-5]+"_raw.geojson"
    kernel_size = 6
    
    n_dilations = 5
    
    # check if the input data is of type tif, display a warning, if not
    if (not of_format("tif", geotiff_path) and not of_format("tif", geotiff_path)):
        print(f"WARNING: {geotiff_path} is not a tif file - no meaninful geojson can be generated")
    
    # check if the boundaries file is of type tif, display a warning, if not
    if (not of_format("tif", boundaries_path) and not of_format("tif", boundaries_path)):
        print(f"WARNING: {boundaries_path} is not a tif file - the output geojson may contain some errors")
    
    # Read pixel to utm coordinate transformation parameters
    info = gdal.Info(geotiff_path, format='json')
    gt = info['geoTransform']
    
    # info messages
    print("Geotiff read from...", geotiff_path)
    print("Coordinate system info... \n\n\n", info)
    print("\n\n")    # read image with masks (= extracted boundaries)
    print("EPSG Code of the geotiff",  info['coordinateSystem']['wkt'].rsplit('ID["EPSG",')[-1].split(']]')[0])
    print("EPSG passed as parameter: ", source_epsg)

    # read the file containing the boundaries (i.e. labelled raster)
    img = cv2.imread(boundaries_path, 0)
    print("Boundaries read from...", boundaries_path)
    
    # post process the image - skip for now
    '''
    kernel = np.ones((kernel_size, kernel_size),np.uint8)

    morph1 = cv2.dilate(img, kernel, iterations = n_dilations) # 5 iterations during the week of September 12
    img_post = cv2.morphologyEx(morph1, cv2.MORPH_CLOSE, kernel)
    '''
    img_post = img
 
    print("Generating the skeleton from the image...")
    image = img_post/255.0 # skeletonize needs image with only 0 and 1 as values
    skel = skeletonize(image)
    skeleton = skel.astype(np.uint8) # we need a convertion to an unsigned byte for further processing
    skeleton*= 255 # if necessary, we may save the skeleton here
    
    
    # Generate contours from mask 
    contours = contours_from_mask(skeleton) 
    print("Done. Number of polygons from the image's skeleton: ", len(contours))
    
    print("Georefencing the polygons...")
    
    skel_polygons = []
    for cnt in contours: 
        if(len(cnt) >= 3): 
            # 1 - transform coordinates of contours into georeferenced (projected coordinates)
            # 2- build a polygon from the projected coordinates
            # 3- transform the projected coordinates into geographic coordinates
            poly_utm = Polygon(georeference(cnt, gt))
            # https://shapely.readthedocs.io/en/stable/manual.html#constructive-methods
            poly_buffer = poly_utm.buffer(0, join_style=2) # 2 = mitre
            poly_wgs84 = towgs84(poly_buffer, source_epsg) 
            new_polygon = poly_wgs84

            skel_polygons.append(new_polygon)
         
    parcels_hole = filter_by_geodesic_area(area_thresh, skel_polygons)  
    print(f"Number of parcels: {len(parcels_hole)}; min area per parcel: {area_thresh} m^2")
    
    #fixing the holes - Keeping the exterior ring only from every polygon
    #some polygons are multipolygons, so two options are needed
    parcels=[]
    for poly in parcels_hole:
        if poly.geom_type == 'MultiPolygon':
            try:
                Polygons = list(poly)# do multipolygon things.
                for multiparts in Polygons:
                    new_polygon = Polygon(multiparts.exterior.coords, holes=None)
                    parcels.append(new_polygon)
            except:
                print("a multipolygon is skipped, resolve this after testing")
            #Polygons = list(poly['geom'].iloc[0].geoms)# do multipolygon things.
        elif poly.geom_type == 'Polygon':
            new_polygon = Polygon(poly.exterior.coords, holes=None)
            parcels.append(new_polygon)
        else:
            print("Error: not a polygon")
    
    
   # Generate GeoJSON data
    geo_dict_pre = {}
    geo_dict_pre["type"] = "FeatureCollection"
    geo_dict_pre["features"] = [{"type": "Feature", 
                             "geometry": permute_coordinates(a),
                             "properties": { "parcelID": "n/a", "parcelType": "n/a"}} 
                             for a in [shapely.geometry.mapping(b) for b in parcels]]
    
    for index, parcel in enumerate(geo_dict_pre["features"]): 
        parcel['properties']['parcelID'] = index + 1
           
    geo_dict_final = geo_dict_pre
    print("Saving raw geojson file at...", raw_path) 
    
    # Save GeoJSON file
    # https://gis.stackexchange.com/questions/130963/write-geojson-into-a-geojson-file-with-python
    with open(raw_path, 'w') as f:
       dump(geo_dict_final, f)
    
    # run postprocessing
    postprocess (runs_num, raw_path, douglas_thresh) 

    # delete raw polygons if specified
    if delraw:
        os.remove(raw_path) 
        print("Raw polygons GeoJSON file deleted.")

# end time
end = time.time()

# total time taken
print(f"Runtime of the program: {end - start} seconds")
