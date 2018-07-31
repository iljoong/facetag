# FaceTag

__FaceTag__ app is a simple AI-based photo gallery service which is similar to many online services like, [Facebook tag](https://www.facebook.com/about/tagging).

(Click to watch video)

[![Watch Demo](https://img.youtube.com/vi/C07SaD5ZwGY/0.jpg)](https://youtu.be/C07SaD5ZwGY)

## Overview

This app demonstrates followings:

- Basic photo gallery features
    - responsive web design
    - upload, show with paging, search by tag, edit tag
    - exif (rotation, timetaken) handling
    
- AI/DL model to recognize(classify) faces
    - keras with tensorflow backend
    - automatically detect & tag faces using AI/DL
    - support continuous learning process for improving model
    - crop face from images, zip and upload to blob

- Multi-model support
    - run different model without changing code

## DL Model training

Get training dataset, for example [5 Celebrity Face Dataset](https://www.kaggle.com/dansbecker/5-celebrity-faces-dataset), from Kaggle or create your own face dataset using this script, [facecrop](./utils/facecrop.py).

Run training and evaluate model with [nb-facetraining-celebrity.ipynb](nb-facetraining-celebrity.ipynb).

Save model file (`celebrity_model.h5`) in the `models` folder after completed training. Please refer _folder structure_ in the next section.

You could also experiment various face detection method, [Haar-cascade detection](https://docs.opencv.org/trunk/d7/d8b/tutorial_py_face_detection.html), [histogram-of-oriented-gradient (HOG) based object detectors](http://blog.dlib.net/2014/02/dlib-186-released-make-your-own-object.html) or [CNN/Faster-RCNN based detector](http://blog.dlib.net/2016/10/easily-create-high-quality-object.html), with [nb-facedetection.ipynb](nb-facedetection.ipynb).

## Installation & Run

### folder structure

```
 - AOA-FACE     <- current folder
    - face      <- face detection data files
    - samples   <- sample test photos
    - templates <- web template file
    - utils     <- py script
    - wwwroot   <- static file folder
 - models       <- keras .h5 model folder
 - mongodb      <- mongodb folder
 - webroot      <- static file folder
    - pix       <- original size image
    - smpix     <- small-size/preview images
```
 
### running on docker

Update blob account name/key and custom vision api info in `appconfig.py`

Create the docker image using docker build (cpu/gpu)
```
docker build -f Dockerfile-cpu -t <id>/facetag:cpu .
docker build -f Dockerfile-cpu -t <id>/facetag:gpu .
```

Run app (facetag and mongodb)
```
docker-compose -f docker-app.yaml up -d
```
__note 1__ : modify IMAGE and HOSTIP variables in `.env` before run `docker-compose`.

__note 2__ : inital start is __very slow__ due to GPU or DL framework initialization.

To view logs from docker for debugging, use following cli
```
docker logs -f facetag_facetag_1
```
### runing on docker on GPU VM

To run `docker-compose` on GPU VM, you must explicitly set default runtime to _nvidia_.
Add following line in `/etc/docker/daemon.json`.

```
 "default-runtime": "nvidia",
```

Then restart docker daemon to apply new setting
```
sudo service stop docker
sudo service start docker
```

You can also run using `nvidia-docker`/`docker` cli.

```
nvidia-docker run -v ~/webroot:/webroot -v ~/models:/models -e MODELPATH="../models/celebrity_model.h5" -e MODELTAGS='ben_afflek;elton_john;jerry_seinfeld;madonna;mindy_kaling' -e MONGOURI='mongodb://10.1.1.4:27017' -p 8080:8080 -d <id>/facetag:gpu
or
docker run --runtime nvidia -v ~/webroot:/webroot -v ~/models:/models -e MODELPATH="../models/celebrity_model.h5" -e MODELTAGS='ben_afflek;elton_john;jerry_seinfeld;madonna;mindy_kaling' -e MONGOURI='mongodb://10.1.1.4:27017' -p 8080:8080 -d <id>/facetag:gpu
```

Please read following for more information
[https://marmelab.com/blog/2018/03/21/using-nvidia-gpu-within-docker-container.html](https://marmelab.com/blog/2018/03/21/using-nvidia-gpu-within-docker-container.html)

### running on vm

Please refer `Dockerfile-cpu` file for installing packages run app by following commands.

```
# set environment variables
export MODELPATH="../models/celebrity_model.h5"
export MODELTAGS="ben_afflek;elton_john;jerry_seinfeld;madonna;mindy_kaling"
export MONGOURI="mongodb://10.1.0.4:27017"
export MONGOCOLL=celebrity

# switch to anaconda py35 if you needed
source activate

python main.py
```

### Azure Cosmos DB

You could use [Azure Cosmos DB](https://azure.microsoft.com/en-us/services/cosmos-db/) instead of Mongo DB. Create a Cosmos DB with `Mongo API` and set environment variable with the connection string provided by Cosmos DB.

```
export MONGOURI="mongodb://facedb:yyyyyxxxxxzzz==@<facetagdb>.documents.azure.com:10255/?ssl=true&replicaSet=globaldb"
```

### Upload from console

You can upload image file to _FaceTag_ service using cli.
```
curl -i -X POST -H "Content-Type: multipart/form-data" -F "file=@IMG_0263.JPG" http://<facetag ip>/api/classify
```

If you want to bulk upload files in folder, use following commands (in Linux)
```
ls *.JPG \
    | awk '{print "curl -i -X POST -H \"Content-Type: multipart/form-data\" -F \"file=@"$1"\" http://<facetag ip>/api/classify" }' \
    | bash
```
