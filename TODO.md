# List of ideas, features, fixes, improvements...



* TEST: maxopen is working?

* strict nodename matching
  * set in ini file: strict_node_match: True|False
  * if True: node_match: node1 node2 node3 node4, etc...

* Improved statistics

* Reduce verbosity such as when a node is updated, etc.

* DONE: When closing and/or deleting an issue, check siblings for open issues before releasing.
  * if issue (node) has attached siblings:
    * check each sibling to determine if an issue is open on the sibling node
    * check each sibling to deterine if that node is a sibling for another issue
  * If node has another issue, dont release

* convert to mariadb 


