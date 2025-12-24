from cluster.sslsocket import SSLSocket, SSLSocketType

try:
    sock = SSLSocket(SSLSocketType.Client)
except:
    print("success")
