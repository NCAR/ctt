#!/usr/bin/env python3

import os
import re
import socket
import sqlite3 as SQL
import sys
import textwrap

from ClusterShell.Task import task_self

import config
import extraview
import slack

config = config.get_config()
defaults = config["DEFAULTS"]
pbsadmin = defaults["pbsadmin"]
users = config["USERS"]
pbsnodes_path = defaults["pbsnodes_path"]
clush_path = defaults["clush_path"]
maxissuesopen = defaults[
    "maxissuesopen"
]  # ONLY USED WITH AUTO, CAN STILL MANUALLY OPEN ISSUES
maxissuesrun = defaults["maxissuesrun"]
pbs_enforcement = defaults[
    "pbs_enforcement"
]  # with False, will not resume or offline nodes in pbs
strict_node_match = defaults["strict_node_match"]  # False or comma del list of nodes
strict_node_match_auto = defaults[
    "strict_node_match_auto"
]  # False or comma del list of nodes
transient_errors = defaults["transient_errors"]
transient_errors_enabled = defaults["transient_errors_enabled"]
slack_enabled = defaults["slack_enabled"]
slack_bot_token = defaults["slack_bot_token"]
slack_channel = defaults["slack_channel"]
cluster = defaults["cluster"]
EV = extraview.Client(config)

# Get viewnotices list from ctt.ini
userslist = []
usersdict = dict(config.items("USERS"))


def release(cttissue, date, node):  # --release
    nodes2resume = list(node.split(" "))
    con = SQL.connect("ctt.sqlite")

    with con:
        cur = con.cursor()  # 1. Check if node is primary
        cur.execute(
            """SELECT rowid FROM issues WHERE hostname = ? and status = ? and cttissue = ?""",
            (
                node,
                "open",
                cttissue,
            ),
        )
        data = cur.fetchone()
        if data:
            print(
                "%s is not a sibling for issue %s. Only run --release to release a sibling from a primary node issue."
                % (node, cttissue)
            )
            if len(nodes2resume) > 0:
                nodes2resume.remove(node)
            next

        if len(nodes2resume) > 0:
            cur.execute(
                """SELECT rowid FROM issues WHERE hostname = ? and status = ? and cttissue != ?""",
                (
                    node,
                    "open",
                    cttissue,
                ),
            )
            data = (
                cur.fetchone()
            )  # 2. Check if node is primary for a different issue number
            if data:
                print(
                    "There is another issue for %s. Detaching sibling, but not resuming."
                    % (node)
                )
                cur.execute(
                    """UPDATE siblings SET status = ? WHERE cttissue = ? and sibling = ?""",
                    (
                        "closed",
                        cttissue,
                        node,
                    ),
                )
                nodes2resume.remove(node)
                next

    if len(nodes2resume) > 0:
        with con:  # 3. Sibling is a sibling for a different issue number
            cur = con.cursor()
            cur.execute(
                """SELECT rowid FROM siblings WHERE sibling = ? and status = ? and cttissue != ?""",
                (
                    node,
                    "open",
                    cttissue,
                ),
            )
            data = cur.fetchone()
            if data:
                print(
                    "%s is a sibling to another issue. Detaching sibling, but not resuming."
                    % (node)
                )
                cur.execute(
                    """UPDATE siblings SET status = ? WHERE cttissue = ? and sibling = ?""",
                    (
                        "closed",
                        cttissue,
                        node,
                    ),
                )
                nodes2resume.remove(node)

    if len(nodes2resume) > 0:
        with con:
            cur = con.cursor()
            cur.execute(
                """UPDATE siblings SET status = ? WHERE cttissue = ? and sibling = ?""",
                (
                    "closed",
                    cttissue,
                    node,
                ),
            )

    if pbs_enforcement == "True" and len(nodes2resume) > 0:
        pbs_resume(cttissue, date, os.environ.get("SUDO_USER"), nodes2resume)
    elif pbs_enforcement == "True" and len(nodes2resume) < 1:
        next


def check_holdback(node):
    con = SQL.connect("ctt.sqlite")
    with con:
        cur = con.cursor()
        cur.execute(
            """SELECT * FROM holdback WHERE hostname = ? and state = ?""",
            (node, "True"),
        )
        if cur.fetchone() is None:
            return False


def update_holdback(node, state):
    con = SQL.connect("ctt.sqlite")
    with con:
        cur = con.cursor()
        if "remove" in state:
            cur.execute(
                """UPDATE holdback SET state = ? WHERE hostname = ? and state = ?""",
                (
                    "False",
                    node,
                    "True",
                ),
            )
        if "add" in state:
            cur.execute(
                """INSERT INTO holdback(
                    hostname,state)
                    VALUES(?, ?)""",
                (node, "True"),
            )


def assign_EV(cttissue, assignto):
    """assign ev to group"""
    data = get_issue_data(cttissue)
    global EV
    EV.assign_group(
        data[3],
        assignto,
        None,
        {
            "COMMENTS": """
        CTT issue number {} assigned to {}.
        """.format(
                cttissue, assignto
            )
        },
    )


def open_EV(cttissue):
    """open ev ticket"""
    data = get_issue_data(cttissue)
    data = list(map(str, data))
    issue_data_formatted = (
        "CTT issue: %s\nCTT Severity: %s\nHostname: %s\nIssue Title: %s\nIssue Description: %s"
        % (data[0], data[2], data[6], data[7], data[8])
    )
    global EV
    ev_id = EV.create(
        "ssgev",
        "ssg",
        None,
        "CTT Issue: %s: %s: %s " % (data[5].capitalize(), data[6], data[7]),
        "%s" % (issue_data_formatted),
        {
            "HELP_LOCATION": EV.get_field_value_to_field_key("HELP_LOCATION", "NWSC"),
            "HELP_HOSTNAME": EV.get_field_value_to_field_key(
                "HELP_HOSTNAME", data[3].capitalize()
            ),
            "HELP_HOSTNAME_CATEGORY": EV.get_field_value_to_field_key(
                "HELP_HOSTNAME_CATEGORY", "Supercomputer"
            ),
            "HELP_HOSTNAME_OTHER": data[5],
        },
    )
    return ev_id


def comment_EV(cttissue, ev_comment):
    """comment on an open ev ticket"""
    data = get_issue_data(cttissue)
    global EV
    EV.add_resolver_comment(data[3], "CTT Comment:\n%s\n" % (ev_comment))
    print('EV %s updated with "%s"' % (data[3], ev_comment))


def close_EV(cttissue, ev_comment):
    """close ev ticket"""
    data = get_issue_data(cttissue)
    global EV
    EV.close(data[3], "CTT Comment:\n%s" % (ev_comment))
    print("EV %s closed" % (data[3]))


def reopen_EV(cttissue, ev_comment):
    """reopen ev ticket"""
    data = get_issue_data(cttissue)
    global EV
    EV.open(data[3], "CTT Comment:\n%s" % (ev_comment))
    print("EV %s reopened" % (data[3]))


def get_issue_data(cttissue):
    con = SQL.connect("ctt.sqlite")
    with con:
        cur = con.cursor()
        cur.execute("""SELECT * FROM issues WHERE cttissue = ?""", (cttissue,))
        for row in cur:  # COULD JUST RETURN THE ROW
            cttissue = row[1]
            date = row[2][0:16]
            severity = row[3]
            ticket = row[4]
            status = row[5]
            cluster = row[6]
            hostname = row[7]
            issuetitle = row[8]
            issuedescription = row[9]
            assignedto = row[10]
            issueoriginator = row[11]
            updatedby = row[12]
            issuetype = row[13]
            state = row[14]
            updatedtime = row[15][0:16]

    return [
        cttissue,
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
    ]


for key in usersdict:
    userslist.append(key)
    userslist = list(set(userslist))  # remove duplicates in list
    viewnotices = " ".join(userslist)  # list to str


# Get valid groups
def GetGroups(dict, user):
    groupsList = []
    itemsList = dict.items()
    for item in itemsList:
        groupsList.append(item[0])
    return groupsList


# Get users group name
def GetUserGroup(dict, user):
    userList = []
    itemsList = dict.items()
    for item in itemsList:
        if user in item[1]:
            userList.append(item[0])
    if not userList:
        print("Your username is not found in configuration, Exiting!")
        sys.exit()
    UserGroup = "".join(userList)
    return UserGroup


def maxissueopen_issue():
    con = SQL.connect("ctt.sqlite")
    cur = con.cursor()
    cur.execute(
        """SELECT * FROM issues WHERE status = ? and issuetitle = ?""",
        ("open", "MAX OPEN REACHED"),
    )
    if cur.fetchone() is None:
        return False


def get_open_count():
    con = SQL.connect("ctt.sqlite")
    cur = con.cursor()
    cur.execute("""SELECT * FROM issues WHERE status = ?""", ("open",))
    return len(cur.fetchall())


def create_attachment(cttissue, filepath, attach_location, date, updatedby):
    import shutil

    if os.path.isfile(filepath) is False:
        print("File %s does not exist, Exiting!" % (filepath))
        sys.exit(1)
    if os.path.exists(attach_location) is False:
        print(
            "Attachment root location does not exist. Check ctt.ini attach_location setting"
        )
        sys.exit(1)
    if issue_exists_check(cttissue) is False:
        print(
            "Issue %s is not open. Can not attach a file to a closed, deleted, or nonexisting issue"
            % (cttissue)
        )
        sys.exit(1)
    newdir = "%s/%s" % (attach_location, cttissue)
    if os.path.exists(newdir) is False:
        os.mkdir(newdir)
    thefile = os.path.basename(filepath)
    destination_file = "%s.%s" % (date[0:16], thefile)
    final_destination_file = "%s/%s" % (newdir, destination_file)
    shutil.copy(filepath, final_destination_file)
    if os.path.isfile(final_destination_file) is True:
        print("File attached to %s" % (cttissue))
    else:
        print("Error: File not attached, unknown error")


def sibling_open_check(node):
    con = SQL.connect("ctt.sqlite")
    with con:
        cur = con.cursor()
        cur.execute(
            """SELECT rowid FROM siblings WHERE status = ? and sibling = ?""",
            (
                "open",
                node,
            ),
        )
        data = cur.fetchone()
        if data is None:
            return False
        else:
            return True


def update_sibling(node, state):
    con = SQL.connect("ctt.sqlite")
    with con:
        cur = con.cursor()
        cur.execute(
            """UPDATE siblings SET state = ? WHERE sibling = ? and status = ?""",
            (
                state,
                node,
                "open",
            ),
        )


def get_THIS_IS_A_BAD_NODE(
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


def run_auto(date, severity, assignedto, updatedby, cluster, UserGroup):
    try:
        pbs_states_csv = os.popen(
            "{0} -t30 -Nw {1} {2} -av -Fdsv -D,".format(
                clush_path, pbsadmin, pbsnodes_path
            )
        ).readlines()
    except:
        print("Can not process --auto")
        details = "Can not get pbsnodes from %s" % (pbsadmin)
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
        sys.exit(1)

    newissuedict = {}
    if int(maxissuesopen) != int(0):
        open_count = get_open_count()
        if open_count >= int(maxissuesopen):
            if maxissueopen_issue() is False:
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
            sys.exit(1)

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

        if sibling_open_check(node) is True:  # update sibling node state if open exists
            update_sibling(node, state)

        transient_errors_check(node, date, updatedby)

        if (
            node_open_check(node) is True
        ):  # update node state if open issue on node and state changed
            cttissue = check_node_state(node, state)
            if cttissue is None:  # no change in state
                next
            else:  # change in pbs state
                cttissue = "".join(cttissue)
                update_issue(cttissue, "state", state)
                update_issue(cttissue, "updatedby", "ctt")
                update_issue(cttissue, "updatedtime", date)
                log_history(
                    cttissue,
                    date,
                    "ctt",
                    "%s state changed to %s" % (node, state),
                )

        elif state in (
            "state-unknown",
            "offline",
            "down",
        ):  # if no issue on node
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
        sys.exit(1)

    # Force Offline
    if pbs_enforcement == "True":
        # pbs_drain(cttissue,date,updatedby,nodes)
        for line in pbs_states_csv:
            splitline = line.split(",")
            node = splitline[0]
            x, node = node.split("=")
            state = splitline[5]
            x, state = state.split("=")

            if sibling_open_check(node) is True:
                if not re.search("offline", splitline[5]) and not re.search(
                    "offline", splitline[6]
                ):
                    sibcttissue = get_sibcttissue(node)
                    if sibcttissue:
                        nodes2drain = node.split(",")
                        pbs_drain(sibcttissue, date, "ctt", nodes2drain)
                        update_sibling(node, "offline")
                        log_history(sibcttissue, date, "ctt", "Auto forced pbs offline")

            if primary_node_open_check(node) is True:
                if not re.search("offline", splitline[5]) and not re.search(
                    "offline", splitline[6]
                ):
                    cttissue = get_cttissue(node)
                    if cttissue:
                        nodes2drain = node.split(",")
                        pbs_drain(cttissue, date, "ctt", nodes2drain)
                        update_issue(cttissue, "state", "offline")
                        log_history(cttissue, date, "ctt", "Auto forced pbs offline")


def pass_nhc(node):
    task = task_self()
    task.shell("/usr/sbin/nhc -a", nodes=node)
    task.run()
    if task.max_retcode() == 0:
        return True
    else:
        print("Node {} did not pass nhc".format(node))
        for output, _ in task.iter_buffers():
            print("stdout: {}".format(output.message()))
        for output, _ in task.iter_errors():
            print("stderr: {}".format(output.message()))
        return False


def transient_errors_check(node, date, updatedby):  # jon
    if primary_node_open_check(node) is True and transient_errors_enabled == "True":
        cttissue = get_cttissue(node)
        data = get_issue_data(cttissue)
        data = list(map(str, data))  # data[7] == issuetitle
        transient_errors_list = transient_errors.split(", ")
        for item in transient_errors_list:
            if item in data[7] and pass_nhc(node):
                close_issue(cttissue, date, updatedby)
                closemessage = "Transient error: %s" % (item)
                if slack_enabled == "True":
                    slack_message = "Issue %s for %s: %s closed by ctt\n%s" % (
                        cttissue,
                        cluster,
                        node,
                        closemessage,
                    )
                    slackclient = slack.Slack(config)
                    slackclient.send_slack(slack_message)

                log_history(cttissue, date, "ctt", "Closed issue %s" % (closemessage))


def primary_node_open_check(node):
    con = SQL.connect("ctt.sqlite")
    with con:
        cur = con.cursor()
        cur.execute(
            '''
            SELECT rowid FROM issues WHERE hostname = ? and status = "open"''',
            (node,),
        )
        data1 = cur.fetchone()
        if data1 is None:
            return False
        else:
            return True


def get_sibcttissue(node):
    con = SQL.connect("ctt.sqlite")
    with con:
        cur = con.cursor()
        cur.execute(
            """SELECT cttissue FROM siblings WHERE sibling = ? and status = ?""",
            (node, "open"),
        )
        cttissue = cur.fetchone()
        if cttissue:
            cttissue = "".join(cttissue)  # tuple to str
            return cttissue


def get_cttissue(node):
    con = SQL.connect("ctt.sqlite")
    with con:
        cur = con.cursor()
        cur.execute(
            """SELECT cttissue FROM issues WHERE hostname = ? and status = ?""",
            (node, "open"),
        )
        cttissue = cur.fetchone()
        if cttissue:
            cttissue = "".join(cttissue)  # tuple to str
            return cttissue


def test_arg_size(arg, what, maxchars):
    size = sys.getsizeof(arg)
    if int(size) > int(maxchars):
        print(
            "Maximum argument size of %s characters reached for %s. Exiting!"
            % (maxchars, what)
        )
        sys.exit(1)


def check_for_ticket(cttissue):
    con = SQL.connect("ctt.sqlite")
    with con:
        cur = con.cursor()
        cur.execute(
            """SELECT * FROM issues WHERE cttissue = ? and ticket != ?""",
            (
                cttissue,
                "---",
            ),
        )
        if cur.fetchone() is None:
            return False
        else:
            return True


def update_ticket(cttissue, ticketvalue):
    con = SQL.connect("ctt.sqlite")
    with con:
        cur = con.cursor()
        cur.execute("""SELECT * FROM issues WHERE cttissue = ?""", (cttissue,))
        for row in cur:
            ticket = row[4]
            if ticketvalue == ticket:
                ticket = "---"
                cur.execute(
                    """UPDATE issues SET ticket = ? WHERE cttissue = ?""",
                    (
                        ticket,
                        cttissue,
                    ),
                )
            elif ticket == "---":
                cur.execute(
                    """UPDATE issues SET ticket = ? WHERE cttissue = ?""",
                    (
                        ticketvalue,
                        cttissue,
                    ),
                )
            else:
                print(
                    "There is another ticket for this issue. Remove existing before adding another. Not adding %s"
                    % (ticketvalue)
                )


def update_xticket(cttissue, xticketvalue):
    con = SQL.connect("ctt.sqlite")
    with con:
        cur = con.cursor()
        cur.execute("""SELECT * FROM issues WHERE cttissue = ?""", (cttissue,))
        for row in cur:
            xticketlist = row[17]  ## CHECK THIS
            xticketlist = xticketlist.split(",")
            if "---" in xticketlist:
                xticketlist.remove("---")
            if xticketvalue in xticketlist:
                xticketlist.remove(xticketvalue)
            else:
                xticketlist.append(xticketvalue)
            xticketlist = ",".join(xticketlist)
            if not xticketlist:
                xticketlist = "---"
            cur.execute(
                """UPDATE issues SET xticket = ? WHERE cttissue = ?""",
                (
                    xticketlist,
                    cttissue,
                ),
            )


def view_tracker_new(cttissue, UserGroup, viewnotices):
    userlist = []
    for user in viewnotices.split(" "):
        if UserGroup == user:
            next
        else:
            userlist.append(user)
    if userlist:
        userlist = ".".join(userlist)
    else:
        userlist = "---"

    con = SQL.connect("ctt.sqlite")
    with con:
        cur = con.cursor()
        cur.execute(
            """UPDATE issues SET viewtracker = ? WHERE cttissue = ?""",
            (userlist, cttissue),
        )


def view_tracker_update(
    cttissue, UserGroup
):  # used to update viewtracker column when a user runs --show
    con = SQL.connect("ctt.sqlite")
    with con:
        cur = con.cursor()
        cur.execute("""SELECT * FROM issues WHERE cttissue = ?""", (cttissue,))
        for row in cur:
            userlist = row[16]
            userlist = userlist.split(".")
            if UserGroup in userlist:
                userlist.remove(UserGroup)
            userlist = ".".join(userlist)
            if not userlist:
                userlist = "---"
            cur.execute(
                """UPDATE issues SET viewtracker = ? WHERE cttissue = ?""",
                (userlist, cttissue),
            )


def get_pbs_sib_state(node):
    con = SQL.connect("ctt.sqlite")
    with con:
        cur = con.cursor()
        cur.execute(
            """SELECT state FROM siblings WHERE sibling = ? and status = ?""",
            (
                node,
                "open",
            ),
        )
        state = cur.fetchone()
        return state


def get_hostname(cttissue):
    con = SQL.connect("ctt.sqlite")
    with con:
        cur = con.cursor()
        cur.execute(
            """SELECT hostname FROM issues WHERE cttissue = ? and status = ?""",
            (
                cttissue,
                "open",
            ),
        )
        hostname = cur.fetchone()
        if hostname:
            return hostname


def add_siblings(cttissue, date, updatedby):
    if issue_open_check(cttissue) is False:
        print("Issue %s is not open" % (cttissue))
        sys.exit()
    node = get_hostname(cttissue)
    node = "".join(node)  # tuple to str
    try:
        nodes = resolve_siblings(node)
    except:
        print("Can not get siblings. Check node name.")
        sys.exit(1)

    nodes.remove(node)

    if pbs_enforcement == "True":
        pbs_drain(cttissue, date, updatedby, nodes)
    else:
        print("pbs_enforcement is False. Not draining nodes")

    for sib in nodes:
        if node != sib:
            con = SQL.connect("ctt.sqlite")
            with con:
                cur = con.cursor()
                cur.execute(
                    """INSERT INTO siblings(
                        cttissue,date,status,parent,sibling,state)
                        VALUES(?, ?, ?, ?, ?, ?)""",
                    (cttissue, date, "open", node, sib, "---"),
                )

        info = "Attached sibling %s to issue" % (sib)
        log_history(cttissue, date, updatedby, info)


#### SIB UPDATE FOR GUST/DE ####
def node_to_tuple(n):  # used by add_siblings()
    m = re.match("([rR])([0-9]+)([iI])([0-9]+)([nN])([0-9]+)", n)
    if m is not None:
        # (rack, iru, node)
        return (int(m.group(2)), int(m.group(4)), int(m.group(6)))
    else:
        return None


def resolve_siblings(
    node,
):  # This is the func to change for gust can remove node_to_duple()
    nodes_per_blade = 4
    slots_per_iru = 9
    if re.search("^la", socket.gethostname()) is not None:
        nodes_per_blade = 2
    """ resolve out list of sibling nodes to given set of nodes """
    result = []
    nt = node_to_tuple(node)
    for i in range(0, nodes_per_blade):
        nid = (nt[2] % slots_per_iru) + (i * slots_per_iru)
        nodename = "r%di%dn%d" % (nt[0], nt[1], nid)

        if nodename not in result:
            result.append(nodename)
    return result


#### END SIB UPDATE FOR GUST/DE ####


def check_node_state(
    node, state
):  # checks if node has open issue, returns cttissue number
    con = SQL.connect("ctt.sqlite")
    with con:
        cur = con.cursor()
        cur.execute(
            """SELECT cttissue FROM issues WHERE hostname = ? and state != ? and status = ?""",
            (
                node,
                state,
                "open",
            ),
        )
        result = cur.fetchone()
        if result:
            return result


def node_open_check(node):  # checks if node has open issue
    con = SQL.connect("ctt.sqlite")
    with con:
        cur = con.cursor()
        cur.execute(
            '''
            SELECT rowid FROM siblings WHERE sibling = ? and status = "open"''',
            (node,),
        )
        data1 = cur.fetchone()
        cur.execute(
            '''
            SELECT rowid FROM issues WHERE hostname = ? and status = "open"''',
            (node,),
        )
        data2 = cur.fetchone()
        if data1 is None and data2 is None:
            return False
        else:
            return True


def check_nolocal():
    if os.path.isfile("/etc/nolocal"):
        print("/etc/nolocal exists, Exiting!")
        sys.exit(1)


def get_history(cttissue):  # used only when issuing --show with -d option
    if issue_exists_check(cttissue):
        cols = "{0:<24}{1:<14}{2:<50}"
        fmt = cols.format
        print("\n----------------------------------------")
        print(fmt("DATE", "UPDATE.BY", "INFO"))
        con = SQL.connect("ctt.sqlite")
        with con:
            cur = con.cursor()
            cur.execute("""SELECT * FROM history WHERE cttissue = ?""", (cttissue,))
            for row in cur:
                date = row[2][0:16]
                updatedby = row[3]
                info = row[4]

                print(
                    fmt(
                        "%s" % date,
                        "%s" % updatedby,
                        "%s" % textwrap.fill(info, width=80),
                    )
                )
    else:
        return


def log_history(cttissue, date, updatedby, info):
    if issue_deleted_check(cttissue) is False or issue_exists_check(cttissue) is True:
        con = SQL.connect("ctt.sqlite")
        with con:
            cur = con.cursor()
            cur.execute(
                """INSERT INTO history(
                     cttissue,date,updatedby,info)
                     VALUES(?, ?, ?, ?)""",
                (cttissue, date, updatedby, info),
            )
        return
    else:
        return


def conv_issuetype(issuetype):
    s, h, o, t, u = ("software", "hardware", "other", "test", "unknown")
    if issuetype == "s":
        return s
    if issuetype == "h":
        return h
    if issuetype == "o":
        return o
    if issuetype == "t":
        return t
    if issuetype == "u":
        return u


def get_issue_full(cttissue):  # used for the --show option
    if issue_exists_check(cttissue) is True:
        con = SQL.connect("ctt.sqlite")
        with con:
            cur = con.cursor()
            cur.execute("""SELECT * FROM issues WHERE cttissue = ?""", (cttissue,))
            for row in cur:
                cttissue = row[1]
                date = row[2][0:16]
                severity = row[3]
                ticket = row[4]
                status = row[5]
                cluster = row[6]
                hostname = row[7]
                issuetitle = row[8]
                issuedescription = row[9]
                assignedto = row[10]
                issueoriginator = row[11]
                updatedby = row[12]
                issuetype = row[13]
                state = row[14]
                updatedtime = row[15][0:16]
                xticket = row[17]
                print("CTT Issue: %s" % (cttissue))
                print("EV Ticket: %s" % (ticket))
                print("External Ticket: %s" % (xticket))
                print("Date Opened: %s" % (date))
                print("Assigned To: %s" % (assignedto))
                print("Issue Originator: %s" % (issueoriginator))
                print("Last Updated By: %s" % (updatedby))
                print("Last Update Time: %s" % (updatedtime))
                print("Severity: %s" % (severity))
                print("Status: %s" % (status))
                print("Type: %s" % (conv_issuetype(issuetype)))
                # print("Type: %s" % (issuetype))
                print("Cluster: %s" % (cluster))
                print("Hostname: %s" % (hostname))
                print("Node State: %s" % (state))
                if check_has_sibs(cttissue) is True:
                    print("Attached Siblings:")
                    sibs = resolve_siblings(hostname)
                    for node in sibs:
                        if node != hostname:
                            state = get_pbs_sib_state(node)
                            state = " ".join(state)
                            print("%s state = %s" % (node, state))
                else:
                    print("Attached Siblings: None")
                print("----------------------------------------")
                print("\nIssue Title:\n%s" % (issuetitle))
                print("\nIssue Description:")
                print(textwrap.fill(issuedescription, width=60))
                print("\n----------------------------------------")
                get_comments(cttissue)
    else:
        print("Issue not found")


def get_comments(cttissue):  # used for --show option (displays the comments)
    if issue_deleted_check(cttissue) is False and issue_exists_check(cttissue) is True:
        con = SQL.connect("ctt.sqlite")
        with con:
            cur = con.cursor()
            cur.execute("""SELECT * FROM comments WHERE cttissue = ?""", (cttissue,))
            for row in cur:
                date = row[2][0:16]
                updatedby = row[3]
                comment = row[4]

                print("\nComment by: %s at %s" % (updatedby, date))
                print(textwrap.fill(comment, width=60))


def comment_issue(cttissue, date, updatedby, newcomment, UserGroup):
    if issue_deleted_check(cttissue) is False and issue_exists_check(cttissue) is True:
        con = SQL.connect("ctt.sqlite")
        with con:
            cur = con.cursor()
            cur.execute(
                """INSERT INTO comments(
                    cttissue,date,updatedby, comment)
                    VALUES(?, ?, ?, ?)""",
                (cttissue, date, updatedby, newcomment),
            )
    else:
        print("Can't add comment to %s. Issue not found or deleted" % (cttissue))
        sys.exit()

    view_tracker_new(cttissue, UserGroup, viewnotices)


def issue_exists_check(cttissue):
    con = SQL.connect("ctt.sqlite")
    with con:
        cur = con.cursor()
        cur.execute("""SELECT rowid FROM issues WHERE cttissue = ?""", (cttissue,))
        data = cur.fetchone()
        if data is None:
            return False
        else:
            return True


def update_issue(cttissue, updatewhat, updatedata):
    if issue_deleted_check(cttissue) is False and issue_exists_check(cttissue) is True:
        con = SQL.connect("ctt.sqlite")
        with con:
            cur = con.cursor()
            cur.execute(
                """UPDATE issues SET {0} = ? WHERE cttissue = ?""".format(updatewhat),
                (updatedata, cttissue),
            )
    else:
        print("Issue %s not found or deleted" % (cttissue))


def check_has_sibs(cttissue):
    con = SQL.connect("ctt.sqlite")
    with con:
        cur = con.cursor()
        cur.execute(
            """SELECT rowid FROM siblings WHERE cttissue = ? and status = ?""",
            (cttissue, "open"),
        )
        data = cur.fetchone()
        if data is None:
            next
        else:
            return True


def get_issues(statustype):  # used for the --list option
    cols = "{0:<8}{1:<19}{2:<12}{3:<13}{4:<16}{5:<6}{6:<12}{7:<11}{8:<12}{9:<28}"
    fmt = cols.format
    print(
        fmt(
            "ISSUE",
            "DATE",
            "EV TICKET",
            "HOSTNAME",
            "STATE",
            "SEV",
            "TYPE",
            "ASSIGNED",
            "UNSEEN",
            "TITLE (25 chars)",
        )
    )
    con = SQL.connect("ctt.sqlite")
    with con:
        cur = con.cursor()
        if "all" in statustype:
            cur.execute("""SELECT * FROM issues ORDER BY id ASC""")
        else:
            cur.execute(
                """SELECT * FROM issues WHERE status = ? ORDER BY id ASC""",
                (statustype,),
            )
        for row in cur:
            cttissue = row[1]
            date = row[2][0:16]
            severity = row[3]
            ticket = row[4]
            row[5]
            row[6]
            hostname = row[7]
            issuetitle = row[8][:25]
            row[9]
            assignedto = row[10]
            row[11]
            row[12]
            issuetype = conv_issuetype(row[13])
            state = row[14]
            row[15][0:16]
            viewtracker = row[16]
            if severity == 1:
                print(
                    bcolors.FAIL
                    + fmt(
                        "%s" % cttissue,
                        "%s" % date,
                        "%s" % ticket,
                        "%s" % hostname,
                        "%s" % state,
                        "%s" % severity,
                        "%s" % issuetype,
                        "%s" % assignedto,
                        "%s" % viewtracker,
                        "%s" % issuetitle,
                    )
                    + bcolors.ENDC
                )
            else:
                print(
                    fmt(
                        "%s" % cttissue,
                        "%s" % date,
                        "%s" % ticket,
                        "%s" % hostname,
                        "%s" % state,
                        "%s" % severity,
                        "%s" % issuetype,
                        "%s" % assignedto,
                        "%s" % viewtracker,
                        "%s" % issuetitle,
                    )
                )

            if check_has_sibs(cttissue) is True:
                sibs = resolve_siblings(hostname)
                for node in sibs:
                    if node != hostname:
                        state = get_pbs_sib_state(node)
                        state = "".join(state)
                        issuetitle = "Sibling to %s" % (hostname)
                        issuetype = "other"
                        print(
                            fmt(
                                "%s" % cttissue,
                                "%s" % date,
                                "%s" % ticket,
                                "%s" % node,
                                "%s" % state,
                                "%s" % severity,
                                "%s" % issuetype,
                                "%s" % assignedto,
                                "%s" % viewtracker,
                                "%s" % issuetitle,
                            )
                        )


def get_issues_vv(statustype):  # -vv option
    cols = "{0:<8}{1:<19}{2:<12}{3:<16}{4:<13}{5:<16}{6:<6}{7:<12}{8:<11}{9:<12}{10:<12}{11:<8}{12:<10}{13:<19}{14:<10}{15:<18}{16:<10}"
    fmt = cols.format
    print(
        fmt(
            "ISSUE",
            "DATE",
            "EV TICKET",
            "EXT TICKET",
            "HOSTNAME",
            "STATE",
            "SEV",
            "TYPE",
            "ASSIGNED",
            "UNSEEN",
            "CLUSTER",
            "ORIG",
            "UPD BY",
            "UPD TIME",
            "STATUS",
            "TITLE",
            "DESC",
        )
    )
    con = SQL.connect("ctt.sqlite")
    with con:
        cur = con.cursor()
        if "all" in statustype:
            cur.execute("""SELECT * FROM issues ORDER BY id ASC""")
        else:
            cur.execute(
                """SELECT * FROM issues WHERE status = ? ORDER BY id ASC""",
                (statustype,),
            )
        for row in cur:
            cttissue = row[1]
            date = row[2][0:16]
            severity = row[3]
            ticket = row[4]
            status = row[5]
            cluster = row[6]
            hostname = row[7]
            issuetitle = row[8]
            issuedescription = row[9]
            assignedto = row[10]
            issueoriginator = row[11]
            updatedby = row[12]
            issuetype = conv_issuetype(row[13])
            state = row[14]
            updatedtime = row[15][0:16]
            viewtracker = row[16]
            xticket = row[17]
            cols = (
                "{0:<8}{1:<19}{2:<12}{3:<16}{4:<13}{5:<16}{6:<6}{7:<12}{8:<11}{9:<12}{10:<12}{11:<8}{12:<10}{13:<19}{14:<10}{15:<20}{16:<%s}"
                % (len(issuetitle) + 10)
            )
            fmt = cols.format
            if severity == 1:
                print(
                    bcolors.FAIL
                    + fmt(
                        "%s" % cttissue,
                        "%s" % date,
                        "%s" % ticket,
                        "%s" % xticket,
                        "%s" % hostname,
                        "%s" % state,
                        "%s" % severity,
                        "%s" % issuetype,
                        "%s" % assignedto,
                        "%s" % viewtracker,
                        "%s" % cluster,
                        "%s" % issueoriginator,
                        "%s" % updatedby,
                        "%s" % updatedtime,
                        "%s" % status,
                        "%s" % issuetitle,
                        "%s" % issuedescription,
                    )
                    + bcolors.ENDC
                )
            else:
                print(
                    fmt(
                        "%s" % cttissue,
                        "%s" % date,
                        "%s" % ticket,
                        "%s" % xticket,
                        "%s" % hostname,
                        "%s" % state,
                        "%s" % severity,
                        "%s" % issuetype,
                        "%s" % assignedto,
                        "%s" % viewtracker,
                        "%s" % cluster,
                        "%s" % issueoriginator,
                        "%s" % updatedby,
                        "%s" % updatedtime,
                        "%s" % status,
                        "%s" % issuetitle,
                        "%s" % issuedescription,
                    )
                )

            if check_has_sibs(cttissue) is True:
                sibs = resolve_siblings(hostname)
                for node in sibs:
                    if node != hostname:
                        state = get_pbs_sib_state(node)
                        state = "".join(state)
                        issuetitle = "Sibling to %s" % (hostname)
                        issuetype = "other"
                        print(
                            fmt(
                                "%s" % cttissue,
                                "%s" % date,
                                "%s" % ticket,
                                "%s" % xticket,
                                "%s" % hostname,
                                "%s" % state,
                                "%s" % severity,
                                "%s" % issuetype,
                                "%s" % assignedto,
                                "%s" % viewtracker,
                                "%s" % cluster,
                                "%s" % issueoriginator,
                                "%s" % updatedby,
                                "%s" % updatedtime,
                                "%s" % status,
                                "%s" % issuetitle,
                                "%s" % issuedescription,
                            )
                        )


def get_issues_v(statustype):  # -v option
    cols = "{0:<8}{1:<19}{2:<12}{3:<16}{4:<13}{5:<16}{6:<6}{7:<12}{8:<11}{9:<12}{10:<12}{11:<8}{12:<10}{13:<19}{14:<10}{15:<22}"
    fmt = cols.format
    print(
        fmt(
            "ISSUE",
            "DATE",
            "EV TICKET",
            "EXT TICKET",
            "HOSTNAME",
            "STATE",
            "SEV",
            "TYPE",
            "ASSIGNED",
            "UNSEEN",
            "CLUSTER",
            "ORIG",
            "UPD BY",
            "UPD TIME",
            "STATUS",
            "TITLE (25 chars)",
        )
    )
    con = SQL.connect("ctt.sqlite")
    with con:
        cur = con.cursor()
        if "all" in statustype:
            cur.execute("""SELECT * FROM issues ORDER BY id ASC""")
        else:
            cur.execute(
                """SELECT * FROM issues WHERE status = ? ORDER BY id ASC""",
                (statustype,),
            )
        for row in cur:
            cttissue = row[1]
            date = row[2][0:16]
            severity = row[3]
            ticket = row[4]
            status = row[5]
            cluster = row[6]
            hostname = row[7]
            issuetitle = row[8][:25]
            row[9]
            assignedto = row[10]
            issueoriginator = row[11]
            updatedby = row[12]
            issuetype = conv_issuetype(row[13])
            state = row[14]
            updatedtime = row[15][0:16]
            viewtracker = row[16]
            xticket = row[17]
            if severity == 1:
                print(
                    bcolors.FAIL
                    + fmt(
                        "%s" % cttissue,
                        "%s" % date,
                        "%s" % ticket,
                        "%s" % xticket,
                        "%s" % hostname,
                        "%s" % state,
                        "%s" % severity,
                        "%s" % issuetype,
                        "%s" % assignedto,
                        "%s" % viewtracker,
                        "%s" % cluster,
                        "%s" % issueoriginator,
                        "%s" % updatedby,
                        "%s" % updatedtime,
                        "%s" % status,
                        "%s" % issuetitle,
                    )
                    + bcolors.ENDC
                )
            else:
                print(
                    fmt(
                        "%s" % cttissue,
                        "%s" % date,
                        "%s" % ticket,
                        "%s" % xticket,
                        "%s" % hostname,
                        "%s" % state,
                        "%s" % severity,
                        "%s" % issuetype,
                        "%s" % assignedto,
                        "%s" % viewtracker,
                        "%s" % cluster,
                        "%s" % issueoriginator,
                        "%s" % updatedby,
                        "%s" % updatedtime,
                        "%s" % status,
                        "%s" % issuetitle,
                    )
                )

            if check_has_sibs(cttissue) is True:
                sibs = resolve_siblings(hostname)
                for node in sibs:
                    if node != hostname:
                        state = get_pbs_sib_state(node)
                        state = "".join(state)
                        issuetitle = "Sibling to %s" % (hostname)
                        issuetype = "other"
                        print(
                            fmt(
                                "%s" % cttissue,
                                "%s" % date,
                                "%s" % ticket,
                                "%s" % xticket,
                                "%s" % hostname,
                                "%s" % state,
                                "%s" % severity,
                                "%s" % issuetype,
                                "%s" % assignedto,
                                "%s" % viewtracker,
                                "%s" % cluster,
                                "%s" % issueoriginator,
                                "%s" % updatedby,
                                "%s" % updatedtime,
                                "%s" % status,
                                "%s" % issuetitle,
                            )
                        )


def issue_open_check(cttissue):
    con = SQL.connect("ctt.sqlite")
    with con:
        cur = con.cursor()
        cur.execute(
            """SELECT rowid FROM issues WHERE cttissue = ? and status = ?""",
            (cttissue, "open"),
        )
        data = cur.fetchone()
        if data is None:
            return False
        else:
            return True


def issue_closed_check(cttissue):
    con = SQL.connect("ctt.sqlite")
    with con:
        cur = con.cursor()
        cur.execute(
            """SELECT rowid FROM issues WHERE cttissue = ? and status = ?""",
            (cttissue, "closed"),
        )
        data = cur.fetchone()
        if data is None:
            return False
        else:
            return True


def issue_deleted_check(cttissue):
    con = SQL.connect("ctt.sqlite")
    with con:
        cur = con.cursor()
        cur.execute(
            """SELECT rowid FROM issues WHERE cttissue = ? and status = ?""",
            (cttissue, "deleted"),
        )
        data = cur.fetchone()
        if data is None:
            return False
        else:
            return True


def delete_issue(cttissue):
    if issue_deleted_check(cttissue) is False and issue_exists_check(cttissue) is True:
        con = SQL.connect("ctt.sqlite")
        with con:
            cur = con.cursor()
            cur.execute(
                """UPDATE issues SET status = ? WHERE cttissue = ?""",
                ("deleted", cttissue),
            )


def pbs_resume(cttissue, date, updatedby, nodes2resume):
    for node in nodes2resume:
        if node == "FATAL":
            next
        else:
            try:
                os.popen(
                    "{0} -t30 -w {1} -qS -t30 -u120 '{2} -r -C \"\" {3}'".format(
                        clush_path, pbsadmin, pbsnodes_path, node
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

            log_history(cttissue, date, updatedby, "ctt resumed %s" % (node))


def pbs_drain(cttissue, date, updatedby, nodes2drain):
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


def close_issue(cttissue, date, updatedby):
    if issue_open_check(cttissue) is False:
        print("Issue %s is not open" % (cttissue))
        sys.exit()
    if (
        issue_deleted_check(cttissue) is False
        and issue_exists_check(cttissue) is True
        and check_for_siblings(cttissue) is False
    ):
        node = get_hostname(cttissue)
        node = "".join(node)
        nodes2resume = []
        nodes2resumeA = []
        nodes2resumeB = []
        con = SQL.connect("ctt.sqlite")
        with con:
            cur = con.cursor()
            cur.execute(
                """SELECT rowid FROM issues WHERE hostname = ? and status = ? and cttissue != ?""",
                (
                    node,
                    "open",
                    cttissue,
                ),
            )
            data = cur.fetchone()
            if data is None:
                nodes2resumeA.append(node)
                next
            else:
                print(
                    "There is another issue for this node. Closing issue, but not resuming."
                )
                cur.execute(
                    """UPDATE siblings SET status = ? WHERE cttissue = ?""",
                    ("closed", cttissue),
                )
                cur.execute(
                    """UPDATE issues SET status = ? WHERE cttissue = ?""",
                    ("closed", cttissue),
                )

        with con:
            cur = con.cursor()
            cur.execute(
                """SELECT rowid FROM siblings WHERE cttissue != ? and status = ? and sibling = ?""",
                (
                    cttissue,
                    "open",
                    node,
                ),
            )
            data = cur.fetchone()
            if data is None:
                nodes2resumeB.append(node)
                cur.execute(
                    """UPDATE siblings SET status = ? WHERE cttissue = ?""",
                    ("closed", cttissue),
                )
                cur.execute(
                    """UPDATE issues SET status = ? WHERE cttissue = ?""",
                    ("closed", cttissue),
                )
            else:
                print(
                    "This node is a sibling to another issue. Closing issue, but not resuming."
                )
                cur.execute(
                    """UPDATE siblings SET status = ? WHERE cttissue = ?""",
                    ("closed", cttissue),
                )
                cur.execute(
                    """UPDATE issues SET status = ? WHERE cttissue = ?""",
                    ("closed", cttissue),
                )

        nodes2resume = set(nodes2resumeA).intersection(nodes2resumeB)

    if (
        issue_deleted_check(cttissue) is False
        and issue_exists_check(cttissue) is True
        and check_for_siblings(cttissue) is True
    ):
        node = get_hostname(cttissue)
        node = "".join(node)
        allnodes = resolve_siblings(node)
        nodes2resume = []
        nodes2resumeA = []
        nodes2resumeB = []
        con = SQL.connect("ctt.sqlite")
        for sibnode in allnodes:
            with con:
                cur = con.cursor()
                cur.execute(
                    """SELECT rowid FROM siblings WHERE sibling = ? and status = ? and cttissue != ?""",
                    (
                        sibnode,
                        "open",
                        cttissue,
                    ),
                )
                data = cur.fetchone()
                if data is None:
                    nodes2resumeA.append(sibnode)
                else:
                    print(
                        "%s is a sibling for another issue. No nodes will be resumed, but issue will be closed."
                        % (sibnode)
                    )
                    cur.execute(
                        """UPDATE siblings SET status = ? WHERE cttissue = ?""",
                        ("closed", cttissue),
                    )
                    cur.execute(
                        """UPDATE issues SET status = ? WHERE cttissue = ?""",
                        ("closed", cttissue),
                    )

            with con:
                cur = con.cursor()
                cur.execute(
                    """SELECT rowid FROM issues WHERE cttissue != ? and status = ? and hostname = ?""",
                    (
                        cttissue,
                        "open",
                        sibnode,
                    ),
                )
                data = cur.fetchone()
                if data is None:
                    nodes2resumeB.append(sibnode)
                else:
                    print("Can not resume %s. Sibnode has another issue." % (sibnode))

    with con:
        cur = con.cursor()
        cur.execute(
            """UPDATE siblings SET status = ? WHERE cttissue = ?""",
            ("closed", cttissue),
        )
        cur.execute(
            """UPDATE issues SET status = ? WHERE cttissue = ?""",
            ("closed", cttissue),
        )

    nodes2resume = set(nodes2resumeA).intersection(nodes2resumeB)

    if pbs_enforcement == "True":
        pbs_resume(cttissue, date, updatedby, nodes2resume)
    else:
        print("pbs_enforcement is False. Not resuming nodes")


def check_for_siblings(cttissue):
    con = SQL.connect("ctt.sqlite")
    with con:
        cur = con.cursor()
        cur.execute(
            """SELECT * from siblings WHERE cttissue = ? and status = ?""",
            (
                cttissue,
                "open",
            ),
        )
        if cur.fetchone() is None:
            return False  # no siblings
        else:
            return True  # has siblings


def assign_issue(cttissue, assignto):
    if assignto not in (config.get("users", "teams").split(" ")):
        print("%s not a valid group, Exiting!" % (assignto))
        sys.exit(1)
    if issue_deleted_check(cttissue) is False and issue_exists_check(cttissue) is True:
        con = SQL.connect("ctt.sqlite")
        with con:
            cur = con.cursor()
            cur.execute(
                """UPDATE issues SET assignedto = ? WHERE cttissue = ?""",
                (assignto, cttissue),
            )
    else:
        print("Issue %s not found or deleted" % (cttissue))


def get_new_cttissue():
    con = SQL.connect("ctt.sqlite")
    with con:
        cur = con.cursor()
        cur.execute("""SELECT * FROM issues ORDER BY rowid DESC LIMIT 1""")
        for row in cur:
            return int(row[1]) + 1


def new_issue(
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
):
    cttissue = get_new_cttissue()
    print("Issue %s opened" % (cttissue))
    con = SQL.connect("ctt.sqlite")
    with con:
        cur = con.cursor()
        cur.execute(
            """INSERT INTO issues(
        cttissue,date,severity,ticket,status,
                cluster,hostname,issuetitle,issuedescription,assignedto,
                issueoriginator,updatedby,issuetype,state,updatedtime,xticket)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                cttissue,
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
                xticket,
            ),
        )

    view_tracker_new(cttissue, UserGroup, viewnotices)

    if pbs_enforcement == "True":
        nodes2drain = hostname.split(" ")
        pbs_drain(cttissue, date, updatedby, nodes2drain)
    else:
        print("pbs_enforcement is False. Not draining nodes")

    return cttissue  # for log_history


def checkdb(date):
    cttissuestart = 1000
    con = SQL.connect("ctt.sqlite")
    with con:
        cur = con.cursor()
        cur.execute(
            '''SELECT name FROM sqlite_master WHERE type="table" AND name="issues"'''
        )
        if cur.fetchone() is None:
            cur.execute(
                """CREATE TABLE IF NOT EXISTS issues(
            id INTEGER PRIMARY KEY,
            cttissue TEXT NOT NULL,
            date TEXT NOT NULL,
            severity INT NOT NULL,
            ticket TEXT,
            status TEXT NOT NULL,
            cluster TEXT NOT NULL,
            hostname TEXT NOT NULL,
            issuetitle TEXT NOT NULL,
            issuedescription TEXT NOT NULL,
            assignedto TEXT,
            issueoriginator TEXT NOT NULL,
            updatedby TEXT NOT NULL,
                    issuetype TEXT NOT NULL,
                    state TEXT,
                    updatedtime TEXT,
                    viewtracker TEXT,
            xticket TEXT)"""
            )

            # Set first row in issues table
            cur.execute(
                """INSERT INTO issues(
            cttissue,date,severity,ticket,status,
            cluster,hostname,issuetitle,issuedescription,assignedto,
            issueoriginator,updatedby,issuetype,state,updatedtime,viewtracker,xticket)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    cttissuestart,
                    date,
                    99,
                    "---",
                    "---",
                    "---",
                    "---",
                    "---",
                    "Created table",
                    "---",
                    "---",
                    "---",
                    "---",
                    "---",
                    "---",
                    "---",
                    "---",
                ),
            )

    with con:
        cur = con.cursor()
        cur.execute(
            """CREATE TABLE IF NOT EXISTS comments(
                id INTEGER PRIMARY KEY,
                cttissue TEXT NOT NULL,
                date TEXT NOT NULL,
                updatedby TEXT NOT NULL,
                comment TEXT NOT NULL)"""
        )

    with con:
        cur = con.cursor()
        cur.execute(
            """CREATE TABLE IF NOT EXISTS history(
                id INTEGER PRIMARY KEY,
        cttissue TEXT NOT NULL,
        date TEXT NOT NULL,
                updatedby TEXT NOT NULL,
        info TEXT)"""
        )

    with con:
        cur = con.cursor()  # 1 | 1241 | open | r1i5n24 | r1i5n10 | down
        cur.execute(
            """CREATE TABLE IF NOT EXISTS siblings(
                id INTEGER PRIMARY KEY,
                cttissue TEXT NOT NULL,
                date TEXT NOT NULL,
                status TEXT NOT NULL,
                parent TEXT NOT NULL,
                sibling TEXT NOT NULL,
        state TEXT)"""
        )

    with con:
        cur = con.cursor()
        cur.execute(
            """CREATE TABLE IF NOT EXISTS holdback(
                id INTEGER PRIMARY KEY,
                hostname TEXT NOT NULL,
                state TEXT NOT NULL)"""
        )


class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
