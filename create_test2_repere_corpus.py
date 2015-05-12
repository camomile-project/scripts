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
  create_test2_repere_corpus.py <serverURL> <port> <user> <password> <media_path> <media.lst>
  create_test2_repere_corpus.py -h | --help
"""

from docopt import docopt
from camomile import Camomile

if __name__ == '__main__':
    # read args
    args = docopt(__doc__)

    client = Camomile(args['<serverURL>']+":"+args['<port>'])    
    client.login(args['<user>'], args['<password>'])

    # template of path to video files (relative to /media)
    URL = args['<media_path>']

    # create new corpus
    corpus = client.createCorpus('REPERE_TEST2', returns_id=True)

    # add media to corpus
    for medium in open(args['<media.lst>']).read().splitlines():
        client.createMedium(corpus, medium, url=URL+medium)
