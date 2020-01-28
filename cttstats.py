#!/usr/bin/env python3
import sqlite3 as SQL
#import textwrap
#from configparser import ConfigParser 
#import os
#import socket
#import sys
#import re

cols = "{0:<8}{1:<19}{2:<9}{3:<11}{4:<7}{5:<8}{6:<16}{7:<19}{8:<12}{9:<28}" 
fmt = cols.format




def run_stats():
#    print('Gathering Statistics...')

# stats:
# Open issues
# Closed issues
# Deleted issues
# Comments
# Issue Types (h,s,u,o,t)
# 	Hardware:
#	Software:
#	Unknown:
#	Testing:
#	Other:
# With associated ticket
# Node issue count
# Severity Counts (1,2,3,4)
#	Sev1:
#	Sev2:
#	Sev3:
#	Sev4:
# 
    
    ticket_list = []
    severity_list = []
    status_list = []
    issueoriginator_list = []

    con = SQL.connect('ctt.sqlite')
    cur = con.cursor()
    cur.execute('''SELECT * FROM issues''')
    data = cur.fetchall()
    
    for row in data:
        date = (row[2][0:16])
        severity = (row[3])
        if severity:
            severity_list.append(severity)
        ticket = (row[4])
        if ticket != '----':
            ticket_list.append(ticket)
        status = (row[5])
        if status != '----':
            status_list.append(status)
        cluster = (row[6])
        hostname = (row[7])
        issuetitle = (row[8])  
        assignedto = (row[10])
        issueoriginator = (row[11])
        if issueoriginator != '----':
            issueoriginator_list.append(issueoriginator)
        issuetype = (row[13])
        ##print("External Ticket: %s" % (ticket))
        #print("Date Opened: %s" % (date))
        #print("Assigned To: %s" % (assignedto))
        #print("Issue Originator: %s" % (issueoriginator))
        ##print("Severity: %s" % (severity))
        ##print("Status: %s" % (status))
        #print("Type: %s" % (issuetype))
        #print("Cluster: %s" % (cluster))
        #print("Hostname: %s" % (hostname))
        #print("Issue Title: %s" % (issuetitle))
        #print("\n------------------------------------------------------------")

    print("Issues with associated tickets: %s" % len(ticket_list))
    
    print("\nSeverity Counts:")
    print("Sev 1: %s" % severity_list.count(1))
    print("Sev 2: %s" % severity_list.count(2))
    print("Sev 3: %s" % severity_list.count(3))
    print("Sev 4: %s" % severity_list.count(4))

    print("\nIssue status counts:")
    print("open: %s" % status_list.count('open'))
    print("closed: %s" % status_list.count('closed'))
    print("deleted: %s" % status_list.count('deleted'))

    print("\nIssue Originator:")
    print("ctt: %s" % issueoriginator_list.count('ctt'))
    print("ssg: %s" % issueoriginator_list.count('ssg'))
    print("casg: %s" % issueoriginator_list.count('casg'))
    




    con.close()

