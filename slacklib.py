#!/usr/bin/env python3
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

SLACK_BOT_TOKEN = "xoxb-3354205449411-3354659409506-xiTyGhU3lApKpYWcMLMt9XBN" #TEST
#SLACK_BOT_TOKEN = "xoxb-1350249964867-3355150119426-QCDNawDTGa1dx3wWnim7zk3b"
client = WebClient(token=SLACK_BOT_TOKEN)

try:
    response = client.chat_postMessage(
        channel="new-products",
        #channel="hsg-changelog",
        text="Testing CTT issue closure message"
    )

except SlackApiError as e:
    # You will get a SlackApiError if "ok" is False
    assert e.response["error"]    # str like 'invalid_auth', 'channel_not_found'
    print("Error sending message to Slack")


    ########
    #CTT bot for production: xoxb-1350249964867-3355150119426-QCDNawDTGa1dx3wWnim7zk3b
    #channel="hsg-changelog"

