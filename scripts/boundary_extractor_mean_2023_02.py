# -*- coding: utf-8 -*-
"""
Created on January 20, 2022; last modified on October 03, 2022.


@author: Auriol Degbelo

Note: the entry function, if any, is specified last. The keyword (ENTRY) is mentioned in the comments
describing that function. The entry function is the one that is called first among all functions.
All other functions are listed in the alphabetical order

Variables of the approach
-----
External Variables:
   - resolution: the higher number of pixels, the better [+ 5 min to make the pictures, 2/3 hours for the computer to generate the images]
   - size (MB): does not influence the quality of the results
   - scan vs pictures (innovation): pictures make it possible to always leave the map in the field

Internal Variables
   - Spatial window radius (MeanShiftFiltering): 
   - Color window radius (MeanShiftFiltering): 
   - Sigma (Edge detection): 
   - Peaks' min_distance (Region labeling): number of pixels separating peaks
   - Patch shape (Pixel labeling): the form of the patch
   - Threshold (Pixel labeling): which color range should be labelled

Steps
-----
read the image
crop it
generate patches for the cropped image
   for each patch 
      - label the pixels
rebuild image from the labelled patches 
-----

"""


import cv2
from patchify import patchify, unpatchify # divide image in smaller patches, and reconstruct images from small patches
import matplotlib.pyplot as plt # create interactive visualizations in Python
import numpy as np # mathematical functions on multi-dimensional arrays and matrices

from osgeo import gdal
from scipy import ndimage
from skimage import color
from skimage import feature
from skimage import segmentation
from skimage import measure


# Local Maximum Definition: https://github.com/scikit-image/scikit-image/issues/3016#issuecomment-381087758
# Watershed: intensity value as height (the brighter, the higher)

import time

# starting time
start = time.time()


# check if the file provided as input is of a given format
def file_is_of_format(data_format, source_file): 
    
    file_format = source_file.rsplit(".", 1)[1]
    
    if (file_format == data_format): 
        return True
    else:
        return False

# important parameters
# thres: say which colors range of the image should be taken into account for labelling
# sigma: influence the detection of edges
# min_distance: say the minimum number of pixels separating peaks
def find_boundaries(image, thres, i, j, plot): 

    #blur the image to reduce the number of edges
    #blurred = cv2.blur(image, (5,5))
    shifted = cv2.pyrMeanShiftFiltering(image, 20, 55)
    # convert the image to a gray colour scale
    image_2d = cv2.cvtColor(shifted, cv2.COLOR_BGR2GRAY) 

    # find edges in the image
    # Edge detection identifies points where there are discontinuities (i.e. at which the image brightness changes sharply)
    # https://dsp.stackexchange.com/questions/10736/which-sigma-to-use-for-edge-detection
    edges = feature.canny(image_2d, sigma=0.3) # the smaller sigma, the more edges detected
    #plt.imshow(edges)
       
    # ~edges make the edge to become the background, so that we can compute how far away we are from the edges
    dt = ndimage.distance_transform_edt(~edges) 
   
    # find coordinates of the peaks
    peak_idx = feature.peak_local_max(dt, min_distance=1, indices = False) # indices = false for watershed, indices = true for the distance transform
    # kaspar min_distance = 10
    # claudia_benin = 5
    #peak_idx = feature.peak_local_max(dt, num_peaks=10, indices = False)
   # peak_idx = feature.peak_local_max(dt,footprint=np.ones((50, 50)), indices = False)
    markers = measure.label(peak_idx) # label connected regions based on the peaks, number of peaks = number of regions in the image

    # Say which color range of the image should be labelled
    watershed_mask = image_2d.copy()
    #thres = 60 # do the segmentation for black regions in the image only (60)
    watershed_mask[image_2d <= thres] = 255
    watershed_mask[image_2d > thres] = 0
    
    # get labelled regions in the image
    labels = segmentation.watershed(-dt, markers, mask=watershed_mask) # black regions as peaks
    #print("[INFO] {} unique segments found".format(len(np.unique(labels)) - 1))
          
    mask = labels.copy()
    mask[mask > 0] = 255
    
    if plot:
        plt.figure()
        plt.subplot(1, 4, 1)
        plt.imshow(image_2d)
        plt.subplot(1, 4, 2)
        plt.imshow(dt)
        plt.subplot(1, 4, 3)
        plt.imshow(color.label2rgb(labels, image=image))
        plt.subplot(1, 4, 4)
        plt.imshow(mask)
        plt.show()
      
    return mask


# function that maps the parameters of the gdal geotransform to the lines of a tfw
def generate_tfw(tiff_raster, info):

    '''
    gdal geotransform
    https://gdal.org/tutorials/geotransforms_tut.html
    
    GT(0) x-coordinate of the upper-left corner of the upper-left pixel.
    GT(1) w-e pixel resolution / pixel width.
    GT(2) row rotation (typically zero).
    GT(3) y-coordinate of the upper-left corner of the upper-left pixel.
    GT(4) column rotation (typically zero).
    GT(5) n-s pixel resolution / pixel height (negative value for a north-up image).
    
    world file 
    
    https://en.wikipedia.org/wiki/World_file
    Line 1: A: pixel size in the x-direction in map units/pixel
    Line 2: D: rotation about y-axis
    Line 3: B: rotation about x-axis
    Line 4: E: pixel size in the y-direction in map units, almost always negative[3]
    Line 5: C: x-coordinate of the center of the upper left pixel
    Line 6: F: y-coordinate of the center of the upper left pixel
    '''
    
    gt = info['geoTransform']
    
    # generate a tfw with the same name as the tiff raster
    wld_filename = tiff_raster.rsplit(".", 1)[0]+'.tfw'
    wld_transform_parameters = [gt[1], 
                                gt[4],
                                gt[2],
                                gt[5],
                                gt[0],
                                gt[3]]    
    
    print("Saving tfw for the tiff raster at...", wld_filename) 
    with open(wld_filename, 'w') as f:
      for item in wld_transform_parameters:
          f.write("%s\n" % item)


# read and then resize the image slightly => Use Padding, not resizing!
def read_and_resize(im_path, patch_shape, rgba): 
    # get the size of the patches
    patch_size = patch_shape[0]
    
    if (rgba): 
        rgba_image = cv2.imread(im_path)
        image = cv2.cvtColor(rgba_image, cv2.COLOR_RGBA2RGB)
    else: 
        image = cv2.imread(im_path)
        
        
    raster_w = image.shape[0]     
    raster_l = image.shape[1]
    
    # create white padding on the bottom and the right so that none of the image is lost
    padded = cv2.copyMakeBorder(image, 0, patch_size, 0, patch_size, cv2.BORDER_CONSTANT, value=(255,255,255))
    width = padded.shape[0]
    height = padded.shape[1]
    cropped_1 = padded[0:int(np.floor(width/patch_size)*patch_size), 0:int(np.floor(height/patch_size)*patch_size)]
    
    #create another image with a different padding so patches are positioned differently
    padded_2 = cv2.copyMakeBorder(image, int(patch_size/2), patch_size, int(patch_size/2), patch_size, cv2.BORDER_CONSTANT, value=(255,255,255))
    width_2 = padded_2.shape[0]
    height_2 = padded_2.shape[1]
    cropped_2 = padded_2[0:int(np.floor(width_2/patch_size)*patch_size), 0:int(np.floor(height_2/patch_size)*patch_size)]
    
    return cropped_1, cropped_2, raster_w, raster_l

# (ENTRY) function to extract boundaries from a raster image - it reuses the functions defined above
def extract_boundaries(input_raster, boundaries, patch_shape, current_threshold, rgba, tfw, plot): 
    
    print("The input raster is ...", input_raster)
    # read and resize image slightly
    cropped_image_1, cropped_image_2, im_width, im_length = read_and_resize(input_raster, patch_shape, rgba)
    
    ############
    # convert the image to a numpy array
    cropped_sketch = np.asarray(cropped_image_1)
    
    # Generate patches, code adapted from https://github.com/bnsreenu/python_for_microscopists/blob/master/Tips_Tricks_5_extracting_patches_from_large_images_and_masks_for_semantic_segm.py
    patches = patchify(cropped_sketch, (patch_shape[0], patch_shape[1], patch_shape[2]), step=patch_shape[0])  #Step=256 for 256 patches means no overlap

    masks = np.empty((patches.shape[0], 
                     patches.shape[1],
                     patches.shape[3],
                     patches.shape[4]),
                     dtype=np.uint8)
   
    print("Extracting the boundaries from the input raster...")
    # extract boundaries from patches and bring the smaller patches together
    for i in range(patches.shape[0]):  
        for j in range(patches.shape[1]):
              single_patch_img = patches[i,j,0,:,:,:] 
              current_mask = find_boundaries(single_patch_img, current_threshold, i, j, plot)
              masks[i,j,:,:] = current_mask
  
    reconstructed_1 = unpatchify(masks, (cropped_sketch.shape[0], cropped_sketch.shape[1]))
    reconstructed_1 = reconstructed_1[0 : im_width, 0 : im_length]

    
    # do it a second time with different patches
    
    cropped_sketch_2 = np.asarray(cropped_image_2)
    
    patches_2 = patchify(cropped_sketch_2, (patch_shape[0], patch_shape[1], patch_shape[2]), step=patch_shape[0])  
    masks_2 = np.empty((patches_2.shape[0], 
                     patches_2.shape[1],
                     patches_2.shape[3],
                     patches_2.shape[4]),
                     dtype=np.uint8)
   
    print("Extracting the boundaries from the input raster...")
    # extract boundaries from patches and bring the smaller patches together
    for i in range(patches_2.shape[0]):  
        for j in range(patches_2.shape[1]):
              single_patch_img = patches_2[i,j,0,:,:,:] 
              current_mask = find_boundaries(single_patch_img, current_threshold, i, j, plot)
              masks_2[i,j,:,:] = current_mask
  
    reconstructed_2 = unpatchify(masks_2, (cropped_sketch_2.shape[0], cropped_sketch_2.shape[1]))
    reconstructed_2 = reconstructed_2[int(patch_shape[0]/2) : im_width+int(patch_shape[0]/2), int(patch_shape[0]/2) : im_length+int(patch_shape[0]/2)]
    
    #dilation so small gaps are closed
    kernel = np.ones((5,5),np.uint8)
    dilation_1 = cv2.dilate(reconstructed_1,kernel,iterations = 1)
    dilation_2 = cv2.dilate(reconstructed_2,kernel,iterations = 1)   
    
    # add the two rasters
    added = cv2.bitwise_or(dilation_1, dilation_2)
   
    #save the reconstructed image
    print("Saving the boundaries at ...", boundaries)
    cv2.imwrite(boundaries, added)
    
    
    if (tfw):
        # Read pixel to utm coordinate transformation parameters
        info = gdal.Info(input_raster, format='json')
        
        if (not file_is_of_format("tif", input_raster) and not file_is_of_format("tif", input_raster)):
            print("WARNING: input raster is not a tif file - no meaningful tfw file can be generated")
        
        # generate a tfw file for the boundaries
        generate_tfw(boundaries, info)
    
# end time
end = time.time()

# total time taken
print(f"Runtime of the program: {end - start} seconds")
