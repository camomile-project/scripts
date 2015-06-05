
import sys
from camomile import Camomile

server = sys.argv[1]
login = sys.argv[2]
pwd = sys.argv[3]

client = Camomile(server)
client.login(login, pwd)





# Robot label in

# Pour tous les shots dans L.shot qui ne sont pas dans L.label.GT.agregated : 
# - Récupérer la liste des personnes hypothèses dans L.label.hyp.copy
# - Trouver les mugshot pour ces personnes dans L.evidence.GT.mugshot
# - Récupérer la liste des mugshots des personnes apparaissant dans la vidéo du shot
# - Trouver quels annotateurs ont déjà annoté ce shot
# - Trouver les annotations déjà effectuées pour ce shot
# - Classer (comment ???) les personnes qui ont un mugshot, pour les autres écrire le nom ???
# - Ajouter un élément dans Q.label.in

# Pour les shots annotés avec un inconnu, vérifier si il y a une nouvelle hypothèse avec un mugshot, si oui ajouté le shot a Q.label.in, sinon le remettre dans Q.label.unknown