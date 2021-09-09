--open

                ctt --open ISSUETITLE ISSUEDESC -n NODE
                # You may open multiple issues with a comma separated list such as r1i1n1,r4i3n12,++

                Examples:
                ctt --open "Persistent memory errors" "Please open HPE ticket for persistent memory errors on P2-DIMM1G" -n r1i1n1
                ctt --open "Will not boot" "Please open a severity 1 HPE ticket to determine why this node will not boot" -n r1i1n1 -a casg -s1
                ctt --open "Persistent memory errors" "Persistent memory errors on P2-DIMM1G. HPE ticket already opened" -n r1i1n1 -t HPE48207411

                Optional arguments:
                -s, --severity, Choices: {1, 2, 3, 4}
                -c, --cluster, 
                -a, --assign, 
                -t, --ticket, 
                -x, --type, Choices: {h, s, t, u, o}    #Hardware, Software, Testing, Unknown, Other

--show

                ctt --show ISSUENUMBER
                
                Examples:
                ctt --show 1045
                ctt --show 1031 -d

                Optional Arguments:
                -d     #Show detail/history of ticket

--list

                ctt --list

                Examples:
                ctt --list
                ctt --list -vv
                ctt --list -s closed -v

                Optional Arguments:
                -v
                -vv
                -s, Choices: {Open, Closed, All}

--update

                ctt --update ISSUENUMBER ARGUMENTS++
                # You may update multiple issues with a comma separated list of ISSUENUMBERs such as 1031,1022,1009,++

                Examples:
                ctt --update 1039 -s 1 -c cheyenne -n r1i1n1 -t 689725 -a casg -i "This is a new title" -d "This is a new issue description"
                ctt --update 1092 -s 1


                Optional Arguments:
                -s, --severity, Choices: {1,2,3,4}
                -c, --cluster
                -n, --node                                    #WARNING: Changing the node name will NOT drain a node nor resume the old node name
                -t, --ticket
                -a , --assign
                -i , --issuetitle
                -d , --issuedesc
                -x, --type, Choices: {h!,h,s,t,u,o}           #Issue Type {Hardware(with siblings), Hardware, Software, Test, Unknown, Other}

--comment

                ctt --comment ISSUENUMBER COMMENT
                # You may comment multiple issues with a comma separated list of ISSUENUMBERs such as 1011,1002,1043,++
                
                Example:
                ctt --comment 1008 "Need an update on this issue"

--close

                ctt --close ISSUENUMBER COMMENT
                # You may close multiple issues with a comma separated list such as 1011,1002,1043,++

                Example:
                ctt --close 1082 "Issue resolved after reseat"

--reopen

                ctt --reopen ISSUENUMBER COMMENT
                # You may reopen multiple issues with a comma separated list such as 1011,1002,1043,++

                Examples:
                ctt --reopen 1042 "Need to reopen this issue. Still seeing memory failures."

--attach
        
                ctt --attach ISSUENUMBER FILE  #absolute path

                Examples:
                ctt --attach 1098 /ssg/tmp/output.log

--stats

                ctt --stats
                # The output will be in csv format.


