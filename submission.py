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
    user1 = Config.get('userSection', 'user1')
    pwdUser1 = Config.get('userSection', 'pwdUser1')
    corpusName = Config.get('ressourceSection', 'corpusName')
    shotLayerName = Config.get('ressourceSection', 'shotLayerName')    
    submissionName = Config.get('ressourceSection', 'submissionName')
    labelFile = Config.get('ressourceSection', 'label')
    evidenceFile = Config.get('ressourceSection', 'evidence')

    client = Camomile(server)
    client.login(user1, pwdUser1)
    
    # find id corpus and id layer
    id_corpus = client.getCorpora(corpusName, returns_id=True)
    if id_corpus == []:
        print args['<corpusName>'], 'is not found in the database'
        sys.exit(0)
    id_corpus = id_corpus[0]

    id_layer = client.getLayers(corpus=id_corpus, name=shotLayerName, returns_id=True)
    if id_layer == []:
        print shotLayerName, 'is not found in the database'
        sys.exit(0)
    id_layer = id_layer[0]

    
    # create layer
    id_layer_label = client.createLayer(id_corpus, 
                                        submissionName+".label",
                                        description={"id_label": "", "submission": "primary", "status": "workInProgress"},
                                        fragment_type='mediaeval.persondiscovery._id_shot',
                                        data_type='mediaeval.persondiscovery.evidence',
                                        returns_id=True)

    id_layer_evidence = client.createLayer(id_corpus, 
                                           submissionName+".evidence",
                                           description={"id_evidence": "", "submission": "primary", "status": "workInProgress"},
                                           fragment_type='mediaeval.persondiscovery._id_shot',
                                           data_type='mediaeval.persondiscovery.evidence',
                                           returns_id=True)

    # find id of the shot annotations
    id_shots = {}
    for shot in client.getAnnotations(layer=id_layer):
        id_shots.setdefault(shot['id_medium'], {})
        id_shots[shot['id_medium']][shot['fragment']['shot_number']] = shot['_id']

    # find id of the media
    id_media = {}
    for media in client.getMedia(corpus=id_corpus):
        id_media[media['name']] = media['_id']
    
    # parse label
    labels = {}
    for line in open(labelFile).read().splitlines():
        videoID, shotNumber, personName, confidence = line.split(' ')
        label = {"id_layer": id_layer_label,
                 "id_medium": id_media[videoID],
                 "fragment": id_shots[id_media[videoID]][shotNumber],
                 "data" : {"person_name": personName, "confidence": confidence}
                }
        labels.setdefault(videoID, []).append(label)

    # parse evidence
    evidences = {}
    for line in open(evidenceFile).read().splitlines():
        personName, videoID, shotNumber, source = line.split(' ')
        evidence = {"id_layer": id_layer_evidence,
                    "id_medium": id_media[videoID],
                    "fragment": id_shots[id_media[videoID]][shotNumber],
                    "data" : {"person_name": personName, "source": source}
                }
        evidences.setdefault(videoID, []).append(evidence)

    # add labels
    for videoID in labels:
        client.createAnnotations(id_layer_label, labels[videoID])
    for videoID in evidences:
        client.createAnnotations(id_layer_evidence, evidences[videoID])

    # update layer status and cross id
    client.updateLayer(id_layer_label, description={"id_evidence": id_layer_evidence, "submission": "primary", "status": "complete"})
    client.updateLayer(id_layer_evidence, description={"id_label": id_layer_label, "submission": "primary", "status": "complete"})
    