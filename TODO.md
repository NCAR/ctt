# List of ideas, features, fixes, improvements...


  * TEST: maxopen is working?

* strict nodename matching
  * set in ini file: strict_node_match: True|False
  * if True: node_match: node1 node2 node3 node4, etc...

* FIX: if ticket does not exist, it fails:
```
^[[A[09:25:57 root@chmgt:/ssg/robertsj/ctt]$ ./ctt.py --close 1003 a
99
ctt issue 1003 updated: updatedby
ctt issue 1003 updated: updatedtime
Traceback (most recent call last):
  File "./ctt.py", line 268, in <module>
    close_issue(args.closevalue[0], date, updatedby)
  File "/ssg/robertsj/ctt/cttlib.py", line 668, in close_issue
    node = ''.join(node)
TypeError: can only join an iterable

```

* Log history when a sibling state changes

* Add a default cluster in ini file so its not required to specify a cluster when opening

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


