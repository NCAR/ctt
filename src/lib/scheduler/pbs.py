import logging

import ClusterShell

#TODO switch to using CluserShell module
#TODO check if pbs can batch resume/drain nodes instead of doing 1 at a time

class PBS:
    def __init__(self, conf):
        self.pbsadmin = conf['pbsadmin']
        self.pbsnodes = conf['pbsnodes']

    def resume(self, nodes2resume) -> None:
        task = ClusterShell.Task.task_self()
        toresume = ' '.join(nodes2resume)
        logging.debug(f"Resuming {toresume}")
        task.run(f"{self.pbsnodes} -r -C '' {toresume}", nodes=self.pbsadmin, timeout=30)
        #TODO check if succesfull

    def drain(self, nodes2drain):
        task = ClusterShell.Task.task_self()
        todrain = ' '.join(nodes2drain)
        logging.debug(f"Draining {todrain}")
        task.run(f"{self.pbsnodes} -o {todrain}", nodes=self.pbsadmin, timeout=30)
        #TODO check if succesfull
