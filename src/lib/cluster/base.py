import ClusterShell.Task
from ClusterShell.NodeSet import NodeSet
from scheduler import PBS


class Cluster:
    def __init__(self, conf):
        self.scheduler = PBS(conf)
        self.pbsnodes = conf['pbsnodes']
        self.pbsadmin = conf['pbsadmin']
        self.badnodefile = conf['badnodefile']

    def siblings(self, node: NodeSet) -> NodeSet:
        raise NotImplementedError

    def bad_nodes(self, nodes: NodeSet) -> list((str, NodeSet)):
        #TODO FIXME doesn't need to take in a list of nodes
        """ checks if given nodes are bad
        input: nodeset string (ex: dec[0001-0123])
        output: set(bad node reasons: str, nodeset with that reason)
        """
        task = ClusterShell.Task.task_self()
        bad_nodes = {}
        task.run(f"{self.pbsnodes} -l", nodes=self.pbsadmin, timeout=30)
        for buf, nodelist in task.iter_buffers():
            for line in buf.message().decode("utf-8").split('\n'):
                n = line.split()
                node = n[0]
                n[1]
                title = ' '.join(n[2:])
                #TODO FIXME aggregate issues witht he same issue, or change this silly api
                if title in bad_nodes:
                    bad_nodes[title].update(node)
                else:
                    bad_nodes[title] = NodeSet.fromlist([node])

        #TODO return the full message from self.badnodefile, if it exists
        #task.run(f"[ -f {self.badnodefile} ] && cat {self.badnodefile}; 2>/dev/null", nodes=nodes, timeout=30)
        #for buf, nodelist in task.iter_buffers():
        #    if buf:
        #        bad_nodes.append((buf.message().decode("utf-8"), NodeSet.fromlist(nodelist)))
        return bad_nodes

    def resume(self, nodes: NodeSet) -> None:
        task = ClusterShell.Task.task_self()
        task.run(f"rm {self.badnodefile}", nodes=nodes, timeout=30)
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



