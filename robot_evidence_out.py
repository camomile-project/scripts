
import sys
from camomile import Camomile

server = sys.argv[1]
login = sys.argv[2]
pwd = sys.argv[3]

client = Camomile(server)
client.login(login, pwd)





# Robot evidence out

# Pour tous les éléments dans Q.evidence.out :
# - Ajoute une annotation dans L.evidence.GT.all si elle n'existe pas déjà
# - Ajoute le mapping dans L.evidence.hyp.copy
# - Ajoute une image dans L.evidence.GT.mugshot