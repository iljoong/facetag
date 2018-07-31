###############################################################################################
from keras.models import Model, load_model
from PIL import Image
import numpy as np
import time
import cv2
import os
import logging
import pymongo
#import dlib

import requests
import appconfig
import json

cascade = cv2.CascadeClassifier('./face/haarcascade_frontalface_default.xml')
eyeCascade = cv2.CascadeClassifier('./face/haarcascade_eye.xml')
img_size = 200
labels = []

def loadModel():
    global labels

    try:
        modelpath = os.environ.get('MODELPATH')
        logging.debug("modelpath = %s" % modelpath)
        if (modelpath != None and modelpath != ""):
            model = load_model(modelpath)
            modeltags = os.environ.get('MODELTAGS', 'tag1;tag2;tag3;tag4;tag5;tag6;tag7;tag8;tag9;tag10')
            logging.debug("modeltags = %s" % modeltags)
            labels = modeltags.split(';')
        else:
            model = None

    except Exception as e:
        raise e
    
    return model

def loadCollection():
    # mongodb
    mongouri = os.environ.get('MONGOURI', 'mongodb://localhost:27017')
    mongodb = os.environ.get('MONGODB', 'facedb')
    mongocoll = os.environ.get('MONGOCOLL', 'face')
    logging.debug("env: {}, {}, {}".format(mongouri, mongodb, mongocoll))

    try:
        conn = pymongo.MongoClient(mongouri)
        #conn = pymongo.MongoClient(mongoip, 27017)
        db = conn.get_database(mongodb)

    except Exception as e:
        raise e
        
    return db.get_collection(mongocoll)
    
def detectFaceCV(gray):
    start_time = time.time()
    faces = []
    try:
        rects = cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=4, minSize=(30, 30),flags=cv2.CASCADE_SCALE_IMAGE)
        
        for rect in rects:
            (x, y, w, h) = rect
            roi = gray[y:y+h, x:x+w]
            eyes = eyeCascade.detectMultiScale(roi)
            if len(eyes):
                faces.append(rect)

    except Exception as e:
        print(e)

    return faces, time.time() - start_time

"""
hog_face_detector = dlib.get_frontal_face_detector()

def detectFaceHog(gray):
    
    start_time = time.time()   
    rects = []
    try:
        rects = hog_face_detector(gray, 1)
        
        faces = [ [rect.left(), rect.top(), rect.right()-rect.left(), rect.bottom()-rect.top()] for rect in rects ]

    except Exception as e:
        print(e)

    return faces, time.time() - start_time

cnn_face_detector = dlib.cnn_face_detection_model_v1("../face/mmod_human_face_detector.dat")
def detectFaceCNN(gray):
    
    start_time = time.time()
    rects = []
    try:
        rects = cnn_face_detector(gray, 1)
        
        faces = [ [rect.rect.left(), rect.rect.top(), rect.rect.right()-rect.rect.left(), rect.rect.bottom()-rect.rect.top()] for rect in rects ]

    except Exception as e:
        print(e)

    return faces, time.time() - start_time
"""
def classifyFace(model, frame):
    global labels

    img = cv2.resize(frame, (img_size, img_size), interpolation = cv2.INTER_AREA)
    x = np.expand_dims(img, axis=0)
    x = x.astype(float)
    x /= 255.

    start_time = time.time()

    classes = model.predict(x)
    result = np.squeeze(classes)
    result_indices = np.argmax(result)

    logging.debug("classify time: {:.2f} sec".format(time.time() - start_time))
    
    return labels[result_indices], result[result_indices]*100

def classifyFaceCV(model, frame):
    _, roi = cv2.imencode('.png', frame)

    start_time = time.time()

    apiurl = 'https://southcentralus.api.cognitive.microsoft.com/customvision/v2.0/Prediction/%s/image?iterationId=%s'
    headers = {"Content-Type": "application/octet-stream", "Prediction-Key": appconfig.api_key }

    r = requests.post(apiurl % (appconfig.api_id, appconfig.api_iter), headers=headers, data=roi.tostring())

    if (r.status_code == 200):
        # JSON parse
        pred = json.loads(r.content.decode("utf-8"))

        conf = float(pred['predictions'][0]['probability'])
        label = pred['predictions'][0]['tagName']

        logging.debug("classify time: {:.2f} sec".format(time.time() - start_time))
        return label, conf*100
    else:
        return "none", 0.0

