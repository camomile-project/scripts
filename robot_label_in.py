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
# Johann POIGNANT -- http://johannpoignant.github.io/

"""
MediaEval label in robot

Usage:
  robot_label_in [options]

Options:
  -h --help                 Show this screen.
  --version                 Show version.
  --debug                   Show debug information.
  --url=URL                 Camomile server URL
                            [default: http://api.mediaeval.niderb.fr]
  --password=P45sw0Rd       Password
  --refresh=N               Refresh annotation status every N sec
                            [default: 86400].
  --period=N                Query label queue every N sec [default: 600].
  --limit=N                 Approximate maximum number of items in
                            label queue [default: 400].
  --skip-empty              Put into the queue only shot with hypothesis
  --videos=PATH             List of video to process
  --other=N                 Number of alternative person names [default: 10]
  --log=DIR                 Path to log directory.
  --queue=NAME              Label incoming queue [default: mediaeval.label.in]
  --no-unknown-consensus    Stop looking for consensus when unknown
"""

from common import RobotCamomile, create_logger
from docopt import docopt
from datetime import datetime
from random import sample

emptyAtLaunch = True

ANCHORS = set(["david_pujadas",
               "beatrice_schonberg",
               "laurent_delahousse",
               "francoise_laborde"])
UNKNOWN = '?unknown?'

arguments = docopt(__doc__, version='0.1')

# Camomile API
url = arguments['--url']
password = arguments['--password']
noUnknownConsensus = arguments['--no-unknown-consensus']

# debugging and logging
debug = arguments['--debug']
log = arguments['--log']
logger = create_logger('robot_label_in', path=log, debug=debug)

# how often to refresh annotation status
refresh = int(arguments['--refresh'])

# how often to pick queue length
period = int(arguments['--period'])

# approximate maximum number of items in queue
limit = int(arguments['--limit'])

# put into the queue only shot with hypothesis
skipEmpty = arguments['--skip-empty']

# only annotate those videos
videos = arguments['--videos']

other = int(arguments['--other'])

queueName = arguments['--queue']

robot = RobotCamomile(
    url, 'robot_label', password=password,
    period=period, logger=logger)

# test corpus
test = robot.getCorpusByName('mediaeval.test')

# layer containing submission shots
submissionShotLayer = robot.getLayerByName(
    test, 'mediaeval.submission_shot')

# layer containing every label annotations
allLayer = robot.getLayerByName(
    test, 'mediaeval.groundtruth.label.all')

# layer containing consensus label annotations
consensusLayer = robot.getLayerByName(
    test, 'mediaeval.groundtruth.label.consensus')

# layer containing "unknown" annotations
unknownLayer = robot.getLayerByName(
    test, 'mediaeval.groundtruth.label.unknown')

# mugshot layer
mugshotLayer = robot.getLayerByName(
    test, 'mediaeval.groundtruth.evidence.mugshot')

# filled by this script and popped by label annotation front-end
labelInQueue = robot.getQueueByName(queueName)

# load list of media in test corpus
# as {name: id} dictionary
media = {medium.name: medium._id for medium in robot.getMedia(test)}

if videos:
    with open(videos, 'r') as f:
        videos = [v.strip() for v in f]
    media = [media[v] for v in videos if v in media]
else:
    media = media.values()

logger.info('load mapping of all existing label layers')

# load mapping of all existing label layers
LAYER_MAPPING = {}
for layer in robot.getLayers(test,
                             data_type='mediaeval.persondiscovery.label'):

    # skip original submission layers
    if 'copy' not in layer.description:
        continue

    # skip deleted submission layers
    if 'deleted' in layer.description:
        continue

    # default to empty mapping
    LAYER_MAPPING[layer._id] = layer.description.get('mapping', {})

LOADED = {}
SUBMISSION_SHOTS = {}
SORTED_SUBMISSION_SHOTS = {}
SHOTS = {}
ANNOTATION_HYPOTHESES = {}

def loadOnDemand(medium):

    # load list of shots in test corpus
    # as {id: details} dictionary
    logger.info('loading submission shots')

    SUBMISSION_SHOTS[medium] = {}
    for shot in robot.getAnnotations(submissionShotLayer, medium=medium):
        SUBMISSION_SHOTS[medium][shot._id] = {
            'id_medium': shot.id_medium,
            'start': shot.fragment.segment.start,
            'end': shot.fragment.segment.end}

    # sort SUBMISSION_SHOTS by medium and chronologically
    SORTED_SUBMISSION_SHOTS[medium] = sorted(
        SUBMISSION_SHOTS[medium],
        key=lambda s: (SUBMISSION_SHOTS[medium][s]['start']))

    # subset of submission shots
    SHOTS[medium] = set([s for s, d in SUBMISSION_SHOTS[medium].iteritems()
                         if d['id_medium'] == medium])

    logger.info('hypotheses')

    # get hypothesis person names
    ANNOTATION_HYPOTHESES[medium] = {}
    for layer in LAYER_MAPPING:
        logger.debug('hypotheses - medium = {medium} / layer = {layer}'.format(
            medium=medium, layer=layer))
        ANNOTATION_HYPOTHESES[medium][layer] = {}
        for shot in SUBMISSION_SHOTS[medium]:
            ANNOTATION_HYPOTHESES[medium][layer][shot] = set([])
        for a in robot.getAnnotations(layer=layer, medium=medium):
            ANNOTATION_HYPOTHESES[medium][layer][a.fragment].add(a.data.person_name)

    LOADED[medium] = True

def update(medium):

    # load on demand (done only once)
    if medium not in LOADED:
        loadOnDemand(medium)

    logger.info('refresh - loading consensus shots')

    # shots for which a consensus has already been reached
    shotWithConsensus = {}
    for annotation in robot.getAnnotations(consensusLayer, medium=medium):
        data = annotation.get('data', {})
        # HACK - data might be u'' - I don't know why
        if not data:
            data = {}
        shotWithConsensus[annotation.fragment] = set(data)

    # shots for which a unknown has been annotated
    shotWithUnknown = set([])
    if noUnknownConsensus:
        for annotation in robot.getAnnotations(unknownLayer, medium=medium):
            shotWithUnknown.add(annotation.fragment)

    # shots for which we are still missing annotations
    # in order to reach a consensus
    remainingShots = SHOTS[medium]
    remainingShots -= set(shotWithConsensus.keys())
    remainingShots -= shotWithUnknown

    # update layer mapping
    for layer in LAYER_MAPPING:
        LAYER_MAPPING[layer] = robot.getLayer(layer).description.get('mapping', {})

    logger.info('refresh - loading person names with mugshot')

    # set of person name with a mugshot
    personNameWithMugshot = set(
        robot.getLayer(mugshotLayer).description.mugshots.keys())

    logger.info('refresh - building hypothesis for remaining shots')


    hypotheses = {}
    annotators = {}

    allAnnotations = robot.getAnnotations(layer=allLayer, medium=medium)

    for shot in remainingShots:
        hypotheses[shot] = set([])
        annotators[shot] = set([])

        for annotation in [a for a in allAnnotations if a.fragment == shot]:
            # get set of all hypothesis already annotated
            hypotheses[shot].update(
                set(annotation.data.get('known', {}).keys()))

            # get set of users who already annotated this shot
            annotators[shot] = set([annotation.data.annotator])

        skip_shot = False
        for layer, mapping in LAYER_MAPPING.iteritems():

            for hypothesizedPersonName in ANNOTATION_HYPOTHESES[medium][layer][shot]:

                # find how the hypothesized name was mapped
                correctedPersonName = mapping.get(hypothesizedPersonName, None)

                # in case it has not been checked yet
                # skip this shot entirely
                if correctedPersonName is None:
                    logger.info(
                        'refresh - skipping shot {shot} because evidence '
                        'for {name} has not been checked yet.'.format(
                            shot=shot, name=hypothesizedPersonName))
                    skip_shot = True
                    break

                # in case it has been checked but found to NOT be an evidence
                # don't add this hypothesis
                if correctedPersonName is False:
                    continue

                # in case the mapped person name does not have a mugshot yet
                # skip this shot entirely
                if correctedPersonName not in personNameWithMugshot:
                    logger.info(
                        'refresh - skipping shot {shot} because no mugshot '
                        'is available for {name}.'.format(
                            shot=shot, name=correctedPersonName))
                    skip_shot = True
                    break

                hypotheses[shot].add(correctedPersonName)

            if skip_shot:
                break

        if skip_shot:
            del hypotheses[shot]
            del annotators[shot]

    logger.info('refresh - gathering alternative hypotheses')

    others = {}

    for shot in hypotheses:
        others[shot] = set([])

        i = SORTED_SUBMISSION_SHOTS[medium].index(shot)
        n = len(SORTED_SUBMISSION_SHOTS[medium])
        nearShots = SORTED_SUBMISSION_SHOTS[medium][max(i - other, 0):
                                                  min(i + other, n)]

        others[shot].update(ANCHORS)
        for nearShot in nearShots:
            others[shot].update(
                shotWithConsensus.get(nearShot, set([])))

            others[shot].update(
                hypotheses.get(nearShot, set([])))

        # remove person already in hypotheses
        others[shot] -= hypotheses[shot]

        # remove ?unknown?
        others[shot] -= set([UNKNOWN])

    return hypotheses, others, annotators

while True:

    # randomize media order
    for medium in sample(media, len(media)):

        # only refresh this medium
        now = datetime.now()
        hypotheses, others, annotators = update(medium)
        t = datetime.now()

        logger.info('refresh - medium {medium} finished in {seconds:d} seconds'.format(
            medium=medium, seconds=int((t - now).total_seconds())))

        for shot in SORTED_SUBMISSION_SHOTS[medium]:

            # shot was skipped
            if shot not in hypotheses:
                continue

            # do not annotate a shot if there is no hypothesis
            if hypotheses[shot] == set([]) and skipEmpty:
                continue

            item = {}
            item['id_shot'] = shot
            item['id_medium'] = SUBMISSION_SHOTS[medium][shot]['id_medium']
            item['start'] = SUBMISSION_SHOTS[medium][shot]['start'] + 0.5
            item['end'] = SUBMISSION_SHOTS[medium][shot]['end'] - 0.5
            item['hypothesis'] = list(hypotheses[shot])
            item['others'] = list(others[shot])
            item['annotated_by'] = list(annotators[shot])

            logger.debug('new annotation for shot {shot}'.format(
                shot=shot))

            # empty queue at launch time
            if emptyAtLaunch:
                robot.updateQueue(labelInQueue, elements=[])
                emptyAtLaunch = False

            robot.enqueue_fair(labelInQueue, item, limit=limit)
