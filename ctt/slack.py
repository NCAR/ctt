from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


class Slack:
    def __init__(self, config):
        self.enabled = config.getboolean("slack", "enabled")
        if self.enabled:
            self.token = config.get("slack", "token")
            self.channel = config.get("slack", "channel")
            self.client = WebClient(token=self.token)

    def send_slack(self, slack_message):
        try:
            self.client.chat_postMessage(channel=self.channel, text=slack_message)

        except SlackApiError as e:
            assert e.response["error"]
            print("Error sending message to Slack: %s", e)
