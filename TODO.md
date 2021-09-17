# List of ideas, features, fixes, improvements...

<<<<<<< HEAD
* FIX:
###########

  * Seems when adding ticket, needs to be one word. If more than one, wont remove ticketnumber
    if len(line.split()) > 1:

       if args.assignedtovalue in groupsList:
            try:
                if cttissue:
                    update_issue(cttissue, 'assignedto', args.assignedtovalue)
                    update_issue(cttissue, 'updatedby', updatedby)
                    update_issue(cttissue, 'updatedtime', date)
                    view_tracker_new(cttissue,UserGroup,viewnotices)
                    log_history(cttissue,date,updatedby,'assigned issue to: %s' % (args.assignedtovalue))
            except IndexError:
                parser.print_help()
        else:
            print("Assign to group \"%s\" is not a valid users group, Exiting!" % (args.assignedtovalue))
#########



  * When force offline runs, it updates the issuetitle and description. Seen where it updates and all is blank, need to fix
  * 35|1034|2021-09-10T13:20:01.195102|3|---|open|laramie|r1i3n16| | |ctt|ctt|ctt|u|offline|2021-09-10T15:30:01.872119|casg
  * ^^^ laramie db... issuetitle and issuedesc is blank or maybe ' ' (not '')



* IMPLEMENT:
  * Column for "PBS Jobs" if jobs running, "yes"
  * Write a config option for a unit test... instead of running pbsnodes -a, you specify a csv file to read 
  * Do we want a flagfile config option and if not False: check and clear file on node
  * Check_MK? When ctt has a FATAL err, send to Nagios


* TEST:
  *With lock, ^c to see if lock released
  *WORKS: If comment and THIS, THIS takes issuetitle.
  *WORKS: If NO comment and THIS, will show THIS
  *WORKS: If NO comment and NO THIS, use Unknown Reason
  *WORKS: If comment and NO THIS, use comment
  *WORKS: If node is powered off, what will show in title, etc. Shows Unknown Reason
  *WORKS: Add a comment then resume node. comment should clear at resume.
  *WORKS: Test clush timeout.
  *WORKS: Test unlinking of THIS at resume
  *WORKS: Does /etc/nolocal get unlinked when resumed.
  *WORKS: Test with real flag filename

=======


>>>>>>> ade080c1f9882671cf7dfb3495c35f8ff17bb605

