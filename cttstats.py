#!/usr/bin/env python3
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


cols = "{0:<8}{1:<19}{2:<9}{3:<11}{4:<7}{5:<8}{6:<16}{7:<19}{8:<12}{9:<28}" 
fmt = cols.format

def run_stats_node(nodevalue):
    con = SQL.connect('ctt.sqlite')
    cur = con.cursor()
    cur.execute('''SELECT * FROM issues WHERE hostname = ?''', (nodevalue,))
    data = cur.fetchall()

    for row in data:
        print(row)

    con.close()


def run_stats_counts():
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
        status = (row[5])
        if status != '---':
            status_list.append(status)
        cluster = (row[6])
        hostname = (row[7])
        issuetitle = (row[8])  
        assignedto = (row[10])
#        issueoriginator = (row[11])
#        if issueoriginator != '---':
#            issueoriginator_list.append(issueoriginator)
#        issuetype = (row[13])


    print("\nSeverity,count")
    print("1,%s" % severity_list.count(1))
    print("2,%s" % severity_list.count(2))
    print("3,%s" % severity_list.count(3))
    print("4,%s" % severity_list.count(4))

    print("\nIssue status,count")
    print("open,%s" % status_list.count('open'))
    print("closed,%s" % status_list.count('closed'))
    print("deleted,%s\n" % status_list.count('deleted'))

#    print("\nIssue Originator,count")
#    print(issueoriginator_list)
#    print("ctt,%s" % issueoriginator_list.count('ctt'))
#    print("hsg,%s" % issueoriginator_list.count('hsg'))
#    print("casg,%s\n" % issueoriginator_list.count('casg'))
    

    cur.execute('''SELECT hostname, COUNT(*) FROM issues GROUP BY hostname ORDER BY hostname''')
    data = cur.fetchall()
    print("Issues per node,count")
    for row in data:
        if row[0] !=  '---':
            print("%s,%s" % (row[0], row[1]))





















    con.close()

