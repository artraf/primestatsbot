#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -*- style: pep-8 -*-
#
# ** Stats Converter **
# This is a simple Telegram bot for converting exported stats from Ingress Prime to human readable text
#
# - Author: PascalRoose
# - Repo: https://github.com/PascalRoose/primestatsbot.git
#

import os
import logging

from telegram.ext import Updater, MessageHandler, CommandHandler, Filters, BaseFilter
from dotenv import load_dotenv

# Enable logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load .env file
load_dotenv()

# All possible stats in the order it would appear in the export
stats_header = \
    [
        # General
        'Time Span', 'Agent Name', 'Agent Faction', 'Date (yyyy-mm-dd)', 'Time (hh:mm:ss)', 'Lifetime AP', 'Current AP',

        # Discovery
        'Unique Portals Visited', 'Portals Discovered', 'Seer Points', 'XM Collected', 'OPR Agreements',

        # Health
        'Distance Walked',

        # Building
        'Resonators Deployed', 'Links Created', 'Control Fields Created', 'Mind Units Captured',
        'Longest Link Ever Created', 'Largest Control Field', 'XM Recharged', 'Portals Captured',
        'Unique Portals Captured', 'Mods Deployed',

        # Combat
        'Resonators Destroyed', 'Portals Neutralized', 'Enemy Links Destroyed', 'Enemy Fields Destroyed',

        # Defense
        'Max Time Portal Held', 'Max Time Link Maintained', 'Max Link Length x Days', 'Max Time Field Held',
        'Largest Field MUs x Days',

        # Missions
        'Unique Missions Completed',

        # Resource Gathering
        'Hacks', 'Glyph Hack Points', 'Longest Hacking Streak',

        # Mentoring
        'Agents Successfully Recruited',

        # Events
        'Mission Day(s) Attended', 'NL-1331 Meetup(s) Attended', 'First Saturday Events', 'Clear Fields Events',
        'OPR Live Events', 'Prime Challenges', 'Intel Ops Missions', 'Stealth Ops Missions',

        # Recursions
        'Recursions',

        # NOW Stats
        'Links Active', 'Portals Owned', 'Control Fields Active', 'Mind Unit Control', 'Current Hacking Streak'
    ]


# Custom filter to check if a 'exported stats' message was sent
class StatsFilter(BaseFilter):
    def filter(self, message):
        # Check if the message contains at least the first 7 keys in stats_header (# General)
        return str(message.text).startswith(' '.join(stats_header[:7]))


def fix_timespan(stats_values):
    # Everything in the export gets translated to English EXCEPT the value of timespan /rage

    # In some languages ALL TIME is translated to one or more words.
    # WEEK, MONTH, NOW might be as well, but I'm sure about that...

    # The next bit is gonna find the value for timespan, if . It's a bit of a messy workaround, so hold tight

    # stats_values contains all of the values/words in the second line of the export message.
    # The third element is Faction (either Enlightened or Resistance). Depending on the translation of ALL TIME it's
    # either the 3rd, 4rd or maybe even 5th element in stats_values.
    if 'Enlightened' in stats_values:
        faction_index = stats_values.index('Enlightened')
    else:
        faction_index = stats_values.index('Resistance')

    # Agentname is the element before faction_index
    agentname_index = faction_index - 1

    # Contaminate the values of index 0 untill (not including) the index of agentname
    stats_values[0:agentname_index] = [' '.join(stats_values[0:agentname_index])]

    # Return the fixed stats_values array
    return stats_values


# Convert the exported stats to a nicely formatted message and send it
def process_stats(update, _context):
    # Split first row (keys) and second row (values). Use only the second row (values) and split at every space
    # We now have a list of all values. Timespan needs to be fixed first, see the function above for explaination.
    stats_values = fix_timespan(str(update.message.text).split('\n')[1].split(' '))

    # Init a dictionary. This will represent the name of the stats as key, and the value of the stat as value.
    stats_dict = dict()

    # Create an index to keep track of the element we're  at
    stats_index = 0

    # Loop through the stats header. For each stat check if it's in the export.
    # Event stats that a player doesn't have will not be shown in the export, that's why we have to check
    for stat in stats_header:
        if stat in update.message.text:
            # Add the name and value of the stat to the dictionary
            stats_dict[stat] = stats_values[stats_index]
            # Up the index by 1, next!
            stats_index += 1

    # Loop through the dictionary. Add every key and value as a row to the output message
    stats_message = ''
    for key, value in stats_dict.items():
        stats_message += f'{key}: {value}\n'

    # Send the generated message back
    update.message.reply_text(stats_message)


def process_incorrectmessage(update, _context):
    if update.message.chat.type == 'private':
        update.message.reply_text(os.getenv('INCORRECT_MESSAGE'))


# Send a message to users that start or simply type 'start' in private
def command_start(update, _context):
    if update.message.chat.type == 'private':
        update.message.reply_text(os.getenv('START_MESSAGE'))


# Send a message when a new chat is created with the bot in it
def on_chatcreated(update, _context):
    update.message.reply_text(os.getenv('JOIN_MESSAGE'))


# Send a message when the bot gets added to a group
def on_joinchat(update, _context):
    # Check if the member that was added is the bot itself
    for member in update.message.new_chat_members:
        if member.name == os.getenv('BOTNAME'):
            update.message.reply_text(os.getenv('JOIN_MESSAGE'))


# Log Errors caused by Updates.
def error(update, _context):
    logger.warning('Update "%s" caused error "%s"', update, error)


def main():
    # Create the Updater with the bottoken saved in .env
    updater = Updater(os.getenv('TOKEN'), use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Handlers: what triggers the bot and how should it respond
    dp.add_handler(CommandHandler('start', command_start))
    dp.add_handler(MessageHandler(Filters.status_update.chat_created, on_chatcreated))
    dp.add_handler(MessageHandler(Filters.status_update.new_chat_members, on_joinchat))
    dp.add_handler(MessageHandler(StatsFilter(), process_stats))
    dp.add_handler(MessageHandler(~ StatsFilter(), process_incorrectmessage))
    # Log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
