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
  --other                   Number of alternative person names [default: 10]
  --log=DIR                 Path to log directory.
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

# put into the queue only shot with hypothesis
skipEmpty = arguments['--skip-empty']

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

# load list of media in test corpus
# as {name: id} dictionary
media = {medium.name: medium._id for medium in robot.getMedia(test)}

if videos:
    with open(videos, 'r') as f:
        videos = [v.strip() for v in f]
    media = [media[v] for v in videos if v in media]
else:
    media = media.values()

# load list of shots in test corpus
# as {id: details} dictionary
logger.info('loading submission shots')

submissionShots = {}
for medium in media:
    submissionShots[medium] = {}
    for shot in robot.getAnnotations(submissionShotLayer, medium=medium):
        submissionShots[medium][shot._id] = {'id_medium': medium,
            'start': shot.fragment.segment.start,
            'end': shot.fragment.segment.end}

# sort submissionShots by medium and chronologically
sortedSubmissionShots = {}
for medium in media:
    sortedSubmissionShots[medium] = sorted(
        submissionShots[medium],
        key=lambda s: (submissionShots[medium][s]['start']))

# subset of submission shots
shots = {}
for medium in media:
    shots[medium] = set([s for s, d in submissionShots[medium].iteritems()
                         if d['id_medium'] == medium])


def update(shots):

    logger.info('refresh - loading consensus shots')

    # shots for which a consensus has already been reached
    shotWithConsensus = {}
    for medium in media:
        shotWithConsensus[medium] = set([])
        for annotation in robot.getAnnotations(consensusLayer, medium=medium):
            shotWithConsensus[medium].add(annotation.fragment)

    # shots for which a unknown has been annotated
    shotWithUnknown = {}
    for medium in media:
        shotWithUnknown[medium] = set([])
        for annotation in robot.getAnnotations(unknownLayer, medium=medium):
            shotWithUnknown[medium].add(annotation.fragment)

    # shots for which we are still missing annotations
    # in order to reach a consensus
    remainingShots = {}
    for medium in media:
        remainingShots[medium] = shots[medium]
        remainingShots[medium] -= shotWithConsensus[medium]
        remainingShots[medium] -= shotWithUnknown[medium]

    logger.info('refresh - loading person names with mugshot')

    # set of person name with a mugshot
    personNameWithMugshot = set([
        annotation.fragment
        for _, A in robot.getAnnotations_iter(mugshotLayer)
        for annotation in A])

    logger.info('refresh - loading hypothesized label layers')

    # load mapping of all existing label layers
    layerMapping = {}
    for layer in robot.getLayers(test,
                                 data_type='mediaeval.persondiscovery.label'):

        # skip original submission layers
        if 'copy' not in layer.description:
            continue

        # skip deleted submission layers
        if 'deleted' in layer.description:
            continue

        # default to empty mapping
        layerMapping[layer._id] = layer.description.get('mapping', {})


    logger.info('refresh - building hypothesis for remaining shots')

    hypotheses = {}
    annotators = {}
    for medium in media:
        hypotheses[medium] = {}
        annotators[medium] = {}

        annotations = robot.getAnnotations(layer=allLayer, medium=medium)

        for shot in remainingShots[medium]:
            hypotheses[medium][shot] = set([])
            annotators[medium][shot] = set([])

            for annotation in [a for a in annotations if a.fragment == shot]:
                # get set of all hypothesis already annotated
                hypotheses[medium][shot].update(set(annotation.data.get('known', {}).keys()))

                # get set of users who already annotated this shot
                annotators[medium][shot] = set([annotation.data.annotator])

        for layer, mapping in layerMapping.iteritems():
            annotations = robot.getAnnotations(layer=layer, medium=medium)

            for annotation in [annotation for annotation in annotations
                               if annotation.fragment in remainingShots[medium]]:

                shot = annotation.fragment
                skip = False

                # find if (and how) the hypothesized name was mapped
                hypothesizedPersonName = annotation.data.person_name
                correctedPersonName = mapping.get(hypothesizedPersonName, None)

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

                hypotheses[medium][shot].add(correctedPersonName)

            if skip:
                hypotheses[medium][shot] = set([])

    logger.info('refresh - gathering alternative hypotheses')

    others = {}
    for medium in media:
        others[medium] = {}

        for shot in hypotheses[medium]:
            others[medium][shot] = set([])

            i = sortedSubmissionShots[medium].index(shot)
            n = len(sortedSubmissionShots[medium])
            nearShots = sortedSubmissionShots[medium][max(i - 5, 0):
                                                      min(i + 5, n)]

            for nearShot in nearShots:
                others[medium][shot].update(
                    hypotheses[medium].get(nearShot, set([])))

            others[medium][shot].update(ANCHORS)
            others[medium][shot] -= hypotheses[medium][shot]

    logger.info('refresh is finish')

    return hypotheses, others, annotators, personNameWithMugshot


t = datetime.now()

hypotheses, others, annotators, withMugshot = update(shots)

while True:
    for medium in media:

        for shot in [shot for shot in sortedSubmissionShots[medium] if shot in hypotheses[medium]]:
            # do not annotate a shot if there is no hypothesis
            if hypotheses[medium][shot] == set([]) and skipEmpty:
                continue

            # do not annotate a shot for which at least
            # one hypothesis does not have a mugshot
            if hypotheses[medium][shot] - withMugshot:
                continue

            item = {}
            item['id_shot'] = shot
            item['id_medium'] = submissionShots[medium][shot]['id_medium']
            item['start'] = submissionShots[medium][shot]['start'] + 0.5
            item['end'] = submissionShots[medium][shot]['end'] - 0.5
            item['hypothesis'] = list(hypotheses[medium][shot])
            item['others'] = list(others[medium][shot])
            item['annotated_by'] = list(annotators[medium][shot])

            logger.info('new annotation for shot {shot}'.format(
                            shot=shot))

            robot.enqueue_fair(labelInQueue, item, limit=limit)

            if (datetime.now() - t).total_seconds() > refresh:
                hypotheses, others, annotators, withMugshot = update(shots)
                t = datetime.now()
