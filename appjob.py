from threading import Thread
from subprocess import call

import cv2
from datetime import datetime
import requests
import json

import os
import shutil

import pymongo
import logging

from appblobsas import generate_sas_token
import appconfig

def create_facedata(facedir, res):
    #logging.debug("executing-create_facedata: %s" % facepath)
    # get file since modified data
    for r in res:
        filename = r['filename']
        img = cv2.imread(os.path.join(appconfig.pixpath, filename))
        for f in r['detect']:
            #(x, y, w, h) = f['rect'].values() - mongodb store keyvalue random order
            x = f['rect']['x']
            y = f['rect']['y']
            w = f['rect']['w']
            h = f['rect']['h']
            tag = f['tag']
            roi_face = img[y:y+h, x:x+w]
            facepath = os.path.join(facedir, "{}-{}".format(tag, filename))
            logging.debug(facepath)
            cv2.imwrite(facepath, roi_face)

def zip_facedata(zipname, tmppath, facepath):
    logging.debug("executing-zip_facedata: %s, %s" % (tmppath, facepath))

    zipfile = os.path.join(tmppath, zipname)

    call(["zip", "-jr", zipfile, facepath])

    return zipfile

def upload_blob(zippath, zipname):
    blobpath = appconfig.container + "/" + appconfig.datapath
    logging.debug("upload %s, %s" % (zippath, zipname))

    call(["blobxfer", "upload", "--storage-account", appconfig.blobacct, "--storage-account-key", appconfig.blobkey, 
        "--remote-path", blobpath, "--local-path", zippath])
    
    return blobpath + '/' + zipname

class JobThread(Thread):
    def __init__(self, jobid, coll, timesince):
        Thread.__init__(self)
        self.coll = coll
        self.jobid = jobid
        self.timesince = timesince

    def run(self):
    
        zipname = self.jobid + ".zip"
        coll = self.coll
        timesince = self.timesince

        logging.info("start job thread {}".format(zipname))
       
        #set variables
        tmppath = os.path.join("/tmp", "data")
        if not os.path.exists(tmppath):
            os.makedirs(tmppath)
        facepath = os.path.join(tmppath, "face")
        if not os.path.exists(facepath):
            os.makedirs(facepath)
        logging.debug(facepath)

        # generate face images
        logging.debug( "timesince: {}".format(timesince))
        if (timesince != None):
            res = coll.find({"lastmodified": {"$gt": timesince}})
        else:
            res = coll.find({})
        create_facedata(facepath, res)

        #zip file
        zippath = zip_facedata(zipname, tmppath, facepath)

        #upload to blob
        remotepath = upload_blob(zippath, zipname)

        #cleanup
        shutil.rmtree(tmppath)
