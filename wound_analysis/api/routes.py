
# [START gae_python38_app]
import flask
import os
from werkzeug.utils import secure_filename
import cv2
import time

import pathlib
import uuid

import numpy as np
import json
import wound_analysis
from PIL import Image
import pickle

from imageio import imread
import io
import base64

import zipfile

import wound_analysis.api.analysis as analysis
import wound_analysis.api.helpers as helpers

from flask_cors import CORS, cross_origin
# If `entrypoint` is not defined in app.yaml, App Engine will look for an app
# called `app` in `main.py`.

global test_val
test_val = 0
global data
data = {}

@wound_analysis.app.route('/time/')
def get_current_time():
    return {'time': time.time()}


@wound_analysis.app.route('/post/', methods=['POST', 'GET'])
@cross_origin(supports_credentials=True)
def post():
    print("reached post")
    fileobj = flask.request.files["file"]

    fileobj.save(os.path.join(wound_analysis.app.root_path, "cur_image.jpg"))
    print("post saved")
    return flask.redirect("/")


@wound_analysis.app.route('/testPrint/', methods=['POST', 'GET'])
@cross_origin(supports_credentials=True)
def show_time():
    print("tested")
    return {"test": "testedInFlask"}

@wound_analysis.app.route('/zipMeasure', methods=['POST', 'GET'])
@cross_origin(supports_credentials=True)
def zipMeasure():
    
    fileobj = flask.request.files["file"]
    filename = fileobj.filename

    archive = zipfile.ZipFile(fileobj, 'r')
    namelist = archive.namelist()

    width = float(flask.request.form.get("width"))
    lower_mask_one = str(flask.request.form.get("lower_mask_one"))
    lower_mask_two = str(flask.request.form.get("lower_mask_two"))
    upper_mask_one = str(flask.request.form.get("upper_mask_one"))
    upper_mask_two = str(flask.request.form.get("upper_mask_two"))
    mask_map = {
        "lower_range": {
            "first": helpers.convertStringToNumpyArray(lower_mask_one),
            "second": helpers.convertStringToNumpyArray(lower_mask_two)
        },
        "upper_range": {
            "first": helpers.convertStringToNumpyArray(upper_mask_one),
            "second": helpers.convertStringToNumpyArray(upper_mask_two)
        }
    }
    image_list = []
    for img_name in namelist:
        imgfile = archive.open(img_name)

        # Convert image file to opencv format
        image = Image.open(imgfile)
        buf = io.BytesIO()
        image.save(buf, 'jpeg')
        buf.seek(0)
        image_bytes = buf.read()
        buf.close()

        base64_bytes = base64.b64encode(image_bytes)
        input_base64_image = "data:image/jpeg;base64," + base64_bytes.decode()
        
        pil_image = image.convert('RGB') 
        opencv_image = np.array(pil_image) 

        # Convert RGB to BGR 
        opencv_image = opencv_image[:, :, ::-1].copy() 
        
        small_to_large_image_size_ratio = 0.5
        opencv_image = cv2.GaussianBlur(opencv_image, (3, 3), cv2.BORDER_DEFAULT)
        opencv_image = cv2.resize(opencv_image, # original image
                                (0,0), # set fx and fy, not the final size
                                fx=small_to_large_image_size_ratio, 
                                fy=small_to_large_image_size_ratio, 
                                interpolation=cv2.INTER_NEAREST)
        obj = analysis.zip_measurement(opencv_image, mask_map, width=width)
        obj["orig"] = input_base64_image
        image_list.append(obj)

    response = json.dumps(image_list)
    return response

@wound_analysis.app.route('/measure', methods=['POST', 'GET'])
@cross_origin(supports_credentials=True)
def measure():
    # Retrieve fields
    width = float(flask.request.form.get("width"))
    
    input_base64_image = flask.request.form.get("base64")
    b64_string = input_base64_image.split("data:image/jpeg;base64")[1]
    manual_width = flask.request.form.get("manual_width")
    if manual_width == "true":
        manual_width = True
    else:
        manual_width = False
    lower_mask_one = str(flask.request.form.get("lower_mask_one"))
    lower_mask_two = str(flask.request.form.get("lower_mask_two"))
    upper_mask_one = str(flask.request.form.get("upper_mask_one"))
    upper_mask_two = str(flask.request.form.get("upper_mask_two"))
    mask_map = {
        "lower_range": {
            "first": helpers.convertStringToNumpyArray(lower_mask_one),
            "second": helpers.convertStringToNumpyArray(lower_mask_two)
        },
        "upper_range": {
            "first": helpers.convertStringToNumpyArray(upper_mask_one),
            "second": helpers.convertStringToNumpyArray(upper_mask_two)
        }
    }

    # Convert image file to opencv format
    decoded = base64.b64decode(b64_string)
    ioed = io.BytesIO(decoded)
    image = Image.open(ioed)
    pil_image = image.convert('RGB') 
    opencv_image = np.array(pil_image) 

    # Convert RGB to BGR 
    opencv_image = opencv_image[:, :, ::-1].copy() 
    
    small_to_large_image_size_ratio = 0.5
    opencv_image = cv2.GaussianBlur(opencv_image, (3, 3), cv2.BORDER_DEFAULT)
    opencv_image = cv2.resize(opencv_image, # original image
                            (0,0), # set fx and fy, not the final size
                            fx=small_to_large_image_size_ratio, 
                            fy=small_to_large_image_size_ratio, 
                            interpolation=cv2.INTER_NEAREST)
    data_matrix = analysis.grid_measurement(opencv_image, mask_map, manual=manual_width, width=width)
    for row in data_matrix:
        for col in row:
            col["orig"] = input_base64_image

    response = json.dumps(data_matrix)
    return response


@wound_analysis.app.route('/testImage', methods=['POST', 'GET'])
@cross_origin(supports_credentials=True)
def testImage():

    # Retrieve fields
    fileobj = flask.request.files["file"]
    filename = fileobj.filename

    # Convert image file to opencv format
    pil_image = Image.open(fileobj).convert('RGB') 
    opencv_image = np.array(pil_image) 

    # Convert RGB to BGR 
    opencv_image = opencv_image[:, :, ::-1].copy() 

    response = json.dumps(helpers.convertNumpyImageToString(opencv_image))
    #print(response)
    return response


@wound_analysis.app.route('/testBase64', methods=['POST', 'GET'])
@cross_origin(supports_credentials=True)
def testBase64():
    
    lower_mask_one = str(flask.request.form.get("base64"))
    #print(response)
    return "tested"

@wound_analysis.app.route('/', methods=['POST', 'GET'])
@cross_origin(supports_credentials=True)
def hello():
    """Return a friendly HTTP greeting."""
    return "This is the wound analysis api"

@wound_analysis.app.route('/upload/',  methods=['POST', 'GET'])
@cross_origin(supports_credentials=True)
def upload():
    # Connect to database
    connection = wound_analysis.model.get_db()

    fileobj = flask.request.files["file"]
    filename = fileobj.filename

    # Compute base name (filename without directory).  We use a UUID
    # to avoid clashes with existing files, and ensure that the name
    # is compatible with the filesystem.
    uuid_basename = filename
    '''
    uuid_basename = "{stem}{suffix}".format(
        stem=uuid.uuid4().hex,
        suffix=pathlib.Path(filename).suffix
    )'''

    # Save to disk
    path = wound_analysis.app.config["UPLOAD_FOLDER"]/uuid_basename
    fileobj.save(path)
    
    '''
    connection.execute(
        "INSERT INTO images(filename)"
        "VALUES(?)", (uuid_basename,)
    )'''
    return {"filename": filename}
    
@wound_analysis.app.route('/database/', methods=['POST', 'GET'])
@cross_origin(supports_credentials=True)
def testDataBase():
    return "tested"

@wound_analysis.app.route('/uploads/<path:filename>', methods=['POST', 'GET'])
@cross_origin(supports_credentials=True)
def download_file(filename):
    return flask.send_from_directory(wound_analysis.app.config['UPLOAD_FOLDER'],
                                    filename, as_attachment=True)

def parse_url(url):
    split_url = url.split('\\')
    return "\\\\".join(split_url)

def parse_display(url):
    split_url = url.split('\\\\')
    return "".join(split_url)

# [END gae_python38_app]
