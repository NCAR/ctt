# List of ideas, features, fixes, improvements...


* FIX ME: Just send the node to the list as the if-has-sibs check does!
```
[03:03:50 root@chmgt:/ssg/robertsj/ctt]$ ./ctt.py --close 1098 asd
ctt issue 1098 updated: updatedby
ctt issue 1098 updated: updatedtime
There is another issue for this node, closing cttissue, but not resuming in pbs - 1
ctt issue 1098 closed
Traceback (most recent call last):
  File "./ctt.py", line 269, in <module>
      close_issue(args.closevalue[0], date, updatedby)
	    File "/ssg/robertsj/ctt/cttlib.py", line 703, in close_issue
		    close_and_resume_issue(cttissue,date,updatedby,nodes2resume)                
			  File "/ssg/robertsj/ctt/cttlib.py", line 673, in close_and_resume_issue
			      print("ctt issue %s closed" % (cttissue))
				  sqlite3.OperationalError: database is locked

```


  * TEST: maxopen is working?

* strict nodename matching
  * set in ini file: strict_node_match: True|False
  * if True: node_match: node1 node2 node3 node4, etc...

* Log history when a sibling state changes?

* Function to dump everything to a file

* Improved statistics

* If can not get pbsnodes, add FATAL ctt issue. Use function in --auto as example.

* Reduce verbosity such as when a node is updated, etc.

* DONE: When closing and/or deleting an issue, check siblings for open issues before releasing.
  * if issue (node) has attached siblings:
    * check each sibling to determine if an issue is open on the sibling node
    * check each sibling to deterine if that node is a sibling for another issue
  * If node has another issue, dont release

* convert to mariadb 


