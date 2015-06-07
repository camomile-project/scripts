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


from camomile import Camomile
from getpass import getpass
import time


class RobotCamomile(Camomile):

    def __init__(self, url, login, password=None,
                 dryrun=False, period=3600):
        super(RobotCamomile, self).__init__(url)
        self.dryrun = dryrun
        self.period = period
        if password is None:
            password = getpass()
        self.login(login, password)

    def getUserByName(self, name):

        matchingUsers = [user._id for user in self.getUsers()
                         if user.username == name]

        if len(matchingUsers) == 1:
            return matchingUsers[0]

        else:
            msg = 'Could not find any user with name "%s".'
            raise ValueError(msg % name)

    def getQueueByName(self, name):

        matchingQueues = [queue._id for queue in self.getQueues()
                          if queue.name == name]

        if len(matchingQueues) == 1:
            return matchingQueues[0]

        if len(matchingQueues) < 1:
            msg = 'Could not find any queue with name "%s".'
            raise ValueError(msg % name)

        msg = 'Found too many (%d) queues with name "%s".'
        raise ValueError(msg % (len(matchingQueues, name)))

    def getLayerByName(self, name):

        matchingLayers = [layer._id for layer in self.getLayers()
                          if layer.name == name]

        if len(matchingLayers) == 1:
            return matchingLayers[0]

        if len(matchingLayers) < 1:
            msg = 'Could not find any layer with name "%s".'
            raise ValueError(msg % name)

        msg = 'Found too many (%d) layers with name "%s".'
        raise ValueError(msg % (len(matchingLayers, name)))

    def dequeue_loop(self, queue):

        # do not 'pop' nor 'loop' in dry-run mode
        if self.dryrun:
            for item in self.getQueue(queue).list:
                yield item
            return

        while True:
            try:
                item = self.dequeue(queue)
                yield item
            except Exception:
                time.sleep(self.period)

    def duplicate_layer(self, layer, returns_id=False):

        # get original layer and its fields
        original = self.getLayer(layer)
        corpus = original.id_corpus
        name = original.name + ' [copy]'
        fragment_type = original.fragment_type
        data_type = original.data_type
        description = original.description

        # keep track of original layer
        description.copy = layer

        # create empty copy
        copy = self.createLayer(
            corpus, name, description=description,
            fragment_type=fragment_type, data_type=data_type,
            returns_id=True)

        # copy annotations medium by medium
        media = self.getMedia(corpus, returns_id=True)
        for medium in media:
            annotations = self.getAnnotations(
                layer=layer, medium=medium)
            self.createAnnotations(copy, annotations, returns_id=True)

        if returns_id:
            return copy

        return self.getLayer(copy)