
import sys
from camomile import Camomile

server = sys.argv[1]
login = sys.argv[2]
pwd = sys.argv[3]

client = Camomile(server)
client.login(login, pwd)


#Robot leaderboard

# - Lit les annotations dans L.evidence.GT.all et L.label.GT.complete 
# - calcul les scores 
# - mes à jour les layers L.leaderboard.team de chaque participants
