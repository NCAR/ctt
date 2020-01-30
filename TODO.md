# List of features, fixes, improvements...

* Speed up processing the list view by running pbsnodes once instead of for each sibling or run_auto
* Add path to clush and pbsnodes in configuration ini file
* In list view, if external ticket, state YES and show the actual ticket number in --show
  * if adding a ticket, remove '----' and add new ticket #. if not '----', append.
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
                

