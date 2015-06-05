
# Robot submission

import sys
from camomile import Camomile

server = sys.argv[1]
login = sys.argv[2]
pwd = sys.argv[3]

client = Camomile(server)
client.login(login, pwd)


# pop queue mediaeval.submission.in
# -> get the id_layer.evidence id_layer.label of the submission


# create 2 new layers with a unique name: 
# id_layer.evidence.copy
# id_layer.label.copy


# copy annotation of id_layer.evidence id_layer.label into id_layer.evidence.copy id_layer.label.copy
# add a field mapping in the description field of the id_layer.label.copy


# Add right "WRITE" for robot_evidence_in and robot_evidence_out on id_layer.label.copy
# Add right "READ" for robot_evidence_in on id_layer.evidence.copy


# Add a new element in Q.sub.evidence



