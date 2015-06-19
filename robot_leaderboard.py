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
  robot_submission <videosList> <teamList> [options]

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

def computeAveragePrecision(vReturned, vRelevant):

    nReturned = len(vReturned)
    nRelevant = len(vRelevant)

    if nRelevant == 0 and nReturned == 0:
        return 1.

    if nRelevant == 0 and nReturned > 0:
        return 0.

    if nReturned == 0 and nRelevant > 0:
        return 0.

    returnedIsRelevant = np.array([item in vRelevant for item in vReturned])
    precision = np.cumsum(returnedIsRelevant) / (1. + np.arange(nReturned))
    return np.sum(precision * returnedIsRelevant) / min(nReturned, nRelevant)



arguments = docopt(__doc__, version='0.1')

url = arguments['--url']
password = arguments['--password']
period = int(arguments['--period'])
debug = arguments['--debug']
log = arguments['--log']
threshold = float(arguments['--levenshtein'])

logger = create_logger('robot_leaderboard', path=log, debug=debug)
robot = RobotCamomile(url, 'robot_leaderboard', password=password, period=period, logger=logger)

# corpus id
test = robot.getCorpusByName('mediaeval.test')

# layer containing complete annotations for label grondtruth
labelAggregatedGroudtruthLayer = robot.getLayerByName(test, 'mediaeval.groundtruth.label.aggregated')
# unique layer containing manual annotations
evidenceGroundtruthLayer = robot.getLayerByName(test, 'mediaeval.groundtruth.evidence.all')

# list of team
teamList = [team for team in open(arguments['<teamList>']).read().splitlines()]

# list of video to be evaluated
videos = [video for video in open(arguments['<videosList>']).read().splitlines()]
mediaIds = set([media['_id'] for media in robot.getMedia(test) if media['name'] in videos])

# team name to id_layer_leaderboard
id_LayerLeaderboardTeam = {l.description.team : l._id for l in robot.getLayers(test) if  l.data_type = "leaderboard"}

while True :
    # update groundtruth

    # list of queries for the evaluation
    queries = set([a.data.corrected_person_name for a in robot.getAnnotations(layer = evidenceGroundtruthLayer) if '_' in a.data.corrected_person_name])

    # get list of id_layer hypothesis per team
    submissionTeam = {team:[] for team in teamList}
    for l in robot.getLayers(test, data_type = 'mediaeval.persondiscovery.label'):
        submissionTeam[l.description.team].append(l._id)

    # update groundtruth
    relevant = {query:set([]) for query in queries }
    for a in robot.getAnnotations(layer = labelAggregatedGroudtruthLayer): 
        for query, status in a.aggregated.items():
            if status == "speakingFace":
                relevant[query].add(a.fragment)

    # Compute MAP
    rankPrimary = []
    rankConstrastiveTeam = {}
    for team in teamList:
        # for each layer hypothesis of the current team
        rankConstrastiveTeam[team] = []
        for submissionLayer in submissionTeam[team]:

            returned = {query:set([]) for query in queries}
            for a in robot.getAnnotations(layer = submissionLayer, data): 
                ratio, personName = max([[ratio(query, a.data), query], for query in queries])
                if ratio > threshold:
                    returned[personName].add(a.fragment)

            averagePrecision = {query :computeAveragePrecision(returned[query], relevant[query]) for query in queries}
            MAP = np.mean([averagePrecision[query] for query in queries])
            if submissionLayer.name == 'primary':
                rankPrimary.append([MAP, team, submissionLayer.name])
            else:
                rankConstrastiveteam[team].append([MAP, team, submissionLayer.name])

    # update layerTeam
    for team in teamList:
        description = []
        for s, t, n in sorted(rankPrimary + rankConstrastiveteam[team], reverse = True)
            item {"rank":len(description)+1, "score":'?', "run":'?'}
            if t == team:
                item['score'] = s
                item['run'] = n
            description.append(item)
        robot.updateLayer(id_LayerLeaderboardTeam[team], description=description)

    sleep(period)


