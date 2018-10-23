#import thread
import threading
import time
import discord
from discord.ext import commands
import discord
import os
import psycopg2
import math
import asyncio
from datetime import datetime
import database

bot = commands.Bot(command_prefix='!')

import matchmaking
import teams

async def background_thread():
    bot.delta_time = 0
    loop = asyncio.get_event_loop()
    last_time = loop.time()
    while True:
        now = loop.time()
        bot.delta_time = now - last_time
        last_time = now
        await matchmaking.mm_thread()
        await asyncio.sleep(.1)

@bot.event
async def on_ready() :
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

    bot.appinfo = await bot.application_info()
    bot.CGL_server = int(os.environ['CGL_SERVER'])
    bot.guild = bot.get_guild(bot.CGL_server)
    bot.lobby_category = int(os.environ['LOBBY_CATEGORY'])
    bot.AFK_CHANNEL_ID = int(os.environ['AFK_CHANNEL'])
    bot.MEMBER_ROLE = 499276055585226773
    bot.FREE_AGENT_ROLE = 503654821644206093
    bot.mmqueue = matchmaking.MMQueue()
    bot.matches = {}
    bot.available_lobbies = [i for i in range(20)]

    bot.task = asyncio.create_task(matchmaking.mm_thread())

@bot.event
async def on_message(msg):
    await matchmaking.process_match_commands(msg)
    await bot.process_commands(msg)

@bot.event
async def on_reaction_add(reaction, user):
    if user.id != bot.appinfo.id:
        await teams.process_invite(reaction, user)

#MM_CHANNEL_ID = os.environ['MM_CHANNEL_ID']
#MM_CHANNEL_ID = 498928703091507220
MM_CHANNEL_ID = int(os.environ['MM_CHANNEL'])

@bot.event
async def on_voice_state_update(member, before, after):
    if after.channel != None:
        if after.channel.id == MM_CHANNEL_ID and after.channel != before.channel:
            #make sure that the player is not currently suspended
            suspension = database.player_suspension(member.id)
            if suspension != None:
                susduration = suspension - datetime.now()
                if susduration.total_seconds() <= 0:
                    suspension = None
                    database.cur.execute("UPDATE playerTable SET end_of_suspension=NULL WHERE discordID=%s;" % member.id)
                    database.conn.commit()
            #make sure that the player is not currently participating in a match
            queued = (member.id in matchmaking.mmqueue.queue)
            if not queued:
                for m in matchmaking.matches:
                    for id in matchmaking.matches[m]["players"]:
                        if id == member.id:
                            queued = True
                            break
                    if queued:
                        break
            if suspension != None:
                susduration = suspension - datetime.now()
                await member.send("Due to a suspension, you are currently unable to join matchmaking. Your suspension will end in %s." % susduration)
                await member.edit(voice_channel=bot.get_channel(AFK_CHANNEL_ID))
            elif queued:
                await member.send("You are already participating in a match. Please complete your current match before entering matchmaking again.")
                await member.edit(voice_channel=bot.get_channel(AFK_CHANNEL_ID))
            else:
                matchmaking.mmqueue.push(member.id)
                await member.edit(deafen=True)
    if before.channel != None:
        if before.channel.id == MM_CHANNEL_ID and before.channel != after.channel:
            matchmaking.mmqueue.pop(member.id)
            await member.edit(deafen=False)
