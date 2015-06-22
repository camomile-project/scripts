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
MediaEval label out robot

Usage:
  robot_label_out [options]

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
from pandas import DataFrame

arguments = docopt(__doc__, version='0.1')

url = arguments['--url']
password = arguments['--password']
period = int(arguments['--period'])

debug = arguments['--debug']
log = arguments['--log']
logger = create_logger('robot_label_out', path=log, debug=debug)
robot = RobotCamomile(
    url, 'robot_label', password=password,
    period=period, logger=logger)

# corpus id
test = robot.getCorpusByName('mediaeval.test')

# layer containing consensus annotations
consensusLayer = robot.getLayerByName(
    test, 'mediaeval.groundtruth.label.consensus')

# layer containing shots with at least one annotated unknown
unknownLayer = robot.getLayerByName(
    test, 'mediaeval.groundtruth.label.unknown')

# layer containing complete annotations for label grondtruth
allLayer = robot.getLayerByName(
    test, 'mediaeval.groundtruth.label.all')

# id of the in coming queue
labelOutQueue = robot.getQueueByName(
    'mediaeval.label.out')

for item in robot.dequeue_loop(labelOutQueue):

    # save raw annotation

    shot = item.input.id_shot
    medium = item.input.id_medium
    known = item.output.known
    unknown = item.output.unknown
    annotator = item.log.user

    robot.createAnnotation(
        allLayer,
        medium=medium, fragment=shot,
        data={"known": known,
              "unknown": unknown,
              "annotator": annotator})

    # check new consensus for this shot

    annotations = robot.getAnnotations(layer=allLayer, fragment=shot)

    # start by gathering all person names
    personNames = set([])
    for annotation in annotations:
        personNames.update(annotation.data.known)

    # create an annotator x personName table
    df = DataFrame(columns=personNames.union(set(['?'])))

    # fill this table...
    for a, annotation in enumerate(annotations):

        # get annotator login
        annotator = annotation.data.annotator

        # store whether annotator found an unknown speaking face
        unknown = annotation.data.unknown
        df.at[annotator, '?'] = 'speakingFace' if unknown else 'noFace'

        # store known annotation
        known = annotation.data.known
        for personName in personNames:
            # if the annotator annotated this personName
            # then we use his/her decision.
            # if s/he did not annotate this personName
            #  - we choose 'dontKnow' if s/he marked someone as unknown
            #  - we choose 'noFace' if s/he did not mark anyone as unknown
            status = known.get(personName,
                               'dontKnow' if unknown else 'noFace')
            df.at[annotator, personName] = status

    if df['?'].value_counts().get('speakingFace', 0) > 0:
        robot.createAnnotation(unknownLayer,
                               medium=medium, fragment=shot,
                               data=None, returns_id=True)
        logger.info('found unknown in shot {shot}'.format(shot=shot))
        continue

    # no consensus until we have at least 2 annotators
    nAnnotators = len(df)
    if nAnnotators < 2:
        logger.debug(
            "no consensus for shot {shot} - "
            "only {n} annotators".format(
                shot=shot, n=nAnnotators))
        continue

    for personName in personNames:

        counts = df[personName].value_counts()

        # no consensus if the count of expressed status
        # (ie not 'dontKnow') is smaller than 2
        expressedCounts = sum(count for status, count in counts.iteritems()
                              if status != 'dontKnow')
        if expressedCounts < 2:
            consensus = {}
            logger.debug(
                "no consensus for shot {s} - "
                "only {n} expressed annotation(s) for {p} ".format(
                    s=shot, n=expressedCounts, p=personName))
            break

        # no consensus if the most frequent is 'dontKnow'
        status = counts.argmax()
        if status == 'dontKnow':
            consensus = {}
            logger.debug(
                "no consensus for shot {s} - "
                "most frequent state for {p} is 'dontKnow'".format(
                    s=shot, p=personName))
            break

        # no consensus if the highest frequency is < 2
        count = counts.max()
        if count < 2:
            consensus = {}
            logger.debug(
                "no consensus for shot {s} - "
                "most frequent state for {p} only has {n} votes".format(
                    s=shot, p=personName, n=count))
            break

        # consensus if the most frequent is
        # strictly more frequent than 50%
        ratio = count / float(expressedCounts)
        if ratio > 0.5:
            consensus[personName] = status
        else:
            consensus = {}
            logger.debug(
                "no consensus for shot {s} - "
                "most frequent state for {p} does not have majority (r:d)only has {n} votes".format(
                    s=shot, p=personName, n=count))
            break


    # found consensus
    if consensus:
        robot.createAnnotation(
            consensusLayer,
            medium=medium, fragment=shot,
            data=consensus, returns_id=True)
        logger.info("found consensus for shot {s}".format(s=shot))
