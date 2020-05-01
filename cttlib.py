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
import textwrap
from configparser import ConfigParser 
import os
import socket
import sys
import re


config = ConfigParser()
config.read('ctt.ini')                                                                                                                                                                          
defaults = config['DEFAULTS'] 
pbsadmin = defaults['pbsadmin']
users = config['USERS']
viewnotices = users['viewnotices']
pbsnodes_path = defaults['pbsnodes_path']                                                                                                
clush_path = defaults['clush_path']
maxissuesopen = defaults['maxissuesopen'] #ONLY USED WITH AUTO, CAN STILL MANUALLY OPEN ISSUES
maxissuesrun = defaults['maxissuesrun']


def maxissueopen_issue():
    con = SQL.connect('ctt.sqlite')
    cur = con.cursor()
    cur.execute('''SELECT * FROM issues WHERE status = ? and issuetitle = ?''', ('open', 'MAX OPEN REACHED'))
    if cur.fetchone() == None:
        return False


def get_open_count():
    con = SQL.connect('ctt.sqlite')
    cur = con.cursor()
    cur.execute('''SELECT * FROM issues WHERE status = ?''', ('open',))
    return len(cur.fetchall())


def create_attachment(cttissue,filepath,attach_location,date,updatedby):
    import shutil
    if os.path.isfile(filepath) is False:
        print('File %s does not exist, Exiting!' % (filepath))
        exit(1)
    if os.path.exists(attach_location) is False:
        print('Attachment root location does not exist. Check ctt.ini attach_location setting')
        exit(1)
    if issue_exists_check(cttissue) is False:
        print('ctt issue %s is not open. Can not attach a file to a closed, deleted, or nonexisting issue' % (cttissue))
        exit(1)
    newdir = "%s/%s" % (attach_location,cttissue)
    if os.path.exists(newdir) is False:
        os.mkdir(newdir)
    thefile = os.path.basename(filepath)
    destination_file = "%s.%s" % (date[0:16],thefile)
    final_destination_file = "%s/%s" % (newdir,destination_file) 
    shutil.copy(filepath, final_destination_file)
    if os.path.isfile(final_destination_file) is True:
        print("File attached to %s" % (cttissue))
    else:
        print("Error: File not attached, unknown error")


def sibling_open_check(node):
    con = SQL.connect('ctt.sqlite')
    with con:
        cur = con.cursor()
        cur.execute('''SELECT rowid FROM siblings WHERE status = ? and sibling = ?''', ('open', node,))
        data = cur.fetchone()
        if data is None:
            return False
        else:
            return True


def update_sibling(node, state):
    con = SQL.connect('ctt.sqlite')
    with con:
        cur = con.cursor()
        cur.execute('''UPDATE siblings SET state = ? WHERE sibling = ? and status = ?''', (state, node, 'open',))
        print("Updated sibling %s to pbs state: %s" % (node, state))


def run_auto(date,severity,assignedto,updatedby,cluster):
    try:
        pbs_states_csv = os.popen("{0} -Nw {1} {2} -av -Fdsv -D,".format(clush_path, pbsadmin, pbsnodes_path)).readlines()
    except:
        print('Can not get pbsnodes data from admin node, exiting!')
        exit()

    newissuedict = {} 
    if int(maxissuesopen) != int(0):                                                                                                                        
        open_count = get_open_count()                                                                                                                       
        if open_count >= int(maxissuesopen):                                                                                                                
            if maxissueopen_issue() is False:                                                                                                               
                print('Maximum number of issues (%s) reached for --auto' % (maxissuesopen))                                                                 
                print('Can not process --auto')                                                                                                             
                details = "To gather nodes and failures, increase maxissuesopen"                                                                            
                cttissue = new_issue(date, '1', '---', 'open', \
                            cluster, 'FATAL', 'MAX OPEN REACHED', \
                            details, 'FATAL', 'FATAL', \
                            'FATAL', 'o', 'FATAL', date)                                                                                                    
                log_history(cttissue, date, updatedby, 'new issue')                                                                                         
            exit(1) 
    for line in pbs_states_csv:
        splitline = line.split(",")
        node = splitline[0] 
        x,node = node.split('=')
        state = splitline[5]
        x,state = state.split('=')
        #known pbs states: 'free', 'job-busy', 'job-exclusive', 
        #'resv-exclusive', offline, down, provisioning, wait-provisioning, stale, state-unknown

        if sibling_open_check(node) is True:
            update_sibling(node, state)

        if node_open_check(node) is True:  #update node state if open issue on node and state changed
            cttissue = check_node_state(node,state)
            if cttissue is None:	#no change in state
                next
            else:			#change in pbs state
                cttissue = ''.join(cttissue)
                update_issue(cttissue, 'state', state)  
                update_issue(cttissue, 'updatedby', 'ctt')
                update_issue(cttissue, 'updatedtime', date)
                log_history(cttissue, date, 'ctt', 'state changed to %s' % (state))

        elif state in ('state-unknown', 'offline', 'down'):	#if no issue on node     
            for item in splitline:
                if 'comment=' in item:
                    x,comment = item.split('=')
                    if comment == ' ':
                        comment = 'Unknown Reason'
                    if node_open_check(node) is False:	#Prevents duplicate issues on node 
                        hostname = node
                        newissuedict[hostname]=comment
    if len(newissuedict) != 0 and len(newissuedict) <= int(maxissuesrun):
        status = 'open'
        ticket = '---'
        updatedby = 'ctt'
        issuetype = 'u'
        issueoriginator = 'ctt'
        updatedtime = date
        updatedtime = updatedtime[:-10]
        assignedto = 'ctt'
        state = 'unknown'	 
        for hostname,comment in newissuedict.items():
            issuetitle = issuedescription = comment
            cttissue = new_issue(date,severity,ticket,status,cluster,hostname,issuetitle, \
                                 issuedescription,assignedto,issueoriginator,updatedby,issuetype,state,updatedtime)                        
            print("%s state is %s with comment: %s" %(hostname, state, comment))  #####
            log_history(cttissue, date, 'ctt', 'new issue')
    elif len(newissuedict) >= int(maxissuesrun):
        print('Maximum number of issues reached for --auto')                                                                  
        print('Can not process --auto')                                                                                                             
        details = "This run of ctt discovered more issues than maxissuesrun. \
                   Discovered: %s; maxissuesrun: %s\n\n %s" % (len(newissuedict), maxissuesrun, newissuedict)                                                                           
        cttissue = new_issue(date, '1', '---', 'open', \
                             cluster, 'FATAL', 'MAX RUN REACHED: %s/%s' % (len(newissuedict), maxissuesrun), \
                             details, 'FATAL', 'FATAL', \
                             'FATAL', 'o', 'FATAL', date)                                                                                                    
        log_history(cttissue, date, 'ctt', 'new issue')                                                                                         
        exit(1)


def test_arg_size(arg,what,maxchars):
    size = sys.getsizeof(arg)
    if int(size) > int(maxchars):
        print("Maximum argument size of %s characters reached for %s. Exiting!" % (maxchars,what))
        exit(1)


def view_tracker_new(cttissue,updatedby,viewnotices):        #used for new issues and updates
    userlist = []                               
    for user in viewnotices.split(' '):
        if updatedby == user:
            next       
        else:
            userlist.append(user)       
    if userlist:
        userlist = '.'.join(userlist)
    else:
        userlist = "----"

    con = SQL.connect('ctt.sqlite')
    with con:
        cur = con.cursor()
        cur.execute('''UPDATE issues SET viewtracker = ? WHERE cttissue = ?''', (userlist, cttissue))


def view_tracker_update(cttissue,updatedby):	#used to update viewtracker column when a user runs --show
    con = SQL.connect('ctt.sqlite')
    with con:
        cur = con.cursor()
        cur.execute('''SELECT * FROM issues WHERE cttissue = ?''', (cttissue,))
        for row in cur:
            userlist = (row[16])
            userlist = userlist.split('.')
            if updatedby in userlist:
                userlist.remove(updatedby)
            userlist = '.'.join(userlist)
            if not userlist:
                userlist = '----'
            cur.execute('''UPDATE issues SET viewtracker = ? WHERE cttissue = ?''', (userlist, cttissue))


def get_pbs_sib_state(node):
    con = SQL.connect('ctt.sqlite')
    with con:
        cur = con.cursor()
        cur.execute('''SELECT state FROM siblings WHERE sibling = ? and status = ?''', (node, 'open',))
        state = cur.fetchone()
        #print(state)	#test
        return state        


def set_pbs_offline(node, comment):  #### NOT USED YET
    if comment:		#do we want to update/change comment???
        return os.popen("%s -Nw %s %s -o -C %s %s" % (clush_path, pbsadmin, pbsnodes_path, comment, node))
    else:
        return run_task("%s -o %s" % (pbsnodes_path, node))   #FIX???


def set_pbs_online(node, comment):	#### NOT USED YET    
    if comment:		# we want to clear previous comment out
        return os.popen("%s -Nw %s %s -r -C %s %s" % (clush_path, pbsadmin, pbsnodes_path, comment, node))
    else:
        return os.popen("%s -Nw %s %s -r %s" % (clush_path, pbsadmin, pbsnodes_path, node))


def get_hostname(cttissue):
    con = SQL.connect('ctt.sqlite')
    with con:
        cur = con.cursor()
        cur.execute('''SELECT hostname FROM issues WHERE cttissue = ? and status = ?''', (cttissue,'open',))
        hostname = cur.fetchone()
        if hostname:
            return hostname


def add_siblings(cttissue,date,updatedby): #need to run a drain function (set_pbs_offline()) on the siblings when adding!!!
    node = get_hostname(cttissue)
    node = ''.join(node)	#tuple to str
    try:
        nodes = resolve_siblings(node)
    except:
        print("Can not get siblings. Check node name.")
        exit(1)

    for sib in nodes:
        if node != sib:
            con = SQL.connect('ctt.sqlite')
            with con:
                cur = con.cursor()
                cur.execute('''INSERT INTO siblings(
                        cttissue,date,status,parent,sibling,state)
                        VALUES(?, ?, ?, ?, ?, ?)''',
                        (cttissue, date, 'open', node, sib, '---'))
                print("Attached sibling %s to issue %s" % (sib,cttissue))

        info = "Attached sibling %s to issue" % (sib)
        log_history(cttissue, date, updatedby, info)
    return


def node_to_tuple(n):	#used by add_siblings()
    m = re.match("([rR])([0-9]+)([iI])([0-9]+)([nN])([0-9]+)", n)
    if m is not None:
        #(rack, iru, node)
        return (int(m.group(2)), int(m.group(4)), int(m.group(6)))
    else:
        return None


def resolve_siblings(node): 	#used by add_siblings()
    nodes_per_blade = 4
    slots_per_iru = 9
#    if re.search("^la", socket.gethostname()) is None:               #FIX ME!!!
#        nodes_per_blade = 2
    """ resolve out list of sibling nodes to given set of nodes """
    result = []
    nt = node_to_tuple(node)
    for i in range(0,nodes_per_blade):
        nid = (nt[2] % slots_per_iru) + (i*slots_per_iru)
        nodename = "r%di%dn%d" % (nt[0], nt[1], nid)

        if not nodename in result:
            result.append(nodename)
    return result


def check_node_state(node, state): 	#checks if node has open issue, returns cttissue number
    con = SQL.connect('ctt.sqlite')
    with con:
        cur = con.cursor()
        cur.execute('''SELECT cttissue FROM issues WHERE hostname = ? and state != ? and status = ?''', (node,state,'open',))
        result = cur.fetchone()
        if result:
            return result


def node_open_check(node):	#checks if node has open issue
    con = SQL.connect('ctt.sqlite')
    with con:
        cur = con.cursor()
        cur.execute('''SELECT rowid FROM issues WHERE hostname = ? and status = "open"''', (node,))
        data=cur.fetchone()
        if data is None:
            return False
        else:
            return True    


def check_nolocal():                                                                                                                                                      
    if os.path.isfile('/etc/nolocal'):                                                                                                                                                
        print("/etc/nolocal exists, exiting!")
        exit(1)


def get_history(cttissue):	#used only when issuing --show with -d option
    if issue_exists_check(cttissue):
        cols = "{0:<24}{1:<14}{2:<50}"
        fmt = cols.format
        print("\n----------------------------------------")    
        print(fmt("DATE", "UPDATE.BY", "INFO"))    
        con = SQL.connect('ctt.sqlite')
        with con:
            cur = con.cursor()
            cur.execute('''SELECT * FROM history WHERE cttissue = ?''', (cttissue,))
            for row in cur:
                date = (row[2][0:16])
                updatedby = (row[3])
                info = (row[4])

                print(fmt("%s" % date, "%s" % updatedby, "%s" % textwrap.fill(info, width=80)))
    else:
        return


def log_history(cttissue, date, updatedby, info): 
    if issue_deleted_check(cttissue) is False or issue_exists_check(cttissue) is True:
        con = SQL.connect('ctt.sqlite')
        with con:
            cur = con.cursor()
            cur.execute('''INSERT INTO history(
                     cttissue,date,updatedby,info)
                     VALUES(?, ?, ?, ?)''',
                     (cttissue, date, updatedby, info))
        return
    else:
        return


def get_issue_full(cttissue):	#used for the --show option
    if issue_exists_check(cttissue) is True:
        con = SQL.connect('ctt.sqlite')
        with con:
            cur = con.cursor()
            cur.execute('''SELECT * FROM issues WHERE cttissue = ?''', (cttissue,))
            for row in cur:
                cttissue = (row[1])  
                date = (row[2][0:16])
                severity = (row[3])
                ticket = (row[4])
                status = (row[5])
                cluster = (row[6])
                hostname = (row[7])
                issuetitle = (row[8])  
                issuedescription = (row[9])
                assignedto = (row[10])
                issueoriginator = (row[11])
                updatedby = (row[12])
                issuetype = (row[13])
                state = (row[14])
                updatedtime = (row[15][0:16])
                print("ctt Issue: %s" % (cttissue))
                print("External Ticket: %s" % (ticket))
                print("Date Opened: %s" % (date))
                print("Assigned To: %s" % (assignedto))
                print("Issue Originator: %s" % (issueoriginator))
                print("Last Updated By: %s" % (updatedby))
                print("Last Update Time: %s" % (updatedtime))
                print("Severity: %s" % (severity))
                print("Status: %s" % (status))
                print("Type: %s" % (issuetype))
                print("Cluster: %s" % (cluster))
                print("Hostname: %s" % (hostname))
                print("Node State: %s" % (state))
                if check_has_sibs(cttissue) is True:
                    print("Attached Siblings:")
                    sibs = resolve_siblings(hostname)
                    for node in sibs:
                        if node != hostname:
                            state = get_pbs_sib_state(node)
                            state = ' '.join(state)
                            print('%s state = %s' % (node,state))
                else:
                    print("Attached Siblings: None")
                print("----------------------------------------")
                print("\nIssue Title:\n%s" % (issuetitle))
                print("\nIssue Description:") 
                print(textwrap.fill(issuedescription, width=60))
                print("\n----------------------------------------")
                get_comments(cttissue)
    else:
        print("Issue not found")


def get_comments(cttissue):	#used for --show option (displays the comments)
    if issue_deleted_check(cttissue) is False and issue_exists_check(cttissue) is True:
        con = SQL.connect('ctt.sqlite')
        with con:
            cur = con.cursor()
            cur.execute('''SELECT * FROM comments WHERE cttissue = ?''', (cttissue,))
            for row in cur:
                date = (row[2][0:16])
                updatedby = (row[3])
                comment = (row[4])

                print("\nComment by: %s at %s" % (updatedby, date))
                print(textwrap.fill(comment, width=60))


def comment_issue(cttissue, date, updatedby, newcomment):
    if issue_deleted_check(cttissue) is False and issue_exists_check(cttissue) is True:
        con = SQL.connect('ctt.sqlite')
        with con:
            cur = con.cursor()
            cur.execute('''INSERT INTO comments(
                    cttissue,date,updatedby, comment)
                    VALUES(?, ?, ?, ?)''',
                    (cttissue, date, updatedby, newcomment))
            #print("Comment added to issue %s" % (cttissue))
    else: 
        print("Can't add comment to %s. Issue not found or deleted" % (cttissue))
        exit()

    view_tracker_new(cttissue,updatedby,viewnotices)   
    return


def issue_exists_check(cttissue):	#checks if a cttissue exists
    con = SQL.connect('ctt.sqlite')
    with con:
        cur = con.cursor()
        cur.execute('''SELECT rowid FROM issues WHERE cttissue = ?''', (cttissue,))
        data=cur.fetchone()
        if data is None:
            return False
        else:
            return True


def update_issue(cttissue, updatewhat, updatedata):        
    if issue_deleted_check(cttissue) is False and issue_exists_check(cttissue) is True:
        con = SQL.connect('ctt.sqlite')
        with con:
            cur = con.cursor()
            cur.execute('''UPDATE issues SET {0} = ? WHERE cttissue = ?'''.format(updatewhat), (updatedata, cttissue))    
            print("ctt issue %s updated: %s" % (cttissue, updatewhat))
    else:
        print("ctt issue %s not found or deleted" % (cttissue))
    

def check_has_sibs(cttissue):
    con = SQL.connect('ctt.sqlite')
    with con:
        cur = con.cursor()
        cur.execute('''SELECT rowid FROM siblings WHERE cttissue = ? and status = ?''', (cttissue,'open'))
        data = cur.fetchone()
        if data is None:
            next
        else:
            return True


def get_issues(statustype):	#used for the --list option
    cols = "{0:<8}{1:<19}{2:<9}{3:<13}{4:<16}{5:<6}{6:<7}{7:<8}{8:<12}{9:<28}"
    fmt = cols.format    
    print(fmt("ISSUE", "DATE", "TICKET", "HOSTNAME", "STATE", "SEV", "TYPE", "OWNER", "UNSEEN", "TITLE (25 chars)"))
    con = SQL.connect('ctt.sqlite')
    with con:
        cur = con.cursor()
        print(statustype)
        if 'all' in statustype:
            cur.execute('''SELECT * FROM issues ORDER BY id ASC''')
        else:
            cur.execute('''SELECT * FROM issues WHERE status = ? ORDER BY id ASC''', (statustype,))
        for row in cur:
            cttissue = (row[1])  #broke up all cells just-in-case we need them. Can remove later what isnt needed.
            date = (row[2][0:16])
            severity = (row[3])
            ticket = (row[4])
            if '---' not in ticket:
                ticket = 'yes'
            status = (row[5])
            cluster = (row[6])
            hostname = (row[7])
            issuetitle = (row[8][:25])	#truncated to xx characters 
            issuedescription = (row[9])
            assignedto = (row[10])
            issueoriginator = (row[11])
            updatedby = (row[12])
            issuetype = (row[13])
            state = (row[14])
            updatedtime = (row[15][0:16])
            viewtracker = (row[16])
            print(fmt("%s" % cttissue, "%s" % date, "%s" % ticket, "%s" % hostname, "%s" % state, \
                      "%s" % severity, "%s" % issuetype, "%s" % assignedto, "%s" % viewtracker, "%s" % issuetitle))
            if check_has_sibs(cttissue) is True:
                sibs = resolve_siblings(hostname)
                for node in sibs:
                    if node != hostname:
                        state = get_pbs_sib_state(node) 
                        state = ''.join(state)
                        issuetitle = "Sibling to %s" % (hostname)
                        issuetype = 'o'
                        print(fmt("%s" % cttissue, "%s" % date, "%s" % ticket, "%s" % node, "%s" % state, \
                                  "%s" % severity, "%s" % issuetype, "%s" % assignedto, "%s" % viewtracker, \
                                  "%s" % issuetitle ))


def get_issues_vv(statustype):   # -vv option
    cols = "{0:<8}{1:<19}{2:<9}{3:<13}{4:<16}{5:<6}{6:<7}{7:<8}{8:<12}{9:<12}{10:<8}{11:<10}{12:<19}{13:<10}{14:<20}{15:<22}"  
    fmt = cols.format
    print(fmt("ISSUE", "DATE", "TICKET", "HOSTNAME", "STATE", "SEV", "TYPE", "OWNER", "UNSEEN", "CLUSTER", "ORIG", "UPD.BY", "UPD.TIME", "STATUS", "TITLE", "DESC"))
    con = SQL.connect('ctt.sqlite')
    with con:
        cur = con.cursor()
        if 'all' in statustype:
            cur.execute('''SELECT * FROM issues ORDER BY id ASC''')
        else:
            cur.execute('''SELECT * FROM issues WHERE status = ? ORDER BY id ASC''', (statustype,))
        for row in cur:  #-v option
            cttissue = (row[1])                                                                                                                                    
            date = (row[2][0:16])                                                                                                                                  
            severity = (row[3])                                                                                                                                    
            ticket = (row[4])                                                                                                                                      
            status = (row[5])                                                                                                                                      
            cluster = (row[6])                                                                                                                                     
            hostname = (row[7])                                                                                                                                    
            issuetitle = (row[8])	#[:25])                                                                                                                                  
            issuedescription = (row[9])     #in -vv option                                                                                                                       
            assignedto = (row[10])                                                                                                                                 
            issueoriginator = (row[11])                                                                                                                            
            updatedby = (row[12])                                                                                                                                  
            issuetype = (row[13])                                                                                                                                  
            state = (row[14])                                                                                                                                      
            updatedtime = (row[15][0:16]) 
            viewtracker = (row[16]) 
            cols = "{0:<8}{1:<19}{2:<9}{3:<13}{4:<16}{5:<6}{6:<7}{7:<8}{8:<12}{9:<12}{10:<8}{11:<10}{12:<19}{13:<10}{14:<20}{15:<%s}" % (len(issuetitle) + 10)  #get len(issuetiel) and insert plus a few?
            fmt = cols.format                                                                                                               
            print(fmt("%s" % cttissue, "%s" % date, "%s" % ticket, "%s" % hostname, "%s" % state, "%s" % severity, \
                      "%s" % issuetype, "%s" % assignedto, "%s" % viewtracker, "%s" % cluster, "%s" % issueoriginator, "%s" % updatedby, \
                      "%s" % updatedtime, "%s" % status, "%s" % issuetitle, "%s" % issuedescription))
            if check_has_sibs(cttissue) is True:
                sibs = resolve_siblings(hostname)
                for node in sibs:
                    if node != hostname:
                        state = get_pbs_sib_state(node) 
                        state = ''.join(state)
                        issuetitle = "Sibling to %s" % (hostname)
                        issuetype = 'o'
                        print(fmt("%s" % cttissue, "%s" % date, "%s" % ticket, "%s" % hostname, "%s" % state, "%s" % severity, \
                                   "%s" % issuetype, "%s" % assignedto, "%s" % viewtracker, "%s" % cluster, "%s" % issueoriginator, "%s" % updatedby, \
                                   "%s" % updatedtime, "%s" % status, "%s" % issuetitle, "%s" % issuedescription))


def get_issues_v(statustype):	# -v option
    cols = "{0:<8}{1:<19}{2:<9}{3:<13}{4:<16}{5:<6}{6:<7}{7:<8}{8:<12}{9:<12}{10:<8}{11:<10}{12:<19}{13:<10}{14:<22}"
    fmt = cols.format
    print(fmt("ISSUE", "DATE", "TICKET", "HOSTNAME", "STATE", "SEV", "TYPE", "OWNER", "UNSEEN", "CLUSTER", "ORIG", "UPD.BY", "UPD.TIME", "STATUS", "TITLE (25 chars)"))
    con = SQL.connect('ctt.sqlite')
    with con:
        cur = con.cursor()
        if 'all' in statustype:
            cur.execute('''SELECT * FROM issues ORDER BY id ASC''')
        else:
            cur.execute('''SELECT * FROM issues WHERE status = ? ORDER BY id ASC''', (statustype,))
        for row in cur:  #-v option
            cttissue = (row[1])                                                                                                                                    
            date = (row[2][0:16])                                                                                                                                  
            severity = (row[3])                                                                                                                                    
            ticket = (row[4])                                                                                                                                      
            status = (row[5])                                                                                                                                      
            cluster = (row[6])                                                                                                                                     
            hostname = (row[7])                                                                                                                                    
            issuetitle = (row[8][:25])                                                                                                                                  
            issuedescription = (row[9])     #in -vv option                                                                                                                       
            assignedto = (row[10])                                                                                                                                 
            issueoriginator = (row[11])                                                                                                                            
            updatedby = (row[12])                                                                                                                                  
            issuetype = (row[13])                                                                                                                                  
            state = (row[14])                                                                                                                                      
            updatedtime = (row[15][0:16]) 
            viewtracker = (row[16]) 
     
            print(fmt("%s" % cttissue, "%s" % date, "%s" % ticket, "%s" % hostname, "%s" % state, "%s" % severity, \
                      "%s" % issuetype, "%s" % assignedto, "%s" % viewtracker, "%s" % cluster, "%s" % issueoriginator, "%s" % updatedby, \
                      "%s" % updatedtime, "%s" % status, "%s" % issuetitle))
            if check_has_sibs(cttissue) is True:
                sibs = resolve_siblings(hostname)
                for node in sibs:
                    if node != hostname:
                        state = get_pbs_sib_state(node) 
                        state = ''.join(state)
                        issuetitle = "Sibling to %s" % (hostname)
                        issuetype = 'o'
                        print(fmt("%s" % cttissue, "%s" % date, "%s" % ticket, "%s" % hostname, "%s" % state, "%s" % severity, \
                                   "%s" % issuetype, "%s" % assignedto, "%s" % viewtracker, "%s" % cluster, "%s" % issueoriginator, "%s" % updatedby, \
                                   "%s" % updatedtime, "%s" % status, "%s" % issuetitle))


def issue_closed_check(cttissue):	#TO DO LATER: CHANGE ALL THE issue_xxxx_check functions to get_issue_status(cttissue,STATUS) and return True||False
    con = SQL.connect('ctt.sqlite')
    with con:
        cur = con.cursor()
        cur.execute('''SELECT rowid FROM issues WHERE cttissue = ? and status = ?''', (cttissue, 'closed'))
        data = cur.fetchone()
        if data is None:
            return False
        else:
            return True


def issue_deleted_check(cttissue):	#checks if cttissue is deleted
    con = SQL.connect('ctt.sqlite')
    with con:
        cur = con.cursor()
        cur.execute('''SELECT rowid FROM issues WHERE cttissue = ? and status = ?''', (cttissue, 'deleted'))
        data=cur.fetchone()
        if data is None:
            return False
        else:
            return True


def delete_issue(cttissue): #check to make sure admin only runs this???    Add sib check and close sibs if deleting???
    if issue_deleted_check(cttissue) is False and issue_exists_check(cttissue) is True:
        con = SQL.connect('ctt.sqlite')
        with con:
            cur = con.cursor()
            cur.execute('''UPDATE issues SET status = ? WHERE cttissue = ?''', ('deleted', cttissue))
            print("ctt issue %s deleted" % (cttissue))


def close_and_resume_issue(cttissue,date,updatedby,nodes2resume):
    con = SQL.connect('ctt.sqlite')
    with con:            
        cur = con.cursor()
        cur.execute('''UPDATE siblings SET status = ? WHERE cttissue = ?''', ('closed', cttissue))
        #print("Detached siblings")	#for testing 
        cur.execute('''UPDATE issues SET status = ? WHERE cttissue = ?''', ('closed', cttissue))
        print("ctt issue %s closed" % (cttissue))
 
    log_history(cttissue,date,updatedby, 'Detached Siblings')

    if 'noresume' in nodes2resume:
        #print('Not resuming any nodes')	#test message
        next
    if 'noresume' not in nodes2resume:
        for node in nodes2resume:
            print('%s: Resume nodes function here' % (node))

    exit()


def close_issue(cttissue, date, updatedby):
    if issue_deleted_check(cttissue) is False and issue_exists_check(cttissue) is True and check_for_siblings(cttissue) is False:	#no siblings attached to cttissue
        node = get_hostname(cttissue)
        node = ''.join(node)
        nodes2resume = []
        con = SQL.connect('ctt.sqlite')
        with con:				#1. Another issue with same node?
            cur = con.cursor()
            cur.execute('''SELECT rowid FROM issues WHERE hostname = ? and status = ? and cttissue != ?''', (node, 'open', cttissue,))
            data = cur.fetchone()
            if data is None:
                #print('continue to check if #2... - 1')
                next 
            else:
                print('There is another issue for this node, closing cttissue, but not resuming in pbs - 1')
                nodes2resume.append('noresume')				
                close_and_resume_issue(cttissue,date,updatedby,nodes2resume)                
        
        with con:				#2. In siblings table as sibling for a different issue?
            cur = con.cursor()
            cur.execute('''SELECT rowid FROM siblings WHERE cttissue != ? and status = ? and sibling = ?''', (cttissue, 'open', node,))
            data = cur.fetchone()
            if data is None:
                #print('ok to close cttissue and resume in pbs - 2')
                nodes2resume.append(node)
                close_and_resume_issue(cttissue,date,updatedby,nodes2resume)
            else:
                print('This node is a sibling to another cttissue, closing cttissue, but not resuming in pbs - 2')
                nodes2resume.append('noresume')
                close_and_resume_issue(cttissue,date,updatedby,nodes2resume)

    if issue_deleted_check(cttissue) is False and issue_exists_check(cttissue) is True and check_for_siblings(cttissue) is True:	#3. Are siblings in siblings table for another cttissue. #this if statement checks if the cttissue has sibs attached.
        node = get_hostname(cttissue)
        node = ''.join(node)
        allnodes = resolve_siblings(node)
        nodes2resume = []
        con = SQL.connect('ctt.sqlite')
        for sibnode in allnodes:
            with con:			 
                cur = con.cursor()
                cur.execute('''SELECT rowid FROM siblings WHERE sibling = ? and status = ? and cttissue != ?''', (sibnode, 'open', cttissue,))
                data = cur.fetchone()
                if data is None:
                    #print('continue to check if #4... - 3')
                    next
                else:
                    print('%s is a sibling for another cttissue. No nodes will be resumed, but cttissue will be closed. - 3' % (sibnode))
                    nodes2resume.append('noresume')                    
                    close_and_resume_issue(cttissue,date,updatedby,nodes2resume)

            with con:		#4. If has siblings attached, Do the siblings have a cttissue?
                cur = con.cursor()
                cur.execute('''SELECT rowid FROM issues WHERE cttissue != ? and status = ? and hostname = ?''', (cttissue, 'open', sibnode,))
                data = cur.fetchone()
                if data is None:
                    #print('node %s can be resumed - 4' % (sibnode))
                    nodes2resume.append(sibnode) 
                else:
                    print('Can not resume sibnode %s. sibnode has cttissue  - 4' % (sibnode))
    
    close_and_resume_issue(cttissue,date,updatedby,nodes2resume)


def check_for_siblings(cttissue):
    con = SQL.connect('ctt.sqlite')
    with con:
        cur = con.cursor()
        cur.execute('''SELECT * from siblings WHERE cttissue = ? and status = ?''', (cttissue, 'open',))
        if cur.fetchone() is None:
            return False	#no siblings
        else:
            return True     #has siblings


def assign_issue(cttissue, assignto):	#assign to another person       
    if issue_deleted_check(cttissue) is False and issue_exists_check(cttissue) is True:
        con = SQL.connect('ctt.sqlite')
        with con:
            cur = con.cursor()
            cur.execute('''UPDATE issues SET assignedto = ? WHERE cttissue = ?''', (assignto, cttissue))
            print("ctt issue %s assigned to %s" % (cttissue, assignto))	
    else:
        print("ctt issue %s not found or deleted" % (cttissue))


def get_new_cttissue():		#generates/gets the next cttissue number
    con = SQL.connect('ctt.sqlite')
    with con:
        cur = con.cursor()
        cur.execute('''SELECT * FROM issues ORDER BY rowid DESC LIMIT 1''')
        for row in cur:
            return int(row[1]) + 1


def new_issue(date,severity,ticket,status,cluster,hostname,issuetitle, \
		issuedescription,assignedto,issueoriginator,updatedby,issuetype,state,updatedtime):
    cttissue = get_new_cttissue()
    print("ctt issue %s opened" % (cttissue))
    con = SQL.connect('ctt.sqlite')
    with con:
        cur = con.cursor()
        cur.execute('''INSERT INTO issues(
		cttissue,date,severity,ticket,status,
                cluster,hostname,issuetitle,issuedescription,assignedto,
                issueoriginator,updatedby,issuetype,state,updatedtime)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                (cttissue, date, severity, ticket, status, cluster, hostname, 
                    issuetitle, issuedescription, assignedto, issueoriginator, 
                    updatedby, issuetype, state, updatedtime))

    view_tracker_new(cttissue,updatedby,viewnotices)
    return cttissue #for log_history


def checkdb(date):		#checks the ctt db if tables and/or db itself exists. Creates if not
    cttissuestart = 1000 	#the start number for cttissues     
    con = SQL.connect('ctt.sqlite')
    with con:
        cur = con.cursor()
        cur.execute('''SELECT name FROM sqlite_master WHERE type="table" AND name="issues"''')
        if cur.fetchone() is None:
            cur.execute('''CREATE TABLE IF NOT EXISTS issues(
		    id INTEGER PRIMARY KEY,
		    cttissue TEXT NOT NULL,
		    date TEXT NOT NULL,
		    severity INT NOT NULL,
		    ticket TEXT,
		    status TEXT NOT NULL,
		    cluster TEXT NOT NULL,
		    hostname TEXT NOT NULL,
		    issuetitle TEXT NOT NULL,
		    issuedescription TEXT NOT NULL,
		    assignedto TEXT,
		    issueoriginator TEXT NOT NULL,
		    updatedby TEXT NOT NULL,
                    issuetype TEXT NOT NULL,
                    state TEXT,
                    updatedtime TEXT,
                    viewtracker TEXT)''')

            # Set first row in issues table
            cur.execute('''INSERT INTO issues(	
		    cttissue,date,severity,ticket,status,
		    cluster,hostname,issuetitle,issuedescription,assignedto,
		    issueoriginator,updatedby,issuetype,state,updatedtime,viewtracker)
		    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
		    (cttissuestart, date, 99, "---", "----", "----", "----", 
			"----", "Created table", "----", "----", "----", "----", "----", "----", "----"))
 
    with con:
        cur = con.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS comments(
                id INTEGER PRIMARY KEY,
                cttissue TEXT NOT NULL,
                date TEXT NOT NULL,
                updatedby TEXT NOT NULL,
                comment TEXT NOT NULL)''')

    with con:
        cur = con.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS history(
                id INTEGER PRIMARY KEY,
		cttissue TEXT NOT NULL,
		date TEXT NOT NULL,
                updatedby TEXT NOT NULL,
		info TEXT)''')

    with con:
        cur = con.cursor()	# 1 | 1241 | open | r1i5n24 | r1i5n10 | down
        cur.execute('''CREATE TABLE IF NOT EXISTS siblings(
                id INTEGER PRIMARY KEY,
                cttissue TEXT NOT NULL,
                date TEXT NOT NULL,
                status TEXT NOT NULL,
                parent TEXT NOT NULL,
                sibling TEXT NOT NULL,
				state TEXT)''')

    return


def show_help():
    print("Cluster Ticket Tracker Version 1.0.0")

    print('''

    --open

		ctt.py --open ISSUETITLE ISSUEDESC [-c CLUSTER] -n NODE [-a ASSIGNTO]		# Default ASSIGNTO is ssg

		Examples:
		ctt.py --open "Failed dimm on r1i1n1" "Description here" -c cheyenne -s 1 -n r1i1n1 -a casg


    --show

		ctt.py --show ISSUENUMBER [-d]
		
		Examples:
		ctt.py --show 1045

		Optional Arguments:
		-d	    #Show detail/history of ticket
 
     
    --list

		ctt.py --list [-s {open,closed,deleted}]

		Examples:
		ctt.py --list               # Shows all open                                                                                                                                                             
		ctt.py --list -s closed     # Options: open, closed, deleted, all 

 
    --update

		ctt.py --update ISSUENUMBER [-s {1,2,3,4}]
						[-c CLUSTER] [-n NODE] [-t TICKET]
						[-a ASSIGNEDTO]


		Optional Arguments:
		-s {1,2,3,4}, --severity {1,2,3,4}                 # Update issue severity. Default is 3
		-c CLUSTER, --cluster CLUSTER                      # Update clustername
		-n NODE, --node NODE                               # Update node name
		-t TICKET, --ticket TICKET                         # Update external ticket such as an ev number
		-a ASSIGNEDTO, --assign ASSIGNEDTO                 # Assign issue to another group. Default is ssg
		-i ISSUETITLE, --issuetitle ISSUETITLE             # Update/change the issue's title
		-d ISSUEDESC, --issuedesc ISSUEDESC                # Update/change the issue's description 
		-x {h!,h,s,t,u,o}, --type {h!,h,s,t,u,o}           # Issue Type {Hardware(with siblings), Hardware, Software, Test, Unknown, Other}

		Examples:
		ctt.py --update 1039 -s 1 -c cheyenne -n r1i1n1 -t 689725 -a casg -i "This is a new title" -d "This is a new issue description"


    --comment

		ctt.py --comment ISSUENUMBER COMMENT
		
		Examples:
		ctt.py --comment 12390 "Need an update"


    --close

		ctt.py --close ISSUENUMBER COMMENT

		Examples:
		ctt.py --close 10282 "Issue resolved"	


    --reopen

		ctt.py --reopen ISSUENUMBER COMMENT

		Examples:
		ctt.py --reopen 10421 "Need to reopen this issue"

    --attach
	
		ctt.py --attach ISSUENUMBER FILE
  
		Examples:
		ctt.py --rattach 1098 output.log

    --delete

		ctt.py --delete ISSUENUMBER COMMENT

		Examples:
		ctt.py --delete 10101 "Duplicate issue"

    ''')

    exit()


