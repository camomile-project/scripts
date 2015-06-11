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
  --period=N               Query submission queue every N sec [default: 600].
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
logger = create_logger('robot_evidence_in', path=log, debug=debug)

robot = RobotCamomile(
    url, 'robot_evidence', password=password,
    period=period, logger=logger)

# filled by robot_submission
# {evidence: id_evidence, label: id_label}
evidenceSubmissionQueue = robot.getQueueByName(
    'mediaeval.submission.evidence.in')

# filled by this script and popped by evidence annotation front-end
evidenceInQueue = robot.getQueueByName(
    'mediaeval.evidence.in')

# unique layer containing manual annotations
test = robot.getCorpusByName('mediaeval.test')
evidenceGroundtruthLayer = robot.getLayerByName(
    test, 'mediaeval.groundtruth.evidence.all')

# layer containing submission shots
submissionShotLayer = robot.getLayerByName(test, 'mediaeval.submission_shot')

# forever loop on evidence submission queue
for submissionLayers in robot.dequeue_loop(evidenceSubmissionQueue):

    # evidenceSubmissionQueue is filled by submission script
    # {evidence: id_evidence, label: id_label}
    evidenceHypothesisLayer = submissionLayers.evidence
    id_submission = submissionLayers.label

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

    # process evidence layer medium by medium
    for id_medium, evidences in robot.getAnnotations_iter(
            evidenceHypothesisLayer):

        # loop on evidence from one medium
        for evidence in evidences:

            id_shot = evidence.fragment
            person_name = evidence.data.person_name
            source = evidence.data.source

            # if this hypothesized evidence has been checked already
            if (id_shot, person_name, source) in mapping:

                logger.debug(
                    "existing evidence - {name:s} - {source:s}".format(
                        name=person_name, source=source))

                # propagate this evidence to this submission mapping
                # if the submission copy still exists...
                # (it might have been deleted by hands to free some space)
                try:
                    description = robot.getLayer(id_submission).description
                    # (initialize empty mapping if needed)
                    _ = description.setdefault('mapping', {})
                    description.mapping[person_name] = mapping[id_shot,
                                                               person_name,
                                                               source]
                    robot.updateLayer(id_submission, description=description)
                except Exception:
                    pass

            # if this hypothesized evidence has not been checked yet
            # push to evidence annotation frontend
            else:

                item = {}

                item['id_submission'] = id_submission
                item['person_name'] = person_name
                item['source'] = source

                item['id_medium'] = id_medium
                item['id_shot'] = id_shot
                segment = robot.getAnnotation(id_shot).fragment.segment
                item['start'] = segment.start - (5 if source == 'audio'
                                                 else 0)
                item['end'] = segment.end + (5 if source == 'audio'
                                             else 0)

                robot.enqueue(evidenceInQueue, item)

                logger.info(
                    "new evidence - {name:s} - {source:s}".format(
                        name=person_name, source=source))
