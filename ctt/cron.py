#!/usr/bin/env python3
import os
import re

def main(date, severity, assignedto, updatedby, cluster, UserGroup):
    try:
        pbs_states_csv = os.popen(
            "{0} -t30 -Nw {1} {2} -av -Fdsv -D,".format(
                clush_path, self.pbsadmin, pbsnodes_path
            )
        ).readlines()
    except:
        print("Can not process --auto")
        details = "Can not get pbsnodes from %s" % (self.pbsadmin)
        cttissue = new_issue(
            date,
            "1",
            "---",
            "open",
            cluster,
            "FATAL",
            "Can not get pbsnodes",
            details,
            "FATAL",
            "FATAL",
            "FATAL",
            "other",
            "FATAL",
            date,
            UserGroup,
            "---",
        )
        log_history(cttissue, date, "ctt", "new issue")
        exit(1)

    newissuedict = {}
    if int(maxissuesopen) != int(0):
        open_count = self.db.open_count()
        if open_count >= int(maxissuesopen):
            if not self.db.maxissueopen():
                print(
                    "Maximum number of issues (%s) reached for --auto" % (maxissuesopen)
                )
                print("Can not process --auto")
                details = "To gather nodes and failures, increase maxissuesopen"
                cttissue = new_issue(
                    date,
                    "1",
                    "---",
                    "open",
                    cluster,
                    "FATAL",
                    "MAX OPEN REACHED",
                    details,
                    "FATAL",
                    "FATAL",
                    "FATAL",
                    "other",
                    "FATAL",
                    date,
                    UserGroup,
                    "---",
                )
                log_history(cttissue, date, updatedby, "new issue")
            exit(1)

    for line in pbs_states_csv:
        splitline = line.split(",")
        node = splitline[0]
        x, node = node.split("=")
        state = splitline[5]
        x, state = state.split("=")
        # known pbs states: 'free', 'job-busy', 'job-exclusive',
        #'resv-exclusive', offline, down, provisioning, wait-provisioning, stale, state-unknown

        if strict_node_match_auto != "False":
            if node not in strict_node_match_auto:
                continue

        self.db.siblings_update_state(node, state)

        transient_errors_check(node, date, updatedby)

        if (
            node_open_check(node) is True
        ):  # update node state if open issue on node and state changed
            issue = check_node_state(node, state)
            if issue is not None and issue.state == state:  # no change in state
                cttissue = issue.cttissue
                update_issue(cttissue, "state", state)
                update_issue(cttissue, "updatedby", "ctt")
                update_issue(cttissue, "updatedtime", issue.date)
                log_history(
                    cttissue,
                    issue.date,
                    "ctt",
                    "%s state changed to %s" % (node, state),
                )

        elif state in ("state-unknown", "offline", "down"):  # if no issue on node
            if "comment=" in "".join(splitline):
                for item in splitline:
                    if "comment=" in item:
                        x, comment = item.split("=")
                        if (
                            comment and node_open_check(node) is False
                        ):  # Prevents duplicate issues on node
                            hostname = node
                            newissuedict[hostname] = comment

            else:
                comment = "Unknown Reason"
                hostname = node
                newissuedict[hostname] = comment

    if len(newissuedict) != 0 and len(newissuedict) <= int(maxissuesrun):
        status = "open"
        ticket = "---"
        updatedby = "ctt"
        issuetype = "u"
        issueoriginator = "ctt"
        updatedtime = date
        updatedtime = updatedtime[:-10]
        assignedto = "ctt"
        state = "unknown"
        xticket = "---"
        for hostname, comment in newissuedict.items():
            issuetitle = get_THIS_IS_A_BAD_NODE(hostname)
            if issuetitle is not False:
                issuedescription = issuetitle
                if comment:
                    issuedescription = issuedescription + ", PBS comment=%s" % (comment)
            else:
                issuetitle = issuedescription = comment

            cttissue = new_issue(
                date,
                severity,
                ticket,
                status,
                cluster,
                hostname,
                issuetitle,
                issuedescription,
                assignedto,
                issueoriginator,
                updatedby,
                issuetype,
                state,
                updatedtime,
                UserGroup,
                xticket,
            )
            log_history(cttissue, date, "ctt", "new issue")

    elif len(newissuedict) >= int(maxissuesrun):
        print("Maximum number of issues reached for --auto")
        print("Can not process --auto")
        details = (
            "This run of ctt discovered more issues than maxissuesrun. \
                   Discovered: %s; maxissuesrun: %s\n\n %s"
            % (len(newissuedict), maxissuesrun, newissuedict)
        )
        cttissue = new_issue(
            date,
            "1",
            "---",
            "open",
            cluster,
            "FATAL",
            "MAX RUN REACHED: %s/%s" % (len(newissuedict), maxissuesrun),
            details,
            "FATAL",
            "FATAL",
            "FATAL",
            "other",
            "FATAL",
            date,
            UserGroup,
            "---",
        )
        log_history(cttissue, date, "ctt", "new issue")
        exit(1)

    # Force Offline
    if pbs_enforcement == "True":
        for line in pbs_states_csv:
            splitline = line.split(",")
            node = splitline[0]
            x, node = node.split("=")
            state = splitline[5]
            x, state = state.split("=")

            if self.db.is_open_sibling(node):
                if not re.search("offline", splitline[5]) and not re.search(
                    "offline", splitline[6]
                ):
                    sibcttissue = self.db.sibcttissue(node)
                    if sibcttissue:
                        nodes2drain = node.split(",")
                        pbs_drain(sibcttissue, date, "ctt", nodes2drain)
                        self.db.siblings_update_state(node, "offline")
                        log_history(sibcttissue, date, "ctt", "Auto forced pbs offline")

            if self.db.is_primary(node):
                if not re.search("offline", splitline[5]) and not re.search(
                    "offline", splitline[6]
                ):
                    cttissue = self.db.cttissue(node)
                    if cttissue:
                        nodes2drain = node.split(",")
                        pbs_drain(cttissue, date, "ctt", nodes2drain)
                        update_issue(cttissue, "state", "offline")
                        log_history(cttissue, date, "ctt", "Auto forced pbs offline")


if __name__ == "__main__":
    main()