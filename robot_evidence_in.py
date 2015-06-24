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
MediaEval evidence in

Usage:
  robot_evidence_in [options]

Options:
  -h --help                Show this screen.
  --version                Show version.
  --debug                  Show debug information.
  --url=URL                Submission server URL
                           [default: http://api.mediaeval.niderb.fr]
  --password=P45sw0Rd      Password
  --period=N               Query submission queue every N sec [default: 3600].
  --limit=N                Size of the queue [default: 1000].
  --log=DIR                Path to log directory.

"""

from common import RobotCamomile, create_logger
from docopt import docopt
from time import sleep

arguments = docopt(__doc__, version='0.1')

url = arguments['--url']
password = arguments['--password']
period = int(arguments['--period'])
limit = int(arguments['--limit'])

debug = arguments['--debug']
log = arguments['--log']
logger = create_logger('robot_evidence_in', path=log, debug=debug)

robot = RobotCamomile(
    url, 'robot_evidence', password=password,
    period=period, logger=logger)

# filled by this script and popped by evidence annotation front-end
evidenceInQueue = robot.getQueueByName(
    'mediaeval.evidence.in')

# unique layer containing manual annotations
test = robot.getCorpusByName('mediaeval.test')
evidenceGroundtruthLayer = robot.getLayerByName(
    test, 'mediaeval.groundtruth.evidence.all')


def update(numberOfEvidencesInQueue):

    logger.debug("loading list of existing evidences")

    # keep track of (already done) manual annotations
    # {id_shot, person_name, source: corrected_person_name}
    # {id_shot, person_name, source: False} (if not an evidence)
    mapping = {}
    for _, evidences in robot.getAnnotations_iter(evidenceGroundtruthLayer):
        for evidence in evidences:
            id_shot = evidence.fragment
            person_name = evidence.data.person_name
            source = evidence.data.source
            to = (evidence.data.corrected_person_name
                  if evidence.data.is_evidence
                  else False)
            mapping[id_shot, person_name, source] = to

    # for all evidence layers
    for evidenceLayer in robot.getLayers(
            test, data_type='mediaeval.persondiscovery.evidence'):

        # skip original submission layers
        if 'copy' not in evidenceLayer.description:
            continue

        # skip deleted submission layers
        if 'deleted' in evidenceLayer.description:
            continue

        # skip if all evidences are already checked
        if 'annotationsComplete' in evidenceLayer.description:
            continue

        # {evidence: id_evidence, label: id_label}
        evidenceLayerID = evidenceLayer._id
        labelLayerID = evidenceLayer.description.id_label

        labelLayer = robot.getLayer(labelLayerID)
        labelLayer.description.setdefault('mapping', {})

        # change this to true if at least one evidence needs to be checked
        hasUncheckedEvidences = False

        # loop on all hypothesized evidences
        for id_medium, evidences in robot.getAnnotations_iter(evidenceLayerID):
            for evidence in evidences:

                # get details abouth the evidence
                id_shot = evidence.fragment
                person_name = evidence.data.person_name
                source = evidence.data.source

                # if this evidence has been checked already (locally)
                # no need to check it twice
                if person_name in labelLayer.description.mapping:
                    continue

                # if this evidence has been checked already (globally)
                # add it to the local mapping
                if (id_shot, person_name, source) in mapping:

                    logger.debug(
                        "existing evidence - {name:s} - {source:s}".format(
                            name=person_name, source=source))

                    labelLayer.description.mapping[person_name] = \
                        mapping[id_shot, person_name, source]
                else:
                    hasUncheckedEvidences = True

        robot.updateLayer(labelLayerID, description=labelLayer.description)

        # if all evidences have been checked, mark layer as such
        if not hasUncheckedEvidences:
            evidenceLayer.description['annotationsComplete'] = True
            logger.debug("all evidences were checked for {layer:s}".format(
                         layer=evidenceLayerID))
            robot.updateLayer(evidenceLayerID,
                              description=evidenceLayer.description)

    # do not add any new evidence if the queue is already full
    newEvidences = []
    if numberOfEvidencesInQueue > limit:
        return newEvidences

    # for all evidence layers
    for evidenceLayer in robot.getLayers(
            test, data_type='mediaeval.persondiscovery.evidence'):

        # skip original submission layers
        if 'copy' not in evidenceLayer.description:
            continue

        # skip deleted submission layers
        if 'deleted' in evidenceLayer.description:
            continue

        # skip if all evidences are already checked
        if 'annotationsComplete' in evidenceLayer.description:
            continue

        # {evidence: id_evidence, label: id_label}
        evidenceLayerID = evidenceLayer._id
        labelLayerID = evidenceLayer.description.id_label

        # loop on all hypothesized evidences
        for id_medium, evidences in robot.getAnnotations_iter(evidenceLayerID):
            for evidence in evidences:

                # get details abouth the evidence
                id_shot = evidence.fragment
                person_name = evidence.data.person_name
                source = evidence.data.source

                # if this hypothesized evidence has not been checked yet
                # push to evidence annotation frontend
                if (id_shot, person_name, source) not in mapping:

                    item = {}

                    item['id_submission'] = labelLayerID
                    item['person_name'] = person_name
                    item['source'] = source

                    item['id_medium'] = id_medium
                    item['id_shot'] = id_shot
                    segment = robot.getAnnotation(id_shot).fragment.segment
                    item['start'] = segment.start - (5 if source == 'audio'
                                                     else -0.5)
                    item['end'] = segment.end + (5 if source == 'audio'
                                                 else -0.5)

                    newEvidences.append(item)

                    # stop gathering evidences as soon as we expect to fill
                    # the evidence annotation frontend queue
                    if len(newEvidences) + numberOfEvidencesInQueue > limit:
                        return newEvidences


    return newEvidences


while True:

    # get a certain amount of new evidences to annotate
    # based on the current length of the queue
    newEvidences = update(robot.pickLength(evidenceInQueue))

    # add (and log) all evidences, the one after the other
    for item in newEvidences:
        logger.info(
            "new evidence - {name:s} - {source:s}".format(
                name=item['person_name'], source=item['source']))

        robot.enqueue(evidenceInQueue, item)

    # if there are no new evidences, wait for a while
    if not newEvidences:
        sleep(period)
