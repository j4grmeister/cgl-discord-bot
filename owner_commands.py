from discord.ext import commands
import discord

import database

async def owner_command(ctx, func):
    def wrapper(ctx, *args, **kwargs):
        if ctx.message.author.id == discord.AppInfo.owner.id:
            func(ctx, *args, **kwargs)
        else:
            await ctx.send("This command is only for use by the owner.")
    return wrapper

@owner_command
async def giveelo(ctx, target: discord.User, delo):
    elo = database.player_elo(target.id)
    elo += delo
    database.cur.execute("UPDATE playerTable SET elo=%s WHERE discordID=%s;" % (elo, target.id))
    database.conn.commit()
    await ctx.send("%s has been given %s elo points." % (target.mention, delo))
