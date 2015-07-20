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
Dump MediaEval annotations

Usage:
  dump <output_dir> [options]

Options:
  -h --help             Show this screen.
  --url=URL             Submission server URL
                        [default: http://api.mediaeval.niderb.fr]
  --login=login         login [default: robot_leaderboard]
  --password=P45sw0Rd   Password
"""

from common import RobotCamomile
from docopt import docopt
from getpass import getpass
from datetime import datetime

arguments = docopt(__doc__, version='0.1')

url = arguments['--url']
outputDir = arguments['<output_dir>']
login = arguments['--login']
password = arguments['--password']

if login is None:
    login = raw_input('Login: ')
if password is None:
    password = getpass('{login} password: '.format(login=login))

now = datetime.strftime(datetime.today(), '%Y%m%d-%H%M')

client = RobotCamomile(
    url, 'robot_leaderboard', password=password)

# test corpus
test = client.getCorpusByName('mediaeval.test')

# label consensus layer
labelLayerID = client.getLayerByName(
    test, 'mediaeval.groundtruth.label.consensus')

# evidence layer
evidenceLayerID = client.getLayerByName(
    test, 'mediaeval.groundtruth.evidence.all')

media = {medium._id: medium.name for medium in client.getMedia(test)}

shotLayerID = client.getLayerByName(
    test, 'mediaeval.submission_shot')

shots = {}
for medium, annotations in client.getAnnotations_iter(shotLayerID):
    for shot in annotations:
        videoName = media[shot.id_medium]
        shotNumber = shot.fragment.shot_number
        shotID = shot._id
        shots[shotID] = (videoName, shotNumber)


templateRef = '{videoName} {shotNumber:06d} {personName}\n'
templateShot = '{videoName} {shotNumber:06d}\n'
pathRef = '{outputDir}/{now}.ref'.format(outputDir=outputDir, now=now)
pathShot = '{outputDir}/{now}.consensus'.format(outputDir=outputDir, now=now)
with open(pathRef, 'w') as f, open(pathShot, 'w') as g:

    for mediumID, annotations in client.getAnnotations_iter(labelLayerID):
        print 'Label for', media[mediumID]

        for annotation in annotations:

            shotID = annotation.fragment
            videoName, shotNumber = shots[shotID]
            g.write(templateShot.format(
                videoName=videoName,
                shotNumber=shotNumber))

            # HACK
            data = annotation.data
            if data == '':
                data = dict()

            speakingFaces = {
                p for p, status in data.iteritems()
                if status == 'speakingFace'}

            for personName in speakingFaces:
                f.write(templateRef.format(
                    videoName=videoName,
                    shotNumber=shotNumber,
                    personName=personName))

templateEvi = '{videoName} {shotNumber:06d} {personName} {source}\n'
pathEvi = '{outputDir}/{now}.eviref'.format(outputDir=outputDir, now=now)
with open(pathEvi, 'w') as h:

    for mediumID, annotations in client.getAnnotations_iter(evidenceLayerID):
        print 'Evidence for', media[mediumID]
        for annotation in annotations:

            if not annotation.data.is_evidence:
                continue

            shotID = annotation.fragment
            videoName, shotNumber = shots[shotID]
            personName = annotation.data.corrected_person_name
            source = annotation.data.source

            h.write(templateEvi.format(
                videoName=videoName,
                shotNumber=shotNumber,
                personName=personName,
                source=source))
