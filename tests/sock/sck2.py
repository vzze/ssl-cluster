from cluster.sslsocket import SSLSocket, SSLSocketType

sock = SSLSocket(SSLSocketType.ElectionCandidate).socket()
sock.close()
