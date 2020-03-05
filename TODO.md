# List of ideas, features, fixes, improvements...

* set limits of # of issues opened in a specific run if x number failed in a single --auto, someting bad is happening!
  * ini config: maxissuesrun = 288
  * Include detailed info in the 'details' section of ticket!
  * count # of bad nodes before opening issues on the nodes. -if >= n:
  * Add below entry to db/listing...: 
  * ISSUE   DATE               TICKET   HOSTNAME     STATE     SEV   TYPE   OWNER   UNSEEN      TITLE (25 chars)
  * 0000    2020-02-06T10:07   ERROR    ERROR        ERROR      1     X     ERROR   ERROR       MAX RUN: totalcount/maxissuesrun

* function to dump everything to a file
* improved statistics

* PRIORITY: When closing and/or deleting an issue, check siblings for open issues before releasing.
  * if issue (node) has attached siblings:
    * check each sibling to determine if an issue is open on the sibling node
    * check each sibling to deterine if that node is a sibling for another issue
  * If node has another issue, dont release
  *

check_conflicts(node):
	nodelist = []
        if check_for_siblings(node) is False:
            if check_open_node(node) is True:
                 release_node(node)
            else:
                print("Node associated with another CTT issue, Not releasing node")
        else:
            nodelist.append(get_siblings(node))
            for node in nodelist:
               open database
               if check_open_node(node) is True:
                   print("not releasing %s" % (node))
                   remove node from nodelist
                

