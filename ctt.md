Cluster Ticket Tracker Version 1.0.0
    
    --auto

                ctt.py --auto   

 
    --open      
                
                ctt.py --open ISSUETITLE ISSUEDESC -c CLUSTER -n NODE [-a ASSIGNTO]             # Default ASSIGNTO is ssg
                
                Examples:
                ctt.py --open "Failed dimm on r1i1n1" "Description here" -c cheyenne -s 1 -n r1i1n1 -a casg
    
    
    --show      
                
                ctt.py --show ISSUENUMBER [-d]
                
                Examples:
                ctt.py --show 1045
                
                Optional Arguments:
                -d          #Show detail/history of ticket
    
    
    --list      
                
                ctt.py --list [-s {open,closed,deleted}]
				[-v] [-vv]
                
                Examples:
                ctt.py --list               # Shows all open                                                                                         
                ctt.py --list -s closed     # Options: open, closed, deleted
                ctt.py --list -s closed -vv

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
                -x {h,h!,s,t,u,o}, --type {h,h!,s,t,u,o}           # Issue Type {Hardware, Software, Test, Unknown, Other}
                                                                     h! will mark as hardware AND mark all siblings 
                Examples:
                ctt.py --update 1039 -s 1 -c cheyenne -n r1i1n1 -t 689725 -a casg -i "This is a new title" -d "This is a new issue description"
                ctt.py --update 1039 -x h!


    --comment

                ctt.py --comment ISSUENUMBER COMMENT

                Examples:
                ctt.py --comment 12390 "Need an update"

                
    --close

                ctt.py --close ISSUENUMBER COMMENT

                Examples:
                ctt.py --close 10282 "Issue resolved"
                                                

    --delete	#FUTURE FEATURE. Only the cttadmin can delete issues.

                ctt.py --delete ISSUENUMBER COMMENT

                Examples:
                ctt.py --delete 10101 "Duplicate issue"

    

