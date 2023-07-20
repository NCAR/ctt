# Cluster Ticket Tracker
CTT is a tool for managing tickets for a HPC system

## Requirements:
- pbs
- python 3.6+

## Setup
- need a `ctt.ini` file with most config options (example included in repo)
- need a `secrets.ini` file with secrets
  - `slack_token`
  - `ev_user`
  - `ev_password`
- create and source a python venv
  - pip install -r requirements.txx
- add src/lib to PYTHONPATH

## dev
- before commiting run 
  - `ruff check . --fix` and fix any errors
  - tests are still a WIP, but after they are setup make sure they all pass

