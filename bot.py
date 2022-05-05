import slack
import os
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask
from slackeventsapi import SlackEventAdapter

env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

app = Flask(__name__)
slack_event_adapter = SlackEventAdapter(os.environ['SIGNING_SECRET'], '/slack/events', app)

client = slack.WebClient(token=os.environ['SLACK_TOKEN'])
BOT_ID = client.api_call("auth.test")['user_id']

def get_conversation_id(conversation_name):
    conversation_id = None
    try:
        # Call the conversations.list method using the WebClient
        for result in client.conversations_list():
            if conversation_id is not None:
                break
            for channel in result["channels"]:
                if channel["name"] == conversation_name:
                    conversation_id = channel["id"]
                    return conversation_id
    except SlackApiError as e:
        print(f"Error: {e}")

def get_messages_history(conversation_id):
    try:
        # Call the conversations.history method using the WebClient
        # conversations.history returns the first 100 messages by default
        # These results are paginated, see: https://api.slack.com/methods/conversations.history$pagination
        result = client.conversations_history(channel=conversation_id)
        return result["messages"]
    except SlackApiError as e:
        print("Error creating conversation: {}".format(e))

def init_db():
    conv_id = get_conversation_id('#hackathon')
    msgs = get_messages_history(conv_id)
    print(len(msgs), conv_id)
    return msgs

def is_question(text):
    if text[-1] == '?':
        return True
    return False

@slack_event_adapter.on('message')
def message(payload):
    event = payload.get('event', {})
    channel_id = event.get('channel')
    user_id = event.get('user')
    text = event.get('text')

    if user_id != BOT_ID:
        client.chat_postMessage(channel='#hackathon', text='hi ' + user_id + ', great question')


if __name__ == "__main__":
    db = init_db()
    app.run(debug=True)