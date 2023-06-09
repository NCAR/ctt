# Cluster Ticket Tracker
CTT is a tool for managing tickets for a HPC system

## Requirements:
- pbs pro
- sqlite3
- clustershell
- python 3.6+

## Setup
- need a `ctt.ini` file with most config options (example included in repo)
- need a `secrets.ini` file with secrets
  - `slack_token`
  - `ev_user`
  - `ev_password`

## dev
- before commiting run 
  - `black *.py`
  - `isort *`
  - `ruff check . --fix` and fix any errors
  - tests are still a WIP, but after they are setup make sure they all pass

