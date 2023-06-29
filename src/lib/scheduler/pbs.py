import os

#TODO switch to using CluserShell module
#TODO check if pbs can batch resume/drain nodes instead of doing 1 at a time

class PBS:
    def __init__(self, conf):
        self.clush_path = conf['clush']
        self.pbsadmin = conf['pbsadmin']
        self.pbsnodes = conf['pbsnodes']

    def resume(self, nodes2resume):
        for node in nodes2resume:
            if node != "FATAL":
                try:
                    os.popen(
                        "{0} -t30 -w {1} -qS -t30 -u120 '{2} -r -C \"\" {3}'".format(
                            self.clush_path, self.pbsadmin, self.pbsnodes_path, node
                        )
                    ).read()
                except:
                    print("Can not process pbs_resume() on %s" % (node))

                try:
                    os.popen(
                        "{0} -t30 -w {1} '[ -f /etc/nolocal ] && /usr/bin/unlink /etc/nolocal ; [ -f /etc/THIS_IS_A_BAD_NODE.ncar ] && /usr/bin/unlink /etc/THIS_IS_A_BAD_NODE.ncar;' 2>/dev/null".format(
                            self.clush_path, node
                        )
                    )
                except:
                    print(
                        "Can not unlink /etc/nolocal or /etc/THIS_IS_A_BAD_NODE.ncar on %s"
                        % (node)
                    )


    def drain(self, nodes2drain):
        for node in nodes2drain:
            try:
                os.popen(
                    "{0} -t30 -w {1} -qS -t30 -u120 '{2} -o {3}'".format(
                        self.clush_path, self.pbsadmin, self.pbsnodes_path, node
                    )
                ).read()
            except:
                print("Can not process pbs_drain() on %s" % (node))
