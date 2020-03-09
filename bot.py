# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from botbuilder.core import ActivityHandler, TurnContext
from botbuilder.schema import ChannelAccount
import overlap_finder

class MyBot(ActivityHandler):
    # See https://aka.ms/about-bot-activity-message to learn more about the message and other activity types.

    async def on_message_activity(self, turn_context: TurnContext):
        
        try:
            dt_list = overlap_finder.parse_dt_string(turn_context.activity.text)
            overlap_dict = overlap_finder.find_all_common_intervals(dt_list)
            print(overlap_dict)  # debugging statement.
            to_print = overlap_finder.format_overlaps(overlap_dict)
            await turn_context.send_activity(f"{to_print}")
        except IndexError:
            await turn_context.send_activity("format is incorrect. format should be like this:"\
                + "'31-01-2018:2359 to 03-02-2018:1300 mel ; 03-02-2018:1200 to 03-02-2018:2130 jon'")


    async def on_members_added_activity(
        self,
        members_added: ChannelAccount,
        turn_context: TurnContext
    ):
        for member_added in members_added:
            if member_added.id != turn_context.activity.recipient.id:
                await turn_context.send_activity("Hello and welcome!")
