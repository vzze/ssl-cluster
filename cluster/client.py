from types import FunctionType
from collections import deque
from threading import Lock
from time import sleep

import selectors
import socket
import errno
import ssl

from .sslsocket import SSLSocket

class SSLClient:
    def __handle_events(self, socket: socket.socket, mask) -> None:
        if mask & selectors.EVENT_READ:
            self.__new_msg(socket)

        if mask & selectors.EVENT_WRITE:
            self.__available_for_write(socket)

    def __new_msg(self, socket: socket.socket) -> None:
        try:
            msg = socket.recv(SSLSocket.MSG_SIZE)

            if not msg: return self.stop()

            if self.__msg_cb:
                self.__msg_cb(msg.decode())
        except BlockingIOError as err:
            if err.errno not in (errno.EWOULDBLOCK, errno.EAGAIN):
                return self.stop()
        except ssl.SSLError as err:
            if err.errno != (ssl.SSL_ERROR_WANT_READ):
                return self.stop()
        except Exception as error:
            print(error)
            return self.stop()

    def __available_for_write(self, socket: socket.socket) -> None:
        try:
            try:
                msg: str = self.__msg_queue.popleft()
            except:
                return

            socket.sendall(msg.encode())
        except:
            self.stop()

    def __init__(self, ssl_sock: SSLSocket):
        self.__sock = ssl_sock.socket()
        self.__sel = selectors.DefaultSelector()

        self.__msg_queue = deque()
        self.__listening = False

        self.__sel.register(
            self.__sock,
            selectors.EVENT_READ | selectors.EVENT_WRITE,
            lambda s, m: self.__handle_events(s, m)
        )

        self.__lock = Lock()

        self.__msg_cb: FunctionType | None = None

    def set_msg_cb(self, func: FunctionType) -> None:
        self.__msg_cb = func

    def send_msg(self, msg: str) -> None:
        self.__msg_queue.append(msg)

    def stop(self) -> None:
        with self.__lock:
            self.__listening = False

    def start(self) -> None:
        with self.__lock:
            self.__listening = True

        try:
            while True:
                with self.__lock:
                    if not self.__listening:
                        break

                events = self.__sel.select(1.0)

                for key, mask in events:
                    key.data(key.fileobj, mask)

                sleep(1.0)
        except Exception as err:
            print(err)

        self.__sel.unregister(self.__sock)
        self.__sock.close()

        self.__sel.close()
