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
MediaEval extract submissions

Usage:
  extract_submissions <output_path> [options]

Options:
  -h --help             Show this screen.
  --url=URL             Submission server URL
                        [default: http://api.mediaeval.niderb.fr]
  --login=login         login
  --password=P45sw0Rd   Password
"""

from camomile import Camomile
from docopt import docopt
from getpass import getpass

arguments = docopt(__doc__, version='0.1')

url = arguments['--url']
output_path = arguments['<output_path>']
login = arguments['--login']
password = arguments['--password']

if login is None:
    login = raw_input('Login: ')
if password is None:
    password = getpass()

client = Camomile(url)
client.login(login, password)

# test corpus
test = client.getCorpora(name = 'mediaeval.test', returns_id=True)[0]

# teams
teams = {team._id: team.name
         for team in client.getGroups()
         if team.name.startswith('team_') or team.name == 'organizer'}

media = {medium.name: medium._id for medium in client.getMedia(test)}


shotLayer = client.getLayers(test, name='mediaeval.submission_shot')[0]._id

print "get the shot number"
shots = {}
for medium, id_medium in media.items():
    shots[medium] = {}
    for a in client.getAnnotations(shotLayer, medium=id_medium ):
        shots[medium][a._id] = a.fragment.shot_number

# evaluate every original submissions
for labelLayer in client.getLayers(
        test, data_type='mediaeval.persondiscovery.label'):

    # we are only looking for original submissions (not copies)
    if 'copy' in labelLayer.description:
        continue

    if labelLayer.description.get('status', 'incomplete') != 'complete':
        continue

    print teams[labelLayer.description.id_team], labelLayer.name

    fout = open(output_path+'/'+teams[labelLayer.description.id_team]+'.'+labelLayer.name+'.label' , 'w')
    for medium, id_medium in sorted(media.items()):
        for a in client.getAnnotations(labelLayer._id, medium=id_medium):
            fout.write(medium+' '+str(shots[medium][a.fragment])+' '+a.data.person_name+' '+str(a.data.confidence)+'\n')
    fout.close()
    
    fout = open(output_path+'/'+teams[labelLayer.description.id_team]+'.'+labelLayer.name+'.evidence' , 'w')
    for medium, id_medium in sorted(media.items()):
        for a in client.getAnnotations(labelLayer.description.id_evidence, medium=id_medium):
            fout.write(a.data.person_name+" "+medium+' '+str(shots[medium][a.fragment])+' '+a.data.source+'\n')
    fout.close()


