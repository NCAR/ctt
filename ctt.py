#!/usr/bin/python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
#Copyright (c) 2020, University Corporation for Atmospheric Research
#All rights reserved.
#
#Redistribution and use in source and binary forms, with or without 
#modification, are permitted provided that the following conditions are met:
#
#1. Redistributions of source code must retain the above copyright notice, 
#this list of conditions and the following disclaimer.
#
#2. Redistributions in binary form must reproduce the above copyright notice,
#this list of conditions and the following disclaimer in the documentation
#and/or other materials provided with the distribution.
#
#3. Neither the name of the copyright holder nor the names of its contributors
#may be used to endorse or promote products derived from this software without
#specific prior written permission.
#
#THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
#AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
#IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE 
#ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
#LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR 
#CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF 
#SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS 
#INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, 
#WHETHER IN CONTRACT, STRICT LIABILITY,
#OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. 
import sqlite3 as SQL
from cttlib import *
import datetime
import argparse
import sys
from configparser import ConfigParser
import os
import getpass
from syslog import syslog


logme = ' '.join(sys.argv)
syslog(logme)

con = SQL.connect('ctt.sqlite')
date = datetime.datetime.now().isoformat() #ISO8601
user = os.environ.get("SUDO_USER")
if user is None:
    user = getpass.getuser()	#if not run via sudo

#if user == 'root' and os.getenv('CRONTAB') != 'True':
#    print('You can\'t run ctt as root')
#    exit()

updatedby = user
UserGroup = GetUserGroup(usersdict, user)
groupsList = GetGroups(usersdict, user)
checkdb(date)
config = ConfigParser()
config.read('ctt.ini')
defaults = config['DEFAULTS']
severity = defaults['severity']
issuestatus = defaults['issuestatus']
issuetype = defaults['issuetype']
assignedto = defaults['assignedto']
attach_location = defaults['attach_location']
cluster = defaults['cluster']
strict_node_match = defaults['strict_node_match'] #Only used when --open unless strict_node_match_auto is True. False is off, comma delimeted list of nodes for on
pbs_enforcement = defaults['pbs_enforcement'] #with False, will not resume or offline nodes in pbs
extraview_enabled = defaults['extraview_enabled'] #Enable extraview open, close, etc. True or False
slack_enabled = defaults['slack_enabled']
slack_bot_token = defaults['slack_bot_token']
slack_channel = defaults['slack_channel']
transient_errors = defaults['transient_errors']
transient_errors_enabled = defaults['transient_errors_enabled']

try: #??????
    if not sys.argv[1]:
        show_help()
except IndexError:  #??????                                                                                                                                                                                         
    show_help()


if '--release' in sys.argv[1]:
    #./ctt.py --release 1294 -n r1i1n1   #release list of siblings from parent node
    parser = argparse.ArgumentParser(add_help=False, description="Cluster Ticket Tracker Version 2.1.0")
    parser.add_argument('--release', action='store', dest='issuenumber', nargs=1, required=True)    
    parser.add_argument('-n','--node', action='store', dest='nodevalue', required=True)
    parser.add_argument('-c','--comment', action='store', dest='commentvalue', required=True)
    args = parser.parse_args()
    node_list = args.nodevalue.split(',')
    cttissue = args.issuenumber[0]
    comment = args.commentvalue

    for node in node_list:
        release(cttissue, date, node)         
        update_issue(cttissue, 'updatedby', updatedby)
        update_issue(cttissue, 'updatedtime', date)
        #comment issue here... or in release() 
        log_history(cttissue, date, updatedby, 'Released sibling node %s' % (node))


    exit()

#####################

if '--holdback' in sys.argv[1]:
    #./ctt.py --holdback casper30 add||remove
    parser = argparse.ArgumentParser(add_help=False, description="Cluster Ticket Tracker Version 2.1.0")
    parser.add_argument('--holdback', action='store', dest='holdbackvalue', nargs=2, required=True)
    args = parser.parse_args()
    node = args.holdbackvalue[0]
    state = args.holdbackvalue[1]
    update_holdback(node, state)
    exit(0)


if '--evclose' in sys.argv[1]:
    #./ctt.py --evclose 12345
    parser = argparse.ArgumentParser(add_help=False, description="Cluster Ticket Tracker Version 2.1.0")
    parser.add_argument('--evclose', action='store', dest='evclosevalue', nargs=2, required=True)
    args = parser.parse_args()
    ev_comment = args.evclosevalue[1]
    if args.evclosevalue[0]:
        cttissue = args.evclosevalue[0]
        if extraview_enabled == "True":
            if check_for_ticket(cttissue) is True:
                ev_id = get_issue_data(cttissue)[3]   #ev_id
                close_EV(cttissue, ev_comment)
                update_ticket(cttissue, ev_id)  
                update_issue(cttissue, 'updatedby', updatedby)
                update_issue(cttissue, 'updatedtime', date)
                view_tracker_new(cttissue,UserGroup,viewnotices)
                log_history(cttissue,date,updatedby,'Closed EV ticket')
                #print("EV closed for CTT issue %s" % (cttissue))
                exit(0)
            else:
                print("There is no EV ticket attached to %s, Exiting!" % (cttissue))
                exit(1)
        else:
            print("extraview_enabled is False. Can't close EV")
            #exit(1)

if '--evopen' in sys.argv[1]: # ADD FOR LOOP FOR MULTIPLE ISSUES   
    #./ctt.py --evopen 12345                                       
    parser = argparse.ArgumentParser(add_help=False, description="Cluster Ticket Tracker Version 2.1.0")
    parser.add_argument('--evopen', action='store', dest='evopenvalue', nargs=1, required=True)
    args = parser.parse_args()
    if args.evopenvalue[0]:
        cttissue = args.evopenvalue[0]
        if extraview_enabled == "True":
            if check_for_ticket(cttissue) is False:
                ev_id = open_EV(cttissue)
                update_ticket(cttissue, ev_id)
                update_issue(cttissue, 'updatedby', updatedby)
                update_issue(cttissue, 'updatedtime', date)
                view_tracker_new(cttissue,UserGroup,viewnotices)
                log_history(cttissue,date,updatedby,'Opened EV ticket %s' % (ev_id))
                assignto = get_issue_data(cttissue)[9]
                assign_EV(cttissue,assignto)
                print("EV %s opened for CTT issue %s" % (ev_id, cttissue))
                update_issue(cttissue,'assignedto', assignedto)
            else:
                print("There is already an EV ticket attached to this issue.")
        else:
            print("extraview_enabled is False. Can't open EV")
            exit(0)   #May need to remove this exit when looping!


elif '--auto' in sys.argv[1]:
    check_nolocal()
    run_auto(date,severity,assignedto,updatedby,cluster,UserGroup)   
    exit(0)  

elif '--attach' in sys.argv[1]:
    # ./ctt.py --attach 1020 /tmp/ipmi_sdr_list.out
    import ntpath
    parser = argparse.ArgumentParser(add_help=False, description="Cluster Ticket Tracker Version 2.1.0")
    parser.add_argument('--attach', action='store', dest='attachment', nargs=2, required=True)    
    args = parser.parse_args()

    if args.attachment[0] and args.attachment[1]:  
        create_attachment(args.attachment[0],args.attachment[1],attach_location,date,updatedby)
        update_issue(args.attachment[0], 'updatedby', updatedby)
        update_issue(args.attachment[0], 'updatedtime', date) 
        filename = ntpath.basename(args.attachment[1])     
        log_history(args.attachment[0], date, updatedby, 'Attached file: %s/%s/%s.%s' % (attach_location, args.attachment[0], date[0:16], filename))
        comment_issue(args.attachment[0], date, updatedby, 'Attached file: %s/%s/%s.%s' % (attach_location, args.attachment[0], date[0:16], filename), UserGroup)
        view_tracker_update(args.attachment[0],UserGroup)    
    exit(0)

elif '--list' in sys.argv[1]:
    # ./ctt.py --list           # Shows all open
    # ./ctt.py --list -s closed	# Options: open, closed, deleted
    parser = argparse.ArgumentParser(add_help=False, description="Cluster Ticket Tracker Version 2.1.0")
    parser.add_argument('--list', action='store_true', dest='listvalue', default=True, required=True)
    parser.add_argument('-s', action='store', dest='statusvalue', choices=('open', 'closed', 'deleted', 'all'), required=False)
    parser.add_argument('-v', action='store_true', dest='verbosevalue', default=False, required=False)
    parser.add_argument('-vv', action='store_true', dest='vverbosevalue', default=False, required=False)
    args = parser.parse_args()
    
    if not args.statusvalue:
        args.statusvalue = 'open'
    if args.verbosevalue is True:
        get_issues_v(args.statusvalue)
        exit(0)
    if args.vverbosevalue is True:
        get_issues_vv(args.statusvalue)
        exit(0)
    else:
        get_issues(args.statusvalue)
        exit(0) 

elif '--show' in sys.argv[1]:
    # ./ctt.py --show 1045
    parser = argparse.ArgumentParser(add_help=False, description="Cluster Ticket Tracker Version 2.1.0")
    parser.add_argument('--show', action='store', dest='issuenumber', nargs=1, required=True)    
    parser.add_argument('-d', action='store_true', default=False)
    args = parser.parse_args()

    if args.issuenumber[0]:
        get_issue_full(args.issuenumber[0])

    if args.d is True:
        get_history(args.issuenumber[0])

    view_tracker_update(args.issuenumber[0],UserGroup)

elif '--update' in sys.argv[1]:
    # ./ctt.py --update 1039 -s 1 -c cheyenne -n r1i1n1 -t 689725 -a casg
    parser = argparse.ArgumentParser(add_help=False, description="Cluster Ticket Tracker Version 2.1.0")
    parser.add_argument('--update', action='store', dest='issuenumber', nargs=1, required=True)    
    parser.add_argument('-s','--severity', action='store', dest='severityvalue', choices=('1','2','3','4'), required=False)
    parser.add_argument('-c','--cluster', action='store', dest='clustervalue', required=False)
    parser.add_argument('-n','--node', action='store', dest='nodevalue', required=False)
    parser.add_argument('-t','--ticket', action='store', dest='ticketvalue', required=False)
    parser.add_argument('-T','--xticket', action='store', dest='xticketvalue', required=False)
    parser.add_argument('-a','--assign', action='store', dest='assignedtovalue', required=False)
    parser.add_argument('-i','--issuetitle', action='store', dest='issuetitlevalue', required=False)
    parser.add_argument('-d','--description', action='store', dest='descvalue', required=False)    
    parser.add_argument('-x', '--type', action='store', dest='typevalue', choices=('h','h!', 's', 't', 'u', 'o'), required=False)
    parser.add_argument('--noev', action='store_true', dest='noevvalue', required=False)
    args = parser.parse_args()

    issue_list = args.issuenumber[0].split(',')
    for cttissue in issue_list:

        if args.typevalue:
            try:
                if cttissue:     
                    if args.typevalue == 'h!':      #add ev function here for h!
                        add_siblings(cttissue,date,updatedby)
                        args.typevalue = 'h'
                    update_issue(cttissue, 'issuetype', args.typevalue)
                    update_issue(cttissue, 'updatedby', updatedby)
                    update_issue(cttissue, 'updatedtime', date)
                    view_tracker_new(cttissue,UserGroup,viewnotices)
                    log_history(cttissue,date,updatedby,'Updated issue type to %s' % (args.typevalue))
                    if (args.typevalue == 'h' or args.typevalue == 'h!') and extraview_enabled == "True":     #move this statement up under if for h!
                        if args.noevvalue is False:
                            if check_for_ticket(cttissue) is False:
                                ev_id = open_EV(cttissue)
                                update_ticket(cttissue, ev_id)
                                update_issue(cttissue, 'updatedby', updatedby)
                                update_issue(cttissue, 'updatedtime', date)
                                view_tracker_new(cttissue,UserGroup,viewnotices)
                                log_history(cttissue,date,updatedby,'Opened EV ticket %s' % (ev_id))
                                assignto = get_issue_data(cttissue)[9]
                                assign_EV(cttissue,assignto)
                                if args.typevalue == 'h!':
                                    comment_EV(cttissue, 'Attached Siblings to this ctt issue (%s)' % (cttissue))
                                print("EV %s opened for CTT issue %s assigned to %s" % (ev_id, cttissue, assignto))
                            #else:
                            #    print("There is an existing EV attached to this issue (%s). Not opening EV ticket." % (cttissue))

            except IndexError:
                parser.print_help()

        if args.issuetitlevalue:
            test_arg_size(args.issuetitlevalue,what='issue title',maxchars=150)
            try:
                if cttissue:
                    update_issue(cttissue, 'issuetitle', args.issuetitlevalue)
                    update_issue(cttissue, 'updatedby', updatedby)
                    update_issue(cttissue, 'updatedtime', date)
                    view_tracker_new(cttissue,UserGroup,viewnotices)
                    log_history(cttissue,date,updatedby,'Updated issue title to %s' % (args.issuetitlevalue))
            except IndexError:
                parser.print_help()

        if args.descvalue:
            test_arg_size(args.descvalue,what='issue description',maxchars=4000)
            try:
                if cttissue:
                    update_issue(cttissue, 'issuedescription', args.descvalue)
                    update_issue(cttissue, 'updatedby', updatedby)
                    update_issue(cttissue, 'updatedtime', date)
                    view_tracker_new(cttissue,UserGroup,viewnotices)
                    log_history(cttissue,date,updatedby,'Updated issue description to %s' % (args.descvalue))
            except IndexError:
                parser.print_help()

        if args.severityvalue:
            try:
                if cttissue:
                    update_issue(cttissue, 'severity', args.severityvalue)
                    update_issue(cttissue, 'updatedby', updatedby)
                    update_issue(cttissue, 'updatedtime', date)
                    view_tracker_new(cttissue,UserGroup,viewnotices)
                    log_history(cttissue,date,updatedby,'Updated issue severity to %s' % (args.severityvalue))
            except IndexError:
                parser.print_help()

        if args.clustervalue:
            try:
                if cttissue:
                    update_issue(cttissue, 'cluster', args.clustervalue)
                    update_issue(cttissue, 'updatedby', updatedby)
                    update_issue(cttissue, 'updatedtime', date)
                    view_tracker_new(cttissue,UserGroup,viewnotices)
                    log_history(cttissue,date,updatedby,'Updated cluster to %s' % (args.clustervalue))
            except IndexError:
                parser.print_help()

        if args.nodevalue:
            try:
                if cttissue:
                    update_issue(cttissue, 'node', args.nodevalue)
                    update_issue(cttissue, 'updatedby', updatedby)
                    update_issue(cttissue, 'updatedtime', date)
                    view_tracker_new(cttissue,UserGroup,viewnotices)
                    log_history(cttissue,date,updatedby,'Updated node to %s' % (args.nodevalue))
            except IndexError:
                parser.print_help()

        if args.assignedtovalue in groupsList:
            try:
                if cttissue:
                    update_issue(cttissue, 'assignedto', args.assignedtovalue)
                    update_issue(cttissue, 'updatedby', updatedby)
                    update_issue(cttissue, 'updatedtime', date)
                    view_tracker_new(cttissue,UserGroup,viewnotices)
                    log_history(cttissue,date,updatedby,'Assigned issue to %s' % (args.assignedtovalue))

                    if extraview_enabled == "True":
                        if args.noevvalue is False:
                            if check_for_ticket(cttissue) is True:
                               assign_EV(cttissue, args.assignedtovalue)
                               log_history(cttissue,date,updatedby,'Assigned EV ticket to %s' % (args.assignedtovalue))
                    else:
                        print("extraview_enabled is False. Can't assign EV")

            except IndexError:
                parser.print_help()
        elif args.assignedtovalue != None:
            print("Assign to group \"%s\" is not a valid users group, Exiting!" % (args.assignedtovalue))

        if args.ticketvalue:
            try:
                if cttissue:
                    update_ticket(cttissue, args.ticketvalue)
                    update_issue(cttissue, 'updatedby', updatedby)
                    update_issue(cttissue, 'updatedtime', date)
                    view_tracker_new(cttissue,UserGroup,viewnotices)
                    log_history(cttissue,date,updatedby,'Updated EV ticket to %s' % (args.ticketvalue))
            except IndexError:
                parser.print_help()

        if args.xticketvalue:
            try:
                if cttissue:
                    update_xticket(cttissue, args.xticketvalue)
                    update_issue(cttissue, 'updatedby', updatedby)
                    update_issue(cttissue, 'updatedtime', date)
                    view_tracker_new(cttissue,UserGroup,viewnotices)
                    log_history(cttissue,date,updatedby,'Updated external ticket to %s' % (args.xticketvalue))
            except IndexError:
                parser.print_help()


elif '--comment' in sys.argv[1]: 
    # ./ctt.py --comment 12390,12011 "Need an update"
    parser = argparse.ArgumentParser(add_help=False, description="Cluster Ticket Tracker Version 2.0.0")
    parser.add_argument('--noev', action='store_true', dest='noevvalue', required=False)
    parser.add_argument('--comment', action='store', dest='comment', nargs=2, required=True)    
    args = parser.parse_args()

    if args.comment[0] and args.comment[1]:
        issue_list = args.comment[0].split(',')
        for cttissue in issue_list: 
            test_arg_size(args.comment[1],what='comment',maxchars=500)
            comment_issue(cttissue, date, updatedby, args.comment[1],UserGroup)
            update_issue(cttissue, 'updatedby', updatedby)
            update_issue(cttissue, 'updatedtime', date)
            log_history(cttissue, date, updatedby, 'Commented issue with \"%s\"' % (args.comment[1]))

            if extraview_enabled == "True":
                if args.noevvalue is False:
                    if check_for_ticket(cttissue) is True:
                        comment_EV(cttissue, args.comment[1])
            else:
                #print("extraview_enabled is False. Can't comment EV")
                exit(1)


elif '--close' in sys.argv[1]:
    # ./ctt.py --close 1028,1044 "Issue resolved"
    parser = argparse.ArgumentParser(add_help=False, description="Cluster Ticket Tracker Version 2.0.0")
    parser.add_argument('--close', action='store', dest='closevalue', nargs=2, required=True)    
    parser.add_argument('--noev', action='store_true', dest='noevvalue', required=False)
    args = parser.parse_args()

    if args.closevalue[0] and args.closevalue[1]:
        issue_list = args.closevalue[0].split(',')
        for cttissue in issue_list:
            node = get_hostname(cttissue)
            test_arg_size(args.closevalue[1],what='comment',maxchars=500)
            comment_issue(cttissue, date, updatedby, args.closevalue[1],UserGroup)
            update_issue(cttissue, 'updatedby', updatedby)
            update_issue(cttissue, 'updatedtime', date)
            if node is None:
                print("Issue %s is not open" % (cttissue))
                continue
            node = ''.join(node)
            if check_holdback(node) != False:
                answer = input("\n%s is in holdback state. Are you sure you want to release this node and close issue? [y|n]: " % (node))
                answer = answer.lower()
                if answer == "n":
                    continue
                    #exit()
                elif answer == "y":
                    update_holdback(node, 'remove')
                    next
                else:
                    exit()

            close_issue(cttissue, date, updatedby)
            log_history(cttissue, date, updatedby, 'Closed issue %s' % (args.closevalue[1]))

            if extraview_enabled == "True":
                if args.noevvalue is False:
                    if check_for_ticket(cttissue) is True:
                        close_EV(cttissue, args.closevalue[1])
            else:
                print("extraview_enabled is False. Can't close EV")

            if slack_enabled == "True":
                slack_message = "Issue %s for %s: %s closed by %s\n%s" % (cttissue, cluster, node, updatedby, args.closevalue[1])
                send_slack(slack_bot_token, slack_channel, slack_message)

elif '--reopen' in sys.argv[1]:  #Add EV function to reopen ev unless --noev
    # ./ctt.py --reopen 10282,10122 "Accidental close"
    parser = argparse.ArgumentParser(add_help=False, description="Cluster Ticket Tracker Version 2.0.0")
    parser.add_argument('--reopen', action='store', dest='reopenvalue', nargs=2, required=True)    
    parser.add_argument('--noev', action='store_true', dest='noevvalue', required=False)
    args = parser.parse_args()

    if args.reopenvalue[0] and args.reopenvalue[1]:
        issue_list = args.reopenvalue[0].split(',')
        for cttissue in issue_list:
            test_arg_size(args.reopenvalue[1],what='comment',maxchars=500)
            comment_issue(cttissue, date, updatedby, args.reopenvalue[1],UserGroup)
            update_issue(cttissue, 'updatedby', updatedby)
            update_issue(cttissue, 'updatedtime', date)
            update_issue(cttissue, 'status', 'open')
            log_history(cttissue, date, updatedby, 'Reopened issue %s' % (args.reopenvalue[1]))
            if pbs_enforcement == 'False':
                print("pbs_enforcement is False. Not draining nodes")
            else:
                pbs_drain(cttissue,date,updatedby,get_hostname(cttissue))
            
            if extraview_enabled == "True":
                if args.noevvalue is False:
                    if check_for_ticket(cttissue) is True:
                        reopen_EV(cttissue, args.reopenvalue[1])
                        assignto = get_issue_data(cttissue)[9]
                        assign_EV(cttissue,assignto)
            else:
                print("extraview_enabled is False. Can't close EV")
               



elif '--open' in sys.argv[1]:
    # ./ctt.py --open "Failed dimm on r1i1n1" "Description here" -c cheyenne -s 1 -n r1i1n1,r1i1n10 -a casg
    parser = argparse.ArgumentParser(add_help=False, description="Cluster Ticket Tracker Version 2.0.0")
    parser.add_argument('--open', action='store', dest='openvalue', nargs='+', required=True)
    parser.add_argument('--noev', action='store_true', dest='noevvalue', required=False)
    parser.add_argument('-s','--severity', action='store', dest='severityvalue', required=False)
    parser.add_argument('-c','--cluster', action='store', dest='clustervalue', required=False)
    parser.add_argument('-n','--node', action='store', dest='nodevalue', required=True)
    parser.add_argument('-a','--assign', action='store', dest='assignedtovalue', required=False)
    parser.add_argument('-t', '--ticket', action='store', dest='ticketvalue', required=False)
    parser.add_argument('-T', '--xticket', action='store', dest='xticketvalue', required=False)
    parser.add_argument('-x', '--type', action='store', dest='typevalue', choices=('h', 's', 't', 'u', 'o'), required=False)    
    args = parser.parse_args()


    if strict_node_match != 'False':
        if not (args.nodevalue in strict_node_match):
            print("Can not find %s in strict_node_match, Exiting!" % (args.nodevalue))
            exit()

    if args.assignedtovalue:              #need this still?
        assignedto = args.assignedtovalue #need this still?
    if not args.xticketvalue:
       args.xticketvalue = '---'
    if not args.ticketvalue:      
        args.ticketvalue = '---'
    if not args.severityvalue:
        args.severityvalue = severity 
    if not args.clustervalue:
        args.clustervalue = cluster

    if args.openvalue[0] and args.openvalue[1]:
        node_list = args.nodevalue.split(',')
        if assignedto in groupsList:
            for node in node_list: 
                test_arg_size(args.openvalue[0],what='issue title',maxchars=100)
                test_arg_size(args.openvalue[1],what='issue description',maxchars=4000)
                cttissue = new_issue(date, args.severityvalue, args.ticketvalue, 'open', \
                                     args.clustervalue, node, args.openvalue[0], \
                                     args.openvalue[1], assignedto, updatedby, \
                                     updatedby, issuetype, 'unknown', date, UserGroup, args.xticketvalue) 
                log_history(cttissue, date, updatedby, 'new issue')

                if args.typevalue is 'h' and extraview_enabled == "True":
                    if args.noevvalue is False:                                                                                                                                  
                        if check_for_ticket(cttissue) is False:                                                                                                                  
                            ev_id = open_EV(cttissue)                                                                                                                            
                            update_ticket(cttissue, ev_id)                                                                                                                       
                            update_issue(cttissue, 'updatedby', updatedby)                                                                                                       
                            update_issue(cttissue, 'updatedtime', date)                                                                                                          
                            view_tracker_new(cttissue,UserGroup,viewnotices)                                                                                                     
                            log_history(cttissue,date,updatedby,'Updated ticket to %s' % (ev_id))                                                                               
                            print("EV %s opened for CTT issue %s" % (ev_id, cttissue))                                                                                           
                        #else:                                                                                                                                                    
                        #    print("There is an existing EV attached to this issue (%s). Not opening EV ticket." % (cttissue))

                if args.assignedtovalue in groupsList:                                                                                                                                       
                    update_issue(cttissue, 'assignedto', args.assignedtovalue)                                                                                                       
                    update_issue(cttissue, 'updatedby', updatedby)                                                                                                                   
                    update_issue(cttissue, 'updatedtime', date)                                                                                                                      
                    view_tracker_new(cttissue,UserGroup,viewnotices)                                                                                                                 
                    log_history(cttissue,date,updatedby,'Assigned issue to %s' % (args.assignedtovalue))                                                                            
                                                                                                                                                                                      
                    if extraview_enabled == "True":                                                                                                                                  
                        if args.noevvalue is False:                                                                                                                                  
                            if check_for_ticket(cttissue) is True:                                                                                                                   
                                assign_EV(cttissue, args.assignedtovalue)                                                                                                             
                    else:                                                                                                                                                            
                        print("extraview_enabled is False. Can't assign EV")  

        else:                                                                                                                                           
            print("Assign to group \"%s\" is not a valid users group, Exiting!" % (args.assignedtovalue))


elif '--help' in sys.argv[1] or '-h' in sys.argv[1]:
    show_help()

elif '--stats' in sys.argv[1]:
    from cttstats import *
    
    # ./ctt.py --stats -n casper15  # ./ctt.py --stats -c
    parser = argparse.ArgumentParser(add_help=False, description="Cluster Ticket Tracker Version 2.0.0")
    parser.add_argument('--stats', action='store_true', required=True) 
    parser.add_argument('-n','--node', action='store', dest='nodevalue', required=False)
    parser.add_argument('-c','--counts', action='store_true', dest='countsvalue', required=False)
    args = parser.parse_args()

    if args.countsvalue:
        run_stats_counts()
        exit(0)
    
    if args.nodevalue:
        run_stats_node(args.nodevalue)
        exit(0)

else:
    show_help()

