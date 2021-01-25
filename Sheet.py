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

#Website
rt_website_url = "https://mariokartboards.com/lounge/json/player.php?type=rt&name="
ct_website_url = "https://mariokartboards.com/lounge/json/player.php?type=ct&name="


#Google Sheets
gc = gspread.service_account(filename='credentials.json')
#opens a lookup worksheet so MMR is retrieved quickly
rt_sheet_id = "1FzQrVaeHmFWx8jpWr8XVFx9K7Dc5IVxllf105fwLiRk"
ct_sheet_id = "1daGekJSTjf0KCll5632S35FK99lkCZyQgp5-P0k_i0U"
sheet_rts = gc.open_by_key(rt_sheet_id)
sheet_cts = gc.open_by_key(ct_sheet_id)
rt_sheet_mmrs = sheet_rts.worksheet("Leaderboard")
ct_sheet_mmrs = sheet_cts.worksheet("Leaderboard")

using_sheets = False

class Sheet(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    
    async def google_sheets_mmr(self, member:discord.Member, is_rt=True):
        
        name = member.display_name.lower().replace(" ", "")
        mmrs = rt_sheet_mmrs if is_rt else ct_sheet_mmrs
        
        #updates cell B3 of the lookup sheet with the member name
        try:
            all_mmr_data = mmrs.get("C2:D")
        except: #numerous failure types can occur, but they all mean the same thing: we didn't get out data
            return False
        #Check for corrupt data
        if not isinstance(all_mmr_data, gspread.models.ValueRange):
            return False
        
        check_value = None
        for player_data in all_mmr_data:
            #Checking for corrupt data
            if not isinstance(player_data, list):
                continue
            if len(player_data) != 2:
                continue
            if not (isinstance(player_data[0], str) and isinstance(player_data[1], str) and player_data[1].isnumeric()):
                continue
            this_name = player_data[0].lower().replace(" ", "")
            
            if this_name != name:
                continue
            
            #We found a match
            check_value = int(player_data[1])
        
        #Player wasn't found
        #Or possibly they were a placement player (if the sheet incorporates that)
        #Return False since they don't have mmr/weren't found
        if check_value == None:
            return False
        return check_value
    
    async def website_mmr(self, member:discord.Member, is_rt=True):
        name = member.display_name.lower().replace(" ", "")
        full_url = rt_website_url if is_rt else ct_website_url
        full_url += name
        #Takes a list of players, returns that list of player's matched to their player IDs
        data = None
        try:
            data = await self.getJSONData(full_url)
        except: #numerous failure types can occur, but they all mean the same thing: we didn't get out data
            return False
        
        if self.data_is_corrupt(data):
            return False
        
        return int(data[0]["current_mmr"])
        
        
    async def mmr(self, member: discord.Member, is_rt=True):
        if using_sheets:
            return await self.google_sheets_mmr(member, is_rt)
        else:
            return await self.website_mmr(member, is_rt)
            
    
    async def getJSONData(self, full_url):
        async with aiohttp.ClientSession() as session:
            async with session.get(full_url) as r:
                if r.status == 200:
                    js = await r.json()
                    return js
    
    def data_is_corrupt(self, jsonData):
        if jsonData == None:
            print("Bad request to Lounge API... Data was None.")
            return True
        if "error" in jsonData:
            print("Bad request to Lounge API... Error in data.")
            return True
        if not isinstance(jsonData, list):
            print("Bad request to Lounge API... Data was not a list.")
            return True
        
        if len(jsonData) != 1:
            return True
        
        playerData = jsonData[0]
        if not isinstance(playerData, dict):
            return True
        
        #if "current_mmr" not in playerData or not isinstance(playerData["current_mmr"], int):
        #    return True
        if "current_mmr" not in playerData or not isinstance(playerData["current_mmr"], str) or not playerData["current_mmr"].isnumeric():
            return True
        
        return int(playerData["current_mmr"]) < 0
        

def setup(bot):
    bot.add_cog(Sheet(bot))
