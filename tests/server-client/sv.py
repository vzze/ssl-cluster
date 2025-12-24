from cluster.server import SSLServer
from cluster.sslsocket import SSLSocket, SSLSocketType

server = SSLServer(SSLSocket(SSLSocketType.Server))
server.start()
