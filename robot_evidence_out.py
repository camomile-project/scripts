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

arguments = docopt(__doc__, version='0.1')

url = arguments['--url']
password = arguments['--password']
period = int(arguments['--period'])

debug = arguments['--debug']
log = arguments['--log']
logger = create_logger('robot_evidence_out', path=log, debug=debug)

robot = RobotCamomile(
    url, 'robot_evidence', password=password,
    period=period, logger=logger)

# filled by evidence annotation front-end
evidenceOutQueue = robot.getQueueByName(
    'mediaeval.evidence.out')

# unique layer containing manual annotations
test = robot.getCorpusByName('mediaeval.test')
evidenceGroundtruthLayer = robot.getLayerByName(
    test, 'mediaeval.groundtruth.evidence.all')

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

# forever loop on evidence front-end output
for item in robot.dequeue_loop(evidenceOutQueue):

    # front-end input
    id_shot = item.input.id_shot
    id_medium = item.input.id_medium
    person_name = item.input.person_name
    source = item.input.source

    # id_submission might be missing in case evidences
    # were added manually to the queue independently of
    # any submissions
    id_submission = item.input.get('id_submission', None)

    # front-end output
    is_evidence = item.output.is_evidence
    if is_evidence:
        corrected_person_name = item.output.person_name
        seconds = item.output.time
        bounding_box = item.output.bounding_box

    # if this hypothesized evidence has not been checked yet
    # store it to the manual annotation layer
    if (id_shot, person_name, source) not in mapping:

        data = {}
        data['person_name'] = person_name
        data['is_evidence'] = is_evidence
        data['source'] = source
        if is_evidence:
            data['corrected_person_name'] = corrected_person_name
            data['mugshot'] = {}
            data['mugshot']['time'] = seconds
            data['mugshot']['bounding_box'] = bounding_box

        robot.createAnnotation(evidenceGroundtruthLayer,
                               medium=id_medium,
                               fragment=id_shot,
                               data=data)

        # remember we have just added this new annotation
        mapping[id_shot, person_name, source] = (corrected_person_name
                                                 if is_evidence
                                                 else False)

        logger.info(
            "new evidence - {name:s} - {source:s}".format(
                name=person_name, source=source))

    try:
        # propagate this evidence to the corresponding submission mapping
        description = robot.getLayer(id_submission).description
        # (initialize empty mapping if needed)
        _ = description.setdefault('mapping', {})
        description.mapping[person_name] = mapping[id_shot,
                                                   person_name,
                                                   source]
        robot.updateLayer(id_submission, description=description)
    except Exception:
        logger.debug(
            "layer {layer} no longer exists".format(layer=id_submission))
