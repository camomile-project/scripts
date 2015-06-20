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
MediaEval mugshot

Usage:
  new_mugshot [options] <person_name.png>

Options:
  -h --help                Show this screen.
  --version                Show version.
  --debug                  Show debug information.
  --url=URL                Submission server URL
                           [default: http://api.mediaeval.niderb.fr]
  --password=P45sw0Rd      Password
  --size=N                 Mugshot size in pixel [default: 100].

"""

from common import RobotCamomile
from docopt import docopt
import os
import cv2
from base64 import b64encode

arguments = docopt(__doc__, version='0.1')

size = int(arguments['--size'])

url = arguments['--url']
password = arguments['--password']

robot = RobotCamomile(
    url, 'robot_evidence', password=password)

# test corpus
test = robot.getCorpusByName('mediaeval.test')

# mugshot layer
mugshotLayer = robot.getLayerByName(
    test, 'mediaeval.groundtruth.evidence.mugshot')

path = arguments['<person_name.png>']
basename = os.path.basename(path)
person_name, _ = os.path.splitext(basename)

mugshot = cv2.resize(cv2.imread(path), (size, size))

# extract base64 PNG dump
_, stream = cv2.imencode('.png', mugshot)
png = b64encode(stream)

# get existing annotations for this person
# (there should be at most one)
annotations = robot.getAnnotations(layer=mugshotLayer,
                                   fragment=person_name)

# if there is one, get its data content and update
# 'png' fields
if annotations:
    data = annotations[0].data
    data.png = png
    data.PNG = png

# if not, create it from scratch
else:
    data = {'png': png, 'PNG': png}

# create new annotation (don't update as it might lead
# to very heavy history)

# this is a hack
medium = robot.getMedia(test, returns_id=True)[0]

_ = robot.createAnnotation(mugshotLayer, medium=medium,
                           fragment=person_name, data=data,
                           returns_id=True)

# delete old annotation(s)
for annotation in annotations:
    robot.deleteAnnotation(annotation._id)
