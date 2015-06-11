# The MIT License (MIT)

# Copyright (c) 2014-2015 CNRS

# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import ConfigParser
from camomile import Camomile
import sys

if __name__ == '__main__':
    # read config
    Config = ConfigParser.ConfigParser()
    Config.read("config.ini")

    server = Config.get('mainSection', 'url')+":"+Config.get('mainSection', 'port')
    userAdmin = Config.get('userSection', 'userAdmin')
    pwdAdmin = Config.get('userSection', 'pwdAdmin')
    corpusName = Config.get('ressourceSection', 'corpusName')
    shotLayerName = Config.get('ressourceSection', 'shotLayerName')
    shotList = Config.get('ressourceSection', 'shotList')

    client = Camomile(server)
    client.login(userAdmin, pwdAdmin)

    id_corpus = client.getCorpora(name=corpusName, returns_id=True)
    if id_corpus == []:
        print args['<corpusName>'], 'is not found in the database'
        sys.exit(0)
    id_corpus = id_corpus[0]

    # create layer
    id_layer = client.createLayer(id_corpus, 
                                  shotLayerName,
                                  description={"source": "https://raw.githubusercontent.com/MediaevalPersonDiscoveryTask/metadata/master/dev/submission_shot/test2.shot"},
                                  fragment_type='mediaeval.persondiscovery.shot',
                                  data_type='empty', 
                                  returns_id=True)

    # get id_media
    id_media = {}
    for media in client.getMedia(corpus=id_corpus):
        id_media[media['name']] = media['_id']

    # parse shot segmentation
    shots = {}
    for line in open(shotList).read().splitlines():
        videoID, shotID, startTime, endTime, startFrame, endFrame = line.split(' ')
        shot = {"id_layer": id_layer,
                "id_medium": id_media[videoID],
                "fragment": {"shot_number": shotID,
                             "segment": {"start": startTime, "end": endTime},
                             "frames": {"start": startFrame, "end": endFrame} 
                            },
                "data" : {}
               }
        shots.setdefault(videoID, []).append(shot)

    # create annotations
    for videoID in shots:
        client.createAnnotations(id_layer, shots[videoID])

