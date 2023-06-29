from .base import Cluster


class Casper(Cluster):
    # casper nodes are not blades -- do not have siblings
    def siblings(node):
        return []
