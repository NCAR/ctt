#!/usr/bin/env python3
import extraview_cli


def assign_group(ev_id, node, cttissue):
    EV.assign_group(ev_id, 'casg', None, {       #What is the None ?                                                                                 
        'COMMENTS': """                                                                                                           
        CTT issue number {} for {}assigned to 'casg'.                                                                                    
        """.format(cttissue, node)                                                                                                       
    })                                

#############################################

def close_EV(ev_id, comment):                                                                                                        
    """ close ev """                                                                                           
    global EV                                                                                                                         
    EV.close(ev_id, 'CTT Comment:\n%s' % comment)                                                                        

#############################################

def comment_EV(ev_id, comment):                                                                                                    
    """ add comment to ev """                                                                                                      
    global EV
    EV.add_resolver_comment(ev_id, 'CTT Comment:\n%s' % comment)

#############################################

def open_EV(node, comment, new_state = 'suspect-pending', skip_ev = False):  #remove new_state and skip_ev
    """ open ev ticket """    
    global EV
    ev_id = EV.create( \
                       'ssgev', \
                       'ssg', \
                       None, \
                       'Laramie: Bad Node: %s ' % (node), \
                       '%s has been added to the Cheyenne CTT list.' % (node),
                       {
                           'HELP_LOCATION': EV.get_field_value_to_field_key('HELP_LOCATION', 'NWSC'),
                           'HELP_HOSTNAME': EV.get_field_value_to_field_key('HELP_HOSTNAME', 'cheyenne'),
                           'HELP_HOSTNAME_CATEGORY': EV.get_field_value_to_field_key('HELP_HOSTNAME_CATEGORY', 'Supercomputer'),
                           'HELP_HOSTNAME_OTHER': node
                       }
                    ) 

    EV.add_resolver_comment(ev_id, 'CTT Comment:\n%s' % comment)
    print(ev_id)
    return(ev_id)

#############################################

EV = extraview_cli.open_extraview()
node = 'r1i1n1'
comment = 'Jon testing'
ev_id = open_EV(node, comment)

comment = "This is a new comment to an ev ticket"
comment_EV(ev_id, comment)

comment = "Closing this issue"
ev_id = '305394'
close_EV(ev_id, comment)

node = 'r1i1n1'
cttissue = '1022'
assign_group(ev_id, node, cttissue)

