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
MediaEval submission robot

Usage:
  robot_submission [options]

Options:
  -h --help                Show this screen.
  --version                Show version.
  --debug                  Show debug information.
  --url=URL                Submission server URL
                           [default: http://api.mediaeval.niderb.fr]
  --password=P45sw0Rd      Password
  --period=N               Query evidence queue every N sec [default: 600].
  --log=DIR                Path to log directory.
"""

from common import RobotCamomile, create_logger
from docopt import docopt
from time import sleep

arguments = docopt(__doc__, version='0.1')

url = arguments['--url']
password = arguments['--password']
period = int(arguments['--period'])

debug = arguments['--debug']
log = arguments['--log']
logger = create_logger('robot_evidence_in', path=log, debug=debug)
robot = RobotCamomile(url, 'robot_label', password=password, period=period, logger=logger)

# corpus id
test = robot.getCorpusByName('mediaeval.test')

# layer containing agragated annotations for label grondtruth
labelAgragatedGroudtruthLayer = robot.getLayerByName(test, 'mediaeval.groundtruth.label.agragated')
# layer containing complete annotations for label grondtruth
labelCompleteGroudtruthLayer = robot.getLayerByName(test, 'mediaeval.groundtruth.label.complete')
# layer containing shot with an unknown person
labelUnknownLayer = robot.getLayerByName(test, 'mediaeval.groundtruth.label.unknown')
# id of the in coming queue
OutGoingQueue = robot.getQueueByName('mediaeval.submission.label.out')

for item in robot.dequeue_loop(OutGoingQueue):

    # front-end input
    id_shot = item.input.id_shot
    hypothesis = item.input.hypothesis
    others = item.input.others

    # if there is an unknown speaking face in the shot create an annotation of this shot in the labelUnknownLayer
    if item.output.unknown:
        robot.createAnnotation(labelUnknownLayer, fragment=id_shot, data=hypothesis+others)
        continue

    known = item.output.known

    # find if there is two identical annotations 
    identical = False

    l_labelCompleteGroudtruth = robot.getAnnotations(layer = labelCompleteGroudtruthLayer, fragment = id_shot)

    if len(l_labelCompleteGroudtruth) >= 2:

        for labelCompleteGroudtruth in l_labelCompleteGroudtruth:
            if set(known.keys()) == set(labelCompleteGroudtruth.keys()):
                identical = True
                for p in known:
                    if known[p] != labelCompleteGroudtruth[p] or known[p] == "dontKnow":
                        identical = False
                        break
                if identical: 
                    robot.createAnnotation(labelFinalGroudtruthLayer, fragment=id_shot, data=known)
                    break

    robot.createAnnotation(labelCompleteGroudtruthLayerLayer, fragment=id_shot, data=known)

