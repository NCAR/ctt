# List of features, fixes, improvements...

* Add path to clush and pbsnodes in configuration ini file
* functionality to append to ticket --There may be times when we have multiple external tickets.
* If --update, etc (whatever it may be) and no reason to run pbsnodes, lets NOT
      * therefore, move pbsnodes run back inside run_auto
	  * should be a function call to gather pbsnode states (will be used for releasing nodes)
      * when --list with siblings and --show with siblings, merely pull data from db, NOT pull real-time	  

* ------------------
* When closing and/or deleting an issue, check siblings for open issues before releasing.
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
                

