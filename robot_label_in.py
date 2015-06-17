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
  --period1=N              Query label and evidence groudtruth every N sec [default: 86400].
  --period2=N              Query queue in size every N sec [default: 600].
  --minSizeQueue=N         minimum size of the queue [default: 300].
  --maxSizeQueue=N         maximum size of the queue [default: 400].
  --videosList=vl          list of video to process
  --log=DIR                Path to log directory.
"""

from common import RobotCamomile, create_logger
from docopt import docopt
from time import sleep

arguments = docopt(__doc__, version='0.1')

url = arguments['--url']
password = arguments['--password']
period1 = int(arguments['--period1'])
period2 = int(arguments['--period2'])
minSizeQueue = int(arguments['--minSizeQueue'])
maxSizeQueue = int(arguments['--maxSizeQueue'])
videosList = arguments['--videosList']

debug = arguments['--debug']
log = arguments['--log']
logger = create_logger('robot_evidence_in', path=log, debug=debug)
robot = RobotCamomile(url, 'robot_label', password=password, period=period2, logger=logger)

# corpus id
test = robot.getCorpusByName('mediaeval.test')

# layer containing submission shots
submissionShotLayer = robot.getLayerByName(test, 'mediaeval.submission_shot')
# layer containing agragated annotations for label grondtruth
labelAgragatedGroudtruthLayer = robot.getLayerByName(test, 'mediaeval.groundtruth.label.agragated')
# layer containing complete annotations for label grondtruth
labelCompleteGroudtruthLayer = robot.getLayerByName(test, 'mediaeval.groundtruth.label.complete')
# layer containing shot with an unknown person
labelUnknownLayer = robot.getLayerByName(test, 'mediaeval.groundtruth.label.unknown')
# layer containing manual annotations for mugshot
evidenceMugShotLayer = robot.getLayerByName(test, 'mediaeval.groundtruth.evidence.mugshot')
# id of the in coming queue
InCommingQueue = robot.getQueueByName('mediaeval.submission.label.in')

# list of video to process
if videosList: 
    videos = [video for video in open(videosList).read().splitlines()]
    mediaIds = [media['_id'] for media in robot.getMedia(test) if media['name'] in videos]
else:
    mediaIds = [media['_id'] for media in robot.getMedia(test)]

# initialize a dictionnary with shot as keys and personNames as values
shotHypothesis = {shot['_id']: {"hypothesis":set([]), 
                                "id_medium":shot['id_medium'], 
                                "start":shot['fragment']['segment']['start'], 
                                "end":shot['fragment']['segment']['end']}  
                  for shot in robot.getAnnotations(layer = submissionShotLayer)
                  if shot['id_medium'] in mediaIds
                 }



while True :
    # list of shots completely annotated
    completeGroudtruthLayer = set([a["fragment"] for a in robot.getAnnotations(layer = labelCompleteGroudtruthLayer)])
    
    # remove shot from shotHypothesis if there is enough annotation
    for shot in completeGroudtruthLayer & set(shotHypothesis.keys()): del shotHypothesis[shot]

    # re-initialize hypothesis
    for shot in shotHypothesis:
        shotHypothesis[shot]["hypothesis"] = set([])

    # for each layer hypothesis
    for layer in robot.getLayers(test):
        if layer['data_type'] == 'mediaeval.persondiscovery.label'  and  layer['description']['status'] != "deleted" :  
            # mapping between hypothesis name and correted name
            mapping = layer['description']['mapping']
            
            # count the number of occurence per personName
            for a in robot.getAnnotations(layer = layer['_id']): 
                if a["fragment"] in shotHypothesis:
                    p = a['data']["person_name"]
                    if p in mapping: p = mapping[p]
                    
                    shotHypothesis[a["fragment"]]["hypothesis"].add(p)

    # list of person name with at least one mugshot available
    mugShots = set([a['fragment'] for a in robot.getAnnotations(layer = evidenceMugShotLayer)])
    
    # initialize the local queue        
    localQueue = [e['id_shot'] for e in robot.pickAll(InCommingQueue)]

    while True :
        # get the number of elements in the queue
        lenQueue = robot.pickLength(InCommingQueue)

        # if the number of elements in the labelInCommingQueue is higher than minSizeQueue, wait period1 seconds:
        if lenQueue > minSizeQueue: continue

        # remove first N elements from the local queue that have been annotated 
        localQueue = localQueue[-lenQueue:]

        for shot in shotHypothesis:
            # if not all mugshots are available skip the shot
            if shotHypothesis[shot]["hypothesis"] - mugShots: continue

            # if this shot has been already annotated with an unknown
            labelUnknown = robot.getAnnotations(layer = labelUnknownLayer, fragment = shot)
            if labelUnknown:
                # if there is no new mugshot to help annotator  
                if not (shotHypothesis[shot]["hypothesis"] - labelUnknown['data']['proposed_mugshot']): continue
                # else re-annotated the shot and remove it from mediaeval.groundtruth.label.unknown
                robot.deleteAnnotation(labelUnknown)

            # get who already annotated the shot
            labelAgragatedGroudtruth = robot.getAnnotations(layer = labelAgragatedGroudtruthLayer, fragment = shot)
            l_annotator = [login['data']['annotator'] for login in labelAgragatedGroudtruth]
            
            # add a new element in the queue in
            item = {}
            item["id_medium"]    = shotHypothesis[shot]["id_medium"]
            item["id_shot"]      = shot
            item["start"]        = shotHypothesis[shot]["start"]
            item["end"]          = shotHypothesis[shot]["end"]
            item["hypothesis"]   = list(shotHypothesis[shot]["hypothesis"])
            item["others"]       = []
            item["annotated_by"] = l_annotator

            robot.enqueue(InCommingQueue, item)
            lenQueue+=1


            if lenQueue > maxSizeQueue: break

        if lenQueue < minSizeQueue: print 'add new video to process'

        sleep(period1)
    sleep(period2)
