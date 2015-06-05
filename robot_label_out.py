

import sys
from camomile import Camomile

server = sys.argv[1]
login = sys.argv[2]
pwd = sys.argv[3]

client = Camomile(server)
client.login(login, pwd)



# Robot label out

# Pour tous les éléments dans Q.label.out :
# - Si il y a un inconnu dans le shot -> ajoute un élément dans Q.label.unknown
# - Sinon si il y a assez d'annotation et un consensus pour ce shot dans L.label.GT.complete ajouter l'annotation dans L.label.GT.agregated et ajouter/compléter l'annotation dans L.label.GT.complete