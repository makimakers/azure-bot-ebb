# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from botbuilder.core import ActivityHandler, TurnContext
from botbuilder.schema import ChannelAccount
from overlap_finder import parse_dt_string, find_all_common_intervals, format_overlaps

class MyBot(ActivityHandler):
    # See https://aka.ms/about-bot-activity-message to learn more about the message and other activity types.

    async def on_message_activity(self, turn_context: TurnContext):
        
        try:
            dt_list = parse_dt_string(turn_context.activity.text)
            overlap_dict = find_all_common_intervals(dt_list)
            print(overlap_dict)  # debugging statement.
            to_print = format_overlaps(overlap_dict)
            await turn_context.send_activity(f"{to_print}")
            
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