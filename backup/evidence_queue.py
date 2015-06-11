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
    submissionName = Config.get('ressourceSection', 'submissionName')

    inQueueEvidence = Config.get('ressourceSection', 'inQueueEvidence')
    outQueueEvidence = Config.get('ressourceSection', 'outQueueEvidence')

    client = Camomile(server)
    client.login(userAdmin, pwdAdmin)

    # create queue
    id_queueIn = client.createQueue(inQueueEvidence, returns_id=True)
    id_queueOut = client.createQueue(outQueueEvidence, returns_id=True)

    id_corpus = client.getCorpora(corpusName, returns_id=True)
    if id_corpus == []:
        print args['<corpusName>'], 'is not found in the database'
        sys.exit(0)
    id_corpus = id_corpus[0]

    id_layerEvidence = client.getLayers(corpus=id_corpus, name=submissionName+".evidence", returns_id=True)
    if id_layerEvidence == []:
        print shotLayerName, 'is not found in the database'
        sys.exit(0)
    id_layerEvidence = id_layerEvidence[0]

    # add annotation in inQueue
    le = []
    for media in client.getMedia(corpus=id_corpus):
        for a in client.getAnnotations(layer=id_layerEvidence, medium=media['_id']):
            shot = client.getAnnotation(a['fragment'])
            e = {"fragment":{"id_medium": media['_id'], "start":shot['fragment']['segment']['start'] , "end":shot['fragment']['segment']['end'] },
                 "data":{"person_name": a['data']['person_name'], "source": a['data']['source']},
                 "id_evidence": id_layerEvidence
                }
            le.append(e)
    client.updateQueue(id_queueIn, elements=le)
