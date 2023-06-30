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

    def ticket_open(self, cttissue: int):
        # TODO document magic strings
        # TODO does it make sense to be able to open 1 ticket for multiple ctt issues
        # ex: lots of targets have the same issue, so open 1 ticket to track them all?
        logging.debug(f'opening ticket for {cttissue}')
        if not self.ticketing_enabled:
            logging.debug('ticketing not enabled, nothing to do')
            return None
        issue = self.db.issue(cttissue)
        if issue is None:
            raise IssueNotFoundException
        if issue.ticket is not None:
            self.ticketing.update(issue.ticket, {issue.target, issue.title, issue.description})
        else:
            ticket_id = self.ticketing.create("ssgticketing", "ssg", None, "CTT Issue: {}: {}: {}".format(self.cluster.name().capitalize(), issue.target, issue.title), "CTT issue: {}, Hosts: {}, Title: {}, Description: {}".format(cttissue, issue.target, issue.title, issue.description), {
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
            return oldissue.id
        else:
            issue.down_siblings = False
            issue.status = ctt.db.IssueStatus.OPEN
            issue.comments.append(ctt.db.Comment(created_by=issue.created_by, comment="opening issue"))
            return self.db.new_issue(issue)

    def prep_for_work(self, cttissue: int, operator: str) -> NodeSet:
        # TODO return nodes that were drained
        # TODO add option to schedule for work later, instead of ASAP
        issue = self.issue(cttissue)
        issue.down_siblings = True
        issue.comments.append(ctt.db.Comment(created_by=operator, comment="draining siblings for work"))
        self.db.update()
        to_drain = self.cluster.siblings(NodeSet(issue.target))
        self.cluster.drain(self.cluster.siblings(NodeSet(issue.target)))
        return to_drain


    def end_work(self, cttissue: int, operator: str) -> NodeSet:
        return self._resume_sibs(self.db.issue(cttissue), operator)

    def close(self, issue: ctt.db.Issue, operator: str, comment: str) -> NodeSet:
        if issue.status == ctt.db.IssueStatus.CLOSED:
            logging.warning(f"Issue {issue.id} already closed, skipping")
            return
        issue.comments.append(ctt.db.Comment(created_by=operator, comment=comment))
        issue.comments.append(ctt.db.Comment(created_by=operator, comment="closing issue"))
        issue.status = ctt.db.IssueStatus.CLOSED
        self.db.update()
        resumed = self._resume_sibs(issue, operator)
        return resumed

    def _resume_sibs(self, issue: ctt.db.Issue, comment: str, operator: str) -> NodeSet:
        to_resume = NodeSet()
        to_check = NodeSet(issue.target)
        issue.comments.append(ctt.db.Comment(created_by=operator, comment=comment))
        if issue.down_siblings:
            issue.down_siblings = False
            to_check.update(self.cluster.siblings(NodeSet(issue.target)))
            issue.comments.append(ctt.db.Comment(created_by=operator, comment="releasing siblings"))
        self.db.update()
        for n in to_check:
            if not self.db.get_issues(target=n, status=ctt.db.IssueStatus.OPEN):
                to_resume.update(n)
        if self.cluster_enabled:
            self.cluster.resume(to_resume)
        return to_resume

