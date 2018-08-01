#!falsk/bin/python
from flask import Flask, request, send_from_directory, render_template, redirect, Response

import requests
import json
import cv2
from PIL import Image
import os
import time
import datetime
from subprocess import call
import math
import logging, optparse
import random, string

import base64
from io import BytesIO
import numpy as np

from keras.models import Model, load_model
from keras import backend as K

import pymongo
from bson.objectid import ObjectId
from bson.json_util import dumps

import appconfig
from appface import loadModel, loadCollection, classifyFace, detectFaceCV, classifyFaceCV #, detectFaceHog, detectFaceCNN
from appjob import JobThread

LOGGING_LEVELS = {'critical': logging.CRITICAL,
                  'error': logging.ERROR,
                  'warning': logging.WARNING,
                  'info': logging.INFO,
                  'debug': logging.DEBUG}

app = Flask(__name__, static_folder="wwwroot")
model = None
coll = None
usecvapi = False

# static folder
@app.route('/pix/<path:filename>')
def pix_static(filename):
    return send_from_directory(os.path.join(app.root_path, appconfig.pixpath), filename)

@app.route('/smpix/<path:filename>')
def smpix_static(filename):
    return send_from_directory(os.path.join(app.root_path, appconfig.smpixpath), filename)

@app.route('/')
def index():
    return showpage()

@app.route('/show', methods=['GET'])
def showpage():
    tag = request.args.get('tag')
    if (tag == None):
        tag = ""
    page = request.args.get('page')
    if (page == None or page == ""):
        page = 1
    else:
        page = int(page)

    cond = {"detect": {"$elemMatch": {"tag": tag}}} if not (tag == "") else {}
    total = coll.count(cond)
    pagecount = math.ceil(total/appconfig.pagesize)

    curr = coll.find(cond).skip( (( page - 1 ) * appconfig.pagesize ) if (page > 0) else 0 ).limit( appconfig.pagesize )
    faces = list(curr)
    
    logging.debug("tag: %s, total = %d, currsize = %d" % (tag, total, len(faces)))

    pageinfo = {"pagecount": pagecount, "page": page, "total": total}

    return render_template('show.html', faces=faces, pageinfo=pageinfo, tag=tag )

@app.route('/upload')
def uploadypage():

    mode = "Detection" if (model == None) else "Recognition"
    return render_template('upload.html', mode=mode)

@app.route('/detect')
def detectpage():

    return render_template('detect.html')

@app.route('/about')
def aboutpage():

    return render_template('about.html')

@app.route('/edit/<id>')
def editpage(id):

    try:
        logging.debug("id: %s" % id)
        res = coll.find_one({"_id": ObjectId(id)})
        logging.debug(res['filename'])
    except Exception as e:
        logging.debug(e)
        return render_template('error.html', error=str(e))

    return render_template('edit.html', face=res, fid=id)

@app.route('/edit/<id>', methods=['POST'])
def edittagpage(id):

    try:
        tag = request.form.get('edittag')
        pos = request.form.get('editpos')

        p = int(pos)
        logging.debug(json.dumps({"id": id, "tag": tag, "pos": p}))

        # update data
        res = coll.find_one({"_id": ObjectId(id)})

        res['detect'][p]['tag'] = tag
        res['detect'][p]['confidence'] = 0
        res['lastmodified'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        coll.update({'filename': res['filename']}, res, upsert=True)
    except Exception as e:
        logging.debug(e)
        return render_template('error.html', error=str(e))

    # redirect url
    return redirect("/edit/%s" % id)

@app.route('/api/edit/<id>', methods=['DELETE'])
def deletephoto(id):

    try:
        logging.debug(json.dumps({"id": id}))
        res = coll.remove({"_id": ObjectId(id)})
    except Exception as e:
        logging.debug(e)
        return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=500)

    return Response(json.dumps({"return": "ok"}), mimetype='application/json')

@app.route('/api/tag/<id>', methods=['PUT'])
def edittag(id):

    try:
        b  = request.json
        tag = b['edittag']
        pos = b['editpos'] #int

        logging.debug(json.dumps({"id": id, "tag": tag, "pos": pos}))

        # update data
        res = coll.find_one({"_id": ObjectId(id)})
        p = int(pos)
        res['detect'][p]['tag'] = tag
        coll.update({'filename': res['filename']}, res, upsert=True)

    except Exception as e:
        logging.debug(e)
        return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=500)

    # redirect url
    return Response(json.dumps({"return": "ok"}), mimetype='application/json')

@app.route('/api/tag/<id>', methods=['POST'])
def addtag(id):

    try:
        newtag  = request.json
        logging.debug(json.dumps(newtag))

        # update data
        res = coll.find_one({"_id": ObjectId(id)})
        res['detect'].append(newtag)
        coll.update({'filename': res['filename']}, res, upsert=True)

    except Exception as e:
        logging.debug(e)
        return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=500)

    # redirect url
    return Response(json.dumps({"return": "ok"}), mimetype='application/json')

@app.route('/api/tag/<id>', methods=['DELETE'])
def deltag(id):

    try:
        b  = request.json
        pos = b['editpos'] #int

        logging.debug(json.dumps({"id": id, "pos": pos}))

        # update data
        res = coll.find_one({"_id": ObjectId(id)})
        p = int(pos)
        del(res['detect'][p])
        coll.update({'filename': res['filename']}, res, upsert=True)

    except Exception as e:
        logging.debug(e)
        return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=500)

    # redirect url
    return Response(json.dumps({"return": "ok"}), mimetype='application/json')

@app.route('/api/search/<tag>', methods=['GET'])
def search(tag):

    try:
        if (tag == None):
            res = coll.find()
        else:
            res = coll.find({"detect": {"$elemMatch": {"tag": tag}}})
    except Exception as e:
        logging.debug(e)
        return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=500)

    return Response(dumps(list(res)), mimetype='application/json')

@app.route('/api/classify/face', methods=['POST'])
def classifyface():
    global model

    try:
        # get `image/png` data
        file = request.data
        file = str(file)

        # https://gist.github.com/RaminNietzsche/1c270f176e91fc57ecc5bc0468e46aee
        starter = file.find(',')
        image_data = file[starter+1:]
        image_data = bytes(image_data, encoding="ascii")
        img = np.array(Image.open( BytesIO(base64.b64decode(image_data)) )) 

        # convert 4 Channel BGRA to BRR
        roi_face = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        print(type(roi_face), roi_face.shape)

        if (model != None): # detection/classification mode
            tag, conf = classifyFace(model, roi_face)
        elif (usecvapi):
            tag, conf = classifyFaceCV(model, roi_face)
        else:
            conf = 0
            tag = "none" 

        faceitem = {'tag': tag, 'confidence': conf }

        logging.debug("facedata: %s, %s" % (tag, conf))

    except Exception as e:
        logging.error(e)
        return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=500)
    
    return Response(json.dumps(faceitem), mimetype='application/json', status=201)

@app.route('/api/classify', methods=['POST'])
def classify():
    global model, coll
   
    facedata = ""
    try:
        # load model here because of Docker GPU issue: https://github.com/iljoong/facetag/issues/1
        if (model == None):
            model = loadModel()

        start_time = time.time()
        
        f = request.files['file']

        logging.info('classify: %s' % f.filename)

        # save original image
        filepath = os.path.join(appconfig.pixpath, f.filename)
        f.save(filepath)

        timenow = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # get exif
        i = Image.open(filepath)
        exif = i._getexif()
        #rotation = exif.[274]
        if (exif):
            rotation = exif.get(274, 1)
            timetaken = exif.get(36867, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        else:
            rotation = 1
            timetaken = timenow
        logging.debug("exif: %d, %s" % (rotation, timetaken))

        # classify faces
        img = cv2.imread(filepath)

        rects, dt = detectFaceCV(img)
        logging.info("img detect time: {:.2f}".format(dt))

        faces = []
        i = 0
        for rect in rects:
            ps_time = time.time()
            
            (x, y, w, h) = rect
            roi_face = img[y:y+h, x:x+w]
            #roi_face = cv2.cvtColor(roi_face, cv2.COLOR_BGR2RGB)
            if (model != None): # detection/classification mode
                tag, conf = classifyFace(model, roi_face)
            elif (usecvapi):
                tag, conf = classifyFaceCV(model, roi_face)

            # be aware that convert numpy.int32 to int for json serialization
            drect = { 'x': int(x), 'y': int(y), 'w': int(w), 'h': int(h) }
            face = { 'tag': tag, 'confidence': conf, 'rect': drect }
            faces.append(face)

            logging.info("{}:{:.2f}, recognition time:  {:.2f} sec".format(tag, conf, time.time() - ps_time))
            
        faceitem = {'filename': f.filename, 'detect': faces, 'rotation': rotation, 'timetaken': timetaken, 'lastmodified': timenow}

        #upsert
        coll.update({'filename': f.filename}, faceitem, upsert=True)
        #get id
        upres = coll.find_one({'filename': f.filename}, {"_id": "true"})
        faceitem['_id'] = str(upres['_id'])

        facedata = json.dumps(faceitem)
        logging.debug(facedata)

        # save smallsize
        height, width = img.shape[:2]
        rw = 320
        rh = int(height / width * rw)
        img = cv2.resize(img, (rw, rh), interpolation = cv2.INTER_AREA)
        cv2.imwrite(os.path.join(appconfig.smpixpath, f.filename), img)

    except Exception as e:
        logging.error(e)
        return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=500)

    logging.info("processed time: {:.2f} sec".format(time.time() - start_time))
    
    return Response(json.dumps(facedata), mimetype='application/json', status=201)

def randFileName(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

@app.route('/api/admin/job', methods=['POST'])
def runjob():

    # https://www.pythoncentral.io/how-to-create-a-thread-in-python/
    jobid = randFileName()

    try:
        timesince = None
        if (request.json):
            b  = request.json
            if (b['timesince']):
                timesince = b['timesince']
        logging.debug("param timesince: {}".format(timesince))

        logging.debug("staring job: %s", jobid)

        thr = JobThread(jobid, coll, timesince)
        thr.setName('jobid={}'.format(jobid))
        thr.start()

    except Exception as e:
        return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=500)

    blobpath = "https://%s.blob.core.windows.net/%s/%s/%s.zip" % (appconfig.blobacct, appconfig.container,  appconfig.datapath, jobid)
    return Response(json.dumps({ "blobpath": blobpath }), mimetype='application/json', status=201)

@app.route('/api/admin/model', methods=['PUT'])
def updatemodel():
    global model, coll

    try:
        # sync latest model from blob storage
        blobcont = appconfig.container
        blobpath = blobcont + '/' + appconfig.modeldir
        downpath = os.path.abspath(appconfig.localmodeldir)

        if not os.path.exists(downpath):
            os.makedirs(downpath)

        logging.info("blobxfer download --storage-account {}  --storage-account-key {} --remote-path {} --local-path {} --skip-on-lmt-ge --strip-components 100".format(appconfig.blobacct, appconfig.blobkey, blobpath, downpath))

        call(["blobxfer", "download", "--storage-account", appconfig.blobacct, "--storage-account-key", appconfig.blobkey, "--remote-path", blobpath, "--local-path", downpath, 
            "--skip-on-lmt-ge", "--strip-components", "100"])

        model == None
        logging.info("reloading facetag model...")
        K.clear_session() 
        model = loadModel()

        coll = loadCollection()
    except Exception as e:
            return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=500)

    return Response(json.dumps({ "return": "okay" }), mimetype='application/json')

@app.before_first_request
def initialize():
    global model, coll, usecvapi

    # flag to use cvapi
    usecvapi = False
    _env = os.environ.get('MODELCVAPI')
    if (_env != None and _env != ''):
        usecvapi = True

    # webroot directory
    webrootdirs = [appconfig.pixpath, appconfig.smpixpath, appconfig.facepath]
    for wdir in webrootdirs:
        if not os.path.exists(wdir):
            os.makedirs(wdir)

    # options for logging and etc.
    parser = optparse.OptionParser()
    parser.add_option('-l', '--logging-level', help='Logging level', default='info')
    parser.add_option('-f', '--logging-file', help='Logging file name')
    (options, args) = parser.parse_args()
    logging_level = LOGGING_LEVELS.get(options.logging_level, logging.NOTSET)
    logging.basicConfig(level=logging_level, filename=options.logging_file,
                        format='%(asctime)s %(levelname)s: %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')

    logging.debug("usecvapi = %s" % usecvapi)
    # Docker GPU issue - removed init here
    #model = loadModel()
    coll = loadCollection()

if __name__ == '__main__':

    app.run(debug=True, host='0.0.0.0',port=8080)