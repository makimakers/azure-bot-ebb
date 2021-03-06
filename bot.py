# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from botbuilder.core import ActivityHandler, TurnContext
from botbuilder.schema import ChannelAccount, Activity
import overlap_finder as of


class MyBot(ActivityHandler):
    # See https://aka.ms/about-bot-activity-message
    # to learn more about the message and other activity types.

    async def on_message_activity(self, turn_context: TurnContext):

        if turn_context.activity.text.lower() in ['/help', 'help']:
            await turn_context.send_activity(Activity(type='message',
                                                      text=of.help_msg(),
                                                      text_format='xml'))
        elif turn_context.activity.text.lower() in ['/example', 'example', 'eg']:
            await turn_context.send_activity(Activity(type='message',
                                                      text=of.example_msg(),
                                                      text_format='xml'))
        else:
            try:
                dt_list = of.parse_dt_string(turn_context.activity.text)
                overlap_dict = of.find_all_common_intervals(dt_list)
                to_print = of.format_overlaps(overlap_dict)
                msg_activity = Activity(type='message', text=to_print,
                                        text_format='xml')
                # text_format='markdown' gives formatting issues w newlines.
                # text_format='plain' auto becomes markdown in emulator. plain in Tele.
                # text_format='xml' auto becomes plaintext in Telegram and emulator.
                # note that with 'xml', anything encased in angular brackets are dropped.
                # if argument to send_activity() is string, then markdown is assumed.
                await turn_context.send_activity(msg_activity)

            except Exception as e:
                await turn_context.send_activity(str(e))


    async def on_members_added_activity(
        self,
        members_added: ChannelAccount,
        turn_context: TurnContext
    ):
        for member_added in members_added:
            if member_added.id != turn_context.activity.recipient.id:
                await turn_context.send_activity("Hello and welcome!")

    # TODO: add event handler for unrecognized activity to prevent bot from..
    # crashing? There's a weird bug where @-mentioning the telegram bot will 
    # cause the bot to crash. Need to figure out what kind of activity that is, 
    # then we can catch the buggy behaviour.