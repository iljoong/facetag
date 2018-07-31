import numpy as np
import os
import sys
import time
import cv2
import dlib
import argparse

cascade = cv2.CascadeClassifier('./face/haarcascade_frontalface_default.xml')
eyeCascade = cv2.CascadeClassifier('./face/haarcascade_eye.xml')

def detectFaceCV(gray):

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

    return faces

def detectFaceHog(gray):
    
    rects = []
    try:
        rects = hog_face_detector(gray, 1)
        
        faces = [ [rect.left(), rect.top(), rect.right()-rect.left(), rect.bottom()-rect.top()] for rect in rects ]

    except Exception as e:
        print(e)

    return faces

cnn_face_detector = dlib.cnn_face_detection_model_v1("./face/mmod_human_face_detector.dat")

def detectFaceCNN(gray):
    
    rects = []
    try:
        rects = cnn_face_detector(gray, 1)
        
        faces = [ [rect.rect.left(), rect.rect.top(), rect.rect.right()-rect.rect.left(), rect.rect.bottom()-rect.rect.top()] for rect in rects ]

    except Exception as e:
        print(e)

    return faces

def cropFace(detectfn, tmppath, facepath):
    start_time = time.time()

    if not os.path.exists(facepath):
        os.makedirs(facepath)

    for f in os.listdir(tmppath):

        if os.path.isdir(os.path.join(tmppath, f)):
            continue

        filepath = os.path.join(tmppath, f)
        filename = os.path.splitext(f)[0]

        # detect faces
        img = cv2.imread(filepath)
        rects = detectfn(img)


        print("detecting: {}, faces: {}".format(f, len(rects)))
        i = 0
        for rect in rects:
            (x, y, w, h) = rect
            roi_face = img[y:y+h, x:x+w]
            fpath = os.path.join(facepath, "{}-face{}.jpg".format(filename, i))
            cv2.imwrite(fpath, roi_face)
            i+=1

    print("processed time: {:.2f} sec".format(time.time() - start_time))

# https://docs.python.org/3/library/argparse.html
# handle command line arguments
ap = argparse.ArgumentParser()
ap.add_argument('-a', '--algorithm', help='detection algorithm', choices=['cv', 'hog', 'cnn'], default='cv')
ap.add_argument('srcdir', type=str, help='source directory')
ap.add_argument('destdir', type=str, help='destination direcotry')

args = ap.parse_args()
algo = detectFaceCV

if (args.algorithm == 'hog'):
    algo = detectFaceHog
elif (args.algorithm == 'cnn'):
    algo = detectFaceCNN 

print(args.algorithm, args.srcdir, args.destdir)
cropFace(algo, args.srcdir, args.destdir)
