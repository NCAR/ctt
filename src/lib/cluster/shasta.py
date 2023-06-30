from .base import Cluster
from ClusterShell.NodeSet import NodeSet


# siblings are different for different node types
# {de,gu}c -> 4 nodes per blade
# {de,gu}g -> 2 nodes per blade
class Shasta(Cluster):
    def siblings(node):
        raise NotImplementedError

class Gust(Shasta):
    def all_nodes(self):
        return NodeSet('gu[0001-0010]')

class Derecho(Shasta):
    pass
