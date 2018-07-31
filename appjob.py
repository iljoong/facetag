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

def get_kvsecret(secret):
    # MSI + KV
    headers= {'Metadata': 'true'}
    r = requests.get('http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://vault.azure.net', headers=headers)
    token = r.json()['access_token']

    # get secret from KV
    headers= {'Authorization': 'Bearer {}'.format(token)}
    r = requests.get('{}secrets/{}/?api-version=2016-10-01'.format(appconfig.kvuri, secret), headers=headers)
    val = r.json()['value']

    return val

def getStoragekey(msi = False):

    return get_kvsecret('blobkey') if msi else appconfig.blobkey

def getEGkey(msi = False):

    return get_kvsecret('egkey') if msi else appconfig.blobkey

def create_facedata(facedir, res):
    #logging.debug("executing-create_facedata: %s" % facepath)
    # get file since modified data
    for r in res:
        filename = r['filename']
        img = cv2.imread(os.path.join(appconfig.pixpath, filename))
        for f in r['detect']:
            (x, y, w, h) = f['rect'].values()
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

def upload_blob(zippath, zipname, storkey):
    blobpath = appconfig.container + "/" + appconfig.datapath
    logging.debug("upload %s, %s" % (zippath, zipname))

    call(["blobxfer", "upload", "--storage-account", appconfig.blobacct, "--storage-account-key", storkey, 
        "--remote-path", blobpath, "--local-path", zippath])
    
    return blobpath + '/' + zipname

def email_user(jobid, blobfile, storkey, egkey):
    #generate sastoken
    ttl = 1 # 1 hour
    token_dict = generate_sas_token(appconfig.blobacct, storkey, "rl", 1, appconfig.container, blobfile) 
    logging.debug(token_dict['url'])
    download_link=token_dict['url']

    curtime = datetime.utcnow()

    jsondata = [{"id": jobid, "eventType": "recordInserted", "subject": "Download link from Faceapp", 
        "eventTime": str(curtime), "dataVersion": "1.0",
        "data": {"link": download_link, "email": appconfig.adminemail} }]

    r = requests.post(appconfig.eguri, 
        headers={"Content-Type": "application/json", "aeg-sas-key": egkey}, 
        data=json.dumps(jsondata))

    if (int(r.status_code / 100) != 2):
        logging.error("error-facedb failure: ", r.status_code)

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

        storkey = getStoragekey()
        egkey = getEGkey()
        logging.debug("skey: %s, ekey: %s" % (storkey, egkey))
        
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
        remotepath = upload_blob(zippath, zipname, storkey)

        #notify to user
        #email_user(self.jobid, remotepath, storkey, egkey)

        #cleanup
        shutil.rmtree(tmppath)
