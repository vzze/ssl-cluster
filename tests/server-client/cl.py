from cluster.client import SSLClient
from cluster.sslsocket import SSLSocket, SSLSocketType

client = SSLClient(SSLSocket(SSLSocketType.Client))

client.start()
