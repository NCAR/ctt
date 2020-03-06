# List of ideas, features, fixes, improvements...


* FIX: Need to update sibling pbs states with run_auto()
* FIX: pbs state of node not updating. Drained nodes showing jobs
  * Could be that siblings table is not getting auto updated from run_auto()
* Function to dump everything to a file
* Improved statistics
* If can not get pbsnodes, add FATAL ctt issue. Use function in --auto as example.
* Reduce verbosity such as when a node is updated, etc.

* When closing and/or deleting an issue, check siblings for open issues before releasing.
  * if issue (node) has attached siblings:
    * check each sibling to determine if an issue is open on the sibling node
    * check each sibling to deterine if that node is a sibling for another issue
  * If node has another issue, dont release


########################################
```
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
```                

