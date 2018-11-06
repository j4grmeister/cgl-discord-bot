from bot import bot
from discord.ext import commands
import discord
import database
from cgl_converters import *

class Stats:
    @commands.command(pass_context=True)
    async def elo(self, ctx):
        """displays the player's elo."""
        if database.user_registered(ctx.author.id):
            await ctx.send("Your current elo is %s." % database.player_elo(ctx.author.id))
        else:
            await ctx.send(bot.NOT_REGISTERED_MESSAGE)

    @commands.command(pass_context=True)
    async def rep(self, ctx):
        """displays the player's rep."""
        if database.user_registered(ctx.author.id):
            await ctx.send("Your current rep is %s." % database.player_rep(ctx.author.id))
        else:
            await ctx.send(bot.NOT_REGISTERED_MESSAGE)

    @commands.command(pass_context=True)
    async def playerinfo(self, player: CGLUser):
        if player == None:
            await ctx.send("That player does not exist.")
            return
        info = "__%s__\n" % database.username(player.id)
        info += "**Elo**: %s\n" % database.player_elo(player.id)
        info += "**Rep**: %s\n" % database.player_rep(player.id)
        info += "**Team**: %s\n" % database.player_team(player.id)
        member = bot.guild.get_member(player.id)
        region = None
        if bot.guild.get_role(bot.NA_ROLE) in member.roles:
            region = "NA"
        if bot.guild.get_role(bot.EU_ROLE) in member.roles:
            region = "EU"
        info += "**Region**: %s" % region
        await ctx.send(info)

    @commands.command(pass_context=True)
    async def teaminfo(self, ctx, *, team: CGLTeam):
        if team == None:
            await ctx.send("That team does not exist.")
            return
        info = "**%s**\nPlayers:\n" % team.teamname
        for p in team.players:
            info += "*%s*\n" % database.username(p.id)
        info += "Region: %s" % team.region
        await ctx.send(info)


bot.add_cog(Stats())
