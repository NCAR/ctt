from ClusterShell.NodeSet import NodeSet

from .base import Cluster


# siblings are different for different node types
# {de,gu}c -> 4 nodes per blade
# {de,gu}g -> 2 nodes per blade
class Shasta(Cluster):
    pass

class Gust(Shasta):
    def all_nodes(self):
        return NodeSet('gu[0001-0018]')
    def siblings(self, nodes: NodeSet):
        #TODO give nodes in "thing" if nodes is actually a rack/chassis/slot/board
        sibs = NodeSet()
        for node in nodes:
            sibs.update(node)
            num = int(str(node)[2:])
            if num >= 17:
                sibs.update('gu001[7-8]')
            elif num >= 13:
                sibs.update('gu00[13-16')
            elif num >= 9:
                sibs.update('gu00[09-12]')
            elif num >= 5:
                sibs.update('gu000[5-8]')
            elif num >= 1:
                sibs.update('gu000[1-4]')
            else:
                # do something if node doesn't exist
                raise NotImplementedError
        return sibs

class Derecho(Shasta):
    pass
