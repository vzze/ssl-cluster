# example file that works with cluster.service

if __name__ == "__main__":
    import sys
    sys.path.append("../cluster")

from cluster.cluster import Cluster

from argparse import ArgumentParser

parser = ArgumentParser()

parser.add_argument("ip", type=str, help="Machine IP")
parser.add_argument("--peers", type=str, nargs='*', help="Peer addresses", required=False)

args = parser.parse_args()

args.peers = [args.ip] if not args.peers else args.peers + [args.ip]

cluster = Cluster(args.peers, args.ip)

cluster.start()
