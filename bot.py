import slack
import os
import numpy as np

from pathlib import Path
from dotenv import load_dotenv
from flask import Flask
from slackeventsapi import SlackEventAdapter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

app = Flask(__name__)
slack_event_adapter = SlackEventAdapter(os.environ['SIGNING_SECRET'], '/slack/events', app)

client = slack.WebClient(token=os.environ['SLACK_TOKEN2'])
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
    except:
        print(f"Error")

def get_text_from_json(results):
    return [msg['text'] for msg in results]


def get_messages_history(conversation_id):
    try:
        # Call the conversations.history method using the WebClient
        # conversations.history returns the first 100 messages by default
        # These results are paginated, see: https://api.slack.com/methods/conversations.history$pagination
        result = client.conversations_history(channel=conversation_id)
        return get_text_from_json(result["messages"])
    except:
        print("Error creating conversation")


def tfidf(msgs, vectorizer=None):
    if vectorizer is None:
        vectorizer = TfidfVectorizer()
    db_rep = vectorizer.fit_transform(msgs)
    return db_rep, vectorizer

def retrieve_similars_idxs(question_rep, db_rep, n=5):
    best_matches = cosine_similarity(question_rep, db_rep)
    best_matches_idx = np.argsort(best_matches)
    return best_matches_idx[0, :n]

def get_similar_msgs(question, msgs, db_rep, vectorizer):
    if not isinstance(question, list):
        question = [question]
    question_rep = vectorizer.transform(question)
    idxs = retrieve_similars_idxs(question_rep, db_rep)
    # int_idxs = [int(idx) for idx in idxs]
    return [msgs[int(idx)] for idx in idxs]

def init_db():
    conv_id = get_conversation_id('qwerty-channel')
    msgs = get_messages_history(conv_id)
    print(len(msgs), conv_id)
    db_rep, vectorizer = tfidf(msgs)
    return db_rep, msgs, vectorizer

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
        # if is_question(text):
        print(f'Received text:{text}')
        sim_msgs = get_similar_msgs(text, msgs, db_rep, vectorizer)
        for msg in sim_msgs:
            client.chat_postMessage(channel=channel_id, text=msg)
            # print(msg)

if __name__ == "__main__":
    db_rep, msgs, vectorizer = init_db()
    app.run(debug=True)