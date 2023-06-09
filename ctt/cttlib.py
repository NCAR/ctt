import os
import shutil
import sys
import textwrap

import db
import extraview
import pbs
import slack
from cluster import casper as cluster


class CTT:
    def __init__(self, config):
        self.user = config.get("user", "user")
        self.group = config.get("user", "group")
        self.teams = config.get("users", "teams").split(" ")
        self.pbs_enforcement = config.get("pbs", "enabled")
        self.slack_enabled = config.getboolean("slack", "enabled")
        self.cluster = config.get("cluster", "name")
        self.ev = extraview.Client(config)
        self.slack = slack.Slack(config)
        self.db = db.DB(config)

    def release(self, cttissue, date, node):
        issue = self.db.issue(cttissue)
        if not issue:
            print("Error: Issue not found")
        elif issue.hostname == cttissue:
            print(
                "Error: Issue is for this node, can only release siblings from a ticket"
            )
        else:
            self.db.release_sib(cttissue, node)
            self.log_touch(
                issue, "Released node {} cttissue: {}".format(node, cttissue), date
            )

        if not self.db.in_other_open_issue(cttissue, node) and self.pbs_enforcement:
            print("Resuming node")
            pbs.resume(cttissue, date, self.user, node)
            self.log_history(issue, date, self.user, "ctt resumed %s" % (node))

    def update_holdback(node, state):
        self.db.update_holdback(node, state)

    def assign_ev(cttissue, assignto):
        """assign ev to group"""
        issue = self.db.issue(cttissue)
        ev.assign_group(
            issue.ticket,
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

    def open_ev(cttissue):
        """open ev ticket"""
        issue = self.db.issue(cttissue)
        issue_data_formatted = (
            "CTT issue: %s\nCTT Severity: %s\nHostname: %s\nIssue Title: %s\nIssue Description: %s"
            % (
                issue.cttissue,
                issue.severity,
                issue.hostname,
                issue.title,
                issue.description,
            )
        )
        global ev
        ev_id = ev.create(
            "ssgev",
            "ssg",
            None,
            "CTT Issue: %s: %s: %s "
            % (self.cluster.capitalize(), issue.hostname, issue.title),
            "%s" % (issue_data_formatted),
            {
                "HELP_LOCATION": ev.get_field_value_to_field_key(
                    "HELP_LOCATION", "NWSC"
                ),
                "HELP_HOSTNAME": ev.get_field_value_to_field_key(
                    "HELP_HOSTNAME", issue.ticket.capitalize()
                ),
                "HELP_HOSTNAME_CATEGORY": ev.get_field_value_to_field_key(
                    "HELP_HOSTNAME_CATEGORY", "Supercomputer"
                ),
                "HELP_HOSTNAME_OTHER": issue.cluster,
            },
        )
        return ev_id

    def comment_ev(cttissue, ev_comment):
        """comment on an open ev ticket"""
        ticket = self.db.get_ticket(cttissue)
        ev.add_resolver_comment(ticket, "CTT Comment:\n%s" % (ev_comment))
        print("ev %s updated with '%s'" % (ticket, ev_comment))

    def close_ev(cttissue, ev_comment):
        """close ev ticket"""
        ticket = self.db.get_ticket(cttissue)
        ev.close(ticket, "CTT Comment:\n%s" % (ev_comment))
        print("ev %s closed" % (ticket))

    def reopen_ev(cttissue, ev_comment):
        """reopen ev ticket"""
        ticket = self.db.get_ticket(cttissue)
        ev.open(ticket, "CTT Comment:\n%s" % (ev_comment))
        print("ev %s reopened" % (ticket))

    def create_attachment(cttissue, filepath, attach_location, date, updatedby):
        if os.path.isfile(filepath) is False:
            print("File %s does not exist, Exiting!" % (filepath))
            exit(1)
        if os.path.exists(attach_location) is False:
            print(
                "Attachment root location does not exist. Check ctt.ini attach_location setting"
            )
            exit(1)
        if issue_exists_check(cttissue) is False:
            print(
                "Issue %s is not open. Can not attach a file to a closed, deleted, or nonexisting issue"
                % (cttissue)
            )
            exit(1)
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

    def transient_errors_check(node, date, updatedby):  # jon
        if self.db.is_primary(node) and transient_errors_enabled == "True":
            cttissue = self.db.cttissue(node)
            issue = self.db.issue(cttissue)
            transient_errors_list = transient_errors.split(", ")
            for item in transient_errors_list:
                if item in issue.title:
                    close_issue(cttissue, date, updatedby)
                    closemessage = "Transient error: %s" % (item)
                    if slack_enabled == "True":
                        self.slack.send_slack(
                            "Issue %s for %s: %s closed by ctt\n%s"
                            % (cttissue, cluster, node, closemessage)
                        )
                    self.log_history(
                        cttissue, date, "ctt", "Closed issue %s" % (closemessage)
                    )

    def test_arg_size(arg, what, maxchars):
        size = sys.getsizeof(arg)
        if int(size) > int(maxchars):
            print(
                "Maximum argument size of %s characters reached for %s. Exiting!"
                % (maxchars, what)
            )
            exit(1)

    def check_for_ticket(cttissue):
        issue = self.db.issue(cttissue)
        return issue is not None and issue.ticket != "---"

    def update_ticket(cttissue, ticketvalue):
        issue = self.db.issue(cttissue)
        if issue is not None:
            issue.ticket = ticketvalue
            issue.update()

    def update_xticket(cttissue, xticketvalue):
        issue = self.db.issue(cttissue)
        if issue is not None:
            issue.xticket = xticketvalue
            issue.update()

    def view_tracker_new(self, issue, UserGroup):
        teams = self.teams
        if self.group in teams:
            teams.remove(self.group)
            issue.viewtracker = teams
            issue.update()

    def view_tracker_update(
        cttissue, UserGroup
    ):  # used to update viewtracker column when a user runs --show
        issue = self.db.issue(cttissue)
        viewtracker = issue.viewtracker.split(".")
        if UserGroup in viewtracker:
            viewtracker.remove(UserGroup)
        if viewtracker:
            viewtracker = ".".join(viewtracker)
        issue.viewtracker = viewtracker
        issue.update()

    def get_hostname(cttissue):
        issue = self.db.issue(cttissue)
        if issue:
            return issue.hostname
        else:
            return None

    def check_node_state(
        node, state
    ):  # checks if node has open issue, returns cttissue number
        issue = self.db.node_issue(node)
        if issue:
            return issue.cttissue
        else:
            return None

    def get_history(cttissue):  # used only when issuing --show with -d option
        return self.db.get_history(cttissue)

    def log_history(self, issue, date, updatedby, info):
        self.db.log_history(issue.cttissue, date, updatedby, info)

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
        issue = self.db.issue(cttissue)
        if issue is None:
            print("Issue not found")
            return
        print("CTT Issue: %s" % (issue.cttissue))
        print("ev Ticket: %s" % (issue.ticket))
        print("External Ticket: %s" % (issue.xticket))
        print("Date Opened: %s" % (issue.date))
        print("Assigned To: %s" % (issue.assignedto))
        print("Issue Originator: %s" % (issue.originator))
        print("Last Updated By: %s" % (issue.updatedby))
        print("Last Update Time: %s" % (issue.updatedtime))
        print("Severity: %s" % (issue.severity))
        print("Status: %s" % (issue.status))
        print("Type: %s" % (conv_issuetype(issue.type)))
        print("Cluster: %s" % (issue.cluster))
        print("Hostname: %s" % (issue.hostname))
        print("Node State: %s" % (issue.state))
        print("----------------------------------------")
        print("\nIssue Title:\n%s" % (issue.title))
        print("\nIssue Description:")
        print(textwrap.fill(issue.description, width=60))
        print("\n----------------------------------------")
        get_comments(issue.cttissue)

    def get_comments(cttissue):  # used for --show option (displays the comments)
        comments = self.db.get_comments(cttissue)
        for c in comments:
            print("\nComment by: %s at %s" % (c[0], c[1]))
            print(textwrap.fill(c[2], width=60))

    def comment_issue(cttissue, date, updatedby, newcomment, UserGroup):
        self.db.comment_issue(cttissue, date, updatedby, newcomment)
        self.view_tracker_new(cttissue, UserGroup)

    def issue_exists_check(cttissue):
        issue = self.db.issue(cttissue)
        return issue is None

    def get_issues(statustype):  # used for the --list option
        cols = "{0:<8}{1:<19}{2:<12}{3:<13}{4:<16}{5:<6}{6:<12}{7:<11}{8:<12}{9:<28}"
        fmt = cols.format
        print(
            fmt(
                "ISSUE",
                "DATE",
                "ev TICKET",
                "HOSTNAME",
                "STATE",
                "Sev",
                "TYPE",
                "ASSIGNED",
                "UNSEEN",
                "TITLE (25 chars)",
            )
        )
        issues = self.db.get_issues(statustype)
        for i in issues:
            issue_str = fmt(
                "%s" % i.cttissue,
                "%s" % i.date,
                "%s" % i.ticket,
                "%s" % i.hostname,
                "%s" % i.state,
                "%s" % i.severity,
                "%s" % i.type,
                "%s" % i.assignedto,
                "%s" % i.viewtracker,
                "%s" % i.title,
            )
            if i.severity == 1:
                print(bcolors.FAIL + issue_str + bcolors.ENDC)
            else:
                print(issue_str)

    def delete_issue(cttissue):
        issue = self.db.issue(cttissue)
        if issue:
            issue.status = "deleted"
            issue.update()

    def close_issue(cttissue, date, updatedby):
        issue = self.db.issue(cttissue)
        if not issue:
            print("issue not found")
            return
        if issue.status != "open":
            print("issue status is {}, can't close".format(issue.status))
            return
        issue.status = "closed"

        if pbs_enforcement == "True":
            pbs_resume(cttissue, date, updatedby, issue.hostname)
        else:
            print("pbs_enforcement is False. Not resuming nodes")
        issue.update()

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
        issue = self.db.new_issue(
            {
                "date": date,
                "severity": severity,
                "ticket": ticket,
                "status": status,
                "hostname": hostname,
                "title": issuetitle,
                "description": issuedescription,
                "assignedto": assignedto,
                "originator": issueoriginator,
                "updatedby": updatedby,
                "type": type,
                "state": state,
                "updatedtime": updatedtime,
                "xticket": xticket,
            }
        )

        print("created issue {}".format(issue.cttissue))

        self.view_tracker_new(issue.cttissue, UserGroup)

        if pbs_enforcement == "True":
            nodes2drain = issue.hostname.split(" ")
            pbs_drain(cttissue, date, updatedby, nodes2drain)
        else:
            print("pbs_enforcement is False. Not draining nodes")

        return issue.cttissue

    def log_touch(self, issue, msg, when):
        if issue:
            issue.updatedby = self.user
            issue.updatedtime = when
        self.view_tracker_new(issue, self.group)
        self.log_history(issue, when, self.user, msg)


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
