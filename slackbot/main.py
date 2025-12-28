import os

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# Install the Slack app and get xoxb- token in advance
app = App()

@app.event("app_mention")
def handle_app_mention_events(body, say):
    say(f"Hey there <@{body['event']['user']}>!")

if __name__ == "__main__":
    SocketModeHandler(app).start()