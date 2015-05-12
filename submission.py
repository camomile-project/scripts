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
  submission.py <server> <port> <user> <password> <MESegFile> <submissionName>
  submission.py -h | --help
"""

from docopt import docopt
from camomile import Camomile

if __name__ == '__main__':
    # read args
    args = docopt(__doc__)

    client = Camomile(args['<server>'])+":"+args['<port>']))
    client.login(args['<user>']), args['<password>']))

    # create layer
    id_layer = client.createLayer(
        corpus, args['<submissionName>']),
        fragment_type='segment',
        data_type='label+confidence',
        returns_id=True)

    # parse MESeg
    annotations = {}
    idMedias = {}
    for line in open(args['<MESegFile>']).read().splitlines():
        videoID, startTime, endTime, startFrame, endFrame, trackID, label, conf = line.split(' ')
        if videoID not in idMedias:
            idMedias[videoID] = client.getMedia(corpus=corpus, name=videoID)
        anno = {'fragment': {'start': startTime, 'end': endTime},
                'data': {"PersonName":label, "confidence":conf},
                'id_medium': idMedias[videoID],
               }
        annotations.setdefault(videoID, []).append(anno)

    # create annotations
    for videoID in annotations:
        client.createAnnotations(id_layer, annotations[videoID])

