from enum import Enum
import socket
import ssl

from .certs import SSLCert

class SSLSocketType(Enum):
    Server = "server"
    Client = "client"
    WantElection = "want_elect"
    ElectionCandidate = "candidate"
    HeartBeat = "heartbeat"

class SSLSocket:
    MSG_SIZE = 2048

    def __create_ssl_context(self, client: SSLCert, server: SSLCert) -> ssl.SSLContext:
        if self.__type == SSLSocketType.Server:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        else:
            client, server = server, client
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

        context.load_cert_chain(certfile=server.certfile(), keyfile=server.keyfile())
        context.load_verify_locations(cafile=client.certfile())

        context.verify_mode = ssl.CERT_REQUIRED
        context.check_hostname = False

        return context

    def __init__(
        self,
        socket_type: SSLSocketType,
        host: str = "",
        port: int = 65432,
        cert_client: SSLCert = SSLCert("certs/client"),
        cert_server: SSLCert = SSLCert("certs/server"),
    ):
        self.__type = socket_type

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.__sock = self.__create_ssl_context(cert_client, cert_server).wrap_socket(
            sock, server_side=(self.__type == SSLSocketType.Server)
        )

        if self.__type == SSLSocketType.Server:
            self.__sock.bind((host, port))
            self.__sock.listen(100)
        else:
            self.__sock.connect((host, port))
            self.__sock.sendall(socket_type.value.encode())

        self.__sock.setblocking(False)

    def socket(self) -> ssl.SSLSocket:
        return self.__sock
