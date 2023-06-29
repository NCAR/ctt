import ClusterShell
from scheduler import PBS
from ClusterShell import NodeSet

class Cluster:
    def __init__(self, conf):
        self.scheduler = PBS(conf)

    def _siblings(self, node: str) -> list[str]:
        raise NotImplementedError

    def bad_nodes(self, nodes: str) -> set((str, list[str])):
        """ checks if given nodes are bad
        input: nodeset string (ex: dec[0001-0123])
        output: set(bad node reasons: str, nodeset with that reason: str)
        """
        task = ClusterShell.Task.task_self()
        task.run("[ -f /etc/THIS_IS_A_BAD_NODE.ncar ] && cat /etc/THIS_IS_A_BAD_NODE.ncar;' 2>/dev/null", nodes=nodeset, timeout=30)
        bad_nodes = set()
        for buf, nodelist in task.iter_buffers():
            if buf:
                bad_nodes.add((buf, NodeSet.fromlist(nodelist)))
        return bad_nodes

    def resume(self, nodes: NodeSet) -> None:
        self.scheduler.resume(nodes)

    def drain(self, nodes: NodeSet) -> None:
        self.scheduler.drain(nodes)



