# SmartLandMaps Digitization Software

This repository shows the code for boundary extraction and vectorization used during the SmartLandMaps project.

## :wrench: Scripts 

The scripts can be found in the /scripts folder.

* boundary_extractor_blur_2023_02 is useful to extract boundaries from the original image (raster-to-raster)
* vectorizer_grass_2023_02 is useful to generate polygons from the boundaries extracted (raster-to-vector)
* OCR_colab_2023_02 helps to extract the stickers from the original image
* analyser_2023_02 is useful for analyzing the results and gives feedback on the number of parcels or stickers that need editing
* joiner_2023_03 merges ODK data with polygons by sticker ID

You can run the different modules independently. The SmartLandMaps_Notebook is a Colab Notebook that brings all the pieces together. Note that running the Notebook requires you to upload the dataset to be digitized to the Cloud (e.g. Google Drive) if you intend to run the software in Colab directly. Finally, we trained a unet-model and fine-tuned a segformer model for boundary extraction at the patch level. Both models can be found [here](https://huggingface.co/aurioldegbelo/slm-unet-080823) and [here](https://huggingface.co/aurioldegbelo/slm-segformer-080823-b1) respectively.

## 👩‍🏭👨‍🏭 Contributors
* Auriol Degbelo (Ideas & Implementation)
* Kaspar Kundert (Ideas & Testing)
* Claudia Linder (Ideas & Testing)
* Gergely Vassányi (Ideas & Implementation)


## :clipboard: Documentation 

* The SmartLandMaps approach and the key intuitions of the software modules: Lindner, C., Degbelo, A., Vassányi, G., Kundert, K. and Schwering, A. (2023) ‘The SmartLandMaps approach for participatory land rights mapping’, Land, 12(11). Available at: https://doi.org/10.3390/land12112043.
* FIG publications including:
    * General introduction to the [pillars](https://github.com/aurioldegbelo/smartlandmaps/blob/main/publications/TS07.5_degbelo_stocker_et_al_11155.pdf) of the SmartLandMaps approach
    * Pilot study in [Benin](https://github.com/aurioldegbelo/smartlandmaps/blob/main/publications/TS03E_stocker_degbelo_et_al_11615.pdf) in 2022
    * Pilot study in [Chad and Sierra Leone](https://github.com/aurioldegbelo/smartlandmaps/blob/main/publications/TS04I_stocker_degbelo_et_al_12116.pdf) in 2023

## ❔ Questions
You are most welcome to [open an issue](https://github.com/aurioldegbelo/smartlandmaps/issues) if you have a question. You can also get in touch with [Auriol Degbelo](https://sites.google.com/site/aurioldegbelo/).

