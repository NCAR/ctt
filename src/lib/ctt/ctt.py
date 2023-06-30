#!usr/bin/env python3
import logging
from configparser import ConfigParser

import cluster
import extraview
from ClusterShell.NodeSet import NodeSet

import ctt.db


class CTTException(Exception):
    pass

class IssueNotFoundException(CTTException):
    pass

class TicketNotFoundException(CTTException):
    pass

def get_config(configFile="conf/ctt.ini", secretsFile="conf/secrets.ini"):
    parser = ConfigParser()
    parser.read(configFile)
    parser.read(secretsFile)
    return parser

class CTT:
    def __init__(self, conf):
        self.db = ctt.db.DB(conf['db'])
        self.ticketing = extraview.Extraview(conf['ticketing'])
        self.ticketing_enabled = conf['ticketing']['enabled'] == 'True'
        self.cluster = cluster.get_cluster(conf["cluster"])
        self.cluster_enabled = conf['cluster']['enabled'] == 'True'

    def ticket_close(self, cttissue: int, comment: str) -> None:
        logging.debug(f'closing ticket for {cttissue}')
        if not self.ticketing_enabled:
            logging.debug('ticketing not enabled, nothing to do')
            return
        issue = self.db.issue(cttissue)
        if issue is None:
            raise IssueNotFoundException
        if issue.ticket is None:
            raise TicketNotFoundException
        self.ticketing.close(issue.ticket, comment)
        issue.ticket = None
        self.db.update()

    def ticket_open(self, cttissue: int, sticketing: int, nodes: str, title: str, description: str):
        # TODO document magic strings
        logging.debug(f'opening ticket for {cttissue}')
        if not self.ticketing_enabled:
            logging.debug('ticketing not enabled, nothing to do')
            return None
        issue = self.db.issue(cttissue)
        if issue is None:
            raise IssueNotFoundException
        if issue.ticket is not None:
            self.ticketing.update(issue.ticket, {sticketing, nodes, title, description})
        else:
            ticket_id = self.ticketing.create("ssgticketing", "ssg", None, "CTT Issue: {}: {}: {}".format(self.cluster.name().capitalize(), nodes, title), "CTT issue: {}, Sticketing: {}, Hosts: {}, Title: {}, Description: {}".format(cttissue, sticketing, nodes, title, description), {
                "HELP_LOCATION": self.ticketing.get_field_value_to_field_key("HELP_LOCATION", "NWSC"),
                "HELP_HOSTNAME": self.ticketing.get_field_value_to_field_key(
                    "HELP_HOSTNAME", ""),
                "HELP_HOSTNAME_CATEGORY": self.ticketing.get_field_value_to_field_key(
                    "HELP_HOSTNAME_CATEGORY", "Supercomputer"
                ),
                "HELP_HOSTNAME_OTHER": issue.cluster,
            },

            )
            issue.ticket = ticket_id
            self.db.update()

        return issue.ticket

    def issue_list(self, **kwargs) -> [ctt.db.Issue]:
        """
        list all issues that fit the given state
        """
        logging.debug('listing issues')
        return self.db.get_issues(**kwargs)

    def issue(self, cttissue: int) -> ctt.db.Issue:
        logging.debug(f'showing issue details for: {cttissue}')
        return self.db.issue(cttissue)

    def open(self, issue: ctt.db.Issue) -> int:
        """Open an issue and return its issue number"""
        # TODO check if issue is a duplicate
        if self.cluster_enabled:
            self.cluster.drain(NodeSet(issue.target))
        oldissue = self.db.get_issues(title=issue.title, target=issue.target)
        if oldissue and len(oldissue) != 0:
            oldissue = oldissue[0]
            if oldissue.status != ctt.db.IssueStatus.OPEN:
                oldissue.status = ctt.db.IssueStatus.OPEN
                oldissue.down_siblings = False
                oldissue.comments.append(ctt.db.Comment(created_by=issue.created_by, comment="reopening issue"))
            else:
                #TODO update any fields that are different between old issue and the new one
                pass
            self.db.update()
        else:
            issue.down_siblings = False
            issue.status = ctt.db.IssueStatus.OPEN
            issue.comments.append(ctt.db.Comment(created_by=issue.created_by, comment="opening issue"))
            return self.db.new_issue(issue)

    def close(self, issue: ctt.db.Issue, operator: str, comment: str) -> None:
        if issue.status == ctt.db.IssueStatus.CLOSED:
            logging.warning(f"Issue {issue.id} already closed, skipping")
            return
        issue.comments.append(ctt.db.Comment(created_by=operator, comment=comment))
        issue.comments.append(ctt.db.Comment(created_by=operator, comment="closing issue"))
        issue.status = ctt.db.IssueStatus.CLOSED
        to_resume = NodeSet()
        if issue.down_siblings:
            issue.down_siblings = False
            for n in self.cluster.siblings(issue.target):
                if self.db.get_issues(target=n, state="open") is None:
                    to_resume.update(n)
            if self.db.get_issues(target=issue.target, state="open") is None:
                to_resume.update(issue.target)
        if self.cluster_enabled:
            self.cluster.resume(to_resume)
        self.db.update()




'''
def issue_open(args):
    logging.debug('opening issue')
    db = ctt.db.DB(conf)

    db.new_issue(
        datetime.datetime.now().isoformat(),
        args.sticketingerity,
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

    if args.type == "h" and not args.noticketing:
        ticketingopen(args)


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
                "h" in args.type and not args.noticketing
            ):  # move this statement up under if for h!
                if issue.ticket is not None:
                    ticketing_id = _open_ticketing(issue, conf.get("cluster", "name"))
                    issue.ticket = ticketing_id
        if args.title:
            issue.title = args.title
        if args.description:
            issue.description = args.description
        if args.sticketingerity:
            issue.sticketingerity = args.sticketingerity
        if args.node:
            issue.hostname = args.node
        if args.assign:
            issue.assignedto = args.assign

            if not args.noticketing:
                if issue.ticket is not None:
                    _assign_ticketing(issue, issue.assignedto)
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
        if not args.noticketing:
            issue = db.issue(cttissue)
            if issue is not None and issue.ticket is not None:
                ticketing.add_resolver_comment(
                    issue.ticket, "CTT Comment:\n%s" % (args.comment)
                )
                print("ticketing %s updated with '%s'" % (issue.ticket, args.comment))


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

        ticketingclose(args)

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

        if not args.noticketing:
            if issue.ticket is not None:
                ticketing.open(issue.ticket, "CTT Comment:\n%s" % (issue.comment))
                print("ticketing %s reopened" % (issue.ticket))
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

def _assign_ticketing(issue, assignto):
    """assign ticketing to group"""
    ticketing.assign_group(
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


def _open_ticketing(issue, cluster):
    """open ticketing ticket"""
    issue_data_formatted = (
        "CTT issue: %s\nCTT Sticketingerity: %s\nHostname: %s\nIssue Title: %s\nIssue Description: %s"
        % (
            issue.cttissue,
            issue.sticketingerity,
            issue.hostname,
            issue.title,
            issue.description,
        )
    )
    ticketing_id = ticketing.create(
        "ssgticketing",
        "ssg",
        None,
        "CTT Issue: %s: %s: %s " % (cluster.capitalize(), issue.hostname, issue.title),
        "%s" % (issue_data_formatted),
        {
            "HELP_LOCATION": ticketing.get_field_value_to_field_key("HELP_LOCATION", "NWSC"),
            "HELP_HOSTNAME": ticketing.get_field_value_to_field_key(
                "HELP_HOSTNAME", issue.ticket.capitalize()
            ),
            "HELP_HOSTNAME_CATEGORY": ticketing.get_field_value_to_field_key(
                "HELP_HOSTNAME_CATEGORY", "Supercomputer"
            ),
            "HELP_HOSTNAME_OTHER": issue.cluster,
        },
    )
    return ticketing_id


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
'''
