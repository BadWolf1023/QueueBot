import discord
from discord.ext import commands, tasks
import json
import random
from dateutil.parser import parse
from datetime import datetime, timedelta
import collections
import dill as p

CHECKMARK_ADDITION = "-\U00002713"
CHECKMARK_ADDITION_LEN = 2
time_print_formatting = "%B %d, %Y at %I:%M%p EST"
#There are two timezones: the timezone your staff schedules events in, and your server's timezone
#Set this to the number of hours ahead (or behind) your staff's timezone is from your server's timezone
#This is so that you don't have to adjust your machine clock to accomodate for your staff

#For example, if my staff is supposed to schedule events in EST and my machine is PST, this number would be 3 since EST is 3 hours ahead of my machine's PST
TIME_ADJUSTMENT = timedelta(hours=3)

#This is the amount of time that players have to queue in the joining channel before Queuebot closes the channel and makes the rooms
JOINING_TIME = timedelta(minutes=45)
EXTENTSION_TIME = timedelta(minutes=5)

Scheduled_Event = collections.namedtuple('Scheduled_Event', 'track_type size time started')

class Mogi(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open('./config.json', 'r') as cjson:
            self.config = json.load(cjson)
        
            
        # no commands should work when self.started or self.gathering is False, 
        # except for start, which initializes each of these values.
        self.started = False
        self.gathering = False
        self.making_rooms_run = False
        
        
        # can either be 2, 3, or 4, representing the respective mogi sizes
        self.size = 2
        
        # self.waiting is a list of dictionaries, with the keys each corresponding to a
        # Discord member class, and the values being a list with 2 values:
        # index 0 being the player's confirmation status, and index 1 being the player's MMR.
        self.waiting = []
        
        # self.list is also a list of dictionaries, with the keys each corresponding to a
        # Discord member class, and the values being the player's MMR.
        self.list = []
        
        # contains the avg MMR of each confirmed team
        self.avgMMRs = []

        #list of Channel objects created by the bot for easy deletion
        self.channels = []
        
        self.scheduled_events = []
        
        self.is_automated = False
        
        self.mogi_channel = None
        
        self.start_time = None
               
        
        #Specify whether RTs or CTs, necessary for MMR lookup
        self.is_rt = True
        self._scheduler_task = self.sqscheduler.start()
        
        #Load in the schedule from the pkl
        self.load_pkl_schedule()
    
    async def lockdown(self, channel:discord.TextChannel):
        overwrite = channel.overwrites_for(channel.guild.default_role)
        overwrite.send_messages = False
        await channel.set_permissions(channel.guild.default_role, overwrite=overwrite)
        await channel.send("Locked down " + channel.mention)
    
    async def unlockdown(self, channel:discord.TextChannel):
        overwrite = channel.overwrites_for(channel.guild.default_role)
        overwrite.send_messages = None
        await channel.set_permissions(channel.guild.default_role, overwrite=overwrite)
        await channel.send("Unlocked " + channel.mention)
    


    
    async def scheduler_mogi_start(self):
        """Functions that tries to launch scheduled mogis - Note that it won't launch any sscheduled mogis
        if an there is already a mogi ongoing, instead it will send an error message and delete that event from the schedule"""
        
        cur_time = datetime.now()
        
        to_remove = [] #Keep a list of indexes to remove - can't remove while iterating
        for ind, event in enumerate(self.scheduled_events):
            if (event.time - JOINING_TIME) < cur_time:
                mogi_chan = self.get_mogi_channel()
                to_remove.append(ind)
                if mogi_chan == None: #cannot see the mogi channel, no where to send an error message, must silently fail
                    pass
                else:
                    if self.started or self.gathering: #We can't start a new event while the current event is already going
                        await mogi_chan.send(f"Because there is an ongoing event right now, the following event has been removed: {self.get_event_str(event)}\n")
                    else:
                        await self.launch_mogi(mogi_chan, event.track_type, event.size, True, event.time)
                        await self.unlockdown(mogi_chan)
        
        for ind in reversed(to_remove):
            del self.scheduled_events[ind]
            
            
    async def ongoing_mogi_checks(self):
            #If it's not automated, not started, we've already started making the rooms, don't run this
            if not self.is_automated or not self.started or self.making_rooms_run:
                return
            
            cur_time = datetime.now()
            if (self.start_time + EXTENTSION_TIME) <= cur_time:
                await self.makeRoomsLogic(self.mogi_channel, (cur_time.minute + 1)%60, True)
                return
            
            if self.start_time <= cur_time:
                #check if there are an even amount of teams since we are past the queue time
                numLeftoverTeams = len(self.list) % int((12/self.size))
                if numLeftoverTeams == 0:
                    await self.makeRoomsLogic(self.mogi_channel, (cur_time.minute + 1)%60, True)
                    return
                else:
                    if int(cur_time.second / 20) == 0:
                        force_time = self.start_time + EXTENTSION_TIME
                        minutes_left = int((force_time - cur_time).seconds/60) + 1
                        x_teams = int(int(12/self.size) - numLeftoverTeams)
                        await self.mogi_channel.send(f"Need {x_teams} more team(s) to start immediately. Starting in {minutes_left} minute(s) regardless.")
            

        
    @tasks.loop(seconds=20.0)
    async def sqscheduler(self):
        """Scheduler that checks if it should start mogis and close them"""
        #It may seem silly to do try/except Exception, but this coroutine **cannot** fail
        #This coroutine *silently* fails and stops if exceptions aren't caught - an annoying abtraction of asyncio
        #This is unacceptable considering people are relying on these mogis to run, so we will not allow this routine to stop
        try:
            await self.scheduler_mogi_start()
        except Exception as e:
            print(e)
            
        try:
            await self.ongoing_mogi_checks()
        except Exception as e:
            print(e)
        
            
    async def __create_testing_env__(self):
        self.avgMMRs = [100, 0, 300, 200, 500, 400]
        temp_ids = [706120725882470460, 196574963673595904,
                    474389780067778580, 235148962103951360,
                    155149108183695360, 775415990238314518,
                    476660593525260289, 735782213118853180,
                    450127943012712448, 444514223075360800,
                    459860530618695681, 698232485653381142]
        self.list = []
        self.size = 2
        for i in range(6):
            self.list.append({})
            for disc_id in temp_ids[self.size*i:(self.size*i + self.size)]:
                member = await self.bot.fetch_user(disc_id)
                self.list[i][member] = [self.avgMMRs[i], False]
        self.started = True
        
                


    # the 4 functions below act as various checks for each of the bot commands.
    # if any of these are false, sends a message to the channel
    # and throws an exception to force the command to stop

    async def hasroles(self, ctx):
        for rolename in self.config["roles"]:
            for role in ctx.author.roles:
                if role.name == rolename:
                    return
        raise commands.MissingAnyRole(self.config["roles"])

    def get_mogi_channel(self):
        mogi_channel_id = self.config["testingchannel"] if self.config["testingenviornment"] else self.config["mogichannel"]
        return self.bot.get_channel(mogi_channel_id)
            
            
    async def is_mogi_channel(self, ctx):
        if ctx.channel == self.get_mogi_channel():
            return
            
        await(await ctx.send("You cannot use this command in this channel!")).delete(delay=5)
        raise Exception()

    async def is_started(self, ctx):
        if self.started == False:
            await(await ctx.send("Mogi has not been started yet.. type !start")).delete(delay=5)
            raise Exception()

    async def is_gathering(self, ctx):
        if self.gathering == False:
            await(await ctx.send("Mogi is closed; players cannot join or drop from the event")).delete(delay=5)
            raise Exception()
        
            

    # Checks if a user is in a squad currently gathering players;
    # returns False if not found, and returns the squad index in
    # self.waiting if found
    async def check_waiting(self, member: discord.Member):
        if(len(self.waiting) == 0):
            return False
        for i in range(len(self.waiting)):
            for player in self.waiting[i].keys():
                # for testing, it's convenient to change player.id
                # and member.id to player.display_name
                # and member.display_name respectively
                # (lets you test with only 2 accounts and changing
                #  nicknames)
                if player.id == member.id:
                    return i
        return False

    # Checks if a user is in a full squad that has joined the mogi;
    # returns False if not found, and returns the squad index in
    # self.list if found
    async def check_list(self, member: discord.Member):
        if (len(self.list) == 0):
            return False
        for i in range(len(self.list)):
            for player in self.list[i].keys():
                # for testing, it's convenient to change player.id
                # and member.id to player.display_name
                # and member.display_name respectively
                # (lets you test with only 2 accounts and changing
                #  nicknames)
                if player.id == member.id:
                    return i
        return False
        
    @commands.command(aliases=['c', 'ch', 'canhost'])
    @commands.max_concurrency(number=1,wait=True)
    @commands.guild_only()
    async def can(self, ctx, members: commands.Greedy[discord.Member]):
        """Tag your partners to invite them to a mogi or accept a invitation to join a mogi"""
        can_host = ctx.invoked_with.lower() in {'ch', 'canhost'}

        try:
            await Mogi.is_mogi_channel(self, ctx)
            await Mogi.is_started(self, ctx)
            await Mogi.is_gathering(self, ctx)
        except:
            return

        if (len(members) > 0 and len(members) < self.size - 1):
            await ctx.send("You didn't tag the correct number of people for this format (%d)"
                           % (self.size-1))
            return

        sheet = self.bot.get_cog('Sheet')

        # checking if message author is already in the mogi
        checkWait = await Mogi.check_waiting(self, ctx.author)
        checkList = await Mogi.check_list(self, ctx.author)
        if checkWait is not False:
            if self.waiting[checkWait][ctx.author][0] == True:
                if self.waiting[checkWait][ctx.author][2] == True: #if they are hosting...
                    if can_host:
                        await ctx.send("You have already confirmed for this event; type `!d` to drop")
                    else:
                        self.waiting[checkWait][ctx.author][2] = False
                        await ctx.send("No longer host for this event; type `!d` to drop")
                else: #If they are not hosting...
                    if can_host:
                        self.waiting[checkWait][ctx.author][2] = True
                        await ctx.send("Changed to host for this event; type `!d` to drop")
                    else:
                        await ctx.send("You have already confirmed for this event; type `!d` to drop")  
                return
            
        if checkList is not False:
            currently_hosting = self.list[checkList][ctx.author][1]
            
            if currently_hosting:
                if can_host:
                    await ctx.send("You have already confirmed for this event; type `!d` to drop")
                else:
                    self.list[checkList][ctx.author][1] = False
                    await ctx.send("No longer host for this event; type `!d` to drop")
            else: #If they are not hosting...
                if can_host:
                    self.list[checkList][ctx.author][1] = True
                    await ctx.send("Changed to host for this event; type `!d` to drop")
                else:
                    await ctx.send("You have already confirmed for this event; type `!d` to drop")  
            return
            

        # logic for when no players are tagged
        if len(members) == 0:
            #runs if message author has been invited to squad
            #but hasn't confirmed
            if checkWait is not False:
                self.waiting[checkWait][ctx.author][0] = True
                self.waiting[checkWait][ctx.author][2] = can_host
                confirmedPlayers = []
                missingPlayers = []
                for player in self.waiting[checkWait].keys():
                    if self.waiting[checkWait][player][0] == True:
                        confirmedPlayers.append(player)
                    else:
                        missingPlayers.append(player)
                string = ("Successfully confirmed for your squad [%d/%d]\n"
                          % (len(confirmedPlayers), self.size))
                if len(missingPlayers) > 0:
                    string += "Missing players: "
                    string += ", ".join([player.display_name for player in missingPlayers])
                
                
                #if player is the last one to confirm for their squad,
                #add them to the mogi list
                if len(missingPlayers) == 0:
                    squad = self.waiting[checkWait]
                    squad2 = {}
                    teamMsg = ""
                    totalMMR = 0
                    for player in squad.keys():
                        playerMMR = int(squad[player][1])
                        _can_host = squad[player][2]
                        squad2[player] = [playerMMR, _can_host]
                        totalMMR += playerMMR
                        teamMsg += "%s (%d MMR)\n" % (player.display_name, int(playerMMR))
                    self.avgMMRs.append(int(totalMMR/self.size))
                    self.waiting.pop(checkWait)
                    self.list.append(squad2)
                    if len(self.list) > 1:
                        s = "s"
                    else:
                        s = ""
                    
                    string += "Squad successfully added to mogi list `[%d team%s]`:\n%s" % (len(self.list), s, teamMsg)
                
                await ctx.send(string)
                await self.ongoing_mogi_checks()
                return
            
            await ctx.send("You didn't tag the correct number of people for this format (%d)"
                           % (self.size-1))
            return

        # Input validation for tagged members; checks if each tagged member is already
        # in a squad, as well as checks if any of them are duplicates
        for member in members:
            checkWait = await Mogi.check_waiting(self, member)
            checkList = await Mogi.check_list(self, member)
            if checkWait is not False or checkList is not False:
                msg = ("%s is already confirmed for a squad for this event `("
                               % (member.display_name))
                if checkWait is not False:
                    msg += ", ".join([player.display_name for player in self.waiting[checkWait].keys()])
                else:
                    msg += ", ".join([player.display_name for player in self.list[checkList].keys()])
                msg += ")` They should type `!d` if this is in error."
                await ctx.send(msg)
                return
            if member == ctx.author:
                await ctx.send("Duplicate players are not allowed for a squad, please try again")
                return
        if len(set(members)) < len(members):
            await ctx.send("Duplicate players are not allowed for a squad, please try again")
            return
            
        # logic for when the correct number of arguments are supplied
        # (self.size - 1)
        players = {ctx.author: [True]}
        playerMMR = await sheet.mmr(ctx.author, self.is_rt)
        if playerMMR is False:
            await(await ctx.send("Error: MMR for player %s cannot be found! Placement players are not allowed to queue. If you are not placement, please contact a staff member for help"
                           % ctx.author.display_name)).delete(delay=10)
            return
        
        players[ctx.author].append(playerMMR)
        players[ctx.author].append(can_host)
        for i in range(self.size-1):
            players[members[i]] = [False]
            playerMMR = await sheet.mmr(members[i], self.is_rt)
            if playerMMR is False:
                await(await ctx.send("Error: MMR for player %s cannot be found! Placement players are not allowed to queue. If you are not placement, please contact a staff member for help"
                               % members[i].display_name)).delete(delay=10)
                return
            players[members[i]].append(playerMMR)
            players[members[i]].append(False)
        self.waiting.append(players)
        
        msg = "%s has created a squad with " % ctx.author.display_name
        msg += ", ".join([player.display_name for player in members])
        msg += "; each player must type `!c` to join the queue [1/%d]" % (self.size)
        await(await ctx.send(msg)).delete(delay=10)


           
    @commands.command(aliases=['d'])
    @commands.max_concurrency(number=1,wait=True)
    @commands.guild_only()
    @commands.cooldown(1, 15, commands.BucketType.member)
    async def drop(self, ctx):
        """Remove your squad from a mogi"""
        try:
            await Mogi.is_mogi_channel(self, ctx)
            await Mogi.is_started(self, ctx)
            await Mogi.is_gathering(self, ctx)
        except:
            return

        checkWait = await Mogi.check_waiting(self, ctx.author)
        checkList = await Mogi.check_list(self, ctx.author)
        # "is" instead of "==" is essential here, otherwise if
        # i=0 is returned, it will think it's False
        if checkWait is False and checkList is False:
            await(await ctx.send("You are not currently in a squad for this event; type `!c @partnerNames`")).delete(delay=5)
            return
        if checkWait is not False:
            droppedTeam = self.waiting.pop(checkWait)
            fromStr = " from unfilled squads"
        else:
            droppedTeam = self.list.pop(checkList)
            self.avgMMRs.pop(checkList)
            fromStr = " from mogi list"
        string = "Removed team "
        string += ", ".join([player.display_name for player in droppedTeam.keys()])
        string += fromStr
        await(await ctx.send(string)).delete(delay=5)

    @commands.command(aliases=['r'])
    @commands.max_concurrency(number=1,wait=True)
    @commands.guild_only()
    async def remove(self, ctx, num: int):
        """Removes the given squad ID from the mogi list"""
        await Mogi.hasroles(self, ctx)
        try:
            await Mogi.is_mogi_channel(self, ctx)
            await Mogi.is_started(self, ctx)
        except:
            return
        if num > len(self.list) or num < 1:
            await(await ctx.send("Invalid squad ID; there are %d squads in the mogi"
                                 % len(self.list))).delete(delay=10)
            return
        squad = self.list.pop(num-1)
        self.avgMMRs.pop(num-1)
        await ctx.send("Removed squad %s from mogi list"
                       % (", ".join([player.display_name for player in squad.keys()])))


    #The caller is responsible to make sure the paramaters are correct
    async def launch_mogi(self, mogi_channel:discord.TextChannel, track_type:str, size: int, is_automated=False, start_time=None):       
        self.started = True
        self.gathering = True
        self.making_rooms_run = False
        self.is_automated = is_automated
        self.size = size
        self.waiting = []
        self.list = []
        self.avgMMRs = []
        self.is_rt = track_type == "rt"
        
        if not is_automated:
            self.is_automated = False
            self.mogi_channel = None
            self.start_time = None
        else:
            self.is_automated = True
            self.mogi_channel = mogi_channel
            self.start_time = start_time
        
        await mogi_channel.send("A%s %dv%d mogi has been started - @here Type `!c`, `!d`, or `!list`" % ("n RT" if self.is_rt else " CT", size, size))

    @commands.command()
    @commands.guild_only()
    async def start(self, ctx, track_type:str, size: int):
        
        """Start a mogi in the channel defined by the config file"""
        await Mogi.hasroles(self, ctx)
        try:
            await Mogi.is_mogi_channel(self, ctx)
        except:
            return

        if not await Mogi.start_input_validation(ctx, track_type, size):
            return False
        self.is_automated = False
        await self.launch_mogi(ctx.channel, track_type, size)
    
    
    @commands.command()
    @commands.guild_only()
    async def close(self, ctx):
        """Close the mogi so players can't join or drop"""
        await Mogi.hasroles(self, ctx)
        try:
            await Mogi.is_mogi_channel(self, ctx)
            await Mogi.is_started(self, ctx)
            await Mogi.is_gathering(self, ctx)
        except:
            return
        self.gathering = False
        self.is_automated = False
        await ctx.send("Mogi is now closed; players can no longer join or drop from the event")

    @commands.command()
    @commands.guild_only()
    async def open(self, ctx):
        """Reopen the mogi so that players can join and drop"""
        await Mogi.hasroles(self, ctx)
        try:
            await Mogi.is_mogi_channel(self, ctx)
            await Mogi.is_started(self, ctx)
        except:
            return
        if self.gathering is True:
            await(await ctx.send("Mogi is already open; players can join and drop from the event")
                  ).delete(delay=5)
            return
        self.gathering = True
        self.is_automated = False
        await ctx.send("Mogi is now open; players can join and drop from the event")

    @commands.command()
    @commands.guild_only()
    async def end(self, ctx):
        """End the mogi"""
        await Mogi.hasroles(self, ctx)
        try:
            await Mogi.is_mogi_channel(self, ctx)
            await Mogi.is_started(self, ctx)
        except:
            return
        try:
            for i in range(len(self.channels)-1, -1, -1):
                await self.channels[i][0].delete()
                self.channels.pop(i)
        except:
            pass
        self.started = False
        self.gathering = False
        self.making_rooms_run = False
        self.is_automated = False
        self.mogi_channel = None
        self.start_time = None
        self.waiting = []
        self.list = []
        self.avgMMRs = []
        self.is_rt = True
        await ctx.send("%s has ended the mogi" % ctx.author.display_name)
            

    @commands.command(aliases=['l'])
    @commands.cooldown(1, 40)
    @commands.guild_only()
    async def list(self, ctx):
        """Display the list of confirmed squads for a mogi; sends 15 at a time to avoid
           reaching 2000 character limit"""
        try:
            await Mogi.is_mogi_channel(self, ctx)
            await Mogi.is_started(self, ctx)
        except:
            return
        if len(self.list) == 0:
            await(await ctx.send("There are no squads in the mogi - confirm %d players to join" % (self.size))).delete(delay=5)
            return
        msg = "`Mogi List`\n"
        for i in range(len(self.list)):
            #safeguard against potentially reaching 2000-char msg limit
            if i > 0 and i % 15 == 0:
                await ctx.send(msg)
                msg = ""
            msg += "`%d.` " % (i+1)
            msg += ", ".join([player.display_name + (" (host)" if self.list[i][player][1] else "") for player in self.list[i].keys()])
            msg += " (%d MMR)\n" % (self.avgMMRs[i])
        if(len(self.list) % (12/self.size) != 0):
            msg += ("`[%d/%d] teams for %d full rooms`"
                    % ((len(self.list) % (12/self.size)), (12/self.size), int(len(self.list) / (12/self.size))+1))
        await ctx.send(msg)

    @commands.command()
    @commands.cooldown(1, 30, commands.BucketType.member)
    @commands.guild_only()
    async def squad(self, ctx):
        """Displays information about your squad for a mogi"""
        try:
            await Mogi.is_mogi_channel(self, ctx)
            await Mogi.is_started(self, ctx)
        except:
            return
        checkWait = await Mogi.check_waiting(self, ctx.author)
        checkList = await Mogi.check_list(self, ctx.author)
        if checkWait is False and checkList is False:
            await(await ctx.send("You are not currently in a squad for this event; type `!c @partnerNames`")
                  ).delete(delay=5)
            return
        msg = ""
        playerNum = 1
        if checkWait is not False:
            myTeam = self.waiting[checkWait]
            listString = ""
            confirmCount = 0
            for player in myTeam.keys():
                host_str = "(host) " if myTeam[player][2] else ""
                listString += ("`%d.` %s %s(%d MMR)" % (playerNum, player.display_name, host_str, int(myTeam[player][1])))
                if myTeam[player][0] is False:
                    listString += " `✘ Unconfirmed`\n"
                else:
                    
                    listString += " `✓ Confirmed`\n"
                    confirmCount += 1
                playerNum += 1
            msg += ("`%s's squad [%d/%d confirmed]`\n%s"
                    % (ctx.author.display_name, confirmCount, self.size, listString))
            await(await ctx.send(msg)).delete(delay=30)
        else:
            myTeam = self.list[checkList]
            msg += ("`%s's squad [registered]`\n" % (ctx.author.display_name))
            for player in myTeam.keys():
                host_str = "(host) " if myTeam[player][1] else ""
                msg += ("`%d.` %s %s(%d MMR)\n"
                        % (playerNum, player.display_name, host_str, int(myTeam[player][0])))
                playerNum += 1
            await(await ctx.send(msg)).delete(delay=30)

    @commands.command()
    @commands.guild_only()
    async def sortTeams(self, ctx):
        """Backup command if !makerooms doesn't work; doesn't make channels, just sorts teams in MMR order"""
        await Mogi.hasroles(self, ctx)
        try:
            await Mogi.is_mogi_channel(self, ctx)
            await Mogi.is_started(self, ctx)
        except:
            return
        indexes = range(len(self.avgMMRs))
        sortTeamsMMR = sorted(zip(self.avgMMRs, indexes), reverse=True)
        sortedMMRs = [x for x, _ in sortTeamsMMR]
        sortedTeams = [self.list[i] for i in (x for _, x in sortTeamsMMR)]
        msg = "`Sorted list`\n"
        for i in range(len(sortedTeams)):
            if i > 0 and i % 15 == 0:
                await ctx.send(msg)
                msg = ""
            msg += "`%d.` " % (i+1)
            msg += ", ".join([player.display_name + (" (host)" if sortedTeams[i][player][1] else "") for player in sortedTeams[i].keys()])
            msg += " (%d MMR)\n" % sortedMMRs[i]
        await ctx.send(msg)

    async def makeRoomsLogic(self, mogi_channel:discord.TextChannel, openTime:int, startedViaAutomation=False):
        """Sorts squads into rooms based on average MMR, creates room channels and adds players to each room channel"""
        if self.making_rooms_run and startedViaAutomation: #Reduce race condition, but also allow manual !makeRooms
            return
        if startedViaAutomation:
            await self.lockdown(mogi_channel)
        
        self.making_rooms_run = True
        if self.gathering:
            self.gathering = False
            await mogi_channel.send("Mogi is now closed; players can no longer join or drop from the event")

        numRooms = int(len(self.list) / (12/self.size))
        if numRooms == 0:
            await mogi_channel.send("Not enough players to fill a room! Try this command with at least %d teams" % int(12/self.size))
            return

        if openTime >= 60 or openTime < 0:
            await mogi_channel.send("Please specify a valid time (in minutes) for rooms to open (00-59)")
            return
        startTime = openTime + 10
        while startTime >= 60:
            startTime -= 60
            
        category = mogi_channel.category
            
        numTeams = int(numRooms * (12/self.size))
        finalList = self.list[0:numTeams]
        finalMMRs = self.avgMMRs[0:numTeams]

        indexes = range(len(finalMMRs))
        sortTeamsMMR = sorted(zip(finalMMRs, indexes), reverse=True)
        sortedMMRs = [x for x, _ in sortTeamsMMR]
        sortedTeams = [finalList[i] for i in (x for _, x in sortTeamsMMR)]
        for i in range(numRooms):
            #creating room roles and channels
            roomName = "Room %d" % (i+1)
            overwrites = {
                mogi_channel.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                mogi_channel.guild.me: discord.PermissionOverwrite(read_messages=True)
            }
            
            #tries to retrieve all these roles, and add them to the
            #channel overwrites if the role specified in the config file exists
            for bot_role_id in self.config["roles_for_channels"]:
                bot_role = mogi_channel.guild.get_role(bot_role_id)
                if bot_role is not None:
                    #giving developer role manage_channels perm
                    if bot_role.id == 521154917675827221:
                        overwrites[bot_role] = discord.PermissionOverwrite(read_messages=True, manage_channels=True)
                    else:
                        overwrites[bot_role] = discord.PermissionOverwrite(read_messages=True)
            

            msg = "`%s`\n" % roomName
            for j in range(int(12/self.size)):
                index = int(i * 12/self.size + j)
                msg += "`%d.` " % (j+1)
                msg += ", ".join([player.display_name + (" (host)" if sortedTeams[index][player][1] else "") for player in sortedTeams[index].keys()])
                msg += " (%d MMR)\n" % sortedMMRs[index]
                for player in sortedTeams[index].keys():
                    overwrites[player] = discord.PermissionOverwrite(read_messages=True)
            roomMsg = msg
            mentions = ""
            hosts = []
            scoreboard = "Table: `!scoreboard %d " % (12/self.size)
            for j in range(int(12/self.size)):
                index = int(i * 12/self.size + j)
                mentions += " ".join([player.mention for player in sortedTeams[index].keys()])
                mentions += " "
                for player in sortedTeams[index].keys():
                    #Scoreboard logic
                    scoreboard += player.display_name.replace(" ", "")
                    scoreboard += " "
                    #Host logic
                    if sortedTeams[index][player][1]: #If they queued as host
                        hosts.append(player.display_name)
            
            roomMsg += "%s`\n" % scoreboard
            host_str = "Decide a host amongst yourselves; "
            if len(hosts) > 0:
                random.shuffle(hosts)
                host_str = "**Host order:**\n"
                for x, host in enumerate(hosts, 1):
                    host_str += f"{x}. {host}\n"
                host_str += "\n"

            
            roomMsg += ("\n%sRoom open at :%02d, start at :%02d. Good luck!\n\n"
                        % (host_str, openTime, startTime))
            roomMsg += mentions
            roomChannel = await category.create_text_channel(name=roomName, overwrites=overwrites)
            self.channels.append([roomChannel, False])
            await roomChannel.send(roomMsg)
            await mogi_channel.send(msg)
            
        if numTeams < len(self.list):
            missedTeams = self.list[numTeams:len(self.list)]
            missedMMRs = self.avgMMRs[numTeams:len(self.list)]
            msg = "`Late teams:`\n"
            for i in range(len(missedTeams)):
                msg += "`%d.` " % (i+1)
                msg += ", ".join([player.display_name for player in missedTeams[i].keys()])
                msg += " (%d MMR)\n" % missedMMRs[i]
            await mogi_channel.send(msg)
            

    @commands.command()
    @commands.bot_has_guild_permissions(manage_channels=True)
    @commands.guild_only()
    async def makeRooms(self, ctx, openTime: int):
        await Mogi.hasroles(self, ctx)
        try:
            await Mogi.is_mogi_channel(self, ctx)
            await Mogi.is_started(self, ctx)
        except:
            return
        await self.makeRoomsLogic(ctx.channel, openTime)
        
    
    @commands.command()
    @commands.bot_has_guild_permissions(manage_channels=True)
    @commands.guild_only()
    async def finish(self, ctx):
        """Finishes the room by adding a checkmark to the channel. Anyone in the room can call this command."""
        current_channel = ctx.channel
        for index, (channel, isFinished) in enumerate(self.channels):
            if current_channel == channel:
                if not isFinished:
                    await current_channel.edit(name=current_channel.name + CHECKMARK_ADDITION)
                    self.channels[index] = [current_channel, True]
       
       
    @staticmethod
    async def start_input_validation(ctx, track_type:str, size:int):
        valid_sizes = [2, 3, 4]
        if size not in valid_sizes:
            await(await ctx.send("The size you entered is invalid; proper values are: 2, 3, 4")).delete(delay=5)
            return False
        valid_track_types = ["rt", "ct"]
        track_type = track_type.lower()
        if track_type not in valid_track_types:
            await(await ctx.send("The track type you entered is invalid; proper values are: rt, ct")).delete(delay=5)
            return False
        
        return True 
                   
                                      
    @commands.command()
    @commands.guild_only()
    async def schedule(self, ctx, track_type:str, size: int, schedule_time:str):
        """Schedules a room in the future so that the staff doesn't have to be online to open the mogi and make the rooms"""
        
        await Mogi.hasroles(self, ctx)
        
        if not await Mogi.start_input_validation(ctx, track_type, size):
            return False
              
        schedule_time = " ".join(ctx.message.content.split(" ")[3:])
        try:
            actual_time = parse(schedule_time)
            actual_time = actual_time - TIME_ADJUSTMENT
            mogi_channel = self.get_mogi_channel()
            if mogi_channel == None:
                ctx.send("I can't see the mogi channel, so I can't schedule this event.")
                return
            event = Scheduled_Event(track_type, size, actual_time, False)
            
            self.scheduled_events.append(event)
            self.scheduled_events.sort(key=lambda data:data.time)
            await ctx.send(f"Scheduled {Mogi.get_event_str(event)}")
        except (ValueError, OverflowError):
            await ctx.send("I couldn't figure out the date and time for your event. Try making it a bit more clear for me.")
        self.pkl_schedule()
        
    @commands.command()
    @commands.guild_only()
    async def view_schedule(self, ctx):
        """Displays the schedule"""
        await Mogi.hasroles(self, ctx)
        
        if len(self.scheduled_events) == 0:
            await ctx.send("There are currently no schedule events. Do `!schedule` to schedule a future event.")
        else:
            event_str = ""
            for ind, this_event in enumerate(self.scheduled_events, 1):
                event_str += f"`{ind}.` {Mogi.get_event_str(this_event)}\n"
            event_str += "\nDo `!remove_event` to remove that event from the schedule."
            await ctx.send(event_str)
            
    @commands.command()
    @commands.guild_only()
    @commands.max_concurrency(number=1,wait=True)
    async def remove_event(self, ctx, event_num: int):
        """Removes an event from the schedule"""
        await Mogi.hasroles(self, ctx)
        
        if event_num < 1 or event_num > len(self.scheduled_events):
            await ctx.send("This event number isn't in the schedule. Do `!view_schedule` to see the scheduled events.")
        else:
            removed_event = self.scheduled_events.pop(event_num-1)
            await ctx.send(f"Removed `{event_num}.` {self.get_event_str(removed_event)}")
        self.pkl_schedule()
        
    @commands.command()
    @commands.guild_only()
    @commands.max_concurrency(number=1,wait=True)
    async def testenv(self, ctx):
        if ctx.author.id != 706120725882470460:
            return
        await self.__create_testing_env__()
        await ctx.send("Done.")
        
    @staticmethod
    def get_event_str(this_event):
        track_type, event_size, event_time = this_event.track_type, this_event.size, this_event.time
        timezone_adjusted_time = event_time + TIME_ADJUSTMENT
        event_time_str = timezone_adjusted_time.strftime(time_print_formatting)
        return f"{track_type.upper()} {event_size}v{event_size} on {event_time_str}"
    
    def pkl_schedule(self):
        pkl_dump_path = "schedule_backup.pkl"
        with open(pkl_dump_path, "wb") as pickle_out:
            try:
                p.dump(self.scheduled_events, pickle_out)
            except:
                print("Could not dump pickle for scheduled events.")
                
    def load_pkl_schedule(self):
        try:
            with open("schedule_backup.pkl", "rb") as pickle_in:
                try:
                    temp = p.load(pickle_in)
                    if temp == None:
                        temp = []
                    self.scheduled_events = temp
                except:
                    print("Could not read in pickle for schedule_backup.pkl data.")
                    self.scheduled_events = []
        except:
            print("schedule_backup.pkl does not exist, so no events loaded in. Will create when events are scheduled.")         
            self.scheduled_events = []
            
        
def setup(bot):
    bot.add_cog(Mogi(bot))
