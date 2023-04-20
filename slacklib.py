from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

with open(".slacktoken") as f:
    SLACK_BOT_TOKEN = f.readline()
client = WebClient(token=SLACK_BOT_TOKEN)

try:
    response = client.chat_postMessage(
        channel="new-products",
        text="Testing CTT issue closure message"
    )

except SlackApiError as e:
    # You will get a SlackApiError if "ok" is False
    assert e.response["error"]    # str like 'invalid_auth', 'channel_not_found'
    print("Error sending message to Slack")
