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
from datetime import datetime

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

def update(nbAnnotationInQueue):
    # for all hypothesis layer

    items = []
    if nbAnnotationInQueue == limit:
        return items

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

    
    for layer in robot.getLayers(
            test, data_type='mediaeval.persondiscovery.evidence'):

        # skip original submission layers
        if 'copy' not in layer.description:
            continue

        # skip deleted submission layers
        if 'deleted' in layer.description:
            continue

        # skip if all annotations are done
        if 'annotationsComplete' in layer.description:
            continue

        # {evidence: id_evidence, label: id_label}
        evidenceLayer = layer._id
        labelLayer = layer.description.id_label

        description = robot.getLayer(labelLayer).description
        # (initialize empty mapping if needed)
        _ = description.setdefault('mapping', {})
        # keep track of (already done) manual annotations
        # {id_shot, person_name, source: corrected_person_name}
        # {id_shot, person_name, source: False} (if not an evidence)

        annotationToDo = False

        for id_medium, evidences in robot.getAnnotations_iter(evidenceLayer):

            # loop on evidence from one medium
            for evidence in evidences:

                id_shot = evidence.fragment
                person_name = evidence.data.person_name
                source = evidence.data.source

                if person_name in description.mapping:
                    continue

                # if this hypothesized evidence has been checked already
                if (id_shot, person_name, source) in mapping:

                    logger.debug(
                        "existing evidence - {name:s} - {source:s}".format(
                            name=person_name, source=source))

                    # propagate this evidence to this submission mapping

                    description.mapping[person_name] = mapping[id_shot,
                                                               person_name,
                                                               source]
                    robot.updateLayer(labelLayer, description=description)

                # if this hypothesized evidence has not been checked yet
                # push to evidence annotation frontend
                else:

                    annotationToDo = True

                    item = {}

                    item['id_submission'] = labelLayer
                    item['person_name'] = person_name
                    item['source'] = source

                    item['id_medium'] = id_medium
                    item['id_shot'] = id_shot
                    segment = robot.getAnnotation(id_shot).fragment.segment
                    item['start'] = segment.start - (5 if source == 'audio'
                                                       else -0.5)
                    item['end'] = segment.end + (5 if source == 'audio'
                                                   else -0.5)

                    items.append(item)

                    if len(items) > limit - nbAnnotationInQueue:
                        return items

        if not annotationToDo:
            description = layer.description
            description['annotationsComplete'] = True
            robot.updateLayer(evidenceLayer, description=description)

            logger.debug("all evidences are annotated for {layer:s}".format(
                         layer=evidenceLayer))

    return items


t = datetime.now()
while True:

    items = update(robot.pickLength(evidenceInQueue))
    if not items:
        sleep(period)

    for item in items:
        logger.info(
            "new evidence - {name:s} - {source:s}".format(
                name=item['person_name'], source=item['source']))

        robot.enqueue_fair(evidenceInQueue, item, limit=limit)

        if (datetime.now() - t).total_seconds() > period:
            t = datetime.now()
            break
