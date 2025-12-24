if __name__ == "__main__":
    import sys
    sys.path.append("../cluster")

from cluster.cluster import Cluster

cluster = Cluster([""], "") # 0.0.0.0

master_sent_something = False

def master(socket, msg: str) -> None:
    global master_sent_something

    print(msg)

    if not master_sent_something:
        cluster.master_send_msg(socket, "hi")
        cluster.master_broadcast("hi2")
        master_sent_something = True

def master_loop() -> None:
    print("loopy")

slave_sent_something = False

def slave(msg: str) -> None:
    global slave_sent_something

    print(msg)

    if not slave_sent_something:
        cluster.slave_send_msg("hello")
        slave_sent_something = True

cluster.set_master_msg_cb(master)
cluster.set_master_loop_cb(master_loop)
cluster.set_slave_msg_cb(slave)

cluster.start()
