#!/usr/bin/env python3
import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from time import time,localtime,strptime,strftime
from threading import Timer

import remi.gui as gui
from remi import start,App

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.date import DateTrigger

sem_path = os.environ.get('SEMAPHORES')
if not sem_path:
    print("No env var for semaphores, setting default")
    sem_path = '/opt/semaphores'

with open(f'{os.path.dirname(os.path.realpath(__file__))}/rules.json', 'r') as f:
    rules = json.load(f)
with open(f'{os.path.dirname(os.path.realpath(__file__))}/config.json', 'r') as f:
    config = json.load(f)


jobstores = {
    #'default': SQLAlchemyJobStore(url='sqlite:///sunrise_jobs.sqlite3')
    'default': SQLAlchemyJobStore(url=f'sqlite:///{sem_path}/firewall_jobs.sqlite3') # absolute paths need 4 slashes.  whatever.
}


class FirewallUi(App):

    def __init__(self, *args):
        super().__init__(*args)

    def main(self):

        verticalContainer = gui.Container(width=350, height="100%", margin='0px auto', style={'display': 'block', 'overflow': 'hidden'})
        horizontalContainer = gui.Container(width='100%', height='100%', layout_orientation=gui.Container.LAYOUT_HORIZONTAL, margin='0px',
                                            style={'display': 'block', 'overflow': 'auto'})

        self.rowList = []
        self.statuses = {}
        self.runUpdateTimer = True

        verticalContainer.append(self.buildGrid())
        self.updateRows()
        return verticalContainer


    def buildRow(self, rowName, rowStatus, header=False):
        gridStyle = {
            'grid-template-columns':'33% 33% 33%',
            'margin':'0px auto'
        }

        headerStyle = { 'background-color': 'lavender', 'text-align': 'center', 'vertical-align': 'middle', 'font-weight': 'bold' }
        rowStyle = {'text-align': 'center',  'vertical-align': 'middle'}
        nameLabel = gui.Label(rowName, style=rowStyle)
        statusLabel = gui.Label(rowStatus, style=rowStyle)

        # need to reconcile what's in the directory when we startup with the statuses on the table.
        if Path(f"{sem_path}/{rowName}").exists():
            statusLabel.style['background-color'] = 'lightcoral'
            statusLabel.text = 'Blocked'
        else:
            statusLabel.style['background-color'] = 'lightgreen'
            statusLabel.text = 'Open'

        if header:
            changeButton = gui.Label("Change")
            changeButton.style.update(headerStyle)
            nameLabel.style.update(headerStyle)
            statusLabel.style.update(headerStyle)
            height = 25
        else:
            changeButton = gui.Button("ChangeState")
            changeButton.associatedLabel = statusLabel
            self.statuses[rowName] = statusLabel
            changeButton.onclick.do(self.on_change_rule_state, statusLabel, rowName)
            height = 50
        
        gridContainer = gui.GridBox(width='100%', height=height, style=gridStyle)
        gridContainer.set_from_asciiart('|name                           |status        |change        |')
        gridContainer.append({'name':nameLabel, 'status': statusLabel, 'change': changeButton})
        return gridContainer
        
    def buildGrid(self):
        vbox = gui.Container(width='100%', height='100%', margin='0px',
                             style={'display': 'block', 'overflow': 'auto'})
        headerContainer  = self.buildRow('Device', 'Status', header=True)
        vbox.append(headerContainer)
        for rule in rules:
            row = self.buildRow(rule, 'Open')
            self.rowList.append(row)
            vbox.append(row)
        return vbox

    
    def updateRows(self):
        for rule in rules:
            if Path(f"{sem_path}/{rule}").exists():
                self.statuses[rule].style['background-color'] = 'lightcoral'
                self.statuses[rule].text = 'Blocked'
            else:
                self.statuses[rule].style['background-color'] = 'lightgreen'
                self.statuses[rule].text = 'Open'

        if self.runUpdateTimer:
            Timer(1, self.updateRows).start()

    def on_change_rule_state(self, emitter, target, ruleName):
        if target.get_text() == 'Blocked':
            print(f"Opening {ruleName}")
            target.set_text('Open')
            target.style['background-color'] = 'lightgreen'
            Path(f"{sem_path}/{ruleName}").unlink()
            return
        if target.get_text() == 'Open':
            print(f"Blocking {ruleName}")
            target.set_text('Blocked')
            target.style['background-color'] = 'lightcoral'
            Path(f"{sem_path}/{ruleName}").touch()
            return


if __name__ == "__main__":

    #bs = BackgroundScheduler(jobstores=jobstores)
    #bs.start()

    # starts the webserver
    start(FirewallUi,
          address=config['listen'],
          port=config['port'],
          multiple_instance=False,
          start_browser=False,
          username=config['username'],
          password=config['password']
    )
