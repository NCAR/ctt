#!/usr/bin/env python3
import argparse
import datetime
import grp
import ntpath
import os
import sys
from syslog import syslog

import config
import slack

import os
import shutil
import sys
import textwrap

import db
import extraview
import pbs
import slack
from cluster import casper as cluster

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

def release(args, conf):
    date = datetime.datetime.now().isoformat()
    db = db.DB(config)
    for node in args.node:
        cttissue = args.issue
        issue = db.issue(cttissue)
        if not issue:
            print("Error: Issue not found")
        elif issue.hostname == cttissue:
            print(
                "Error: Issue is for this node, can only release siblings from a ticket"
            )
        else:
            db.release_sib(cttissue, node)

        if not db.in_other_open_issue(cttissue, node) and config.getboolean("pbs", "enabled"):
            print("Resuming node")
            pbs.resume(cttissue, date, self.user, node)
            db.log_history(issue, date, self.user, "ctt resumed %s" % (node))

def holdback(args, config):
    db = db.DB(config)
    db.update_holdback(node, state)


def evclose(args, config):
    ev_comment = args.comment
    for cttissue in args.issue:
        if not args.noev:
            db = db.DB(config)
            issue = db.issue(cttissue)
            if issue is not None and issue.ticket is not None:
                ev.close(issue.ticket, "CTT Comment:\n%s" % (ev_comment)):
                print("ev %s closed" % (issue.ticket))
                issue.ticket = None
                issue.update(db)
            else:
                print("There is no EV ticket attached to %s, Exiting!" % (cttissue))
                sys.exit(1)
        else:
            print("extraview_enabled is False. Can't close EV")


def evopen(args, config):
    for cttissue in args.issue:
        if not args.noev:
            db = db.DB(config)
            issue = db.issue(cttissue)
            if issue is not None and issue.ticket is not None:
                ev_id = _open_ev(issue, config.get("cluster", "name"))
                issue.ticket = ev_id
                issue.assignedto = config["ev"]["assignedto"]
                _assign_ev(issue, issue.assignto)
                print("EV %s opened for CTT issue %s" % (ev_id, cttissue))
                issue.update(db)
            else:
                print("There is already an EV ticket attached to this issue.")
        else:
            print("extraview_enabled is False. Can't open EV")


def attach(args, conf):
    db = DB.db(conf)
    for issue in args.issue:
        _create_attachment(
            issue,
            args.filepath,
            conf["DEFAULTS"]["attach_location"],
            datetime.datetime.now().isoformat(),
            os.environ.get("SUDO_USER"),
            db
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


def listcmd(args):
    if args.verbose == 1:
        cttlib.get_issues_v(args.status)
    if args.vverbosevalue > 1:
        cttlib.get_issues_vv(args.status)
    else:
        cttlib.get_issues(args.status)


def show(args, conf):
    db = db.DB(config)
    for issue in args.issue:
        _get_issue_full(args.issue, db)
        if args.d is True:
            db.get_history(cttissue)
        )


def update(args, config):
    for cttissue in args.issue:
        db = db.DB(config)
        issue = db.issue(cttissue)
        if issue is None:
            print("Issue does not exist")
            exit(1)
        if args.type:
            issue.type = args.type
            if args.type == "h!":  # add ev function here for h!
                cttlib.add_siblings(
                    cttissue,
                    datetime.datetime.now().isoformat(),
                    os.environ.get("SUDO_USER"),
                )
            if (
                "h" in args.type and not args.noev
            ):  # move this statement up under if for h!
                if issue.ticket is not None:
                    ev_id = _open_ev(issue, config.get("cluster", "name"))
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

        issue.update(db)

def comment(args, config):
    for cttissue in args.issue:
        db.comment_issue(
            cttissue,
            datetime.datetime.now().isoformat(),
            updatedby,
            args.comment,
        )
        if not args.noev:
            db = db.DB(config)
            issue = db.issue(cttissue)
            if is issue is not None and issue.ticket is not None:
                ev.add_resolver_comment(issue.ticket, "CTT Comment:\n%s" % (args.comment))
                print("ev %s updated with '%s'" % (issue.ticket, args.comment))


def close(args, config):
    for cttissue in args.issue:
        _comment(cttissue, args)
        db = db.DB(config)
        issue = db.issue(cttissue)
        if issue is None:
            print("Issue {} does not exist".format(cttissue))
            continue
        node = issue.hostname
        if node is None:
            print("Issue %s is not open" % (cttissue))
            continue
        node = "".join(node)
        if cttlib.check_holdback(node) is not False:
            answer = input(
                "\n%s is in holdback state. Are you sure you want to release this node and close issue? [y|n]: "
                % (node)
            )
            answer = answer.lower()
            if answer == "n":
                continue
            elif answer == "y":
                db = db.DB(config)
                db.update_holdback(node, "remove")
                next
            else:
                sys.exit(1)

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

        evclose(args)

        if config["slack"]["enabled"] == "True":
            slack_message = "Issue %s for %s: %s closed by %s\n%s" % (
                cttissue,
                config["cluster"]["name"],
                node,
                os.environ.get("SUDO_USER"),
                args.comment,
            )
            sclient = slack.Slack(config)
            sclient.send_slack(slack_message)


def reopen(args, conf):
    for cttissue in args.issue:
        db = db.DB(config)
        cttlib.test_arg_size(args.comment, what="comment", maxchars=500)
        db.comment_issue(
            cttissue,
            datetime.datetime.now().isoformat(),
            os.environ.get("SUDO_USER"),
            args.comment,
        )
        cttlib.update_field(cttissue, "status", "open")
        if conf["pbs"]["enforcement"] == "False":
            print("pbs_enforcement is False. Not draining nodes")
        else:
            cttlib.pbs_drain(
                cttissue,
                datetime.datetime.now().isoformat(),
                os.environ.get("SUDO_USER"),
                db.issue(cttissue).hostname,
            )

        if not args.noev:
            issue = db.issue(cttissue)
            if issue is not None and issue.ticket is not None:
                ev.open(issue.ticket, "CTT Comment:\n%s" % (ev_comment))
                print("ev %s reopened" % (issue.ticket))

                assignto = cttlib.get_issue_data(cttissue)[9]
                _assign_ev(issue, assignto)
        else:
            print("extraview_enabled is False. Can't close EV")


def opencmd(args, conf):
    if conf["DEFAULTS"]["strict_node_match"] == "False":
        return
    if args.node not in conf["DEFAULTS"]["strict_node_match"]:
        print("Can not find %s in strict_node_match, Exiting!" % (args.node))
        sys.exit(1)
    db = DB.db(conf)

    for node in args.node:
        cttlib.test_arg_size(args.title, what="issue title", maxchars=100)
        cttlib.test_arg_size(args.description, what="issue description", maxchars=4000)
        cttissue = db.new_issue(
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
            _authorized_team(
                os.environ.get("SUDO_USER"), conf.get("users", "teams").split(" ")
            ),
            args.xticket,
        )
        db.log_history(
            cttissue,
            datetime.datetime.now().isoformat(),
            os.environ.get("SUDO_USER"),
            "new issue",
        )

        if args.type == "h" and not args.noev:
            evopen(args)

def stats(args):
    if args.counts:
        cttlib.run_stats_counts()
    if args.node:
        cttlib.run_stats_node(args.node)


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
                cttissue, assignto
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
        "CTT Issue: %s: %s: %s "
        % (cluster.capitalize(), issue.hostname, issue.title),
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


def _get_issue_full(cttissue, db):  # used for the --show option
    # TODO make this the default print for Issue in db
    issue = db.issue(cttissue)
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
    if issue.type == "s":
        issuetype = "software"
    elif issue.type == "h":
        issuetype = "hardware"
    elif issue.type == "o":
        issuetype = "other"
    elif issue.type == "t":
        issuetype = "test"
    else:
        issuetype="unknown"
    print("Type: %s" % (issuetype))
    print("Cluster: %s" % (issue.cluster))
    print("Hostname: %s" % (issue.hostname))
    print("Node State: %s" % (issue.state))
    print("----------------------------------------")
    print("\nIssue Title:\n%s" % (issue.title))
    print("\nIssue Description:")
    print(textwrap.fill(issue.description, width=60))
    print("\n----------------------------------------")
    comments = db.get_comments(issue.cttissue)
    for c in comments:
        print("\nComment by: %s at %s" % (c[0], c[1]))
        print(textwrap.fill(c[2], width=60))

        print("created issue {}".format(issue.cttissue))

        if pbs_enforcement == "True":
            nodes2drain = issue.hostname.split(" ")
            pbs_drain(cttissue, date, updatedby, nodes2drain)
        else:
            print("pbs_enforcement is False. Not draining nodes")

        return issue.cttissue

def _log_touch(self, issue, msg, when, db):
    if issue:
        issue.updatedby = self.user
        issue.updatedtime = when
    db.log_history(issue, when, self.user, msg)
