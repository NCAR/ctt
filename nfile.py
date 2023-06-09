#!/usr/bin/env python3
import subprocess 
import errno    
import os

def read_file_first_line(filename):
    """ Read first line of given filename """
    result = None
    with open(filename, 'r') as f:
        result = f.readline()
        result = result.rstrip("\n")
        f.close()
    return result

def write_file ( file_name, contents ):
    """ Takes file_name and writes contents to file. it will clobber file_name. """
    #vlog(4, 'Writing File: %s SIZE=%s' % (file_name, len(contents)))
    with open(file_name, 'w') as file:
        file.write(contents)

def exec_to_file ( cmd, output_file, cwd = '/tmp/' ):
    """ Runs cmd and pipes STDOUT to output_file """

    try:
        dn = open(os.devnull, 'r')
        with open(output_file, 'w') as fo:
            #vlog(4, 'Running command: %s > %s from %s '% (cmd, output_file, cwd))
            p = subprocess.Popen(
                    cmd, 
                    stdin=dn,
                    stdout=fo,
                    stderr=fo,
                    cwd=cwd, 
                    close_fds=True
                )

            if p:
                p.wait()
                return p.returncode

    except Exception as e:
        #vlog(1, 'Command Error: %s'% (str(e)))
        return None

    #vlog(1, 'Failed to run command: %s > %s '% (cmd, output_file))
    return None

def exec_to_string_with_input ( cmd, input):
    """ Runs cmd, sends input to STDIN and places Return Value, STDOUT, STDERR into returned list  """
    #vlog(4, 'Running command: %s' % cmd) 
    try:
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd='/tmp/')
        if p:
            stdout, stderr = p.communicate(input=input)
        return [ p.returncode, stdout, stderr ]

    except Exception as e:
        #vlog(1, 'Command %s failed with error: %s' % (cmd, e))
        return [-1, '', 'Failed to run']  

def exec_to_string ( cmd, cwd='/tmp/' ):
    """ Runs cmd and places Return Value, STDOUT, STDERR into returned list  """
    #vlog(4, 'Running command: %s' % cmd) 

    try:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)
        if p:
            stdout, stderr = p.communicate()
            return [ p.returncode, stdout, stderr ] 

    except Exception as e:
        #vlog(1, 'Command %s failed with error: %s' % (cmd, e))
        return [-1, '', 'Failed to run'] 

#https://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python
def mkdir_p(path):
    try:
        osmmakedirs(path, exist_ok=True)
    except Exception as e:
        return None


"""
def mkdir_p(path, mode = 0755):
    try:
        os.makedirs(path, mode)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise
"""	    
