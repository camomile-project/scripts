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
  --password=P45sw0Rd      Password.
  --period=N               Query queue every N seconds [default: 600].
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
logger = create_logger('robot_submission', path=log, debug=debug)

robot = RobotCamomile(
    url, 'robot_submission', password=password,
    period=period, logger=logger)

submissionQueue = robot.getQueueByName('mediaeval.submission.in')
testCorpus = robot.getCorpusByName('mediaeval.test')
robot_evidence = robot.getUserByName('robot_evidence')
robot_label = robot.getUserByName('robot_label')

# forever loop on submission queue
for item in robot.dequeue_loop(submissionQueue):

    id_evidence = item.id_evidence
    id_label = item.id_label

    # withdrawn submission
    if hasattr(item, 'deletedBy'):
        logger.info(
            "del - {team:s}.{user:s} - {evidence:s}.{label:s}".format(
                team=item.team, user=item.user,
                evidence=id_evidence, label=id_label))

        # look for the (label|evidence) copy of this submission
        # and mark them as deleted
        for labelLayer in robot.getLayers(
                testCorpus, data_type="mediaeval.persondiscovery.label"):

            # if this is not a copy or not the copy we are looking for, skip
            description = labelLayer.description
            if description.get('copy', None) != id_label:
                continue

            # if we reached this point, it means that we found the copy

            # mark label layer copy as deleted
            description['deleted'] = item
            del description['copy']
            robot.updateLayer(labelLayer._id, description=description)

            # mark evidence layer copy as deleted
            evidenceLayer = robot.getLayer(description.id_evidence)
            description = evidenceLayer.description
            description['deleted'] = item
            del description['copy']
            robot.updateLayer(evidenceLayer._id, description=description)

            # no need to keep looking for the copy of the submission
            break

        # back to the top of the loop
        continue

    logger.info(
        "new - {team:s}.{user:s} - {name:s} - {evidence:s}.{label:s}".format(
            team=item.team, user=item.user, name=item.name,
            evidence=id_evidence, label=id_label))

    # duplicate evidence layer
    try:
        # in a try/except scope because it might have been deleted by now
        evidence = robot.duplicate_layer(id_evidence, returns_id=False)
    except Exception:
        logger.error(
            "error when create the copy of {evidence:s} ".format(
                evidence=id_evidence))        
        continue

    # duplicate label layer
    try:
        # in a try/except scope because it might have been deleted by now
        label = robot.duplicate_layer(id_label, returns_id=False)
    except Exception:
        robot.deleteLayer(evidence._id)
        logger.error(
            """error when create the copy of {label:s}, 
               remove the copy of {evidence:s}""".format(
            label=id_label, evidence=id_evidence))        
        continue

    # update evidence --> label cross-reference
    evidence.description.id_label = label._id
    robot.updateLayer(evidence._id, description=evidence.description)

    # update label --> evidence cross-reference
    label.description.id_evidence = evidence._id
    robot.updateLayer(label._id, description=label.description)

    # give ADMIN permission to robot_evidence
    robot.setLayerPermissions(evidence._id, robot.ADMIN, user=robot_evidence)

    # give READ permission to robot_label
    robot.setLayerPermissions(label._id, robot.READ, user=robot_label)

    # give ADMIN permission to robot_evidence
    # (allowing to later update the mapping)
    robot.setLayerPermissions(label._id, robot.ADMIN, user=robot_evidence)
