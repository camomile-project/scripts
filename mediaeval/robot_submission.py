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
  --dryrun                 Dry-run

"""

from common import RobotCamomile
from docopt import docopt

arguments = docopt(__doc__, version='0.1')
url = arguments['--url']
dryrun = arguments['--dryrun']

robot = RobotCamomile(url, 'robot_submission', dryrun=dryrun)

submissionQueue = robot.getQueueByName('mediaeval.submission.in')
robot_evidence = robot.getUserByName('robot_evidence')
evidenceSubmissionQueue = robot.getQueueByName(
    'mediaeval.submission.evidence.in')

for item in robot.dequeue_loop(submissionQueue):

    # withdrawn submission
    if hasattr(item, 'deletedBy'):
        continue

    # duplicate evidence layer
    id_evidence = item.id_evidence
    evidence = robot.duplicate_layer(id_evidence, returns_id=False)

    # duplicate label layer
    id_label = item.id_label
    label = robot.duplicate_layer(id_label, returns_id=False)

    # update evidence --> label cross-reference
    evidence.description.id_label = label._id
    robot.updateLayer(evidence._id, description=evidence.description)

    # update label --> evidence cross-reference
    # add empty {personName: correctedPersonName} mapping
    label.description.id_evidence = evidence._id
    label.description.mapping = {}
    robot.updateLayer(label._id, description=label.description)

    # give READ permission to robot_evidence
    robot.setLayerPermissions(evidence._id, robot.READ, user=robot_evidence)

    # give ADMIN permission to robot_evidence
    # (allowing to later update the mapping)
    robot.setLayerPermissions(label._id, robot.ADMIN, user=robot_evidence)

    # enqueue evidence layer
    robot.enqueue(evidenceSubmissionQueue, evidence._id)
