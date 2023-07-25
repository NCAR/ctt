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

    def issue_list(self, **kwargs) -> [ctt.db.Issue]:
        """
        list all issues that fit the given state
        """
        logging.debug('listing issues')
        return self.db.get_issues(**kwargs)

    def update(self, cttissue: int, args):
        issue = self.issue(cttissue)
        for k in vars(issue):
            if k in args:
                setattr(issue, k, args[k])
        self.db.update()

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
                self.db.update()
                return oldissue.id
            else:
                #TODO update any fields that are different between old issue and the new one
                return None
        else:
            issue.down_siblings = False
            issue.status = ctt.db.IssueStatus.OPEN
            issue.comments.append(ctt.db.Comment(created_by=issue.created_by, comment="opening issue"))
            issueid =  self.db.new_issue(issue)
            return issueid

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
        return self._resume(self.db.issue(cttissue), operator)

    def close(self, issue: ctt.db.Issue, operator: str, comment: str) -> NodeSet:
        if issue.status == ctt.db.IssueStatus.CLOSED:
            logging.warning(f"Issue {issue.id} already closed, skipping")
            return
        issue.comments.append(ctt.db.Comment(created_by=operator, comment=comment))
        issue.comments.append(ctt.db.Comment(created_by=operator, comment="closing issue"))
        issue.status = ctt.db.IssueStatus.CLOSED
        issue.enforce_down=False
        self.db.update()
        resumed = self._resume(issue, operator)
        return resumed

    def _resume(self, issue: ctt.db.Issue, operator: str) -> NodeSet:
        """ Resumes any node or sibling related to the issue that no longer needs to be down"""
        to_resume = NodeSet()
        to_check = NodeSet(issue.target)
        if issue.down_siblings:
            issue.down_siblings = False
            to_check.update(self.cluster.siblings(NodeSet(issue.target)))
        self.db.update()
        for n in to_check:
            if not self.db.get_issues(target=n, status=ctt.db.IssueStatus.OPEN):
                to_resume.update(n)
        if self.cluster_enabled:
            self.cluster.resume(to_resume)
        issue.comments.append(ctt.db.Comment(created_by=operator, comment=f"Resuming Nodes {to_resume}"))
        return to_resume

