import ClusterShell.Task
from ClusterShell.NodeSet import NodeSet
from scheduler import PBS


class Cluster:
    def __init__(self, conf):
        self.scheduler = PBS(conf)

    def siblings(self, node: NodeSet) -> NodeSet:
        raise NotImplementedError

    def bad_nodes(self, nodes: NodeSet) -> list((str, NodeSet)):
        """ checks if given nodes are bad
        input: nodeset string (ex: dec[0001-0123])
        output: set(bad node reasons: str, nodeset with that reason)
        """
        task = ClusterShell.Task.task_self()
        task.run("[ -f /etc/THIS_IS_A_BAD_NODE.ncar ] && cat /etc/THIS_IS_A_BAD_NODE.ncar;' 2>/dev/null", nodes=nodes, timeout=30)
        bad_nodes = []
        for buf, nodelist in task.iter_buffers():
            if buf:
                bad_nodes.append((buf.message().decode("utf-8"), NodeSet.fromlist(nodelist)))
        return bad_nodes

    def resume(self, nodes: NodeSet) -> None:
        self.scheduler.resume(nodes)

    def drain(self, nodes: NodeSet) -> None:
        self.scheduler.drain(nodes)

    def logical_to_physical(self, nodes: NodeSet) -> NodeSet:
        raise NotImplementedError

    def physical_to_logical(self, nodes: NodeSet) -> NodeSet:
        raise NotImplementedError

    def real_node(self, nodes: NodeSet) -> bool:
        """checks if all nodes in the nodeset are real or not"""
        raise NotImplementedError

    def all_nodes(self) -> NodeSet:
        """returns a NodeSet of all compute nodes in the cluster"""
        raise NotImplementedError


