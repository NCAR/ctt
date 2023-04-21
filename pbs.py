import os


def is_bad_node(
    hostname,
):  # rippersnapper needs to enforce via cron on nodes for this to work correctly.
    try:
        issuetitle = os.popen(
            "{0} -t30 -Nw {1} '[ -f /etc/THIS_IS_A_BAD_NODE.ncar ] && cat /etc/THIS_IS_A_BAD_NODE.ncar;' 2>/dev/null".format(
                clush_path, hostname
            )
        ).readlines()
        issuetitle = "".join(issuetitle)
        issuetitle = issuetitle.strip()
        if not issuetitle:
            return False
        else:
            return issuetitle
    except:
        return False


def resume(cttissue, date, updatedby, nodes2resume):
    for node in nodes2resume:
        if node != "FATAL":
            try:
                os.popen(
                    "{0} -t30 -w {1} -qS -t30 -u120 '{2} -r -C \"\" {3}'".format(
                        clush_path, self.pbsadmin, pbsnodes_path, node
                    )
                ).read()
            except:
                print("Can not process pbs_resume() on %s" % (node))

            try:
                os.popen(
                    "{0} -t30 -w {1} '[ -f /etc/nolocal ] && /usr/bin/unlink /etc/nolocal ; [ -f /etc/THIS_IS_A_BAD_NODE.ncar ] && /usr/bin/unlink /etc/THIS_IS_A_BAD_NODE.ncar;' 2>/dev/null".format(
                        clush_path, node
                    )
                )
            except:
                print(
                    "Can not unlink /etc/nolocal or /etc/THIS_IS_A_BAD_NODE.ncar on %s"
                    % (node)
                )


def drain(cttissue, date, updatedby, nodes2drain):
    for node in nodes2drain:
        try:
            os.popen(
                "{0} -t30 -w {1} -qS -t30 -u120 '{2} -o {3}'".format(
                    clush_path, pbsadmin, pbsnodes_path, node
                )
            ).read()
        except:
            print("Can not process pbs_drain() on %s" % (node))

        log_history(cttissue, date, updatedby, "Drained %s" % (node))
