import requests
# Questo è un esempio di bot per la comunicazione con il backend del sito
# labId: identificativo del laboratorio all'interno del sito, token: token per l'accesso variabile, strumId: numero che identifica lo strumento nel lab, message: testo dell'errore, type: se 0, riguarda la rete, mentre se è 1 riguarda uno strumento.
r = requests.post("https://192.168.2.36/recv_bot", data={'labId': 1, 'token': 'ZENH0C', 'strumId': 0, 'event': 'Test error', 'eventId':1}, verify=False)
print(r.text)