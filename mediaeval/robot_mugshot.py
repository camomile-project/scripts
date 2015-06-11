#!/usr/bin/env python
# encoding: utf-8

#
# The MIT License (MIT)
#
# Copyright (c) 2015 CNRS
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

# AUTHORS
# Hervé BREDIN -- http://herve.niderb.fr/

"""
MediaEval mugshot generator robot

Usage:
  robot_mugshot [options]

Options:
  -h --help                Show this screen.
  --version                Show version.
  --debug                  Show debug information.
  --url=URL                Submission server URL
                           [default: http://api.mediaeval.niderb.fr]
  --password=P45sw0Rd      Password
  --mp4=PATH               Path to MP4 directory.
  --idx=PATH               Path to IDX directory.
  --size=N                 Mugshot size in pixel [default: 100].
  --multiple=N             Number of mugshot in animation [default: 5].
  --period=N               Update mugshot every N sec [default: 10800].
  --log=DIR                Path to log directory.

"""

from common import RobotCamomile
from common import HTMLTime
from common import create_logger
from docopt import docopt
import cv
import cv2
import time
import numpy as np
from base64 import b64encode
import random

arguments = docopt(__doc__, version='0.1')

mp4 = arguments['--mp4']
idx = arguments['--idx']
size = int(arguments['--size'])
multiple = int(arguments['--multiple'])

url = arguments['--url']
password = arguments['--password']
period = int(arguments['--period'])

debug = arguments['--debug']
log = arguments['--log']
logger = create_logger('robot_mugshot', path=log, debug=debug)

robot = RobotCamomile(
    url, 'robot_evidence', password=password,
    period=period, logger=logger)

# unique layer containing manual annotations
test = robot.getCorpusByName('mediaeval.test')
evidenceGroundtruthLayer = robot.getLayerByName(
    test, 'mediaeval.groundtruth.evidence.all')

# mugshot layer
mugshotLayer = robot.getLayerByName(
    test, 'mediaeval.groundtruth.evidence.mugshot')

# loop on evidences, medium by medium
mediumEvidence = {}
urls = {}

# BAD: hard-coded
WIDTH = 384
HEIGHT = 288


while True:

    logger.info('collecting evidences')

    for medium, evidences in robot.getAnnotations_iter(
            evidenceGroundtruthLayer):

        mediumEvidence[medium] = {}

        urls[medium] = robot.getMedium(medium).url

        for evidence in evidences:

            if not evidence.data.is_evidence:
                continue

            person_name = evidence.data.corrected_person_name
            t = float(evidence.data.mugshot.time)

            mediumEvidence[medium].setdefault(t, {})[person_name] = \
                evidence.data.mugshot.bounding_box

    pngs = {}

    for medium, url in urls.iteritems():

        logger.info('mugshot - medium: {medium:s}'.format(
            medium=medium))

        htmlTime = HTMLTime('{idx}/{url}.idx'.format(idx=idx, url=url))
        capture = cv2.VideoCapture('{mp4}/{url}.mp4'.format(mp4=mp4, url=url))

        t = -np.inf
        for T in sorted(mediumEvidence[medium]):

            # read frame by frame until we reach time T
            while t < T:
                _, frame = capture.read()
                frameNumber = int(capture.get(cv.CV_CAP_PROP_POS_FRAMES))
                t = htmlTime(frameNumber)

            # DAR/PAR mismatch
            resized = cv2.resize(frame, (WIDTH, HEIGHT))

            # extract mugshot as PNG data
            for person_name, bbox in mediumEvidence[medium][T].iteritems():
                x, y = int(bbox.x * WIDTH), int(bbox.y * HEIGHT)
                w, h = int(bbox.w * WIDTH), int(bbox.h * HEIGHT)
                mugshot = cv2.resize(resized[y:y + h, x:x + w], (size, size))

                # first time we meet this person
                # quickly add/update its mugshot
                if person_name not in pngs:

                    logger.debug(
                        'mugshot - medium: {medium:s} - {name:s}'.format(
                            medium=medium, name=person_name))

                    # extract base64 PNG dump
                    _, stream = cv2.imencode('.png', mugshot)
                    png = b64encode(stream)

                    # get existing annotations for this person
                    # (there should be at most one)
                    annotations = robot.getAnnotations(layer=mugshotLayer,
                                                       fragment=person_name)

                    # if there is one, get its data content and update
                    # 'png' field (it might contain other fields than 'png')
                    if annotations:
                        data = annotations[0].data
                        data.png = png

                    # if not, create it from scratch
                    else:
                        data = {'png': png}

                    # create new annotation (don't update as it might lead
                    # to very heavy history)
                    _ = robot.createAnnotation(mugshotLayer, medium=medium,
                                               fragment=person_name, data=data,
                                               returns_id=True)

                    # delete old annotation(s)
                    for annotation in annotations:
                        robot.deleteAnnotation(annotation._id)

                # maintain the set of all mugshots as a list of numpy array
                pngs.setdefault(person_name, []).append(mugshot)

    # build wide png for css-animated mugshots for each person
    for person_name, mugshots in pngs.iteritems():

        logger.info('mugshots - {name:s}'.format(
            name=person_name))

        # randomly select at most --multiple mugshots and concatenate them
        mugshot = np.hstack(
            random.sample(mugshots, min(multiple, len(mugshots))))

        # build one wide png out of those multiple mugshots
        _, stream = cv2.imencode('.png', mugshot)
        png = b64encode(stream)

        # get existing annotations for this person
        # (there should be at most one)
        annotations = robot.getAnnotations(layer=mugshotLayer,
                                           fragment=person_name)

        # if there is one, get its data content and update 'PNG' field
        # (it should contain other field than 'PNG')
        if annotations:
            medium = annotations[0].id_medium
            data = annotations[0].data
            data.PNG = png

        # if not, create it from scratch
        # (this should never happen)
        else:
            data = {'PNG': png}
            # medium = random

        # create new annotation (don't update as it might lead
        # to very heavy history)
        _ = robot.createAnnotation(mugshotLayer, medium=medium,
                                   fragment=person_name, data=data,
                                   returns_id=True)

        # delete old annotation(s)
        for annotation in annotations:
            robot.deleteAnnotation(annotation._id)

    logger.info('waiting for {period:d} seconds'.format(period=period))
    time.sleep(period)
