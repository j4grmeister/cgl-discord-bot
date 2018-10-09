import math

from bot import bot
import database

class MMQueue:
    def __init__(self):
        self.queue = {}

    def in_queue(self):
        l = []
        for id in self.queue.keys():
            if self.queue[id]["lobby"] < 0:
                l.append(id)
        return l

    def lobbies(self):
        d = {}
        for id in self.queue.keys():
            if self.queue[id]["lobby"] >= 0:
                if not self.queue[id]["lobby"] in dict:
                    d[self.queue[id]["lobby"]] = {"time": self.queue[id]["time"], "players": {}}
                d[self.queue[id]["lobby"]]["players"][id] = {"team": self.queue[id]["team"], "confirmed": self.queue[id]["confirmed"]}
        return d

    def step_time(self):
        for id in self.queue.keys():
            self.queue[id]["time"] -= 1

    def push(self, discordID):
        self.queue[discordID] = {"lobby": -1, "confirmed": False, "time": 0, "team": 0}

    def pop(self, discordID):
        del self.queue[discordID]

    def move(self, discordID, lobby, team=0):
        self.queue[discordID]["lobby"] = lobby
        self.queue[discordID]["confirmed"] = False
        self.queue[discordID]["time"] = 30
        self.queue[discordID]["team"] = team

available_lobbies = [i for i in range(20)]

mmqueue = MMQueue()
matches = {}

MAP_LIST = ["dust2", "mirage", "cache", "inferno", "nuke", "overpass", "cobblestone"]

def mm_thread():
    while True:
        cycle_queue()
        cycle_matches()
        time.sleep(1)

def cycle_queue():
    inq = mmqueue.in_queue()
    lobby = 0
    for i in range(math.floor(len(inq)/10)*10):
        if i%10 == 0:
            if len(available_lobbies) == 0:
                break
            lobby = available_lobbies[0]
            available_lobbies.pop(0)
        id = inq[i]
        team = 1
        if i%10/5 >= 1:
            team = 2
        mmqueue.move(id, lobby, team)
        user = bot.get_user(id)
        user.send("A game has been found! Type \"!accept\" to confirm.")
        user.send("30 seconds left")
    mmqueue.step_time()
    lobbies = mmqueue.lobbies()
    for l in lobbies.keys():
        ready = True
        for id in lobbies[l]["players"]:
            if not lobbies[l]["players"][id]["confirmed"]:
                ready = False
                user = bot.get_user(id)
                user.send("%s" % lobbies[l]["time"])
        #begin the game if all players have confirmed the match
        if ready:
            #create the lobbies for the teams
            textchat = CGL_server.create_text_channel("Game Chat", category=lobby_category)
            teamchat = [None, None]
            teamchat[0] = CGL_server.create_voice_channel("Your Team", category=lobby_category)
            teamchat[1] = CGL_server.create_voice_channel("Your Team", category=lobby_category)
            matches[l] = {"map": MAP_LIST.copy(), "votes": {}, "time": 30, "channels": {0: textchat, 1: teamchat[0], 2: teamchat[1]}, "players": {}}
            host = lobbies[l]["players"]
            host_rep = database.player_rep(host)
            for id in lobbies[l]["players"]:
                this_rep = database.player_rep(id)
                if this_rep > host_rep:
                    host = id
                    host_rep = this_rep
                team = mmqueue.queue[id]["team"]
                matches[l]["players"][id] = {"team": team}
                user = bot.get_user(id)
                textchat.set_permissions(user, read_messages=True)
                teamchat[team-1].set_permissions(user, connect=True)
                user.edit(voice_channel=teamchat[team-1])
            matches[l]["host"] = host
            mapliststring = "maps remaining:"
            for mv in matches[m]["map"]:
                mapliststring += "\n    %s" % mv
            matches[m]["channels"][0].send("%s\nType \"vote map_name\" to vote to eliminate a map." % mapliststring)
            continue
        if lobbies[l]["time"] <= 0:
            for id in lobbies[l]["players"]:
                if lobbies[l]["players"][id]["confirmed"]:
                    mmqueue.move(id, -1)
                    user = bot.get_user(id)
                    user.send("One or more players in your lobby failed to confirm the match. You have been added back to the queue.")
                else:
                    del mmqueue.queue[id]
                    mmqueue.pop(id)
                    user = bot.get_user(id)
                    user.send("You failed to confirm your match. You have been removed from the queue.")
            available_lobbies.append(l)

ELO_K_FACTOR = 16

def cycle_matches():
    for m in matches:
        if matches[m]["map"] is list:
            if matches[m]["time"] % 5:
                matches[m]["channels"][0].send("%s seconds remaining" % matches[m]["time"])
            matches[m]["time"] -= 1
            if len(matches[m]["votes"]) == 10 or matches[m]["time"] <= 0:
                #determine most popular vote
                track = {}
                for key, value in matches[m]["votes"].items():
                    if value not in track:
                        track[value] = 0
                    else:
                        track[value] += 1
                map = max(track,key=track.get)
                matches[m]["votes"] = {}
                matches[m]["map"].remove(map)
                matches[m]["time"] = 30
                if len(matches[m]["map"]) == 1:
                    matches[m]["time"] = 300
                    matches[m]["map"] = matches[m]["map"][0]
                    matches[m]["channels"][0].send("The match will be played on %s.\nThe match host is %s.\nPlease create a lobby on popflash.site and paste the link in this channel.\nWhen the game has finished, all players must report the result by typing \"result win\" or \"result lose\"." % (matches[m]["map"], bot.get_user(matches[m]["host"]).mention))
                else:
                    mapliststring = "maps remaining:"
                    for mv in matches[m]["map"]:
                        mapliststring += "\n    %s" % mv
                    matches[m]["channels"][0].send("%s\nType \"vote map_name\" to vote to eliminate a map." % mapliststring)
        else:
            if len(matches[m]["votes"]) > 0:
                matches[m]["time"] -= 1
                if matches[m]["time"] == 0:
                    for channel in matches[m]["channels"]:
                        channel.delete()
                    available_lobbies.append(m)
                    result = 0 #positive - team 1 wins; negative - team 2 wins
                    for id in matches[m]["votes"]:
                        vote = 0
                        if matches[m]["votes"][vote] == "win":
                            vote = 1
                        elif matches[m]["votes"][vote] == "lose":
                            vote = -1
                        if matches[m]["players"][id]["team"] == 2:
                            vote *= -1
                        result += vote
                    winners = {}
                    winner_average = 0
                    losers = {}
                    loser_average = 0
                    for id in matches[m]["players"]:
                        elo = database.player_elo(id)
                        team = 0
                        if matches[m]["players"][id]["team"] == 1:
                            team = 1
                        elif matches[m]["players"][id]["team"] == 2:
                            team = -1
                        if result < 0:
                            team *= -1
                        if team == 1:
                            winners[id] = elo
                            winner_average += elo
                        elif team == -1:
                            losers[id] = elo
                            loser_average += elo
                    winner_average /= 5
                    loser_average /= 5
                    for id in winners:
                        expected_score = 1/(1+pow(10, (loser_average-winners[id])/400))
                        new_elo = winners[id] + ELO_K_FACTOR*(1-expected_score)
                        database.cur.execute("UPDATE playerTable SET elo=%s WHERE discordID=%s;" % (new_elo, id))
                    for id in losers:
                        expected_score = 1/(1+pow(10, (loser_average-winners[id])/400))
                        new_elo = winners[id] + ELO_K_FACTOR*(0-expected_score)
                        database.cur.execute("UPDATE playerTable SET elo=%s WHERE discordID=%s;" % (new_elo, id))
                    database.conn.commit()
                    del matches[m]


def process_match_commands(msg):
    is_game_chat = False
    lobby = None
    for l in matches:
        if matches[l]["channels"][0].id == msg.channel.id:
            is_game_chat = True
            lobby = l
            break
    if is_game_chat:
        if msg.content.startswith("vote "):
            if msg.author.id not in matches[lobby]["votes"]:
                map = msg.content[5:]
                if map in matches[lobby]["map"]:
                    matches[lobby]["votes"][msg.author.id] = map
                else:
                    msg.channel.send("%s is not a valid map." % map)
        elif msg.content.startswith("result "):
            if msg.author.id not in matches[lobby]["votes"]:
                result = msg.content[7:]
                if result != "win" and result != "lose":
                    msg.channel.send("%s is not a valid match result." % result)