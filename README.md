# SmartLandMaps Digitization Software

This repository shows the boundary extraction and vectorization code used during the SmartLandMaps project.

## :wrench: Scripts 

The scripts can be found in the /scripts folder.

* boundary_extractor_blur_2023_02 is useful to extract boundaries from the original image (raster-to-raster)
* vectorizer_grass_2023_02 is useful to generate polygons from the boundaries extracted (raster-to-vector)
* OCR_colab_2023_02 helps to extract the stickers from the original image
* analyser_2023_02 is useful for analyzing the results and gives feedback on the number of parcels or stickers that need editing
* joiner_2023_03 merges ODK data with polygons by sticker ID

You can run the different modules independently. The SmartLandMaps_Notebook is a Colab Notebook that brings all the pieces together. Note that running the Notebook requires you to upload the dataset to be digitized to the Cloud (e.g. Google Drive) in case you would use Colab to do so.


## :clipboard: Documentation 

* The SmartLandMaps approach and the key intuitions of the software modules: Lindner, C., Degbelo, A., Vassányi, G., Kundert, K. and Schwering, A. (2023) ‘The SmartLandMaps approach for participatory land rights mapping’, Land, 12(11). Available at: https://doi.org/10.3390/land12112043.
* ....
* ....
* ....


:e-mail: Contact: [Auriol Degbelo](https://sites.google.com/site/aurioldegbelo/)

