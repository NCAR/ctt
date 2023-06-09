#!/usr/bin/env python3
import argparse
import datetime
import grp
import ntpath
import os
import sys
from syslog import syslog

import config
import cttlib
import slack
import ctt


def _authorized_team(user, authorized_teams):
    for team in authorized_teams:
        t = grp.getgrnam(team)
        if user in t[3]:
            return t[0]
    return None


def main():
    conf = config.get_config()
    logme = " ".join(sys.argv)
    syslog(logme)

    user = os.environ.get("SUDO_USER")

    if user is None:
        user = getpass.getuser()  # if not run via sudo

    if user == "root" and os.getenv("CRONTAB") != "True":
        print("You can't run ctt as root")
        sys.exit(1)

    if not _authorized_user(getpass.getuser(), conf.get("users", "teams").split(" ")):
        print("Current user is not authorized to run ctt")
        sys.exit(1)

    parser = cli(conf)
    args = parser.parse_args()

    # when no subcommand given func isn't set
    if "func" not in vars(args):
        parser.print_help()
    else:
        args.func(args, conf)

def _issues(parser):
    parser.add_argument("issue", type=int, nargs="+", help="ctt issue numbers")


def _issues_and_comment(parser):
    issues(parser)
    parser.add_argument("comment")


def _ticket_args(parser, conf):
    parser.add_argument("-T", "--xticket", help="Toggle an external (HPE,IBM) ticket")
    parser.add_argument("-a", "--assign", choices=("ssg", "casg"))
    parser.add_argument("-c", "--cluster", default=conf.get("cluster", "name"))
    parser.add_argument("-s", "--severity", choices=("1", "2", "3", "4"))
    parser.add_argument(
        "-t", "--ticket", help="Attach an existing EV ticket to this issue"
    )
    parser.add_argument(
        "-x",
        "--type",
        choices=("h", "h!", "s", "t", "u", "o"),
        help="Hardware, Software, Test, Unknown, Other",
    )

def _cli(conf):
    parser = argparse.ArgumentParser()
    ev_enabled = "True" != conf.getboolean("ev", "enabled")
    parser.add_argument(
        "--noev",
        action="store_true",
        help="Do not update EV ticket",
        default=(ev_enabled),
    )
    subparsers = parser.add_subparsers()
    # TODO improve reuse of subparser args since so many subcommands have similar arguments

    parser_release = subparsers.add_parser("release")
    parser_release.add_argument("issue", type=int, help="ctt issue number")
    parser_release.add_argument("node", nargs="+")
    parser_release.set_defaults(func=ctt.release)

    parser_holdback = subparsers.add_parser("holdback")
    parser_holdback.add_argument("node")
    parser_holdback.add_argument("state", choices=("add", "remove"))
    parser_holdback.set_defaults(func=ctt.holdback)

    parser_evopen = subparsers.add_parser("evopen")
    issues(parser_evopen)
    parser_evopen.set_defaults(func=ctt.evopen)

    parser_attach = subparsers.add_parser("attach")
    issues(parser_attach)
    parser_attach.add_argument("filepath")
    parser_attach.set_defaults(func=ctt.attach)

    parser_show = subparsers.add_parser("show")
    issues(parser_show)
    parser_show.add_argument(
        "-d", action="store_true", help="Show detail/history of ticket"
    )
    parser_show.set_defaults(func=show)

    parser_stats = subparsers.add_parser("stats")
    parser_stats.add_argument("-n", "--node")
    parser_stats.add_argument("-c", "--counts", action="store_true")
    parser_stats.set_defaults(func=ctt.stats)

    parser_listcmd = subparsers.add_parser("list")
    parser_listcmd.add_argument(
        "-s",
        "--status",
        choices=("open", "closed", "deleted", "all"),
        default="open",
    )
    parser_listcmd.add_argument("--verbose", "-v", action="count", default=0)
    parser_listcmd.set_defaults(func=ctt.listcmd)

    parser_evclose = subparsers.add_parser("evclose")
    issues_and_comment(parser_evclose)
    parser_evclose.set_defaults(func=ctt.evclose)

    parser_comment = subparsers.add_parser("comment")
    issues_and_comment(parser_comment)
    parser_comment.set_defaults(func=ctt.comment)

    parser_close = subparsers.add_parser("close")
    issues_and_comment(parser_close)
    parser_close.set_defaults(func=ctt.close)

    parser_reopen = subparsers.add_parser("reopen")
    issues_and_comment(parser_reopen)
    parser_reopen.set_defaults(func=ctt.reopen)

    parser_update = subparsers.add_parser("update")
    issues(parser_update)
    ticket_args(parser_update, conf)
    parser_update.add_argument("-d", "--description")
    parser_update.add_argument("-i", "--issuetitle", dest="title")
    parser_update.add_argument(
        "-n",
        "--node",
        nargs="+",
        help="Warning: Changing the node name will NOT drain a node nor resume the old node name",
    )
    parser_update.set_defaults(func=ctt.update)

    parser_opencmd = subparsers.add_parser("open")
    parser_opencmd.add_argument("title")
    parser_opencmd.add_argument("description")
    parser_opencmd.add_argument(
        "node",
        nargs="+",
        help="Warning: Changing the node name will NOT drain a node nor resume the old node name",
    )
    ticket_args(parser_opencmd, conf)
    parser_opencmd.set_defaults(func=ctt.opencmd)

    return parser

if "__main__" == __name__:
    main()
    sys.exit(0)
