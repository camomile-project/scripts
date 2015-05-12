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


"""
Submission script

Usage:
  submission.py <server> <port> <user> <password> <corpusName> <submissionName> <label> <evidence>
  submission.py -h | --help
"""

from docopt import docopt
from camomile import Camomile

if __name__ == '__main__':
    # read args
    args = docopt(__doc__)

    client = Camomile(args['<server>']+":"+args['<port>'])
    client.login(args['<user>'], args['<password>'])

    id_corpus = client.getCorpora(name=args['<corpusName>'], returns_id=True)[0]

    # create layer
    id_layer_label = client.createLayer(id_corpus, 
                                        args['<submissionName>']+".label",
                                        description={"id_label": "", "submission": "primary", "status": "workInProgress"},
                                        fragment_type='mediaeval.persondiscovery._id_shot',
                                        data_type='mediaeval.persondiscovery.evidence',
                                        returns_id=True)

    id_layer_evidence = client.createLayer(id_corpus, 
                                           args['<submissionName>']+".evidence",
                                           description={"id_evidence": "", "submission": "primary", "status": "workInProgress"},
                                           fragment_type='mediaeval.persondiscovery._id_shot',
                                           data_type='mediaeval.persondiscovery.evidence',
                                           returns_id=True)

    id_layer = client.getLayers(corpus=id_corpus, name="submission shot", returns_id=True)[0]

    id_shots = {}
    for shot in client.getAnnotations(layer=id_layer):
        id_shots.setdefault(shot['id_medium'], {})
        id_shots[shot['id_medium']][shot['fragment']['shot_number']] = shot['_id']

    id_media = {}
    for media in client.getMedia(corpus=id_corpus):
        id_media[media['name']] = media['_id']
    
    # parse label
    labels = {}
    for line in open(args['<label>']).read().splitlines():
        videoID, shotNumber, personName, confidence = line.split(' ')
        label = {"id_layer": id_layer_label,
                 "id_medium": id_media[videoID],
                 "fragment": id_shots[id_media[videoID]][shotNumber],
                 "data" : {"person_name": personName, "confidence": confidence}
                }
        labels.setdefault(videoID, []).append(label)

    # parse evidence
    evidences = {}
    for line in open(args['<evidence>']).read().splitlines():
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
    