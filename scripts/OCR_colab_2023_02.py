"""
Created on FRI Oct 14 2022

@author: Gergely
"""
# Extracts stickers, preprocesses the images, performs OCR and exports a json
# Adapted for colab

import cv2 as cv
import numpy as np
import imutils
import math
import pytesseract
from statistics import mode
import json
from geojson import Feature, FeatureCollection, Point
from osgeo import gdal
from pyproj import CRS, Transformer


def detect_num(image):
    # Text recognition on images with whitelisted characters
    # Rotates images if:   last character is not *
    #                      first character is not a number
    #                      length is 0 (meaning there was no detection)
    #                      performs detection again then evaluates
    #
    # Check: a column in the csv file which indicates whether results are good or have to be adjusted manually.
    # Loops through widths and tries OCR. Keeps trying until every width is checked, and exports result.
    # Selects mode value from detections at different scales.
    # Only from correct detections if there are any
    
    widthpxes = [200, 150, 250, 100, 300] # widths for images to be resied for tesseract. This is more or less the range that works. 
    padding=50 #this is good 
    
    goodres=[]
    failed=[]
    
    for widthpx in widthpxes:
    
        heightpx = int((widthpx/image.shape[1])*image.shape[0])
        resized = cv.resize(image, (widthpx, heightpx))       
        padded = cv.copyMakeBorder(resized,padding,padding,padding,padding,cv.BORDER_CONSTANT,value=(0,0,0)) 
        
        text = pytesseract.image_to_string(padded, config="-c tessedit_char_whitelist=0123456789*")
        text=text.strip()
            
        if len(text)<1 or not text[0].isnumeric() or text[-1]!="*":
            rotated = imutils.rotate(padded, 180)
            text2 = pytesseract.image_to_string(rotated, config="-c tessedit_char_whitelist=0123456789*")
            text2=text2.strip()
            
            if len(text2)<1:
                failed.append("NULL")
            elif not text2[0].isnumeric() or text2[-1]!="*":
                failed.append(text2)
            else:
                goodres.append(text2[:-1])
        else:
            goodres.append(text[:-1])

    if len(goodres) > 0:
        try:
            result = mode(goodres)
            check = "good"
        except:
            result = goodres[0]
            check = "needs check"
    else:
        failednum = [s for s in failed if s.isdigit()]
        if len(failednum)>0:
            try:
                result = mode(failednum)
                check = "needs check"
            except:
                result = failednum[0]
                check = "needs check"
        else:
            result = "NULL"
            check = "needs check"
            
    return result, check
    
  
def detect_stickers(imgname, jsonname, bmin, bmax, gmin, gmax, rmin, rmax, epsg):

    print("Reading image...")
    img = cv.imread(imgname) 
    
    print("Done. Preprocessing...")         
    #rgb-binary segmentation
    thresholded= cv.inRange(img, (bmin, gmin, rmin), (bmax, gmax, rmax))

    #morphological closing - filling holes
    kernel = np.ones((5,5),np.uint8) 
    morph = cv.morphologyEx(thresholded, cv.MORPH_CLOSE, kernel)

    #blurring
    preprocessed = cv.blur(morph, (3,3))

    print("Done. Detecting contours...")
    #contour detection
    contours, _ = cv.findContours(preprocessed, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    maxcont = max(contours, key = cv.contourArea)
    conttresh = cv.contourArea(maxcont)*0.35

    ind_to_del=[]
    for k in range(len(contours)):
        #delete small contours 
        if cv.contourArea(contours[k])<conttresh:
            ind_to_del.append(k)
    newcontours= [v for i, v in enumerate(contours) if i not in ind_to_del]
    contours_poly = [None]*len(newcontours)
        
    centroids=[]
    results=[]
    checks=[]
        
    print("Done. Extraction and OCR...") 
    
        #cropping minimum area rectangles then rotating them
    for i, c in enumerate(newcontours):
        contours_poly[i] = cv.approxPolyDP(c, 3, True)
        rect = cv.minAreaRect(contours_poly[i])
        
        box = cv.boxPoints(rect)
        box = np.int0(box)
        
        xcent=int((rect[0][0]))
        ycent=int((rect[0][1]))
        centroids.append([xcent,ycent])

        Xs = [j[0] for j in box]
        Ys = [j[1] for j in box]
        
        x1 = min(Xs)
        x2 = max(Xs)
        y1 = min(Ys)
        y2 = max(Ys)
        
        center = (xcent, ycent)
        size = (int(x2-x1),int(y2-y1))
        #calculate which is the longer side
        #Euclidean distance       
        
        point1 = np.array((box[0][0], box[0][1]))
        point2 = np.array((box[1][0], box[1][1]))
        point3 = np.array((box[3][0], box[3][1]))
        
        side1 = np.linalg.norm(point1 - point2)
        side2 = np.linalg.norm(point1 - point3)

        angle = rect[2]
        
        #angle correction so every box is horizontal
        if side1>side2:
            angle -=90
        
        cropped = cv.getRectSubPix(thresholded, size, center)
        rotated_cropped = imutils.rotate_bound(cropped, -angle)
        
        #Crop the middle of the rotated rectangles
        #find contours again on rotated image
        contours2, _ = cv.findContours(rotated_cropped, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
        
        cmax = max(contours2, key = cv.contourArea)       
        cmax_poly =cv.approxPolyDP(cmax, 3, True)
        
        rectcrop = cv.minAreaRect(cmax_poly)
        
        #works the same way, variables are the only difference
        box2 = cv.boxPoints(rectcrop)
        box2 = np.int0(box2)
                
        Xs2 = [j[0] for j in box2]
        Ys2 = [j[1] for j in box2]
        
        x12 = min(Xs2)
        x22 = max(Xs2)
        y12 = min(Ys2)
        y22 = max(Ys2)
        
        #how much of the detected sticker is cropped 
        cropx = int((x22-x12)*0.2)
        cropy = int((y22-y12)*0.2)
        
        #extent to crop only the middle
        size2 = (int(x22-x12)-cropx,int(y22-y12)-cropy)
        
        xcent2=int((rectcrop[0][0]))
        ycent2=int((rectcrop[0][1]))                
        
        #actual cropping
        smallcrop = cv.getRectSubPix(rotated_cropped, size2, (xcent2,ycent2))
        
        #bitwise inversion and padding
        inverted = cv.bitwise_not(smallcrop)
        
        #running OCR
        result, checkval = detect_num(inverted)

        results.append(result)
        checks.append(checkval)
     
    print ("Done. Number of stickers extracted: "+str(len(centroids)))
    print("Writing results...") 
     
    # calculate projection coordinates in the original projection

    info = gdal.Info(imgname, format='json')
    
    upleft_x=info['geoTransform'][0]  
    upleft_y=info['geoTransform'][3]
    dx1=info['geoTransform'][1]
    dy1=info['geoTransform'][4]
    dx2=info['geoTransform'][2]
    dy2=info['geoTransform'][5]
    
    features = []

    for i in range(len(centroids)):
        
        centx=upleft_x+(centroids[i][0]*dx1+centroids[i][0]*dy1) #x projected coordinate
        centy=upleft_y+(centroids[i][1]*dx2+centroids[i][1]*dy2) #y projected coordinate
        
        #reproject to WGS84   
        
        transformer = Transformer.from_crs(epsg, 'EPSG:4326')
        reprojected_x, reprojected_y = transformer.transform(centx, centy)
        
        #Y comes first, then X
        features.append(
            Feature(
                geometry = Point((reprojected_y, reprojected_x)),
                properties = {
                    'Detection': checks[i],
                    'Sticker_number': results[i]
                }
            )
        )

    collection = FeatureCollection(features, crs=epsg)
    with open(jsonname, "w") as f:
        f.write('%s' % collection)
    print ("Finished")
       
        
        
        
