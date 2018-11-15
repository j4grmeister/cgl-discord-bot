from bot import bot
import utils
from discord.ext import commands
import discord
import database
import json
from cgl_converters import *

import teams

TEAM_STATS_DICT = {
    "maps": {
        "dust2": {"wins": 0, "total": 0},
        "mirage": {"wins": 0, "total": 0},
        "cache": {"wins": 0, "total": 0},
        "inferno": {"wins": 0, "total": 0},
        "nuke": {"wins": 0, "total": 0},
        "overpass": {"wins": 0, "total": 0},
        "inferno": {"wins": 0, "total": 0}
    }
}

PROHIBITED_NAMES = [
    "league admin",
    "cgl bot",
    "owner"
]

class Teams:
    @commands.command(pass_context=True)
    async def createteam(self, ctx, *, teamname):
        """create a team
        Creates a new team with the given name and makes the user the captain of that team.
        Players may not create a team if they are already a member of another team."""
        if database.user_registered(ctx.author.id):
            #check that the user is not already on a team
            database.cur.execute("SELECT team FROM playerTable WHERE discordID=%s;" % ctx.author.id)
            if database.cur.fetchone()[0] != None:
                await ctx.send("You cannot be on more than one team at a time. Please leave your current team before creating another one.")
                return
            if teamname == None:
                await ctx.send("Please provide a team name.")
                return
            if teamname.lower() in PROHIBITED_NAMES:
                await ctx.send("You cannot create a team with that name.")
                return
            #check that the team name is not already taken
            database.cur.execute("SELECT * FROM teamTable WHERE lower(teamname)='%s';" % teamname.lower())
            if database.cur.fetchone() != None:
                await ctx.send("The team name '%s' is already taken. Please choose another name." % teamname)
                return
            #create the team
            teamrole = await bot.guild.create_role(name=teamname, colour=discord.Colour.orange(), hoist=True)
            await teamrole.edit(position=bot.guild.get_role(bot.FREE_AGENT_ROLE).position+1)
            await teamrole.edit(permissions=bot.guild.get_role(bot.MEMBER_ROLE).permissions)
            member = bot.guild.get_member(ctx.author.id)
            await member.add_roles(teamrole, bot.guild.get_role(bot.CAPTAIN_ROLE))
            await member.remove_roles(bot.guild.get_role(bot.FREE_AGENT_ROLE))
            database.cur.execute("INSERT INTO teamTable (teamname, stats, captainID, teamRoleID, awards) VALUES ('%s', '%s', %s, %s, '{}');" % (teamname, json.dumps(TEAM_STATS_DICT), ctx.author.id, teamrole.id))
            database.cur.execute("UPDATE playerTable SET team='%s' WHERE discordID=%s;" % (teamname, ctx.author.id))
            database.conn.commit()
            await ctx.send("Team \'%s\' successfully created. Invite other players to your team using the !invite command." % teamname)
            await utils.log("%s created %s." % (database.username(ctx.author.id), teamname))
        else:
            await ctx.author.send(bot.NOT_REGISTERED_MESSAGE)

    @commands.command(pass_context=True)
    async def invite(self, ctx, player: CGLUser):
        """invite a player to your team
        Invites another player to your team. The player can be specified by one of two methods:
            mentioning the player or
            giving the player's full Discord tag."""
        if database.user_registered(ctx.author.id):
            if player == None:
                await ctx.send("Either you didn't supply a player or the one you gave was not valid. Please make sure the player is registered in the league.")
                return
            #make sure the user is the captain of a team
            database.cur.execute("SELECT teamname FROM teamTable WHERE captainID=%s;" % ctx.author.id)
            team = database.cur.fetchone()
            if team == None:
                await ctx.send("You are not a captain of a team.")
                return
            team = team[0]
            #make sure there aren't too many players on the team
            database.cur.execute("SELECT * FROM playerTable WHERE team='%s';" % team)
            if len(database.cur.fetchall()) >= 7:
                await ctx.send("Your team has already reached the maximum of 7 players.")
                await utils.log("%s could not invite %s to %s. There are too many players." % (database.username(ctx.author.id), targetusername, team))
                return
            #make sure the target player isn't already on a team
            database.cur.execute("SELECT team FROM playerTable WHERE discordID=%s;" % player.id)
            targetteam = database.cur.fetchone()
            if targetteam == None:
                await ctx.send("That player is not a member of the league. Please make sure they register with !register <username>.")
                return
            if targetteam[0] != None:
                await ctx.send("That player is already on a team.")
                return
            invite = await player.send("You have been invited to join %s.\n:thumbsup: accept\n:thumbsdown: decline" % team)
            await invite.add_reaction(u"\U0001F44D") #thumbsup
            await invite.add_reaction(u"\U0001F44E") #thumbsdown
            targetusername = database.username(player.id)
            await ctx.send("%s has been invited to %s." % (targetusername, team))
            await utils.log("%s invited %s to %s." % (database.username(ctx.author.id), targetusername, team))
        else:
            await ctx.author.send(bot.NOT_REGISTERED_MESSAGE)

    @commands.command(pass_context=True)
    async def requeststandin(self, ctx):
        """requests a standin for your team
        """
        if database.user_registered(ctx.author.id):
            #make sure the user is the captain of a team
            database.cur.execute("SELECT teamname FROM teamTable WHERE captainID=%s;" % ctx.author.id)
            team = database.cur.fetchone()
            if team == None:
                await ctx.send("You are not a captain of a team.")
                return
            team = team[0]
            channel = bot.guild.get_channel(bot.STANDIN_CHANNEL)
            username = database.username(ctx.author.id)
            await channel.send("%s has requested a stand-in for %s." % (ctx.author.mention, team))
            await ctx.send("a stand-in has been requested for %s." % team)
            await utils.log("%s has requested a stand-in for %s." % (username, team))
        else:
            await ctx.author.send(bot.NOT_REGISTERED_MESSAGE)

    @commands.command(pass_context=True)
    async def leaveteam(self, ctx):
        """leaves your current team
        The captain of a team is not allowed to leave a team if there are other players on it.
        If the user is the last remaining player on the team, the team will be disbanded."""
        if database.user_registered(ctx.author.id):
            #check that the user is on a team
            database.cur.execute("SELECT team FROM playerTable WHERE discordID=%s;" % ctx.author.id)
            team = database.cur.fetchone()[0]
            if team == None:
                await ctx.send("You are not on a team.")
                return
            #check if there are other members on the team
            database.cur.execute("SELECT * FROM playerTable WHERE team='%s';" % team)
            othermembers = (len(database.cur.fetchall()) > 1)
            if not othermembers:
                await teams.disband_team(team, None)
                await ctx.send("Team '%s' has been disbanded." % team)
                await utils.log("%s left %s and disbanded it." % (database.username(ctx.author.id), team))
                return
            #check if the user is the captain of the team
            database.cur.execute("SELECT * FROM teamTable WHERE captainID=%s;" % ctx.author.id)
            if database.cur.fetchone() != None:
                await ctx.send("You cannot leave your team as the captain.\nPlease make another player the captain of the team before leaving.")
                return
            database.cur.execute("UPDATE playerTable SET team=NULL WHERE discordID=%s;" % ctx.author.id)
            database.conn.commit()
            database.cur.execute("SELECT teamRoleID FROM teamTable WHERE teamname='%s';" % team)
            teamrole = database.cur.fetchone()[0]
            member = bot.guild.get_member(ctx.author.id)
            await member.remove_roles(bot.guild.get_role(teamrole))
            await member.add_roles(bot.guild.get_role(bot.FREE_AGENT_ROLE))
            await ctx.send("You have left team '%s'." % team)
            await utils.log("%s left %s." % (database.username(ctx.author.id), team))
        else:
            await ctx.send(bot.NOT_REGISTERED_MESSAGE)

    @commands.command(pass_context=True)
    async def disbandteam(self, ctx):
        """disbands the user's team if they are the captain"""
        if database.user_registered(ctx.author.id):
            #check that the user is on a team
            database.cur.execute("SELECT teamname FROM teamTable WHERE captainID=%s;" % ctx.author.id)
            team = database.cur.fetchone()
            if team == None:
                await ctx.send("You are not the captain of a team.")
                return
            team = team[0]
            await teams.disband_team(team, "Team '%s' has been disbanded by the team captain.\nYou are now a free agent." % team)
            await ctx.author.remove_roles(bot.guild.get_role(bot.CAPTAIN_ROLE))
            await ctx.send("Team '%s' has been disbanded ." % team)
            await utils.log("%s disbanded %s." % (database.username(ctx.author.id), team))
        else:
            await ctx.send(bot.NOT_REGISTERED_MESSAGE)

    @commands.command(pass_context=True)
    async def kickteammate(self, ctx, player: CGLUser):
        """kicks the player from the user's team"""
        if database.user_registered(ctx.author.id):
            if player == None:
                await ctx.send("Please provide a player to kick from your team.")
                return
            #check that the user is the captain of a team
            database.cur.execute("SELECT teamname FROM teamTable WHERE captainID=%s;" % ctx.author.id)
            team = database.cur.fetchone()
            if team == None:
                await ctx.send("You are not the captain of a team.")
                return
            team = team[0]
            #check that the target player is also on the team
            database.cur.execute("SELECT team FROM playerTable WHERE discordID=%s;" % player.id)
            targetteam = database.cur.fetchone()
            if targetteam == None:
                await ctx.send("That player does not exist.")
                return
            if targetteam[0] == team:
                database.cur.execute("SELECT teamRoleID FROM teamTable WHERE teamname='%s';" % team)
                roleid = database.cur.fetchone()[0]
                teamrole = bot.guild.get_role(roleid)
                database.cur.execute("UPDATE playerTable SET team=NULL WHERE discordID=%s;" % player.id)
                database.conn.commit()
                member = bot.guild.get_member(player.id)
                await member.remove_roles(teamrole)
                await member.add_roles(bot.guild.get_role(bot.FREE_AGENT_ROLE))
                await player.send("You have been kicked from team '%s' by the team captain. You are now a free agent." % team)
                targetusername = database.username(player.id)
                await ctx.send("%s has been kicked from team '%s'." % (targetusername, team))
                await utils.log("%s kicked %s from %s." % (database.username(ctx.author.id), targetusername, team))
        else:
            await ctx.send(bot.NOT_REGISTERED_MESSAGE)

    @commands.command(pass_context=True)
    async def makecaptain(self, ctx, player: CGLUser):
        """makes the player the new captain of the user's team"""
        if database.user_registered(ctx.author.id):
            if player == None:
                await ctx.send("Please provide a player to make the captain of your team.")
                return
            #check that the user is the captain of a team
            database.cur.execute("SELECT teamname FROM teamTable WHERE captainID=%s;" % ctx.author.id)
            team = database.cur.fetchone()
            if team == None:
                await ctx.send("You are not the captain of a team.")
                return
            team = team[0]
            #check that the target player is also on the team
            database.cur.execute("SELECT team FROM playerTable WHERE discordID=%s;" % player.id)
            targetteam = database.cur.fetchone()
            if targetteam == None:
                await ctx.send("That player does not exist.")
                return
            database.cur.execute("UPDATE teamTable SET captainID=%s WHERE teamname='%s';" % (player.id, team))
            database.conn.commit()
            await target.add_roles(bot.guild.get_role(bot.CAPTAIN_ROLE))
            await ctx.author.remove_roles(bot.guild.get_role(bot.CAPTAIN_ROLE))
            await target.send("You have been made the new captain of your team.")
            targetusername = database.username(target.id)
            await ctx.send("%s has been made the new captain of %s." % (targetusername, team))
            await utils.log("%s made %s the captain of %s." % (database.username(ctx.author.id), targetusername, team))
        else:
            await ctx.send(bot.NOT_REGISTERED_MESSAGE)


    @commands.command(pass_context=True)
    async def editroster(self, ctx):
        """set primary and substitute team members"""
        emojis = ["1⃣", "2⃣", "3⃣", "4⃣", "5⃣", "6⃣", "7⃣"]
        if database.user_registered(ctx.author.id):
            #check that the user is the captain of a team
            database.cur.execute("SELECT teamname FROM teamTable WHERE captainID=%s;" % ctx.author.id)
            team = database.cur.fetchone()
            if team == None:
                await ctx.send("You are not the captain of a team.")
                return
            team = team[0]
            database.cur.execute("SELECT username FROM playerTable WHERE team='%s';" % team)
            players = database.cur.fetchall()
            msg = "Please select your team's primary players.\nThen select ✅ ."
            index = 0
            for p in players:
                msg += "\n%s  %s" % (emojis[index], p[0])
                index += 1
            message = await ctx.author.send(msg)
            for i in range(index):
                await message.add_reaction(emojis[i])
            await message.add_reaction("✅")
        else:
            await ctx.send(bot.NOT_REGISTERED_MESSAGE)

bot.add_cog(Teams())
