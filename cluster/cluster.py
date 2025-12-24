from enum import Enum
from time import sleep
from types import FunctionType
from typing import List
from threading import Thread, Lock

from .client import SSLClient
from .server import SSLServer
from .sslsocket import SSLSocket, SSLSocketType

class ClusterType(Enum):
    Master = "master"
    Slave  = "slave"
    Unknown = "unknown"

class Cluster:
    def __init__(
        self,
        peers: List[str],
        my_ip: str,
        port: int = 65432
    ):
        peers.sort()
        self.__peers = peers

        self.__ip = my_ip
        self.__port = port

        self.__lock = Lock()
        self.__type = ClusterType.Unknown

        self.__server = SSLServer(
            SSLSocket(SSLSocketType.Server, self.__ip, self.__port)
        )

        self.__heartbeat_thread = Thread(target=self.__heartbeat_loop)
        self.__heartbeat_thread.start()

        self.__server.set_msg_cb(lambda s, m, a=None: self.__server_msg_cb(s, m, a))
        self.__server.set_loop_cb(lambda: self.__server_loop_cb())

        self.__server_thread = Thread(target=self.__server.start)
        self.__server_thread.start()

        self.__client: SSLClient | None = None
        self.__client_thread: Thread | None = None

        self.__heartbeat: bool = True

        self.__master_msg_cb: None | FunctionType = None
        self.__master_loop_cb: None | FunctionType = None

        self.__slave_msg_cb: None | FunctionType = None

    def __check_server_status(self) -> None:
        if self.__server_thread.is_alive():
            return

        self.set_type(ClusterType.Unknown)

        self.__server = SSLServer(
            SSLSocket(SSLSocketType.Server, self.__ip, self.__port)
        )

        self.__server.set_msg_cb(lambda s, m, a=None: self.__server_msg_cb(s, m, a))
        self.__server.set_loop_cb(lambda: self.__server_loop_cb())

        self.__server_thread = Thread(target=self.__server.start)
        self.__server_thread.start()

    def __server_msg_cb(self, socket, msg: str, addr: str | None) -> None:
        if msg == SSLSocketType.WantElection.value:
            print(f"Cluster({self.__ip}): Received request for election, complying...")
            return self.__server.disconnect_all()

        if msg == SSLSocketType.ElectionCandidate.value:
            return self.__server.disconnect(socket)

        if msg == SSLSocketType.HeartBeat.value:
            print(f"Cluster({self.__ip}): Received heartbeat")

            if addr and self.get_type() == ClusterType.Master and self.__ip < addr:
                print(f"Cluster({self.__ip}): Heartbeat sent by bully, stepping down...")

                self.set_type(ClusterType.Unknown)
                return self.__server.disconnect_all()
            else:
                return self.__server.disconnect(socket)

        if self.get_type() != ClusterType.Master:
            return

        if self.__master_msg_cb:
            self.__master_msg_cb(socket, msg)

    def __heartbeat_loop(self) -> None:
        counter = 0

        while True:
            counter += 1
            sleep(1.0)

            with self.__lock:
                if not self.__heartbeat:
                    return

            if counter < 30:
                continue
            else:
                counter = 0

            if self.get_type() != ClusterType.Master:
                continue

            for peer in self.__peers:
                if peer != self.__ip:
                    try:
                        print(f"Cluster({self.__ip}): Sending heartbeat to peer({peer})")
                        SSLClient(SSLSocket(SSLSocketType.HeartBeat, peer, self.__port)).start()
                    except:
                        print(f"Cluster({self.__ip}): Peer({peer}) not online")

    def __server_loop_cb(self) -> None:
        if self.get_type() != ClusterType.Master:
            return

        if self.__master_loop_cb:
            self.__master_loop_cb()

    def __want_election(self) -> None:
        self.set_type(ClusterType.Unknown)

        print(f"Cluster({self.__ip}): Wants election")

        for peer in self.__peers:
            if peer != self.__ip:
                try:
                    print(f"Cluster({self.__ip}): Notifying peer({peer})")
                    SSLClient(SSLSocket(SSLSocketType.WantElection, peer, self.__port)).start()
                except:
                    print(f"Cluster({self.__ip}): Peer({peer}) not online")

    def __elect(self) -> None:
        established_conn_to_bully = False
        bully = self.__ip

        print(f"Cluster({self.__ip}): Beginning election")

        for peer in self.__peers:
            if peer > self.__ip:
                try:
                    print(f"Cluster({self.__ip}): Checking on candidate({peer})")
                    SSLClient(SSLSocket(SSLSocketType.ElectionCandidate, peer, self.__port)).start()

                    established_conn_to_bully = True
                    bully = peer
                except:
                    print(f"Cluster({self.__ip}): Candidate({peer}) not online")

        if established_conn_to_bully:
            self.set_type(ClusterType.Slave)
            print(f"Cluster({self.__ip}): Became slave to peer({bully})")
        else:
            self.set_type(ClusterType.Master)
            print(f"Cluster({self.__ip}): Became master")

        if self.__client:
            self.__client.stop()

        if self.__client_thread:
            self.__client_thread.join()

        self.__client = SSLClient(SSLSocket(SSLSocketType.Client, bully, self.__port))

        if self.__slave_msg_cb:
            self.__client.set_msg_cb(lambda msg: self.__slave_msg_cb(msg)) # type: ignore (bullshit)

        self.__client_thread = Thread(target=self.__client.start)
        self.__client_thread.start()

    def start(self) -> None:
        try:
            self.__want_election()

            while True:
                sleep(1.0)

                self.__check_server_status()

                if self.get_type() == ClusterType.Unknown or not self.__client_thread or not self.__client_thread.is_alive():
                    self.__elect()
        except:
            print(f"Cluster({self.__ip}): Cleaning up")

            with self.__lock:
                self.__heartbeat = False

            print(f"Cluster({self.__ip}): Joining heartbeat thread")
            self.__heartbeat_thread.join()

            print(f"Cluster({self.__ip}): Stopping client")

            if self.__client:
                self.__client.stop()

            print(f"Cluster({self.__ip}): Joining client thread")

            if self.__client_thread:
                self.__client_thread.join()

            print(f"Cluster({self.__ip}): Stopping server")
            self.__server.stop()

            print(f"Cluster({self.__ip}): Joining server thread")
            self.__server_thread.join()

            return

    def set_master_msg_cb(self, func: FunctionType) -> None:
        self.__master_msg_cb = func

    # loop is called every 2 seconds if no connections
    # and every second if there is at least one connection
    def set_master_loop_cb(self, func: FunctionType) -> None:
        self.__master_loop_cb = func

    def set_slave_msg_cb(self, func: FunctionType) -> None:
        self.__slave_msg_cb = func

    def master_send_msg(self, socket, msg: str) -> None:
        if not self.__server_thread.is_alive():
            return

        self.__server.send_message(socket, msg)

    def master_broadcast(self, msg: str) -> None:
        if not self.__server_thread.is_alive():
            return

        self.__server.broadcast(msg)

    def slave_send_msg(self, msg: str) -> None:
        if not self.__client:
            return

        if not self.__client_thread:
            return

        if not self.__client_thread.is_alive():
            return

        self.__client.send_msg(msg)

    def get_type(self) -> ClusterType:
        with self.__lock:
            return self.__type

    def set_type(self, new_type: ClusterType) -> None:
        with self.__lock:
            self.__type = new_type
