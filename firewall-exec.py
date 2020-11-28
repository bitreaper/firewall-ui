#!/usr/bin/env python3

import os
import sys
import json
import inotify.adapters
import subprocess
from subprocess import CalledProcessError, DEVNULL


# let's setup logging so we can keep track of things
import logging
from logging import handlers

log_path = '/var/log/firewallExec.log'

log = logging.getLogger('firewallExecLogger')
log.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s %(levelname)s:  %(message)s')

rotatingHandler = handlers.TimedRotatingFileHandler(log_path,when="H", interval=24, backupCount=2)
rotatingHandler.setFormatter(formatter)
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(formatter)

log.addHandler(consoleHandler)
log.addHandler(rotatingHandler)



# setup semaphore path.  Get it from the Env if it's there, otherwise assume /opt/semaphores.
# Wherever it is, it's going to need to be writable by the user that launchs firewallui.py 
sem_path = os.environ.get('SEMAPHORES')

if not sem_path:
    log.info("No env var for semaphores, setting default")
    sem_path = '/opt/semaphores'

directives_path = f'{os.path.dirname(os.path.realpath(__file__))}/rules.json'
with open(directives_path) as f:
    directives = json.load(f)

def deleteRule(directive):
    log.info(f"Deleting {directive}")
    for chain,details in directives[directive]["rules"]:
        cmd = f'iptables -D {chain} {details}'
        log.debug(f"command: {cmd}")
        try:
            subprocess.check_call(cmd.split(' '))
        except CalledProcessError as e:
            return False
    return True
    
        
def insertRule(directive):
    log.info(f"Inserting {directive}")

    if checkRule(directive):
        log.info(f"{directive} already in iptables, not inserting")
        return

    for chain,details in directives[directive]["rules"]:
        cmd = f'iptables -I {chain} 1 {details}'
        log.debug(f"command: {cmd}")
        try:
            subprocess.check_call(cmd.split(' '))
        except CalledProcessError as e:
            log.warning(f"Not sure why we didn't succeed: {e}")
            return False
    return True

                
def checkRule(directive):
    for chain,details in directives[directive]["rules"]:
        cmd = f'iptables -C {chain} {details}'
        log.debug(f"command: {cmd}")
        try:
            subprocess.check_call(cmd.split(' '), stderr=DEVNULL)
        except CalledProcessError as e:
            return False
    return True


def reconcileDirectives():
    log.info("Reconciling rules in iptables with semaphores directory")
    for entry in os.listdir(sem_path):
        log.info(f"  '{entry}' entry found")
        if entry in directives:
            log.info(f"    '{entry}' is a directive")
            if not checkRule(entry):
                log.info(f"      '{entry}' not in iptables, adding it")
                insertRule(entry)
            else:
                log.info(f"      '{entry}' exists in iptables. Not adding it")
        else:
            log.info(f"    '{entry}' is't a directive")
            
            
if __name__ == '__main__':

    # we should put together a init function that makes sure the rules in the table are matching what's on disk.
    # Probably should take what's in the table as more relevant than what's on disk, and reconcile the disk with
    # the table.

    # when we start up, we need to reconcile what rules are in the tables with what's in the directory.  Since
    # we could be restarting from a reboot, we need to take the directory as truth rather than what's in the
    # tables.  this keeps rules from being purged by a reboot when they should be active.

    reconcileDirectives()

    # now for the event loop part of our program...
    watcher = inotify.adapters.Inotify([sem_path])

    for event in watcher.event_gen(yield_nones=False):
        (_, type_names, path, filename) = event

        if 'IN_CREATE' in type_names or 'IN_DELETE' in type_names:
            log.info(f"Notified: {filename} with action {type_names}")
            if filename in directives:
                log.info(f"File {filename} found in directives")
                if 'IN_CREATE' in type_names:
                    insertRule(filename)
                elif 'IN_DELETE' in type_names:
                    deleteRule(filename)



