from .base import Cluster


# siblings are different for different node types
# {de,gu}c -> 4 nodes per blade
# {de,gu}g -> 2 nodes per blade
class Shasta(Cluster):
    def siblings(node):
        raise NotImplementedError

class Gust(Shasta):
    pass

class Derecho(Shasta):
    pass
