from bot import bot
import discord
from discord.ext import commands
import socket

async def log(msg):
    await bot.guild.get_channel(bot.LOG_CHANNEL).send(msg)

def ip_from_domain(domain):
    return socket.gethostbyname(domain)
