import requests
import os
import json
import database

login_email = os.environ['DATHOST_EMAIL']
login_pass = os.environ['DATHOST_PASSWORD']
rcon_pass = os.environ['RCON_PASSWORD']

def server_id(name):
    database.cur.execute("SELECT serverID FROM serverTable WHERE serverName='%s';" % name)
    return database.cur.fetchone()[0]

def create_server(name, location, map):
    p = {
        'game': 'csgo',
        'location': location,
        'name': name,
        'csgo_settings.enable_gotv': 'true',
        'csgo_settings.game_mode': 'classic_competitive',
        'csgo_settings.maps_source': 'mapgroup',
        'csgo_settings.mapgroup': 'mg_active',
        'csgo_settings.mapgroup_start_map': map,
        'csgo_settings.pure_server': 'true',
        'csgo_settings.rcon': rcon_pass,
        'csgo_settings.slots': 5,
        'csgo_settings.tickrate': 128
    }
    h = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json'
    }
    r = requests.post('https://dathost.net/api/0.1/game-servers', auth=(login_email, login_pass), data=p)
    return r.json(), r.status_code

def start_server(id):
    p = {
        'allow_host_reassignment': 'true'
    }
    r = requests.post('https://dathost.net/api/0.1/game-servers/%s/start' % id, auth=(login_email, login_pass), data=p)
    return r.status_code

def stop_server(id):
    r = requests.post('https://dathost.net/api/0.1/game-servers/%s/stop' % id, auth=(login_email, login_pass))
    return r.status_code

def server_info(id):
    r = requests.get('https://dathost.net/api/0.1/game-servers/%s' % id, auth=(login_email, login_pass))
    return r.json(), r.status_code

def change_map(id, map):
    p = {
        'csgo_settings': {
            'mapgroup_start_map': map
        }
    }
    r = requests.put('https://dathost.net/api/0.1/game-servers/%s' % id, auth=(login_email, login_pass), data=p)

def get_console(id, max_lines):
    p = {
        'max_lines': line
    }
    r = requests.get('https://dathost.net/api/0.1/game-servers/%s/console' % id, auth=(login_email, login_pass), data=p)
    return r.text

def put_console(id, line):
    p = {
        'line': line
    }
    r = requests.post('https://dathost.net/api/0.1/game-servers/%s/console' % id, auth=(login_email, login_pass), data=p)
