from types import FunctionType
from typing import Dict
from time import sleep
from collections import deque
from threading import Lock

import selectors
import socket

from .sslsocket import SSLSocket

class SSLServer:
    def __log(self, str) -> None:
        print(f"Server: {str}", flush=True)

    def __new_connection(self, socket: socket.socket, _) -> None:
        try:
            sock, (addr, _) = socket.accept()

            self.__log(f"new connection {sock.getsockname()} <- {sock.getpeername()}")
        except:
            return

        try:
            msg = sock.recv(SSLSocket.MSG_SIZE)

            if not msg: raise

            msg = msg.decode()
        except:
            return sock.close()

        sock.setblocking(False)

        self.__sel.register(
            sock,
            selectors.EVENT_READ | selectors.EVENT_WRITE,
            lambda s, m: self.__handle_client(s, m)
        )

        self.__socks += [sock]
        self.__msg_queues[sock] = deque()

        self.__log(f"total number of connections: {len(self.__socks)}")

        if self.__msg_cb:
            self.__msg_cb(sock, msg, addr)

    def __handle_client(self, socket: socket.socket, mask) -> None:
        if mask & selectors.EVENT_READ:
            self.__new_message(socket)

        if mask & selectors.EVENT_WRITE:
            self.__available_to_send(socket)

    def send_message(self, socket: socket.socket, msg: str) -> None:
        self.__msg_queues[socket].append(msg)

    def broadcast(self, msg: str) -> None:
        for key in self.__msg_queues:
            self.__msg_queues[key].append(msg)

    def disconnect_all(self) -> None:
        while len(self.__socks) != 0:
            self.disconnect(self.__socks[0], True)

    def disconnect(self, socket: socket.socket, try_disc: bool = False) -> None:
        self.__log(f"disconnecting socket {socket}")

        try:
            self.__sel.unregister(socket)
            socket.close()

            self.__socks.remove(socket)
            self.__msg_queues.pop(socket)
        except Exception as error:
            if not try_disc: raise error

    def __new_message(self, socket: socket.socket) -> None:
        try:
            msg = socket.recv(SSLSocket.MSG_SIZE)
            if not msg: raise

            self.__log(f"new message {socket.getsockname()} <- {socket.getpeername()}")

            if self.__msg_cb:
                self.__msg_cb(socket, msg.decode())
        except:
            return self.disconnect(socket)

    def __available_to_send(self, socket: socket.socket) -> None:
        try:
            q = self.__msg_queues[socket]
        except:
            return self.disconnect(socket, True)

        try:
            try:
                msg: str = q.popleft()
            except:
                return

            self.__log((
                f"sending message "
                f"{socket.getsockname()} -> {socket.getpeername()}"
            ))

            socket.sendall(msg.encode())
        except:
            return self.disconnect(socket)

    def __init__(self, ssl_sock: SSLSocket):
        self.__server_sock = ssl_sock.socket()

        self.__sel = selectors.DefaultSelector()
        self.__socks = []
        self.__msg_queues: Dict[object, deque] = {}

        self.__sel.register(
            self.__server_sock,
            selectors.EVENT_READ,
            lambda s, m: self.__new_connection(s, m)
        )

        self.__running = False

        self.__lock = Lock()

        self.__msg_cb: None | FunctionType = None
        self.__loop_cb: None | FunctionType = None

    def set_msg_cb(self, func: FunctionType) -> None:
        self.__msg_cb = func

    def set_loop_cb(self, func: FunctionType) -> None:
        self.__loop_cb = func

    def stop(self) -> None:
        with self.__lock:
            self.__running = False

    def start(self) -> None:
        with self.__lock:
            self.__running = True

        try:
            while True:
                events = self.__sel.select(1.0)

                for key, mask in events:
                    key.data(key.fileobj, mask)

                with self.__lock:
                    if not self.__running:
                        break

                sleep(1.0)

                if self.__loop_cb:
                    self.__loop_cb()
        except Exception as err:
            self.__log(err)

        for sock in self.__socks:
            self.disconnect(sock)

        self.__sel.unregister(self.__server_sock)
        self.__server_sock.close()

        self.__sel.close()
