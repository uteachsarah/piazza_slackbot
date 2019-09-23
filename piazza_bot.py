"""
Ze Xuan Ong
15 Jan 2019

Adapted from t-davidson's piazza-slackbot
URL: https://github.com/t-davidson/piazza-slackbot/blob/master/slackbot.py

This is a simple Slackbot that will poll Piazza every minute

Every time a new post is observed a notification will be sent out
"""

import ast
import os
import re

from piazza_api import Piazza
from slacker import Slacker
from time import sleep
from dotenv import load_dotenv, find_dotenv


# Config object to collect all required environment and config vars
class Config():

    # Environment variables
    PIAZZA_ID = ""          # Piazza forum id
    PIAZZA_EMAIL = ""       # User account email
    PIAZZA_PASSWORD = ""    # User account password
    SLACK_TOKEN = ""        # Slack API token
    SLACK_CHANNEL = ""      # Slack channel name
    SLACK_BOT_NAME = ""     # Slack bot name    

    def __init__(self, pid, pemail, ppass, stoken, schannel, sbot):
        self.PIAZZA_ID = pid
        self.PIAZZA_EMAIL = pemail
        self.PIAZZA_PASSWORD = ppass
        self.SLACK_TOKEN = stoken
        self.SLACK_CHANNEL = schannel
        self.SLACK_BOT_NAME = sbot        


# Main method
def main():

    # Read all relevant config variables
    confs = config_env()

    # Setup Piazza
    piazza = Piazza()
    # Piazza login is the same across all configs, so we use the first one
    piazza.user_login(email=confs[0].PIAZZA_EMAIL, password=confs[0].PIAZZA_PASSWORD)

    bots = []
    networks = []
    last_ids = []
    post_base_urls = []
    slack_bot_names = []
    slack_channels = []
    for conf in confs:
        network = piazza.network(conf.PIAZZA_ID)
        last_ids.append(get_max_id(network.get_feed()['feed']))
        post_base_urls.append("https://piazza.com/class/{}?cid=".format(conf.PIAZZA_ID))
        networks.append(network)
        # Setup Slack
        bots.append(Slacker(conf.SLACK_TOKEN))
        slack_bot_names.append(conf.SLACK_BOT_NAME)
        slack_channels.append(conf.SLACK_CHANNEL)

    # Run loop
    check_for_new_posts(networks, bots, slack_bot_names, 
                        slack_channels, last_ids, post_base_urls)


# Collect env vars
def config_env():

    # Get environment variables from .env file if exists
    load_dotenv(find_dotenv())

    # Piazza specific
    PIAZZA_IDS = ast.literal_eval(os.getenv("PIAZZA_IDS"))
    PIAZZA_EMAIL = os.getenv("PIAZZA_EMAIL")
    PIAZZA_PASSWORD = os.getenv("PIAZZA_PASSWORD")

    if not PIAZZA_IDS or not PIAZZA_EMAIL or not PIAZZA_PASSWORD:
        print("Missing Piazza credentials")
        exit(1)

    # Slack specific
    SLACK_TOKENS = ast.literal_eval(os.getenv("SLACK_TOKENS"))
    SLACK_CHANNELS = ast.literal_eval(os.getenv("SLACK_CHANNELS"))
    SLACK_BOT_NAMES = ast.literal_eval(os.getenv("SLACK_BOT_NAMES"))

    if not SLACK_TOKENS or not SLACK_CHANNELS or not SLACK_BOT_NAMES:
        print("Missing Slack credentials")
        exit(1)

    confs = []
    for i in range(len(PIAZZA_IDS)):
        conf = Config(PIAZZA_IDS[i], PIAZZA_EMAIL, PIAZZA_PASSWORD,
                      SLACK_TOKENS[i], SLACK_CHANNELS[i], SLACK_BOT_NAMES[i])
        confs.append(conf)
    return confs


# This method exploits the fact that pinned posts have the field
# 'pin: 1' and non-pinned ones don't. So we can return the first
# non-pinned post id
def get_max_id(feed):
    for post in feed:
        if "pin" not in post:
            return post["nr"]
    return -1


# Method that polls Piazza in constant interval and posts new posts
# to Slack
def check_for_new_posts(networks, bots, bot_names, channels, last_ids,
                        post_base_urls, interval=60, include_link=True):

    # Keep looping
    while True:
        for i in range(len(networks)):
            try:
                UPDATED_LAST_ID = get_max_id(networks[i].get_feed()['feed'])
                # For all the new posts
                while UPDATED_LAST_ID > last_ids[i]:
                    last_ids[i] += 1
                    # Fetch post
                    post = networks[i].get_post(last_ids[i])
                    if not post.get('history', None):
                        continue
                    subject = "Piazza Bot \U0001F355 found a new post:"
                    content = post['history'][0]['subject']
                
                    # subject = post['history'][0]['subject']
                    # content = re.findall(r'<p>(.*?)</p>', post['history'][0]['content'])[0]
                    
                    # Create message and attach relevant parts
                    attachment = None
                    message = None
                    if include_link is True:
                        attachment = [
                            {
                                "fallback": "New post on Piazza!",
                                "title": subject,
                                "title_link": post_base_urls[i] + str(UPDATED_LAST_ID),
                                "text": content,
                                "color": "good"
                            }
                        ]
                    else:
                        message = "New post on Piazza!"

                    # Post message
                    bots[i].chat.post_message(channel,
                                              message,
                                              as_user=bot_names[i],
                                              parse='full',
                                              attachments=attachment)
                print("Slack bot is up!")
                sleep(interval)
            except:
                print("Error when attempting to get Piazza feed, going to sleep...")
                sleep(interval)

# Main
if __name__ == '__main__':
    main()

