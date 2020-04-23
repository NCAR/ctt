# List of ideas, features, fixes, improvements...


* FIX/Change: 
  * Put the pbsnodes run inside run_auto() 
  * Get sibling pbs states from siblings table

* strict nodename matching
  * set in ini file: strict_node_match: True|False
  * if True: node_match: node1 node2 node3 node4, etc...

* Function to dump everything to a file
* Improved statistics
* If can not get pbsnodes, add FATAL ctt issue. Use function in --auto as example.
* Reduce verbosity such as when a node is updated, etc.

* When closing and/or deleting an issue, check siblings for open issues before releasing.
  * if issue (node) has attached siblings:
    * check each sibling to determine if an issue is open on the sibling node
    * check each sibling to deterine if that node is a sibling for another issue
  * If node has another issue, dont release

* convert to mariadb 


########################################
```

# When closing/releasing: 
  1. Another issue with same node?
  2. In siblings table as sibling for a different issue?
  3. If has siblings attached, Do the siblings have a cttissue?
  4. Are siblings in siblings table for another cttissue

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

