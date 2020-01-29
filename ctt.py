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

check_nolocal()
con = SQL.connect('ctt.sqlite')
date = datetime.datetime.now().isoformat() #ISO8601
updatedby = os.environ['LOGNAME']
if updatedby == 'root':
    updatedby = 'ssg'

# TEST
#updatedby = 'casg'

checkdb(date)
config = ConfigParser()
config.read('ctt.ini')
defaults = config['DEFAULTS']
severity = defaults['severity']
issuestatus = defaults['issuestatus']
assignedto = defaults['assignedto']
attach_location = defaults['attach_location']

cluster = get_cluster()	#determine the cluster based on the pbsadmin value in ctt.ini

try:
    if not sys.argv[1]:
        show_help()
except IndexError:  #??????                                                                                                                                                                                         
    show_help()

if '--auto' in sys.argv[1]:
    run_auto(date,severity,assignedto,updatedby,cluster)   
    exit(0)  

elif '--attach' in sys.argv[1]:
    # ./ctt.py --attach 1020 /tmp/ipmi_sdr_list.out
    import ntpath
    parser = argparse.ArgumentParser(add_help=False, description="Cluster Ticket Tracker Version 1.0.0")
    parser.add_argument('--attach', action='store', dest='attachment', nargs=2, required=True)    
    args = parser.parse_args()

    if args.attachment[0] and args.attachment[1]:  
        create_attachment(args.attachment[0],args.attachment[1],attach_location,date,updatedby)
        update_issue(args.attachment[0], 'updatedby', updatedby)
        update_issue(args.attachment[0], 'updatedtime', date) 
        filename = ntpath.basename(args.attachment[1])     
        log_history(args.attachment[0], date, updatedby, 'Attached file: %s/%s/%s.%s' % (attach_location, args.attachment[0], date[0:16], filename))	
        view_tracker_update(args.attachment[0],updatedby)    
    exit(0)

elif '--list' in sys.argv[1]:
    # ./ctt.py --list           # Shows all open
    # ./ctt.py --list -s closed	# Options: open, closed, deleted
    parser = argparse.ArgumentParser(add_help=False, description="Cluster Ticket Tracker Version 1.0.0")
    parser.add_argument('--list', action='store_true', dest='listvalue', default=True, required=True)
    parser.add_argument('-s', action='store', dest='statusvalue', choices=('open', 'closed', 'deleted'), required=False)
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

elif '--show' in sys.argv[1]:   #We want to see deleted issues as well!!!, FIX
    # ./ctt.py --show 1045
    parser = argparse.ArgumentParser(add_help=False, description="Cluster Ticket Tracker Version 1.0.0")
    parser.add_argument('--show', action='store', dest='issuenumber', nargs=1, required=True)    
    parser.add_argument('-d', action='store_true', default=False)
    args = parser.parse_args()

    if args.issuenumber[0]:
        get_issue_full(args.issuenumber[0])

    if args.d is True:
        get_history(args.issuenumber[0])

    view_tracker_update(args.issuenumber[0],updatedby)

elif '--update' in sys.argv[1]:
    # ./ctt.py --update 1039 -s 1 -c cheyenne -n r1i1n1 -t 689725 -a casg
    parser = argparse.ArgumentParser(add_help=False, description="Cluster Ticket Tracker Version 1.0.0")
    parser.add_argument('--update', action='store', dest='issuenumber', nargs=1, required=True)    
    parser.add_argument('-s','--severity', action='store', dest='severityvalue', choices=('1','2','3','4'), required=False)
    parser.add_argument('-c','--cluster', action='store', dest='clustervalue', required=False)
    parser.add_argument('-n','--node', action='store', dest='nodevalue', required=False)
    parser.add_argument('-t','--ticket', action='store', dest='ticketvalue', required=False)
    parser.add_argument('-a','--assign', action='store', dest='assignedtovalue', required=False)
    parser.add_argument('-i','--issuetitle', action='store', dest='issuetitlevalue', required=False)
    parser.add_argument('-d','--description', action='store', dest='descvalue', required=False)    
    parser.add_argument('-x', '--type', action='store', dest='typevalue', choices=('h','h!', 's', 't', 'u', 'o'), required=False)
    args = parser.parse_args()

    if args.typevalue:
        try:
            if args.issuenumber[0]:
                if args.typevalue == 'h!':
                    add_siblings(args.issuenumber[0],date,updatedby)
                    args.typevalue = 'h'
                update_issue(args.issuenumber[0], 'issuetype', args.typevalue)	# 1009 issuetype {hardware,software,test,unknown,other}
                update_issue(args.issuenumber[0], 'updatedby', updatedby)
                update_issue(args.issuenumber[0], 'updatedtime', date)
                view_tracker_new(args.issuenumber[0],updatedby,viewnotices)
                log_history(args.issuenumber[0],date,updatedby,'updated issue type to: %s' % (args.typevalue))
                #exit()
        except IndexError:
            parser.print_help()

    if args.issuetitlevalue:
        test_arg_size(args.issuetitlevalue,what='issue title',maxchars=100)
        try:
            if args.issuenumber[0]:
                update_issue(args.issuenumber[0], 'issuetitle', args.issuetitlevalue)
                update_issue(args.issuenumber[0], 'updatedby', updatedby)
                update_issue(args.issuenumber[0], 'updatedtime', date)
                view_tracker_new(args.issuenumber[0],updatedby,viewnotices)
                log_history(args.issuenumber[0],date,updatedby,'updated issue title to: %s' % (args.issuetitlevalue))
        except IndexError:
            parser.print_help()

    if args.descvalue:
        test_arg_size(args.descvalue,what='issue description',maxchars=4000)
        try:
            if args.issuenumber[0]:
                update_issue(args.issuenumber[0], 'issuedescription', args.descvalue)
                update_issue(args.issuenumber[0], 'updatedby', updatedby)
                update_issue(args.issuenumber[0], 'updatedtime', date)
                view_tracker_new(args.issuenumber[0],updatedby,viewnotices)
                log_history(args.issuenumber[0],date,updatedby,'updated issue description to: %s' % (args.descvalue))
        except IndexError:
            parser.print_help()

    if args.severityvalue:
        try:
            if args.issuenumber[0]:
                update_issue(args.issuenumber[0], 'severity', args.severityvalue)
                update_issue(args.issuenumber[0], 'updatedby', updatedby)
                update_issue(args.issuenumber[0], 'updatedtime', date)
                view_tracker_new(args.issuenumber[0],updatedby,viewnotices)
                log_history(args.issuenumber[0],date,updatedby,'updated issue severity to: %s' % (args.severityvalue))
        except IndexError:
            parser.print_help()

    if args.clustervalue:
        try:
            if args.issuenumber[0]:
                update_issue(args.issuenumber[0], 'cluster', args.clustervalue)
                update_issue(args.issuenumber[0], 'updatedby', updatedby)
                update_issue(args.issuenumber[0], 'updatedtime', date)
                view_tracker_new(args.issuenumber[0],updatedby,viewnotices)
                log_history(args.issuenumber[0],date,updatedby,'updated cluster to: %s' % (args.clustervalue))
        except IndexError:
            parser.print_help()

    if args.nodevalue:
        try:
            if args.issuenumber[0]:
                update_issue(args.issuenumber[0], 'node', args.nodevalue)
                update_issue(args.issuenumber[0], 'updatedby', updatedby)
                update_issue(args.issuenumber[0], 'updatedtime', date)
                view_tracker_new(args.issuenumber[0],updatedby,viewnotices)
                log_history(args.issuenumber[0],date,updatedby,'updated node to: %s' % (args.nodevalue))
        except IndexError:
            parser.print_help()

    if args.assignedtovalue:
        try:
            if args.issuenumber[0]:
                update_issue(args.issuenumber[0], 'assignedto', args.assignedtovalue)
                update_issue(args.issuenumber[0], 'updatedby', updatedby)
                update_issue(args.issuenumber[0], 'updatedtime', date)
                view_tracker_new(args.issuenumber[0],updatedby,viewnotices)
                log_history(args.issuenumber[0],date,updatedby,'assigned issue to: %s' % (args.assignedtovalue))
        except IndexError:
            parser.print_help()

    if args.ticketvalue:
        try:
            if args.issuenumber[0]:
                update_issue(args.issuenumber[0], 'ticket', args.ticketvalue)
                update_issue(args.issuenumber[0], 'updatedby', updatedby)
                update_issue(args.issuenumber[0], 'updatedtime', date)
                view_tracker_new(args.issuenumber[0],updatedby,viewnotices)
                log_history(args.issuenumber[0],date,updatedby,'updated ticket to: %s' % (args.ticketvalue))
        except IndexError:
            parser.print_help()

elif '--comment' in sys.argv[1]: 
    # ./ctt.py --comment 12390 "Need an update"
    parser = argparse.ArgumentParser(add_help=False, description="Cluster Ticket Tracker Version 1.0.0")
    parser.add_argument('--comment', action='store', dest='comment', nargs=2, required=True)    
    args = parser.parse_args()

    if args.comment[0] and args.comment[1]:   #add a check in comment function in lib to not comment if deleted or closed
        test_arg_size(args.comment[1],what='comment',maxchars=500)
        comment_issue(args.comment[0], date, updatedby, args.comment[1])
        update_issue(args.comment[0], 'updatedby', updatedby)
        update_issue(args.comment[0], 'updatedtime', date)
        log_history(args.comment[0], date, updatedby, 'commented issue with: %s' % (args.comment[1]))

elif '--delete' in sys.argv[1]:	#make where must be 'admin' to delete 
    # ./ctt.py --delete 10101 "Duplicate issue"
    parser = argparse.ArgumentParser(add_help=False, description="Cluster Ticket Tracker Version 1.0.0")
    parser.add_argument('--delete', action='store', dest='deletevalue', nargs=2, required=True) #NEED TO FIX DELETE   
    args = parser.parse_args()

    if args.deletevalue[0] and args.deletevalue[1]:
        test_arg_size(args.deletevalue[1],what='comment',maxchars=500)
        comment_issue(args.deletevalue[0], date, updatedby, args.deletevalue[1])
        delete_issue(args.deletevalue[0])
        update_issue(args.deletevalue[0], 'updatedby', updatedby)
        update_issue(args.deletevalue[0], 'updatedtime', date)
        log_history(args.deletevalue[0],date,updatedby,'deleted issue: %s' % (args.deletevalue[1]))

elif '--close' in sys.argv[1]:     # need to check if already deleted. also says closing sibs regardless if there are any attached.
    # ./ctt.py --close 10282 "Issue resolved"
    parser = argparse.ArgumentParser(add_help=False, description="Cluster Ticket Tracker Version 1.0.0")
    parser.add_argument('--close', action='store', dest='closevalue', nargs=2, required=True)    
    args = parser.parse_args()

    if args.closevalue[0] and args.closevalue[1]:
        test_arg_size(args.closevalue[1],what='comment',maxchars=500)
        comment_issue(args.closevalue[0], date, updatedby, args.closevalue[1])
        update_issue(args.closevalue[0], 'updatedby', updatedby)
        update_issue(args.closevalue[0], 'updatedtime', date)
        close_issue(args.closevalue[0], date, updatedby)
        log_history(args.closevalue[0], date, updatedby, 'closed issue: %s' % (args.closevalue[1]))

elif '--open' in sys.argv[1]:
    # ./ctt.py --open "Failed dimm on r1i1n1" "Description here" -c cheyenne -s 1 -n r1i1n1 -a casg
    parser = argparse.ArgumentParser(add_help=False, description="Cluster Ticket Tracker Version 1.0.0")
    parser.add_argument('--open', action='store', dest='openvalue', nargs='+', required=True)
    parser.add_argument('-s','--severity', action='store', dest='severityvalue', required=False)
    parser.add_argument('-c','--cluster', action='store', dest='clustervalue', required=True)
    parser.add_argument('-n','--node', action='store', dest='nodevalue', required=True)
    parser.add_argument('-a','--assign', action='store', dest='assignedtovalue', required=False)
    parser.add_argument('-t', '--ticket', action='store', dest='ticketvalue', required=False)
    parser.add_argument('-x', '--type', action='store', dest='typevalue', choices=('h', 's', 't', 'u', 'o'), required=False)    
    args = parser.parse_args()

    if args.assignedtovalue:
        assignedto = args.assignedtovalue
    if not args.ticketvalue:       #tagging an external ticket is optional
        args.ticketvalue = '----'
    if not args.typevalue:
        args.typevalue = 's'	#can set default ticket type in ini cfg later
    if not args.severityvalue:
        args.severityvalue = '3'    #can set default severity in ini cfg later


    if args.openvalue[0] and args.openvalue[1]:
        test_arg_size(args.openvalue[0],what='issue title',maxchars=100)
        test_arg_size(args.openvalue[1],what='issue description',maxchars=4000)
        cttissue = new_issue(date, args.severityvalue, args.ticketvalue, 'open', \
                         args.clustervalue, args.nodevalue, args.openvalue[0], \
                         args.openvalue[1], assignedto, updatedby, \
                         updatedby, args.typevalue, 'unknown', date)	#state (last item) is unknown initially until another run of ctt
        log_history(cttissue, date, updatedby, 'new issue')

elif '--help' in sys.argv[1] or '-h' in sys.argv[1]:
    show_help()

elif '--stats' in sys.argv[1]:
    from cttstats import *
    run_stats()
    exit(0)

else:
    show_help()

