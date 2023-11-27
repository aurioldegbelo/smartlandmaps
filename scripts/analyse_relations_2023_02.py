"""
Created on TUE Nov 8 2022

@author: Gergely
"""

#Performs an analysis regarding spatial relations of point and polygon data and compares it to odk
#Writes a statistical report into a log file
def analyze_relations(raster_name, pointjson, polyjson, odk_data, logdir):
    from geopandas import gpd 
    import time 
    
    points = gpd.GeoDataFrame.from_file(pointjson) # Stickers JSON  
    polys = gpd.GeoDataFrame.from_file(polyjson) # Parcels JSON
    points_to_check=0
    polys_to_join=0
    polys_check_ids=[]
    polys_point_count=[]
    sticker_values=[]
    log=[]
    missing_det_ids=0
    missing_odk_ids=0

    for i in range(len(points)):
        if points['Detection'][i]=='needs check':
            points_to_check+=1
        sticker_values.append(points['Sticker_number'][i])

    for i in range(len(polys)):
        count=0
        for j in range(len(points)):
            if polys['geometry'][i].contains(points['geometry'][j]):
                count+=1
                
        if count==1:
            polys_to_join+=1
        else:
            polys_check_ids.append(polys.loc[i]['parcelID'])
            polys_point_count.append(count)

    odk_ids= [row['SpatialID'] for row in odk_data]

    for value in sticker_values:
        if value not in odk_ids:
            missing_det_ids+=0

    for id in odk_ids:
        if value not in sticker_values:
            missing_odk_ids+=0

    log.append('Filename: ' +raster_name)
    log.append('Number of parcels detected: '+ str(len(polys)))
    log.append('Number of stickers detected: '+ str(len(points)))
    log.append('Number of records in odk: '+ str(len(odk_ids)))
    log.append('Number of parcels containing exactly 1 sticker: '+str(polys_to_join))     
    
    if len(sticker_values) == len(set(sticker_values)):
        log.append('No duplicate records in detected numbers')
    else:
        log.append('Duplicate records in detected numbers, needs to be checked')
    if len(polys_check_ids)+points_to_check==0:
        log.append('No parcels or stickers need to be checked')
    else:
        log.append('Number of parcels that need to be checked: '+str(len(polys_check_ids)))
        log.append('Number of stickers that need to be checked: '+str(points_to_check))
        if len(polys_check_ids)>0:
            for i in range(len(polys_check_ids)):
                log.append("Polygon with parcelID "+str(polys_check_ids[i])+" contains "+str(polys_point_count[i])+" stickers.")


    if len(odk_ids)==len(sticker_values): 
        log.append('The same amount of records ('+str(len(odk_ids)) +') were detected as in odk')
    else:
        log.append('Number of records detected ('+str(len(sticker_values))+') does not match with number of records in odk (' +str(len(odk_ids))+')')
    
    if missing_det_ids+missing_odk_ids==0:
        log.append('ID-s match odk data, no check needed')
    else:
        log.append('Number of sticker id-s detected but missing from odk: '+str(missing_det_ids))   
        log.append('Number of is-s in odk but undetected: '+str(missing_odk_ids))     
    
    for line in log:
        print(line)
        
    file_dtime=time.strftime("%Y%m%d_%H%M%S")     
    with open(logdir+raster_name[:-4]+'_'+file_dtime+'_log.txt' , 'w') as logfile:
        logfile.write('\n'.join(log))

'''
number of stickers without polygons
number of records in odk form:
where not kaspar    
odk spatial id matches sticker id
'''
    
#polyid = gpd.sjoin(polys, points, how='inner') 
#polyid.to_file("joined_poly_inner.json") # Polygons with ID-s output filename




