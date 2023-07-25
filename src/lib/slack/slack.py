from slack_sdk import WebClient


class Slack:
    def __init__(self, kwargs):
        self.token = kwargs["token"]
        self.channel = kwargs["channel"]
        self.client = WebClient(token=self.token)
        self.enabled = kwargs["enabled"] == "True"

    def send(self, slack_message):
        if self.enabled:
            self.client.chat_postMessage(channel=self.channel, text=slack_message)
