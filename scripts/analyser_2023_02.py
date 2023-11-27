# -*- coding: utf-8 -*-
"""
Created on Sun Sep  5 22:56:08 2021

@author: Auriol Degbelo

Steps
-----
set up authentification credentials
form a request and send it
convert to csv, then to json, and save it
convert to dataframe (just for fun, and also to possibly make further manipulation of the json objects easier) 
-----

"""


import csv
import json
import random
import requests
import pandas as pd

# get the token to be able to authentificate and retrieve the data 
def get_token (url_post, credentials):
    
    # Step 1: https://github.com/getodk/central-backend/blob/master/docs/api.md#logging-in-post
    url_post = url_post
    headers_post_request = {'Content-Type': 'application/json; charset=utf-8'}
    credentials = credentials
    res = requests.post(url_post, headers=headers_post_request,  json = credentials)
    token = "Bearer "+res.json()['token']
    return token 

# retrieve administrative data, save it as a json file, and diplay one random instance
def retrieve_odk_administrative_data (url_get, auth_token, s_path):   

    # Step 2: https://github.com/getodk/central-backend/blob/master/docs/api.md#using-the-session-get-v1example
    url_get = url_get
    headers_get_request = {"X-Extended-Metadata": "true", "Authorization": auth_token}

    response = requests.get(url_get, headers=headers_get_request)
    print("Response Code: ", response.status_code)

    # csv to JSON (via DictReader)
    # https://www.kite.com/python/answers/how-to-read-a-%60.csv%60-file-into-a-dictionary-in-python
    lines = response.text.splitlines()
    dict_reader = csv.DictReader(lines)
    dict_from_csv = list(dict_reader)
 
    saving_path = s_path
    with open(saving_path, "w") as write_file:
        json.dump(dict_from_csv, write_file) # encode dict into JSON
    
    return dict_from_csv


