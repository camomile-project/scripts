

import sys
from camomile import Camomile

server = sys.argv[1]
login = sys.argv[2]
pwd = sys.argv[3]

client = Camomile(server)
client.login(login, pwd)





# Robot evidence in

# - Pour tous les éléments dans Q.sub.evidence et pour toutes les annotations de L.evidence.hyp.copy correspondant : 
#     * Si il n'y a déjà une évidence annoté pour ce shot/nom 
#             -> ajoute le mapping dans L.evidence.hyp.copy      
#     * Sinon ajoute un élément à Q.evidence.in
# - Purge la Q.evidence.in des shot/nom déjà annotés