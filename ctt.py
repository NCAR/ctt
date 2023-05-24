#!/usr/bin/env python3
import cttlib
import datetime
import argparse
import sys
import os
import config
import getpass
from syslog import syslog
import ntpath

def main():
    logme = ' '.join(sys.argv)
    syslog(logme)
    
    user = os.environ.get("SUDO_USER")
    if user is None:
        user = getpass.getuser()	#if not run via sudo
    
    if user == 'root' and os.getenv('CRONTAB') != 'True':
        print('You can\'t run ctt as root')
        exit(1)
    
    updatedby = user

    conf = config.get_config()
    parser = cli(conf)
    args = parser.parse_args()

    # when no subcommand given func isn't set
    if 'func' not in vars(args):
        parser.print_help()
    else:
        args.func(args, conf)


def issues(parser):
    parser.add_argument('issue', type=int, nargs='+', help="ctt issue numbers")

def issues_and_comment(parser):
    issues(parser)
    parser.add_argument('comment')

def ticket_args(parser, conf):
    parser.add_argument('-T','--xticket', help="Toggle an external (HPE,IBM) ticket")
    parser.add_argument('-a','--assign', choices=('ssg', 'casg'))
    parser.add_argument('-c','--cluster', default=conf.get('cluster', 'name'))
    parser.add_argument('-s','--severity', choices=('1','2','3','4'))
    parser.add_argument('-t','--ticket', help="Attach an existing EV ticket to this issue")
    parser.add_argument('-x', '--type', choices=('h','h!', 's', 't', 'u', 'o'), help="Hardware, Software, Test, Unknown, Other")

def cli(conf):
    parser = argparse.ArgumentParser()
    ev_enabled = "True" != conf.getboolean('ev', 'enabled')
    parser.add_argument('--noev', action='store_true', help="Do not update EV ticket", default=(ev_enabled))
    subparsers = parser.add_subparsers()
    #TODO improve reuse of subparser args since so many subcommands have similar arguments

    parser_release = subparsers.add_parser('release')
    parser_release.add_argument('issue', type=int, help="ctt issue number")
    parser_release.add_argument('node', nargs='+')
    parser_release.set_defaults(func=release)

    parser_holdback = subparsers.add_parser('holdback')
    parser_holdback.add_argument('node')
    parser_holdback.add_argument('state', choices=('add', 'remove'))
    parser_holdback.set_defaults(func=holdback)

    parser_evopen = subparsers.add_parser('evopen')
    issues(parser_evopen)
    parser_evopen.set_defaults(func=evopen)

    parser_attach = subparsers.add_parser('attach')
    issues(parser_attach)
    parser_attach.add_argument('filepath')
    parser_attach.set_defaults(func=attach)

    parser_show = subparsers.add_parser('show')
    issues(parser_show)
    parser_show.add_argument('-d', action='store_true', help="Show detail/history of ticket")
    parser_show.set_defaults(func=show)

    parser_stats = subparsers.add_parser('stats')
    parser_stats.add_argument('-n','--node')
    parser_stats.add_argument('-c','--counts', action='store_true')
    parser_stats.set_defaults(func=stats)

    parser_listcmd = subparsers.add_parser('list')
    parser_listcmd.add_argument('-s', '--status', choices=('open', 'closed', 'deleted', 'all'), default='open')
    parser_listcmd.add_argument('--verbose', '-v', action='count', default=0)
    parser_listcmd.set_defaults(func=listcmd)

    parser_evclose = subparsers.add_parser('evclose')
    issues_and_comment(parser_evclose)
    parser_evclose.set_defaults(func=evclose)

    parser_comment = subparsers.add_parser('comment')
    issues_and_comment(parser_comment)
    parser_comment.set_defaults(func=comment)

    parser_close = subparsers.add_parser('close')
    issues_and_comment(parser_close)
    parser_close.set_defaults(func=close)

    parser_reopen = subparsers.add_parser('reopen')
    issues_and_comment(parser_reopen)
    parser_reopen.set_defaults(func=reopen)

    parser_update = subparsers.add_parser('update')
    issues(parser_update)
    ticket_args(parser_update, conf)
    parser_update.add_argument('-d','--description')
    parser_update.add_argument('-i','--issuetitle', dest='title')
    parser_update.add_argument('-n','--node', nargs='+', help="Warning: Changing the node name will NOT drain a node nor resume the old node name")
    parser_update.set_defaults(func=update)

    parser_opencmd = subparsers.add_parser('open')
    parser_opencmd.add_argument('title')
    parser_opencmd.add_argument('description')
    parser_opencmd.add_argument('node', nargs='+', help="Warning: Changing the node name will NOT drain a node nor resume the old node name")
    ticket_args(parser_opencmd, conf)
    parser_opencmd.set_defaults(func=opencmd)

    return parser

def release(args, conf):
    ctt = cttlib.CTT(conf)
    for node in args.node:
        ctt.release(args.issue, datetime.datetime.now().isoformat(), node)

def holdback(args, conf):
    ctt = cttlib.CTT(conf)
    ctt.update_holdback(args.node, args.state)

def evclose(args):
    ev_comment = args.comment
    for cttissue in args.issue:
        if not args.noev:
            if check_for_ticket(cttissue) is True:
                ev_id = get_issue_data(cttissue)[3]   #ev_id
                close_EV(cttissue, ev_comment)
                update_field(cttissue, 'ticket', ev_id)
            else:
                print("There is no EV ticket attached to %s, Exiting!" % (cttissue))
                exit(1)
        else:
            print("extraview_enabled is False. Can't close EV")

def evopen(args, config):
    for cttissue in args.issue:
        if not args.noev:
            if check_for_ticket(cttissue) is False:
                ev_id = open_EV(cttissue)
                update_field(cttissue, 'ticket', ev_id)
                assignto = get_issue_data(cttissue)[9]
                assign_EV(cttissue,assignto)
                print("EV %s opened for CTT issue %s" % (ev_id, cttissue))
                update_field(cttissue,'assignedto', config['ev']['assignedto'])
            else:
                print("There is already an EV ticket attached to this issue.")
        else:
            print("extraview_enabled is False. Can't open EV")

def attach(args, config):
    for issue in args.issue:
        create_attachment(issue,args.filepath,config['DEFAULTS']['attach_location'],datetime.datetime.now().isoformat(),updatedby)
        filename = ntpath.basename(args.filepath)
        log_touch(issue, 'Attached file: %s/%s/%s.%s' % (config['DEFAULTS']['attach_location'], issue, datetime.datetime.now().isoformat()[0:16], filename))
        comment_issue(issue, datetime.datetime.now().isoformat(), updatedby, 'Attached file: %s/%s/%s.%s' % (config['DEFAULTS']['attach_location'], issue, datetime.datetime.now().isoformat()[0:16], filename), GetUserGroup(usersdict, user))

def listcmd(args):
    if args.verbose == 1:
        get_issues_v(args.status)
    if args.vverbosevalue > 1:
        get_issues_vv(args.status)
    else:
        get_issues(args.status)

def show(args):
    for issue in args.issue:
        get_issue_full(args.issue)
        if args.d is True:
            get_history(args.issue)
        view_tracker_update(args.issue,GetUserGroup(usersdict, user))

def update(args):
    for cttissue in args.issue:
        if args.type:
            update_field(cttissue, 'issuetype', args.type)
            if args.type == 'h!':      #add ev function here for h!
                add_siblings(cttissue,datetime.datetime.now().isoformat(),updatedby)
            if 'h' in args.type and not args.noev:     #move this statement up under if for h!
                if check_for_ticket(cttissue) is False:
                    ev_id = open_EV(cttissue)
                    update_field(cttissue, 'ticket', ev_id)
                    if 'assign' not in vars(args):
                        args.assign = get_issue_data(cttissue)[9]

        if args.title:
            test_arg_size(args.title,what='issue title',maxchars=100)
            update_field(cttissue, 'issuetitle', args.title)

        if args.description:
            test_arg_size(args.description,what='issue description',maxchars=4000)
            update_field(cttissue, 'issuedescription', args.description)

        if args.severity:
            update_field(cttissue, 'severity', args.severity)

        if args.cluster:
            update_field(cttissue, 'cluster', args.cluster)

        if args.node:
            update_field(cttissue, 'node', args.node)

        if args.assign:
            update_field(cttissue, 'assignedto', args.assign)

            if not args.noev:
                if check_for_ticket(cttissue) is True:
                   assign_EV(cttissue, args.assign)
                   log_history(cttissue,datetime.datetime.now().isoformat(),updatedby,'Assigned EV ticket to %s' % (args.assign))
            else:
                print("extraview_enabled is False. Can't assign EV")

        if args.ticket:
            update_field(cttissue, 'ticket', args.ticket)

        if args.xticket:
            update_field(cttissue, 'xticket', args.xticket)

def _comment(cttissue, args):
    test_arg_size(args.comment,what='comment',maxchars=500)
    comment_issue(cttissue, datetime.datetime.now().isoformat(), updatedby, args.comment,GetUserGroup(usersdict, user))
    log_touch(cttissue, 'Commented issue with \"%s\"' % (args.comment))

    if not args.noev:
        if check_for_ticket(cttissue) is True:
                comment_EV(cttissue, args.comment)

def comment(args):
    for cttissue in args.issue:
        _comment(cttissue, args)

def close(args, config):
    for cttissue in args.issue:
        _comment(cttissue, args)
        node = get_hostname(cttissue)
        if node is None:
            print("Issue %s is not open" % (cttissue))
            continue
        node = ''.join(node)
        if check_holdback(node) != False:
            answer = input("\n%s is in holdback state. Are you sure you want to release this node and close issue? [y|n]: " % (node))
            answer = answer.lower()
            if answer == "n":
                continue
            elif answer == "y":
                update_holdback(node, 'remove')
                next
            else:
                exit(1)

        close_issue(cttissue, datetime.datetime.now().isoformat(), updatedby,config)
        log_touch(cttissue, 'Closed issue %s' % (args.comment))

        evclose(args)

        if config['slack']['enabled'] == "True":
            slack_message = "Issue %s for %s: %s closed by %s\n%s" % (cttissue, config['cluster']['name'], node, updatedby, args.comment)
            slack = Slack(config)
            slack.send_slack(slack_message)

def reopen(args,config):
    for cttissue in args.issue:
        test_arg_size(args.comment,what='comment',maxchars=500)
        comment_issue(cttissue, datetime.datetime.now().isoformat(), updatedby, args.comment,GetUserGroup(usersdict, user))
        update_field(cttissue, 'status', 'open')
        if config['pbs']['enforcement'] == 'False':
            print("pbs_enforcement is False. Not draining nodes")
        else:
            pbs_drain(cttissue,datetime.datetime.now().isoformat(),updatedby,get_hostname(cttissue))

        if not args.noev:
            if check_for_ticket(cttissue) is True:
                reopen_EV(cttissue, args.comment)
                assignto = get_issue_data(cttissue)[9]
                assign_EV(cttissue,assignto)
        else:
            print("extraview_enabled is False. Can't close EV")

def opencmd(args, config):
    if config['DEFAULTS']['strict_node_match'] == 'False':
        return
    if not (args.node in config['DEFAULTS']['strict_node_match']):
        print("Can not find %s in strict_node_match, Exiting!" % (args.node))
        exit(1)

    for node in args.node:
        test_arg_size(args.title,what='issue title',maxchars=100)
        test_arg_size(args.description,what='issue description',maxchars=4000)
        cttissue = new_issue(datetime.datetime.now().isoformat(), args.severity, args.ticket, 'open', \
                             args.cluster, node, args.title, \
                             args.description, config['DEFAULTS']['assignedto'], updatedby, \
                             updatedby, config['DEFAULTS']['issuetype'], 'unknown', datetime.datetime.now().isoformat(), GetUserGroup(usersdict, user), args.xticket)
        log_history(cttissue, datetime.datetime.now().isoformat(), updatedby, 'new issue')

        if args.type == 'h' and not args.noev:
            evopen(args)

def stats(args):
    if args.counts:
        run_stats_counts()
    if args.node:
        run_stats_node(args.node)

def update_field(issue, field, to):
    if field == 'ticket':
        update_ticket(issue, to)
    elif field == 'xticket':
        update_xticket(issue, to)
    else:
        update_issue(issue, field, to)
    log_touch(issue, 'Assigned %s to %s' % (field, to))


if '__main__' == __name__:
    main()
    sys.exit(0)
