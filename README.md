# CTT

## dev
- before commiting run 
  - `black *.py`
  - `isort *`
  - `ruff check . --fix` and fix any errors
## Requirements:
- pbs pro
- sqlite3
- clustershell

## Setup
- need a `ctt.ini` file with most config options (example included in repo)
- need a `secrets.ini` file with secrets
  - `slack_token`
  - `ev_user`
  - `ev_password`
