#!usr/bin/env python3
import datetime
import ntpath
import os
import shutil
import sys
from configparser import ConfigParser
import logging

import extraview
import slack
import cluster
from ClusterShell.NodeSet import NodeSet

import ctt.db

class CTTException(Exception):
    pass

class IssueNotFoundException(CTTException):
    pass

class TicketNotFoundException(CTTException):
    pass


class _bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def get_config(configFile="conf/ctt.ini", secretsFile="conf/secrets.ini"):
    parser = ConfigParser()
    parser.read(configFile)
    parser.read(secretsFile)
    return parser

class CTT:
    def __init__(self, conf):
        self.db = ctt.db.DB(conf['db'])
        self.ev = extraview.Extraview(conf['ev'])
        self.cluster = cluster.get_cluster(conf["cluster"])
        self.default_sev = conf['ctt']['default_sev']
        self.default_assignee = conf['ctt']['default_assignee']

    def drain_blades(self, nodes: NodeSet):
        """
        starts draining a set of blades
        input: a clush nodeset str, will drain all nodes and their siblings
        """
        logging.debug(f'Draining blades: {nodes}')
        nodeset = NodeSet(nodes)
        for node in nodes:
            nodeset.update(self.cluster.siblings(node))
        self.cluster.drain(nodeset)

    def drain_nodes(self, nodes: NodeSet):
        """
        starts draining a set of nodes, DOES NOT drain entire blades, use drain_blades for that
        input: a clush nodeset str of nodes to be drained
        """
        logging.debug(f'Draining nodes: {nodes}')
        self.cluster.drain(nodes)

    def release_siblings(self, cttissue: int):
        """
        nodes who can be released if they have no open issues, along with their siblings
        input: a clush nodeset str of nodes that should be checked for release
        """
        logging.debug(f'Releasing siblings for issue: {cttissue}')
        to_release = NodeSet()
        issue = self.db.issue(cttissue)
        if issue is None:
            raise IssueNotFoundException
        for node in issue.nodes:
            if node.sibling_state == "online":
                # can't relase nodes that are already online
                continue
            for sib in self.cluster.siblings(node.name):
                sib_node = self.db.node(sib)
                if sib_node is None or sib_node.issues is None:
                    to_release.update(sib)
            node.sibling_state = "online"
        self.cluster.resume(to_release)
        self.db.update()

    def ticket_close(self, cttissue: int, comment: str):
        logging.debug(f'closing ticket for {cttissue}')
        issue = self.db.issue(cttissue)
        if issue is None:
            raise IssueNotFoundException
        if issue.ticket is None:
            raise TicketNotFoundException
        self.ev.close(issue.ticket, comment)
        issue.ticket = None
        self.db.update()

    def ticket_open(self, cttissue: int, sev: int, nodes: str, title: str, description: str):
        # TODO document magic strings
        logging.debug(f'opening ticket for {cttissue}')
        issue = self.db.issue(cttissue)
        if issue is None:
            raise IssueNotFoundException
        if issue.ticket is not None:
            self.ev.update(issue.ticket, {sev, nodes, title, description})
        else:
            ticket_id = self.ev.create("ssgev", "ssg", None, "CTT Issue: {}: {}: {}".format(self.cluster.name().capitalize(), nodes, title), "CTT issue: {}, Sev: {}, Hosts: {}, Title: {}, Description: {}".format(cttissue, sev, nodes, title, description), {
                "HELP_LOCATION": self.ev.get_field_value_to_field_key("HELP_LOCATION", "NWSC"),
                "HELP_HOSTNAME": self.ev.get_field_value_to_field_key(
                    "HELP_HOSTNAME", ""),
                "HELP_HOSTNAME_CATEGORY": ev.get_field_value_to_field_key(
                    "HELP_HOSTNAME_CATEGORY", "Supercomputer"
                ),
                "HELP_HOSTNAME_OTHER": issue.cluster,
            },

            )
            issue.ticket = ticket_id
            self.db.update()

        return issue.ticket

    def issue_list(self, **kwargs):
        """
        list all issues that fit the given state
        """
        logging.debug('listing issues')
        return self.db.get_issues(**kwargs)

    def issue_show(self, cttissue: int):
        logging.debug(f'showing issue details for: {cttissue}')
        return self.db.issue(cttissue)

    def open(self, issue: ctt.db.Issue) -> int:
        """Open an issue and return its issue number"""
        nodeset = NodeSet()
        for n in issue.nodes:
            nodeset.update(n.name)
        self.drain_nodes(issue.nodes)
        issue.node_state = ctt.db.NodeState.DRAINING
        if not issue.severity:
            issue.severity = self.default_sev
        if not issue.assigned_to:
            issue.assigned_to = self.default_assignee
        issue.status = ctt.db.IssueStatus.OPEN
        return self.db.new_issue(issue)


def issue_open(args):
    logging.debug('opening issue')
    db = ctt.db.DB(conf)

    issue = db.new_issue(
        datetime.datetime.now().isoformat(),
        args.severity,
        args.ticket,
        "open",
        args.cluster,
        node,
        args.title,
        args.description,
        conf["DEFAULTS"]["assignedto"],
        os.environ.get("SUDO_USER"),
        os.environ.get("SUDO_USER"),
        conf["DEFAULTS"]["issuetype"],
        "unknown",
        datetime.datetime.now().isoformat(),
        os.environ.get("SUDO_USER"),
        conf.get("users", "teams").split(" "),
        args.xticket,
    )

    if args.type == "h" and not args.noev:
        evopen(args)


def issue_update(args, conf):
    logging.debug('updating issues')
    for cttissue in args.issue:
        db = ctt.db.DB(conf)
        issue = db.issue(cttissue)
        if issue is None:
            print("Issue does not exist")
            exit(1)
        if args.type:
            issue.type = args.type
            if (
                "h" in args.type and not args.noev
            ):  # move this statement up under if for h!
                if issue.ticket is not None:
                    ev_id = _open_ev(issue, conf.get("cluster", "name"))
                    issue.ticket = ev_id
        if args.title:
            issue.title = args.title
        if args.description:
            issue.description = args.description
        if args.severity:
            issue.severity = args.severity
        if args.node:
            issue.hostname = args.node
        if args.assign:
            issue.assignedto = args.assign

            if not args.noev:
                if issue.ticket is not None:
                    _assign_ev(issue, issue.assignedto)
                    db.log_history(
                        cttissue,
                        datetime.datetime.now().isoformat(),
                        os.environ.get("SUDO_USER"),
                        "Assigned EV ticket to %s" % (issue.assignedto),
                    )
            else:
                print("extraview_enabled is False. Can't assign EV")
        if args.ticket:
            issue.ticket = args.ticket
        if args.xticket:
            issue.xticket = args.xticket
        db.update()


def comment(args, conf):
    db = ctt.db.DB(conf)
    for cttissue in args.issue:
        db.comment_issue(
            cttissue,
            args.user,
            args.comment,
        )
        if not args.noev:
            issue = db.issue(cttissue)
            if issue is not None and issue.ticket is not None:
                ev.add_resolver_comment(
                    issue.ticket, "CTT Comment:\n%s" % (args.comment)
                )
                print("ev %s updated with '%s'" % (issue.ticket, args.comment))


def issue_close(args, conf):
    logging.debug('closing issue')
    db = ctt.db.DB(conf)
    for cttissue in args.issue:
        comment(cttissue, args)
        issue = db.issue(cttissue)
        if issue is None:
            print("Issue {} does not exist".format(cttissue))
            continue
        node = issue.hostname
        if node is None:
            print("Issue %s is not open" % (cttissue))
            continue
        node = "".join(node)

        if not issue:
            print("issue not found")
            return
        if issue.status != "open":
            print("issue status is {}, can't close".format(issue.status))
            return
        issue.status = "closed"

        if args.pbs is True:
            pbs.resume(issue.host)
            issue.comment.append("{} resumed node {}".format(args.user, issue.host))
        else:
            print("pbs_enforcement is False. Not resuming nodes")
        issue.update()

        evclose(args)

        if args.slack is True:
            slack_message = "Issue %s for %s: %s closed by %s\n%s" % (
                cttissue,
                conf["cluster"]["name"],
                node,
                os.environ.get("SUDO_USER"),
                args.comment,
            )
            sclient = slack.Slack(conf)
            sclient.send_slack(slack_message)


def stats(args, conf):
    db = ctt.db.DB(conf)
    for node in args.node:
        print(db.node_issues(node))

def reopen(args, conf):
    db = ctt.db.DB(conf)
    for cttissue in args.issue:
        issue = db.issue(cttissue)
        if issue is None:
            print("Issue {} doesn't exist".format(cttissue))
            continue

        db.comment_issue(
            cttissue,
            os.environ.get("SUDO_USER"),
            args.comment,
        )
        issue.status = ctt.db.Status.OPEN
        db.update()
        if conf["pbs"]["enforcement"] == "False":
            print("pbs_enforcement is False. Not draining nodes")
        else:
            pbs.drain(
                cttissue,
                os.environ.get("SUDO_USER"),
                issue.host,
            )

        if not args.noev:
            if issue.ticket is not None:
                ev.open(issue.ticket, "CTT Comment:\n%s" % (issue.comment))
                print("ev %s reopened" % (issue.ticket))
        else:
            print("extraview_enabled is False. Can't close EV")

def attach(args, conf):
    db = ctt.db.dB(conf)
    for issue in args.issue:
        _create_attachment(
            issue,
            args.filepath,
            conf["DEFAULTS"]["attach_location"],
            datetime.datetime.now().isoformat(),
            os.environ.get("SUDO_USER"),
            db,
        )
        filename = ntpath.basename(args.filepath)
        db.comment_issue(
            issue,
            datetime.datetime.now().isoformat(),
            os.environ.get("SUDO_USER"),
            "Attached file: %s/%s/%s.%s"
            % (
                conf["DEFAULTS"]["attach_location"],
                issue,
                datetime.datetime.now().isoformat()[0:16],
                filename,
            ),
        )

def _assign_ev(issue, assignto):
    """assign ev to group"""
    ev.assign_group(
        issue.ticket,
        assignto,
        None,
        {
            "COMMENTS": """
        CTT issue number {} assigned to {}.
        """.format(
                issue.cttissue, assignto
            )
        },
    )


def _open_ev(issue, cluster):
    """open ev ticket"""
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
    ev_id = ev.create(
        "ssgev",
        "ssg",
        None,
        "CTT Issue: %s: %s: %s " % (cluster.capitalize(), issue.hostname, issue.title),
        "%s" % (issue_data_formatted),
        {
            "HELP_LOCATION": ev.get_field_value_to_field_key("HELP_LOCATION", "NWSC"),
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


def _create_attachment(cttissue, filepath, attach_location, date, updatedby, db):
    if os.path.isfile(filepath) is False:
        print("File %s does not exist, Exiting!" % (filepath))
        exit(1)
    if os.path.exists(attach_location) is False:
        print(
            "Attachment root location does not exist. Check ctt.ini attach_location setting"
        )
        exit(1)
    if db.issue(cttissue) is None:
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
