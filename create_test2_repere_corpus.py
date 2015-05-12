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

# === EDIT ====================================================================

SERVER = 'http://localhost:12345'

# admin usernname and password
ADMIN = 'administrator'
ADMIN_PASSWORD = 'password'

# template of path to video files (relative to /media)
URL = 'REPERE/phase2/test/{name}'

# =============================================================================

from camomile import Camomile

client = Camomile(SERVER)

# login as admin
client.login(ADMIN, ADMIN_PASSWORD)

# create new corpus
corpus = client.createCorpus('REPERE_TEST2', returns_id=True)

# add media to corpus and keep track of their IDs
mediaID = {}
with open('media.lst', 'r') as f:
    for medium in f:

        # remove trailing "\n"
        name = medium.strip()

        # create medium
        mediaID[name] = client.createMedium(
            corpus, name, url=URL.format(name=name), returns_id=True)
