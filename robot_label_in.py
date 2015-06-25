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
  -h --help                Show this screen.
  --version                Show version.
  --debug                  Show debug information.
  --url=URL                Camomile server URL
                           [default: http://api.mediaeval.niderb.fr]
  --password=P45sw0Rd      Password
  --refresh=N              Refresh annotation status every N sec
                           [default: 86400].
  --period=N               Query label queue every N sec [default: 600].
  --limit=N                Approximate maximum number of items in
                           label queue [default: 400].
  --videos=PATH            List of video to process
  --other                  Number of alternative person names [default: 10]
  --log=DIR                Path to log directory.
"""

from common import RobotCamomile, create_logger
from docopt import docopt
from datetime import datetime

ANCHORS = set(["david_pujadas",
               "beatrice_schonberg",
               "laurent_delahousse",
               "francoise_laborde"])

arguments = docopt(__doc__, version='0.1')

# Camomile API
url = arguments['--url']
password = arguments['--password']

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

# only annotate those videos
videos = arguments['--videos']

other = int(arguments['--other'])

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
labelInQueue = robot.getQueueByName(
    'mediaeval.label.in')

# load list of shots in test corpus
# as {id: details} dictionary

logger.info('loading submission shots')

submissionShots = {}
for _, annotations in robot.getAnnotations_iter(submissionShotLayer):
    for shot in annotations:
        submissionShots[shot._id] = {'id_medium': shot.id_medium,
                                     'start': shot.fragment.segment.start,
                                     'end': shot.fragment.segment.end}


# sort submissionShots by medium and chronologically
sortedSubmissionShots = sorted(
    submissionShots,
    key=lambda s: (submissionShots[s]['id_medium'],
                   submissionShots[s]['start']))

# load list of media in test corpus
# as {name: id} dictionary
media = {medium.name: medium._id for medium in robot.getMedia(test)}

if videos:
    with open(videos, 'r') as f:
        videos = [v.strip() for v in f]
    media = [media[v] for v in videos if v in media]
else:
    media = media.values()

# subset of submission shots
shots = set([s for s, d in submissionShots.iteritems()
             if d['id_medium'] in media])


def update(shots):

    logger.info('refresh - loading consensus shots')

    # shots for which a consensus has already been reached
    shotWithConsensus = set([])
    for _, annotations in robot.getAnnotations_iter(consensusLayer):
        for annotation in annotations:
            shotWithConsensus.add(annotation.fragment)

    # shots for which a unknown has been annotated
    shotWithUnknown = set([])
    for _, annotations in robot.getAnnotations_iter(unknownLayer):
        for annotation in annotations:
            shotWithUnknown.add(annotation.fragment)

    # shots for which we are still missing annotations
    # in order to reach a consensus
    remainingShots = shots - shotWithConsensus.union(shotWithUnknown)

    logger.info('refresh - loading person names with mugshot')

    # set of person name with a mugshot
    personNameWithMugshot = set([
        annotation.fragment
        for _, A in robot.getAnnotations_iter(mugshotLayer)
        for annotation in A])

    logger.info('refresh - loading hypothesized label layers')

    # load mapping of all existing label layers
    layerMapping = {}
    for layer in robot.getLayers(
            test, data_type='mediaeval.persondiscovery.label'):

        # skip original submission layers
        if 'copy' not in layer.description:
            continue

        # skip deleted submission layers
        if 'deleted' in layer.description:
            continue

        # default to empty mapping
        layerMapping[layer._id] = layer.description.get('mapping', {})

    hypotheses = {}
    others = {}

    logger.info('refresh - building hypothesis for remaining shots')

    # build 'hypothesis' and 'others' fields for all remaining shots
    for shot in remainingShots:

        hypothesis = set([])
        skip = False

        for annotation in robot.getAnnotations(layer=allLayer, fragment=shot):
            hypothesis.update(set(annotation.data.get('known', {}).keys()))

        # find shot in all submissions
        for layer, mapping in layerMapping.iteritems():

            for annotation in robot.getAnnotations(layer=layer,
                                                   fragment=shot):

                # find if (and how) the hypothesized name was mapped
                hypothesizedPersonName = annotation.data.person_name
                correctedPersonName = mapping.get(
                    hypothesizedPersonName, None)

                # in case it has not been checked yet
                # skip this shot entirely
                if correctedPersonName is None:
                    logger.info(
                        'refresh - skipping shot {shot} because evidence '
                        'for {name} has not been checked yet.'.format(
                            shot=shot, name=hypothesizedPersonName))
                    skip = True
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
                    skip = True
                    break

                hypothesis.add(correctedPersonName)

            if skip:
                break

        if not skip:
            hypotheses[shot] = hypothesis

    logger.info('refresh - gathering alternative hypotheses')

    for shot in hypotheses:

        other = set([])

        i = sortedSubmissionShots.index(shot)

        n = len(sortedSubmissionShots)
        nearShots = sortedSubmissionShots[max(i - 5, 0):min(i + 5, n)]

        for nearShot in nearShots:
            other.update(hypotheses.get(nearShot, set([])))

        other.difference_update(hypotheses[shot])
        others[shot] = other

    return hypotheses, others, personNameWithMugshot

t = datetime.now()

hypotheses, others, withMugshot = update(shots)

while True:

    # sort shots from the shot with the highest number of hypotheses
    # to the shot with the smallest number of hypotheses
    # (this is to avoid annotating numerous empty shots)

    sortedShots = sorted(hypotheses,
                         key=lambda s: len(hypotheses[s]),
                         reverse=True)

    for shot in sortedShots:

        hypothesis = hypotheses[shot]

        # do not annotate a shot if there is no hypothesis
        if hypothesis == set([]):
            continue

        # do not annotate a shot for which at least
        # one hypothesis does not have a mugshot
        if hypothesis - withMugshot:
            continue

        # get set of users who already annotated this shot
        annotators = set([
            a.data.annotator for a in robot.getAnnotations(
                layer=allLayer, fragment=shot)])

        item = {}
        item['id_shot'] = shot
        item['id_medium'] = submissionShots[shot]['id_medium']
        item['start'] = submissionShots[shot]['start'] + 0.5
        item['end'] = submissionShots[shot]['end'] - 0.5
        item['hypothesis'] = list(hypothesis)
        item['others'] = list(ANCHORS - hypothesis) + list(others[shot] - ANCHORS - hypothesis)
        item['annotated_by'] = list(annotators)

        robot.enqueue_fair(labelInQueue, item, limit=limit)

        if (datetime.now() - t).total_seconds() > refresh:
            hypotheses, others, withMugshot = update(shots)
            t = datetime.now()
