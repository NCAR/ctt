# List of ideas, features, fixes, improvements...


* FIX/Change: 
  * Put the pbsnodes run inside run_auto() 
  * Get sibling pbs states from siblings table

* FIX:
  * maxopen is not working

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


########################################
```

# When closing/releasing: 
  1. Another issue with same node?
  2. In siblings table as sibling for a different issue?
  --> if siblings attached:
  3. Are siblings in siblings table for another cttissue
  4. If has siblings attached, Do the siblings have a cttissue?

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

