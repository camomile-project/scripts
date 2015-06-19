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
from collections import Counter

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

    # add annotation to labelCompleteGroudtruthLayerLayer
    robot.createAnnotation(labelCompleteGroudtruthLayerLayer, fragment=id_shot, data={"known":item.output.known, "annotator":item.log.user})

    labelsCompleteGroudtruth = robot.getAnnotations(layer = labelCompleteGroudtruthLayer, fragment = id_shot)

    # if there is lesss than 2 annotations for this shot, go to the net shot
    if len(labelsCompleteGroudtruth) < 2:
        continue

    # else find if there is a consensus between annotator
    # list all annotated status for each hypothesis person of each annotation
    d = {}
    for labelCompleteGroudtruth in labelsCompleteGroudtruth:
        for p in labelCompleteGroudtruth.known:
            d.setdefault(p, []).append(labelCompleteGroudtruth.known[p])

    # if shot is already in labelFinalGroudtruthLayer: skip the aggragation
    if robot.getAnnotations(layer = labelFinalGroudtruthLayer, fragment = id_shot) != []:
        continue

    # check if the best status of each hypothesis person :
    #  - is different than dontKown
    #  - have at least 2 annotations for this status
    #  - there is a majority of this status
    aggregated = {}
    for p in d:
        state, nb = Counter(d[p]).most_common(1)

        if state == 'dontKnow' or nb < 2 or float(nb)/float(len(d[p])) < 0.5:
            aggregated = False
            break
        else:
            aggregated[p] = state

    # if there is a consensus for this shot, add an annotation with the consensus to labelFinalGroudtruthLayer
    if aggregated: 
        robot.createAnnotation(labelFinalGroudtruthLayer, fragment=id_shot, data=aggregated)


