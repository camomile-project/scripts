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
MediaEval account creator

Expects a CSV file with the following format

team_TEAMNAME,firstname.lastname,password,email@email.com

Usage:
  new_accounts <accounts.csv> [options]

Options:
  -h --help                Show this screen.
  --version                Show version.
  --debug                  Show debug information.
  --url=URL                Submission server URL
                           [default: http://api.mediaeval.niderb.fr]
  --admin=LOGIN            Administrator login
  --password=P45sw0Rd      Password
"""

from common import RobotCamomile
from docopt import docopt

arguments = docopt(__doc__, version='0.1')

accounts_csv = arguments['<accounts.csv>']
url = arguments['--url']
admin = arguments['--admin']
password = arguments['--password']
debug = arguments['--debug']

if admin is None:
    admin = raw_input("Administrator login: ")

client = RobotCamomile(
    url, admin, password=password)

annotator = client.getGroupByName('annotator')
participant = client.getGroupByName('participant')

with open(accounts_csv, 'r') as f:
    for account in f:

        teamName, login, password, email = account.strip().split(',')

        # find or create team group
        try:
            team = client.getGroupByName(teamName)
        except:
            print 'Creating {team}'.format(team=teamName)
            team = client.createGroup(team, returns_id=True)

        # create user
        try:
            user = client.getUserByName(login)
        except:
            print 'Creating user {login}'.format(login=login)
            user = client.createUser(
                login, password, role='user',
                description={'email': email},
                returns_id=True)

        # adding user to their team
        client.addUserToGroup(user, team)

        # adding user as participant
        client.addUserToGroup(user, participant)

        # adding user as annotator
        client.addUserToGroup(user, annotator)

        print ('Adding user {login} to {team}, '
               'annotator and participant').format(
            login=login, team=teamName)
