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
  robot_submission <videos.lst> [options]

Options:
  -h --help                  Show this screen.
  --version                  Show version.
  --debug                    Show debug information.
  --url=URL                  Submission server URL
                             [default: http://api.mediaeval.niderb.fr]
  --password=P45sw0Rd        Password
  --period=N                 Query evidence queue every N sec [default: 6000].
  --log=DIR                  Path to log directory.
  --levenshtein=<threshold>  Levenshtein ratio threshold [default: 0.95]
"""

from common import RobotCamomile, create_logger
from docopt import docopt
from time import sleep
from Levenshtein import ratio
from datetime import datetime
import numpy as np


def computeAveragePrecision(returned, relevant):

    nReturned = len(returned)
    nRelevant = len(relevant)

    if nRelevant == 0 and nReturned == 0:
        return 1.

    if nRelevant == 0 and nReturned > 0:
        return 0.

    if nReturned == 0 and nRelevant > 0:
        return 0.

    returnedIsRelevant = np.array([item in relevant for item in returned])
    precision = np.cumsum(returnedIsRelevant) / (1. + np.arange(nReturned))
    ap = np.sum(precision * returnedIsRelevant) / min(nReturned, nRelevant)
    return ap


def computeMeanAveragePrecision(robot, layer, media, shots, qRelevant):

    # load submission
    qReturned = []
    for medium in media:
        for annotation in robot.getAnnotations(layer=layer, medium=medium):
            shot = annotation.fragment
            if shot not in shots:
                continue
            personName = annotation.data.person_name
            confidence = annotation.data.confidence
            qReturned.append((shot, personName, confidence))

    # sort submitted shot in decreasing confidence order
    qReturned = sorted(qReturned, key=lambda s: s[2], reverse=True)

    # per query average precision
    qAveragePrecision = {}
    for query, relevant in qRelevant.iteritems():
        # filter shots by Levenshtein distance to query
        returned = [s for s, p, _ in qReturned if ratio(query, p) >= 0.95]
        # average precision for this query
        qAveragePrecision[query] = computeAveragePrecision(returned, relevant)

    # mean average precision
    mAP = np.mean(qAveragePrecision.values())
    return mAP


arguments = docopt(__doc__, version='0.1')

url = arguments['--url']
password = arguments['--password']
period = int(arguments['--period'])
debug = arguments['--debug']
log = arguments['--log']
threshold = float(arguments['--levenshtein'])
videos = arguments['<videos.lst>']

logger = create_logger('robot_leaderboard', path=log, debug=debug)
robot = RobotCamomile(
    url, 'robot_leaderboard', password=password, period=period, logger=logger)

# test corpus
test = robot.getCorpusByName('mediaeval.test')

# consensus layer
refLayer = robot.getLayerByName(
    test, 'mediaeval.groundtruth.label.consensus')

# evidence layer
evirefLayer = robot.getLayerByName(
    test, 'mediaeval.groundtruth.evidence.all')

# teams
teams = {team._id: team.name
         for team in robot.getGroups()
         if team.name.startswith('team_') or team.name == 'organizer'}

# leaderboard subset
media = {medium.name: medium._id for medium in robot.getMedia(test)}
with open(videos, 'r') as f:
    videos = [v.strip() for v in f]
media = [media[v] for v in videos if v in media]

# create one leaderboard layer per team (if it does not exist)
leaderboard = {}
for team, team_name in teams.iteritems():
    name = 'leaderboard ({team})'.format(team=team_name)
    try:
        leaderboard[team] = robot.getLayerByName(test, name)
    except Exception, e:
        leaderboard[team] = robot.createLayer(
            test, name,
            fragment_type='', data_type=None,
            returns_id=True)
        robot.setLayerPermissions(leaderboard[team], robot.READ, group=team)

while True:

    qRelevant = {}
    shots = set([])

    for medium in media:
        for annotation in robot.getAnnotations(refLayer, medium=medium):

            shot = annotation.fragment
            shots.add(shot)

            for personName, status in annotation.get('data', {}).iteritems():

                # we are only looking for speaking-faces
                if status != 'speakingFace':
                    continue

                # we are only looking for complete person names
                if '_' not in personName:
                    continue

                # this shot is relevant for query 'personName'
                qRelevant.setdefault(personName, set([])).add(shot)

    nQueries = len(qRelevant)
    nShots = len(shots)

    meanAveragePrecision = {}

    # evaluate every original submissions
    for layer in robot.getLayers(
            test, data_type='mediaeval.persondiscovery.label'):

        # we are only looking for original submissions (not copies)
        if 'copy' in layer.description:
            continue

        if layer.description.get('status', 'incomplete') != 'complete':
            continue

        # which team ? which submission ?
        teamID = layer.description.id_team
        runName = layer.name

        logger.info(
            "evaluating {teamID}'s {name}".format(
                teamID=teams[teamID], name=runName))

        # evaluate this submission and store MAP value
        mAP = computeMeanAveragePrecision(
            robot, layer._id, media, shots, qRelevant)

        meanAveragePrecision.setdefault(teamID, {})[runName] = mAP

    # rank all submissions based on their MAP
    ranking = set([])
    for teamID, runs in meanAveragePrecision.iteritems():
        teamName = teams[teamID]
        for runName, mAP in runs.iteritems():
            ranking.add((teamID, teamName, runName, mAP))
    ranking = sorted(ranking, reverse=True, key=lambda s: s[3])

    for myTeamID, myTeamName in teams.iteritems():

        primaryRanking = []
        combinedRanking = []
        teamBest = {}

        for otherTeamID, otherTeamName, runName, mAP in ranking:

            mAP = '{mAP:.1f}'.format(mAP=100 * mAP)

            if myTeamName == 'organizer':
                privateRunName = runName
                privateTeamName = otherTeamName
                privateMeanAveragePrecision = mAP
            elif otherTeamName == myTeamName:
                privateRunName = runName
                privateTeamName = myTeamName[5:]
                privateMeanAveragePrecision = mAP
            elif otherTeamName == 'team_baseline':
                privateRunName = 'baseline'
                privateTeamName = 'baseline'
                privateMeanAveragePrecision = mAP
            else:
                privateRunName = '?'
                privateTeamName = '?'
                privateMeanAveragePrecision = '?'

            if runName == 'primary':
                primaryRanking.append((privateTeamName, privateRunName,
                                       privateMeanAveragePrecision))

            if otherTeamName == myTeamName or myTeamName == 'organizer':
                combinedRanking.append((privateTeamName, privateRunName,
                                       privateMeanAveragePrecision))
            else:
                if not teamBest.get(otherTeamID, False):
                    teamBest[otherTeamID] = True
                    combinedRanking.append((privateTeamName, privateRunName,
                                           privateMeanAveragePrecision))

        description = {}
        description['date'] = datetime.now().strftime("%Y-%m-%d at %H:%M")
        description['ranking'] = {}
        description['ranking']['primary'] = primaryRanking
        description['ranking']['combined'] = combinedRanking
        description['queries'] = nQueries
        description['shots'] = nShots

        robot.updateLayer(leaderboard[myTeamID], description=description)

    logger.info("waiting for {period}s".format(period=period))
    sleep(period)
