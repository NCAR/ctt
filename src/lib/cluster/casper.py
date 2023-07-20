from .base import Cluster


class Casper(Cluster):
    # casper nodes are not blades -- do not have siblings
    def siblings(node):
        return []

    # casper doesn't have different logical and physical node names like the main clusters
    def logical_to_physical(self, nodes: str) -> str:
        return nodes

    def physical_to_logical(self, nodes: str) -> str:
        return nodes
