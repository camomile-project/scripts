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
import unicodedata

arguments = docopt(__doc__, version='0.1')

list_c="abcdefghijklmnopqrstuvwxyz_" 

def normalize(p):
    p = unicodedata.normalize('NFD',p)
    p = p.encode('ascii','ignore')      
    p = p.lower()

    for i in range(len(p)):
        if p[i] not in list_c:
            p[i] == '_'

    while '__' in p:
        p = p.replace('__', '_')

    if p[0] == '_':
        p = p[1:]

    if p[-1] == '_':
        p = p[:-1]

    return p


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

media = {medium._id: medium.name for medium in client.getMedia(test)}

shotLayer = client.getLayers(test, name='mediaeval.submission_shot')[0]._id

print "get the shot number"
shots = {}
for a in client.getAnnotations(shotLayer):
    shots.setdefault(a.id_medium, {})
    shots[a.id_medium][a._id] = a.fragment.shot_number

# evaluate every original submissions
for labelLayer in client.getLayers(
        test, data_type='mediaeval.persondiscovery.label'):

    # we are only looking for original submissions (not copies)
    if 'copy' in labelLayer.description:
        continue

    if labelLayer.description.get('status', 'incomplete') != 'complete':
        continue

    print teams[labelLayer.description.id_team], labelLayer.name

    annotations = []
    try :
      annotations = client.getAnnotations(labelLayer._id)
    except Exception:
        print 'medium per medium'
        annotations = []
        for id_medium in media:
            for a in client.getAnnotations(labelLayer._id, medium=id_medium):
                annotations.append(a)


    fout = open(output_path+'/'+teams[labelLayer.description.id_team]+'.'+labelLayer.name+'.label' , 'w')
    for a in annotations:
        p = normalize(a.data.person_name)
        fout.write(media[a.id_medium]+' '+str(shots[a.id_medium][a.fragment])+' '+p+' '+str(a.data.confidence)+'\n')
    fout.close()

    annotations = []
    try :
        annotations = client.getAnnotations(labelLayer.description.id_evidence)
    except Exception:
        print 'medium per medium'
        for id_medium in media:
            for a in client.getAnnotations(labelLayer.description.id_evidence, medium=id_medium):
                annotations.append(a)

    fout = open(output_path+'/'+teams[labelLayer.description.id_team]+'.'+labelLayer.name+'.evidence' , 'w')
    for a in annotations:
        p = normalize(a.data.person_name)
        fout.write(p+" "+media[a.id_medium]+' '+str(shots[a.id_medium][a.fragment])+' '+a.data.source+'\n')
    fout.close()


