# every lounge is different so this file will probably
# have to be completely rewritten for each server.
# my implementation is here as an example; gspread is only
# needed if you get MMR from a spreadsheet.

# The important part is that the function returns False
# if a player's MMR can't be found,
# and returns the player's MMR otherwise

import discord
from discord.ext import commands
import aiohttp
import gspread
from collections import namedtuple, defaultdict
import dill as p
from ExtraChecks import owner_or_permissions, carrot_prohibit_check, exception_on_not_lounge, guild_manually_managed_for_elo
import Shared
from datetime import datetime
import unidecode

gc = gspread.service_account(filename='credentials.json')


MKW_LOUNGE_RT_API = "https://www.mkwlounge.gg/api/ladderplayer.php?ladder_type=rt&player_names="
MKW_LOUNGE_CT_API = "https://www.mkwlounge.gg/api/ladderplayer.php?ladder_type=ct&player_names="

MKT_LOUNGE_API = "http://www.mariokarttour.net/api/leaderboard?from=1&to=9999"

LORENZI_WEBSITE_DATA_API = "https://gb.hlorenzi.com/api/v1/graphql"
MK7_GRAPHQL_PAYLOAD = """{
    team(teamId: "3jRk9D")
    {
        players {name, rating}
    }
}"""

MKW_ITEM_RAIN_GRAPHQL_PAYLOAD = """{
    team(teamId: "Y6sCY2")
    {
        players {name, rating}
    }
}"""

MK8DX_ITALIA_GRAPHQL_PAYLOAD = """{
    team(teamId: "FMoheE")
    {
        players {name, rating}
    }
}"""

    



Website_JSON_Framer = namedtuple('Website_JSON_Framer', 'name_name primary_rating_name secondary_rating_name')
Website_JSON_Info = namedtuple('Website_JSON_Info', 'API_URL primary_JSON_framing secondary_JSON_framing')
Website_Data = namedtuple('Website_Data', 'primary_data secondary_data')

Sheet_ = namedtuple('Sheet_', 'sheet_name sheet_range', defaults=[None, None])
Sheet_Data = namedtuple('Sheet_Data', 'sheet_id primary_rating secondary_rating', defaults=[None, Sheet_(), Sheet_()])
Spreadsheet_Data = namedtuple('Spreadsheet_Data', 'primary_sheet secondary_sheet', defaults=[Sheet_Data(), Sheet_Data()])
Guild_Rating_Data = namedtuple('Guild_Rating_Data', 'using_rating using_sheet sheet_data website_data', defaults=[True, True, Spreadsheet_Data(), Spreadsheet_Data()])



json_cacher = {}
CACHE_MKT_LOUNGE_DATA = True


async def getJSONData(full_url):
    async with aiohttp.ClientSession() as session:
        async with session.get(full_url) as r:
            if r.status == 200:
                js = await r.json()
                return js
            
async def lorenzi_fetch(graph_ql_payload):
    async with aiohttp.ClientSession() as session:
        headers = {"Content-Type" : "text/plain"}
        async with session.post(LORENZI_WEBSITE_DATA_API, headers=headers, data=graph_ql_payload) as resp:
            data = await resp.json()
            return data
        
async def mkw_lounge_json_fetch(names, is_rt):
    full_url = MKW_LOUNGE_RT_API if is_rt else MKW_LOUNGE_CT_API
    full_url += ",".join(names)
    return await getJSONData(full_url)
    
async def mkt_lounge_json_fetch():
    return await getJSONData(MKT_LOUNGE_API)


    

#Uses a 20s caching system to relieve spam load on lorenzi's website
async def lorenzi_get_JSON(ctx, graph_ql_payload):
    curTime = datetime.now()
    if graph_ql_payload not in json_cacher or json_cacher[graph_ql_payload][1] + Shared.CACHING_TIME < curTime:
        json_cacher[graph_ql_payload] = (await lorenzi_fetch(graph_ql_payload), curTime)
    return json_cacher[graph_ql_payload][0]
    
        
def lorenzi_json_transformer(json_player_data):
    player_dict = {}
    for player in json_player_data['data']['team']['players']:
        player_dict[player['name'].lower().replace(" ", "")] = int(player['rating'])
    return player_dict

def mkw_lounge_json_transformer(json_player_data):
    player_dict = {}
    for player in json_player_data['results']:
        player_dict[player['player_name'].lower().replace(" ", "")] = int(player['current_mmr'])
    return player_dict

def mkt_lounge_json_transformer(json_player_data):
    player_dict = {}
    for player in json_player_data:
        player_dict[player['name'].lower().replace(" ", "")] = int(player['mmr'])
    return player_dict


def mkw_json_corruption_check(json_data):
    if json_data == None:
        print("Bad request to Lounge API... Data was None.")
        return True
    if "results" not in json_data:
        print("Bad request to Lounge API... Error in data.")
        return True
    if not isinstance(json_data["results"], list):
        print("Bad request to Lounge API... Results not a list.")
        return True
    
    for playerData in json_data["results"]:
        if not isinstance(playerData, dict):
            return True
        
        #if "current_mmr" not in playerData or not isinstance(playerData["current_mmr"], int):
        #    return True
        if "current_mmr" not in playerData or not Shared.isint(playerData["current_mmr"]):
            return True
        if "player_name" not in playerData or not isinstance(playerData["player_name"], str):
            return True
    return False

def mkt_json_corruption_check(json_data):
    if json_data == None:
        print("Bad request to MKT Lounge API... Data was None.")
        return True
    if not isinstance(json_data, list):
        print("Bad request to MKT Lounge API... Results not a list.")
        return True

    for playerData in json_data:
        if not isinstance(playerData, dict):
            return True

        if "mmr" not in playerData or not Shared.isint(playerData["mmr"]):
            return True
        if "name" not in playerData or not isinstance(playerData["name"], str):
            return True
    return False

def lorenzi_data_corruption_check(json_player_data):
    if not isinstance(json_player_data, dict):
        return True
    if 'data' not in json_player_data:
        return True
    if not isinstance(json_player_data['data'], dict):
        return True
    if 'team' not in json_player_data['data']:
        return True
    if not isinstance(json_player_data['data']['team'], dict):
        return True
    if 'players' not in json_player_data['data']['team']:
        return True
    if not isinstance(json_player_data['data']['team']['players'], list):
        return True
    for player in json_player_data['data']['team']['players']:
        if not isinstance(player, dict) or\
        'name' not in player or\
        'rating' not in player or\
        not isinstance(player['name'], str) or\
        (not isinstance(player['rating'], float) and not isinstance(player['rating'], int)):
            return True
    return False

def result_file_write(stuff):
    with open("resultFile.txt", "w") as f:
        f.write(str(stuff))
        
def utf8_to_ascii_mapping_name_fix(name:str):
    name = unidecode.unidecode(name)
    fixed_name = ''
    for char in name:
        if char.isalnum():
            fixed_name += char
    return fixed_name.lower().replace(" ", "")
mk7_name_fix = utf8_to_ascii_mapping_name_fix
mkw_item_rain_name_fix = utf8_to_ascii_mapping_name_fix
mkw_lounge_name_fix = utf8_to_ascii_mapping_name_fix
mk8dx_italia_lounge_name_fix = utf8_to_ascii_mapping_name_fix
mkt_lounge_name_fix = utf8_to_ascii_mapping_name_fix

def json_match_ratings(all_ratings, members:[discord.Member], data_corruption_check, json_transformer, name_fix=None):
    using_str = isinstance(members[0], str)
        
    member_ratings = dict(zip(members, [False]*len(members)))
    names = ['']*len(members)
    if name_fix is None:
        names = [member.display_name.lower().replace(" ", "") for member in members] if not using_str else [member.lower().replace(" ", "") for member in members]
    else:
        names = [name_fix(member.display_name) for member in members] if not using_str else [name_fix(member) for member in members]
    
    check_value = None
    if data_corruption_check(all_ratings):
        return member_ratings
    fixed_ratings = json_transformer(all_ratings)
    for name, rating in fixed_ratings.items():
        if name_fix is not None:
            name = name_fix(name)
            
        if name not in names: #didn't ask for this person, so continue
            continue
        #We found a match
        check_value = rating
        found_member = members[names.index(name)]
        member_ratings[found_member] = False if check_value is None else check_value
    return member_ratings

async def mk7_mmr(ctx, members:[discord.Member], is_primary_leaderboard=True, is_primary_rating=True):
    json_data = await lorenzi_get_JSON(ctx, MK7_GRAPHQL_PAYLOAD)
    return json_match_ratings(json_data, members, lorenzi_data_corruption_check, lorenzi_json_transformer, name_fix=mk7_name_fix)

async def mkw_item_rain_mmr(ctx, members:[discord.Member], is_primary_leaderboard=True, is_primary_rating=True):
    json_data = await lorenzi_get_JSON(ctx, MKW_ITEM_RAIN_GRAPHQL_PAYLOAD)
    return json_match_ratings(json_data, members, lorenzi_data_corruption_check, lorenzi_json_transformer, name_fix=mkw_item_rain_name_fix)

async def mk8_italia_mmr(ctx, members:[discord.Member], is_primary_leaderboard=True, is_primary_rating=True):
    json_data = await lorenzi_get_JSON(ctx, MK8DX_ITALIA_GRAPHQL_PAYLOAD)
    return json_match_ratings(json_data, members, lorenzi_data_corruption_check, lorenzi_json_transformer, name_fix=mk8dx_italia_lounge_name_fix)
    

async def mkw_lounge_website_mmr(members:[discord.Member], is_rt=True, name_fix=None):
    using_str = isinstance(members[0], str)
    names = ['']*len(members)
    if name_fix is None:
        names = [member.display_name.lower().replace(" ", "") for member in members] if not using_str else [member.lower().replace(" ", "") for member in members]
    else:
        names = [name_fix(member.display_name) for member in members] if not using_str else [name_fix(member) for member in members]
    
    data = None
    try:
        data = await mkw_lounge_json_fetch(names, is_rt)
    except: #numerous failure types can occur, but they all mean the same thing: we didn't get out data
        return False
    return json_match_ratings(data, members, mkw_json_corruption_check, mkw_lounge_json_transformer, name_fix)
    

async def mkw_lounge_mmr(ctx, members:[discord.Member], is_primary_leaderboard=True, is_primary_rating=True, name_fix=mkw_lounge_name_fix):
    return await mkw_lounge_website_mmr(members, is_rt=is_primary_leaderboard, name_fix=name_fix)


async def mkt_lounge_website_mmr(members:[discord.Member], name_fix=None):
    using_str = isinstance(members[0], str)
    names = ['']*len(members)
    if name_fix is None:
        names = [member.display_name.lower().replace(" ", "") for member in members] if not using_str else [member.lower().replace(" ", "") for member in members]
    else:
        names = [name_fix(member.display_name) for member in members] if not using_str else [name_fix(member) for member in members]

    data = None

    try:
        data = await mkt_lounge_json_fetch()
        if data is not None and CACHE_MKT_LOUNGE_DATA:
            json_cacher["MKT_Data"] = data
        elif "MKT_Data" in json_cacher:
            data = json_cacher["MKT_Data"]
    except: #numerous failure types can occur, but they all mean the same thing: we didn't get out data
        return False
    return json_match_ratings(data, members, mkt_json_corruption_check, mkt_lounge_json_transformer, name_fix)

async def mkt_lounge_mmr(ctx, members:[discord.Member], is_primary_leaderboard=True, is_primary_rating=True, name_fix=mkt_lounge_name_fix):
    return await mkt_lounge_website_mmr(members, name_fix=name_fix)



class GuildRating():
    def __init__(self):        
        #Website
        
        self.guild_rating = Guild_Rating_Data()

        self.sheet_ratings = {True:
                              {True:None, False:None},
                              False:
                              {True:None, False:None}}
                
    def non_async_set_up_system(self):
        if self.guild_rating.using_sheet:
            if self.guild_rating.sheet_data.primary_sheet.sheet_id is None:
                return False
            if self.guild_rating.sheet_data.primary_sheet.primary_rating.sheet_name is None:
                return False
            if self.guild_rating.sheet_data.primary_sheet.primary_rating.sheet_range is None:
                return False
            
            worksheet_id = self.guild_rating.sheet_data.primary_sheet.sheet_id
            worksheet_name = self.guild_rating.sheet_data.primary_sheet.primary_rating.sheet_name
            try:
                self.sheet_ratings[True][True] = gc.open_by_key(worksheet_id).worksheet(worksheet_name)
            except:
                return False
            
            #Primary sheet, secondary rating connection
            if self.guild_rating.sheet_data.primary_sheet.secondary_rating.sheet_name is None or\
            self.guild_rating.sheet_data.primary_sheet.secondary_rating.sheet_range is None:
                pass
            else:
                worksheet_name = self.guild_rating.sheet_data.primary_sheet.secondary_rating.sheet_name
                try:
                    self.sheet_ratings[True][False] = gc.open_by_key(worksheet_id).worksheet(worksheet_name)
                except:
                    pass
            #Secondary sheet, primary rating connection
            worksheet_id = self.guild_rating.sheet_data.secondary_sheet.sheet_id
            worksheet_name = self.guild_rating.sheet_data.secondary_sheet.primary_rating.sheet_name
            if worksheet_id is None or \
            self.guild_rating.sheet_data.secondary_sheet.primary_rating.sheet_name is None or\
            self.guild_rating.sheet_data.secondary_sheet.primary_rating.sheet_range is None:
                pass
            else:
                worksheet_name = self.guild_rating.sheet_data.secondary_sheet.primary_rating.sheet_name
                try:
                    self.sheet_ratings[False][True] = gc.open_by_key(worksheet_id).worksheet(worksheet_name)
                except:
                    pass
            #Secondary sheet, secondary rating connection
            if worksheet_id is None or \
            self.guild_rating.sheet_data.secondary_sheet.secondary_rating.sheet_name is None or\
            self.guild_rating.sheet_data.secondary_sheet.secondary_rating.sheet_range is None:
                pass
            else:
                worksheet_name = self.guild_rating.sheet_data.secondary_sheet.secondary_rating.sheet_name
                try:
                    self.sheet_ratings[False][False] = gc.open_by_key(worksheet_id).worksheet(worksheet_name)
                except:
                    pass
        return True 
        
    async def set_up_system(self, ctx=None):
        if not self.guild_rating.using_rating:
            if ctx is not None:
                await ctx.send("Not using a rating.")
            return False
        if self.guild_rating.using_sheet:
            if self.guild_rating.sheet_data.primary_sheet.sheet_id is None:
                if ctx is not None:
                    await ctx.send("You must set your primary sheet id using this command: `!set primarysheet sheet id <id>` - If you need help, do `!rating_help`")
                return False
            if self.guild_rating.sheet_data.primary_sheet.primary_rating.sheet_name is None:
                if ctx is not None:
                    await ctx.send("You must set your primary sheet's primary leaderboard name using this command: `!set primarysheet primaryrating name <name>` - If you need help, do `!rating_help`")
                return False
            if self.guild_rating.sheet_data.primary_sheet.primary_rating.sheet_range is None:
                if ctx is not None:
                    await ctx.send("You must set your primary sheet's primary leaderboard name using this command: `!set primarysheet primaryrating range <range>` where range is a valid Excel range (eg C:D or A2:D) - If you need help, do `!set help`")
                return False
            
            info_str = "Connection info:\n"
            worksheet_id = self.guild_rating.sheet_data.primary_sheet.sheet_id
            worksheet_name = self.guild_rating.sheet_data.primary_sheet.primary_rating.sheet_name
            try:
                self.sheet_ratings[True][True] = gc.open_by_key(worksheet_id).worksheet(worksheet_name)
            except:
                if ctx is not None:
                    await ctx.send("✘ Unable to open the sheet.\nMake sure that the following account has access to the spreadsheet: mkw-war-lounge-bot-service-acc@responsive-bird-291003.iam.gserviceaccount.com\nAlso, make sure that your spreadsheet ID is correct, and also the sheet name. (The sheet name is not the title of your entire spreadsheet, it is the name of the sheet tab.)")
                return False
            else:
                info_str += "✓ Primary rating for primary sheet linked.\n"
            
            #Primary sheet, secondary rating connection
            if self.guild_rating.sheet_data.primary_sheet.secondary_rating.sheet_name is None or\
            self.guild_rating.sheet_data.primary_sheet.secondary_rating.sheet_range is None:
                info_str += "✘ Secondary rating for primary sheet not linked because it was not set up.\n"
            else:
                worksheet_name = self.guild_rating.sheet_data.primary_sheet.secondary_rating.sheet_name
                try:
                    self.sheet_ratings[True][False] = gc.open_by_key(worksheet_id).worksheet(worksheet_name)
                except:
                    info_str += "✘ Secondary rating for primary sheet not linked because it failed when I tried to connect. Make sure the secondary sheet name is correct.\n"
                else:
                    info_str += "✓ Secondary rating for primary sheet linked.\n"
            #Secondary sheet, primary rating connection
            worksheet_id = self.guild_rating.sheet_data.secondary_sheet.sheet_id
            worksheet_name = self.guild_rating.sheet_data.secondary_sheet.primary_rating.sheet_name
            if worksheet_id is None or \
            self.guild_rating.sheet_data.secondary_sheet.primary_rating.sheet_name is None or\
            self.guild_rating.sheet_data.secondary_sheet.primary_rating.sheet_range is None:
                info_str += "✘ Primary rating for secondary sheet not linked because it was not set up.\n"
            else:
                worksheet_name = self.guild_rating.sheet_data.secondary_sheet.primary_rating.sheet_name
                try:
                    self.sheet_ratings[False][True] = gc.open_by_key(worksheet_id).worksheet(worksheet_name)
                except:
                    info_str += "✘ Primary rating for secondary sheet not linked because it failed when I tried to connect. Make sure the secondary sheet name is correct and that this email has access to the sheet: mkw-war-lounge-bot-service-acc@responsive-bird-291003.iam.gserviceaccount.com\n"   
                else:
                    info_str += "✓ Primary rating for secondary sheet linked.\n"
            #Secondary sheet, secondary rating connection
            if worksheet_id is None or \
            self.guild_rating.sheet_data.secondary_sheet.secondary_rating.sheet_name is None or\
            self.guild_rating.sheet_data.secondary_sheet.secondary_rating.sheet_range is None:
                info_str += "✘ Secondary rating for secondary sheet not linked because it was not set up.\n"
            else:
                worksheet_name = self.guild_rating.sheet_data.secondary_sheet.secondary_rating.sheet_name
                try:
                    self.sheet_ratings[False][False] = gc.open_by_key(worksheet_id).worksheet(worksheet_name)
                except:
                    info_str += "✘ Secondary rating for secondary sheet not linked because it failed when I tried to connect. Make sure the secondary sheet name is correct.\n"
                else:
                    info_str += "✓ Secondary rating for secondary sheet linked.\n"
                    
            if ctx is not None:
                await ctx.send(info_str)
        return True 
    
    async def sheet_data_pull(self, ctx, sheet_range=None, is_primary_leaderboard=True, is_primary_rating=True):
        ratings = self.sheet_ratings[is_primary_leaderboard][is_primary_rating]
        if ratings is None:
            await ctx.send("Cannot pull data because the sheets were not set up properly. Contact an admin and tell them to use `!rating_help` to set up the sheets correctly.")
            return False
        
        sheet_data = (self.guild_rating.sheet_data.primary_sheet if is_primary_leaderboard\
                          else self.guild_rating.sheet_data.secondary_sheet)
        sheet = sheet_data.primary_rating if is_primary_rating else sheet_data.secondary_rating
        spreadsheet_range = sheet.sheet_range if sheet_range is None else sheet_range
        if spreadsheet_range is None:
            await ctx.send("Cannot pull data because the sheets are not set up properly. Contact an admin and tell them to use `!rating_help` to set up the sheets correctly.")
            return False 
        
        all_mmr_data = None
        try:
            all_mmr_data = ratings.get(spreadsheet_range)
        except: #numerous failure types can occur, but they all mean the same thing: we didn't get out data
            await ctx.send("Cannot pull data. This can happen because the bot temporarily cannot connect to the sheets. However, it is more likely that the sheets were not set up properly. Contact an admin and tell them to use `!rating_help` to set up the sheets correctly if this issue does not resolve itself.")
            return False
        #Check for corrupt data
        if not isinstance(all_mmr_data, gspread.models.ValueRange):
            await ctx.send("Received bad data from the spreadsheet. Wait and try again. If the issue persists, you should DM Bad Wolf.")
            return False
        
        if all_mmr_data is None: #sanity check
            return False
        return all_mmr_data
        
        
    async def google_sheets_mmr(self, ctx, members:[discord.Member], is_primary_leaderboard=True, is_primary_rating=True):
        if len(members) == 0:
            return {}
        using_str = isinstance(members[0], str)
        
        member_ratings = dict(zip(members, [False]*len(members)))
        names = [member.display_name.lower().replace(" ", "") for member in members] if not using_str else [member.lower().replace(" ", "") for member in members]

        all_mmr_data = await self.sheet_data_pull(ctx, is_primary_leaderboard=is_primary_leaderboard, is_primary_rating=is_primary_rating)
        if all_mmr_data is False:
            return member_ratings
        check_value = None
        for player_data in all_mmr_data:
            #Checking for corrupt data
            if not isinstance(player_data, list):
                continue
            if len(player_data) != 2:
                continue
            if not (isinstance(player_data[0], str) and isinstance(player_data[1], str) and Shared.isint(player_data[1])):
                continue
            this_name = player_data[0].lower().replace(" ", "")
            
            if this_name not in names:
                continue
            
            #We found a match
            check_value = int(player_data[1])
            found_member = members[names.index(this_name)]
            member_ratings[found_member] = False if check_value is None else check_value
            if using_str:
                temp = member_ratings[found_member]
                del member_ratings[found_member]
                member_ratings[player_data[0]] = temp
            
        return member_ratings
    
        
        
    async def mmr(self, ctx, members:[discord.Member], is_primary_leaderboard=True, is_primary_rating=True):
        if len(members) == 0:
            return {}
        if not self.guild_rating.using_rating:
            return {member : 0 for member in members}
        if Shared.get_guild_id(ctx) == Shared.MK7_GUILD_ID:
            return await mk7_mmr(ctx, members, is_primary_leaderboard, is_primary_rating)
        elif Shared.get_guild_id(ctx) == Shared.MKW_ITEM_RAIN_LOUNGE_GUILD_ID:
            return await mkw_item_rain_mmr(ctx, members, is_primary_leaderboard, is_primary_rating)
        elif Shared.get_guild_id(ctx) == Shared.MKW_LOUNGE_GUILD_ID:
            return await mkw_lounge_mmr(ctx, members, is_primary_leaderboard, is_primary_rating)
        elif Shared.get_guild_id(ctx) == Shared.MK8DX_ITALIA_GUILD_ID or Shared.get_guild_id(ctx) == Shared.MK8DX_ITALIA_TEST_GUILD_ID:
            return await mk8_italia_mmr(ctx, members, is_primary_leaderboard, is_primary_rating)
        elif Shared.get_guild_id(ctx) == Shared.MKT_LOUNGE_GUILD_ID:
            return await mkt_lounge_mmr(ctx, members, is_primary_leaderboard, is_primary_rating)
        elif self.guild_rating.using_sheet:
            return await self.google_sheets_mmr(ctx, members, is_primary_leaderboard, is_primary_rating)
        return False
    

    
    async def set_use_rating(self, ctx, yes_or_no:str):
        yes_or_no = yes_or_no.lower().replace(" ", "")
        using_rating = None
        if yes_or_no in {'yes','true','y'}:
            using_rating = True
        elif yes_or_no in {'no','false','n'}:
            using_rating = False
        else:
            if ctx is not None:
                await ctx.send("Put `yes` or `no` for this command. This is to specify if your server will use a rating when people queue up.")
            return False
        
        self.guild_rating = self.guild_rating._replace(using_rating=using_rating)
        if ctx is not None:
            await ctx.send(f"Using a rating when queueing: *{'Yes' if using_rating else 'No'}*")
        return True
        


    async def set_guild_rating_setting(self, ctx, which_sheet: str, which_leaderboard: str, item_to_set:str, setting:str):
        setting = " ".join(ctx.message.content.split(" ")[4:])
        valid_sheet_types = {"primarysheet", "secondarysheet"}
        if which_sheet.lower() not in valid_sheet_types:
            await ctx.send(f"Specify which sheet you are setting. Valid choices are: {', '.join(valid_sheet_types)}\nDo `!rating_help` for help.")
            return
        
        valid_leaderboard_types = {"sheet", "primaryrating", "secondaryrating"}
        if which_leaderboard.lower() not in valid_leaderboard_types:
            await ctx.send(f"Specify which leaderboard you are setting. Valid choices are: {', '.join(valid_leaderboard_types)}\nDo `!rating_help` for help.")
            return
        
        valid_item_to_set = {"name", "id", "range"}
        if item_to_set.lower() not in valid_item_to_set:
            await ctx.send(f"Specify which item you are setting. Valid choices are: {', '.join(valid_item_to_set)}\nDo `!rating_help` for help.")
            return
        
        if which_leaderboard == "sheet" and item_to_set != "id":
            await ctx.send(f"If you are trying to set the sheet id, do `!set <primarysheet/secondarysheet> sheet id <id>`\nDo `!rating_help` for help.")
            return
        if which_leaderboard != "sheet" and item_to_set == "id":
            await ctx.send(f"You cannot set the id of a leaderboard, only of a primarysheet or secondarysheet.\nDo `!rating_help` for help.")
            return
        
        is_primary_sheet = which_sheet == "primarysheet"
        new_sheet_data = self.guild_rating.sheet_data.primary_sheet if is_primary_sheet else self.guild_rating.sheet_data.secondary_sheet
        if which_leaderboard == "sheet":
            new_sheet_data = new_sheet_data._replace(sheet_id = setting)
        else:
            is_primaryrating = which_leaderboard == "primaryrating"
            new_sheet = new_sheet_data.primary_rating if is_primaryrating else new_sheet_data.secondary_rating
            if item_to_set == "name":
                new_sheet = new_sheet._replace(sheet_name=setting)
            if item_to_set == "range":
                new_sheet = new_sheet._replace(sheet_range=setting)
            new_sheet_data = new_sheet_data._replace(primary_rating=new_sheet) if is_primaryrating else new_sheet_data._replace(secondary_rating=new_sheet)
        if is_primary_sheet:
            self.guild_rating = self.guild_rating._replace(
            sheet_data=self.guild_rating.sheet_data._replace(primary_sheet = new_sheet_data)
            )
        else:
            self.guild_rating = self.guild_rating._replace(
            sheet_data=self.guild_rating.sheet_data._replace(secondary_sheet = new_sheet_data)
            )
        return True
    
    async def send_settings(self, ctx, is_new=False):
        spreadsheet_base_url = "https://docs.google.com/spreadsheets/d/"
        to_send = "**New Settings:**\n\n" if is_new else ""
        to_send += f"Using rating when queueing: *{'Yes' if self.guild_rating.using_rating else 'No'}*\n"
        if self.guild_rating.using_rating:
            to_send += "Using Google Spreadsheets: *" + ("Yes" if self.guild_rating.using_sheet else "No") + "*\n"
            to_send += "\n**Primary Sheet Info:**\n"
            to_send += f"\u200b\t- Spreadsheet link: {'`'+spreadsheet_base_url + self.guild_rating.sheet_data.primary_sheet.sheet_id +'`' if self.guild_rating.sheet_data.primary_sheet.sheet_id is not None else '*No sheet id set*'}\n"
            to_send += "\u200b\t*Primary Rating Info:*\n"
            to_send += f"\u200b\t\t- Sheet tab name: *{self.guild_rating.sheet_data.primary_sheet.primary_rating.sheet_name}*\n"
            to_send += f"\u200b\t\t- Cell range: *{self.guild_rating.sheet_data.primary_sheet.primary_rating.sheet_range}*\n"
            to_send += "\u200b\t*Secondary Rating Info:*\n"
            to_send += f"\u200b\t\t- Sheet tab name: *{self.guild_rating.sheet_data.primary_sheet.secondary_rating.sheet_name}*\n"
            to_send += f"\u200b\t\t- Cell range: *{self.guild_rating.sheet_data.primary_sheet.secondary_rating.sheet_range}*\n"
    
            to_send += "\n**Secondary Sheet Info:**\n"
            to_send += f"\u200b\t- Spreadsheet link: {'`'+spreadsheet_base_url + self.guild_rating.sheet_data.secondary_sheet.sheet_id +'`' if self.guild_rating.sheet_data.secondary_sheet.sheet_id is not None else '*No sheet id set*'}\n"
            to_send += "\u200b\t*Primary Rating Info:*\n"
            to_send += f"\u200b\t\t- Sheet tab name: *{self.guild_rating.sheet_data.secondary_sheet.primary_rating.sheet_name}*\n"
            to_send += f"\u200b\t\t- Cell range: *{self.guild_rating.sheet_data.secondary_sheet.primary_rating.sheet_range}*\n"
            to_send += "\u200b\t*Secondary Rating Info:*\n"
            to_send += f"\u200b\t\t- Sheet tab name: *{self.guild_rating.sheet_data.secondary_sheet.secondary_rating.sheet_name}*\n"
            to_send += f"\u200b\t\t- Cell range: *{self.guild_rating.sheet_data.secondary_sheet.secondary_rating.sheet_range}*\n"
    
        
            to_send += "\nYou must do `!connect` when you're finished and ready to attempt to connect to your spreadsheet(s)."
            
        await ctx.send(to_send)

def guild_rating_patch_1(guild_rating_data):
    if 'using_rating' not in guild_rating_data._fields:
        new_guild_rating = Guild_Rating_Data(using_rating=True,
                                             using_sheet=guild_rating_data.using_sheet,
                                             sheet_data=guild_rating_data.sheet_data,
                                             website_data=guild_rating_data.website_data)
        return new_guild_rating
    return guild_rating_data

class Elo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild_sheets = defaultdict(GuildRating)
        self.load_pkl_guild_sheets()
        self.connect_all_sheets()
        
    async def mmr(self, ctx, members: [discord.Member], is_primary_leaderboard=True, is_primary_rating=True):
        if str(Shared.get_guild_id(ctx)) not in self.guild_sheets and Shared.get_guild_id(ctx) not in Shared.RATING_MANUALLY_MANAGED_GUILD_IDS:
            #self.guild_sheets[str(Shared.get_guild_id(ctx))] = GuildRating(self.bot, ctx.guild)
            await ctx.send("A server admin needs to set up your rating system. Have a server admin do `!rating_help` for help.")
            return True
        else:
            return await self.guild_sheets[str(Shared.get_guild_id(ctx))].mmr(ctx, members, is_primary_leaderboard, is_primary_rating)
        
        
    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.guild_only()
    @carrot_prohibit_check()
    @commands.max_concurrency(number=1,wait=True)
    @owner_or_permissions(administrator=True)
    @guild_manually_managed_for_elo()
    async def set(self, ctx, which_sheet: str, which_leaderboard: str, item_to_set:str, setting:str):
        """Do !rating_help to understand how to use this command"""
        success = await self.guild_sheets[str(Shared.get_guild_id(ctx))].set_guild_rating_setting(ctx, which_sheet, which_leaderboard, item_to_set, setting)
        if success:
            self.pkl_guild_sheets()
            await self.guild_sheets[str(Shared.get_guild_id(ctx))].send_settings(ctx, is_new=True)
            
    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.guild_only()
    @carrot_prohibit_check()
    @commands.max_concurrency(number=1,wait=True)
    @owner_or_permissions(administrator=True)
    async def use_rating(self, ctx, yes_or_no:str):
        """If you want to use rating or not. If you're a competitive setting with ratings, this should be true. If you just use this bot to keep track of a list without wanting ratings, put this as false."""
        success = await self.guild_sheets[str(Shared.get_guild_id(ctx))].set_use_rating(ctx, yes_or_no)
        if success:
            self.pkl_guild_sheets()
            await self.guild_sheets[str(Shared.get_guild_id(ctx))].send_settings(ctx, is_new=True)
        
    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.guild_only()
    @carrot_prohibit_check()
    @commands.max_concurrency(number=1,wait=True)
    @owner_or_permissions(administrator=True)
    @guild_manually_managed_for_elo()
    async def rating_settings(self, ctx):
        """Displays the settings for how rating is pulled"""
        await self.guild_sheets[str(Shared.get_guild_id(ctx))].send_settings(ctx, is_new=False)
    
    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.member)
    @commands.guild_only()
    @carrot_prohibit_check()
    @commands.max_concurrency(number=1,wait=True)
    @owner_or_permissions(administrator=True)
    @guild_manually_managed_for_elo()
    async def connect(self, ctx):
        """Run this after you change settings and want to refresh your connection."""
        msg = await ctx.send("Testing connection...")
        await self.guild_sheets[str(Shared.get_guild_id(ctx))].set_up_system(ctx)
        await msg.delete()
        
    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.guild_only()
    @carrot_prohibit_check()
    @commands.max_concurrency(number=1,wait=True)
    @owner_or_permissions(administrator=True)
    async def rating_help(self, ctx):
        """Tutorial for how to set up the bot with elo on sheets"""
        for i in range(5):
            try:
                with open(f"sheet_rating_setup_{i}.txt") as fp:
                    stuff = fp.read()
                    if len(stuff) < 5:
                        break
                    await ctx.send(stuff)
            except:
                pass
    
    
    def pkl_guild_sheets(self):
        pkl_dump_path = "guild_sheets_backup.pkl"
        with open(pkl_dump_path, "wb") as pickle_out:
            to_dump = {}
            for guild_id, rating_settings in self.guild_sheets.items():
                to_dump[guild_id] = rating_settings.guild_rating
            try:
                p.dump(to_dump, pickle_out)
            except:
                print("Could not dump pickle for guild sheet settings.")
                raise
                
    def load_pkl_guild_sheets(self):
        self.guild_sheets = defaultdict(GuildRating)
        try:
            with open("guild_sheets_backup.pkl", "rb") as pickle_in:
                try:
                    temp = p.load(pickle_in)
                    if temp is not None:
                        for guild_id, guild_rating in temp.items():
                            guild_rating = guild_rating_patch_1(guild_rating)
                            self.guild_sheets[guild_id].guild_rating = guild_rating
                except:
                    print("Could not read in pickle for guild_sheets_backup.pkl data.")
                    raise
        except:
            print("guild_sheets_backup.pkl does not exist, so no guild data loaded in. Will create when guilds set their settings.")         
    def connect_all_sheets(self):
        for guild_sheet in self.guild_sheets.values():
            guild_sheet.non_async_set_up_system()
        print("All sheets connected.")
        
    async def mogi_bot_defaults(self, ctx):
        success = await self.guild_sheets[str(Shared.get_guild_id(ctx))].set_use_rating(ctx, 'No')
        if success:
            self.pkl_guild_sheets()
        

    
def setup(bot):
    bot.add_cog(Elo(bot))
