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
  --sizeQueue=N            Size of the queue [default: 400].
  --videosList=vl          list of video to process
  --nbOtherNames           number of other names to porposed in addition to the ones in the submissions
  --log=DIR                Path to log directory.
"""

from common import RobotCamomile, create_logger
from docopt import docopt
from datetime import datetime

def update_hypothesis(test, shotWithFinalAnnotation, shotToBeAnnotated, nbOtherNames):
    # remove shot from shotToBeAnnotated if there is enough annotation
    for shot in shotWithFinalAnnotation & set(shotToBeAnnotated.keys()):
        del shotToBeAnnotated[shot]

    # get all layers hypothesis not deleted
    listLayerHypothesis = []
    for layer in robot.getLayers(test):
        if layer.data_type == 'mediaeval.persondiscovery.label'  and  layer.description.status != "deleted" : 
            mapping = 'mapping' in layer.description and mapping = layer.description.mapping or mapping = {}
            listLayerHypothesis.append([layer._id, mapping])

    # for each shot to be annotated list hypothesis person name
    for shot in shotToBeAnnotated:
        for layer, mapping in listLayerHypothesis:
            for a in [a for a in robot.getAnnotations(layer = layer, fragment = shot) if a.data.person_name in mapping]:
                shotToBeAnnotated[a.fragment]["hypothesis"].add(mapping[a.data.person_name)

        # append hypothesis slected by other annotator
        for a in robot.getAnnotations(layer = labelCompleteGroudtruthLayer, fragment = shot)
            shotToBeAnnotated[a.fragment]["hypothesis"].add(a.output.known)

    # for each shot to be annotated list hypothesis to put in others
    for shot in shotToBeAnnotated:
        othersTmp = []
        # list hypothesis in other shots of the same video
        for shotNear in [shotNear for shotNear in shotToBeAnnotated if shot != shotNear and shotToBeAnnotated[shot]["id_medium"] == shotToBeAnnotated[shotNear]["id_medium"]]:
            for p in shotToBeAnnotated[shot]["hypothesis"]:
                othersTmp.append([abs(shotToBeAnnotated[shot]["start"]-shotToBeAnnotated[shotNear]["start"]), p])

        # keep only the XXX hypothesis the more near temporally
        for d, p in sorted(othersTmp)[:nbOtherNames]:
            shotToBeAnnotated[shot]["others"].add(p)

        shotToBeAnnotated[shot]["others"] = shotToBeAnnotated[shot]["others"]+set(["david_pujadas", "beatrice_schonberg", "laurent_delahousse", "francoise_laborde"])


    return shotToBeAnnotated


arguments = docopt(__doc__, version='0.1')

url = arguments['--url']
password = arguments['--password']
period1 = int(arguments['--period1'])
period2 = int(arguments['--period2'])
sizeQueue = int(arguments['--sizeQueue'])
videosList = arguments['--videosList']
nbOtherNames = int(arguments['--nbOtherNames'])


debug = arguments['--debug']
log = arguments['--log']
logger = create_logger('robot_label_in', path=log, debug=debug)
robot = RobotCamomile(url, 'robot_label', password=password, period=period2, logger=logger)

# corpus id
test = robot.getCorpusByName('mediaeval.test')

# layer containing submission shots
submissionShotLayer = robot.getLayerByName(test, 'mediaeval.submission_shot')
# layer containing aggregated annotations for label grondtruth
labelFinalGroudtruthLayer = robot.getLayerByName(test, 'mediaeval.groundtruth.label.aggregated')
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
    mediaIds = set([media['_id'] for media in robot.getMedia(test) if media['name'] in videos])
else:
    mediaIds = set([media['_id'] for media in robot.getMedia(test)])

# initialize a dictionnary with shot as keys and personNames as values
shotToBeAnnotated = {shot['_id']: {"hypothesis":set([]), 
                                   "id_medium":shot.id_medium, 
                                   "start":shot.fragment.segment.start, 
                                   "end":shot.fragment.segment.end,
                                   "others":set([]) }
                     for shot in robot.getAnnotations(layer = submissionShotLayer)
                     if shot.id_medium in mediaIds
                    }

# list of shots with final annotation
shotWithFinalAnnotation = set([a.fragment for a in robot.getAnnotations(layer = labelFinalGroudtruthLayer)])

# initialisze list of hypothesis for each shot
shotToBeAnnotated = update_hypothesis(test, shotWithFinalAnnotation, shotToBeAnnotated, nbOtherNames)

# list of person name with at least one mugshot available
mugShots = set([a.fragment for a in robot.getAnnotations(layer = evidenceMugShotLayer)])

t = datetime.now() 

while True :
    for shot in shotToBeAnnotated:
        # if not all mugshots are available skip the shot
        if shotToBeAnnotated[shot]["hypothesis"] - mugShots: 
            continue

        # if this shot has been already annotated with an unknown
        labelUnknown = robot.getAnnotations(layer = labelUnknownLayer, fragment = shot)
        if labelUnknown:
            # if there is no new mugshot to help annotator  
            if not (shotToBeAnnotated[shot]["hypothesis"] - labelUnknown['data']): 
                continue
            # else re-annotated the shot and remove it from mediaeval.groundtruth.label.unknown
            robot.deleteAnnotation(labelUnknown)

        # get who already annotated the shot
        labelCompleteGroudtruth = robot.getAnnotations(layer = labelCompleteGroudtruthLayer, fragment = shot)
        l_annotator = [login['data']['annotator'] for login in labelCompleteGroudtruth]
        
        # add a new element in the queue in
        item = {}
        item["id_medium"]    = shotToBeAnnotated[shot]["id_medium"]
        item["id_shot"]      = shot
        item["start"]        = shotToBeAnnotated[shot]["start"]
        item["end"]          = shotToBeAnnotated[shot]["end"]
        item["hypothesis"]   = list(shotToBeAnnotated[shot]["hypothesis"])
        item["others"]       = list(shotToBeAnnotated[shot]["others"])
        item["annotated_by"] = l_annotator

        robot.enqueue_fair(InCommingQueue, item, limit=sizeQueue)

        if (datetime.now() - t).total_seconds() < period1:
            # list of shots with final annotation
            shotWithFinalAnnotation = set([a["fragment"] for a in robot.getAnnotations(layer = labelFinalGroudtruthLayer)])
            
            # update list of hypothesis for each shot
            shotToBeAnnotated = update_hypothesis(test, shotWithFinalAnnotation, shotToBeAnnotated, nbOtherNames)

            # list of person name with at least one mugshot available
            mugShots = set([a['fragment'] for a in robot.getAnnotations(layer = evidenceMugShotLayer)])

            # get current time
            t = datetime.now()  
