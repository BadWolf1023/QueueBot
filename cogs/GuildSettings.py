'''
Created on Feb 22, 2021

@author: willg
'''
from discord.ext import commands
from collections import defaultdict
from datetime import timedelta
import dill as p
from CustomExceptions import NoGuildSettings
from ExtraChecks import carrot_prohibit_check
from Shared import QUEUEBOT_INVITE_LINK, get_guild_id, BAD_WOLF_ID

class GuildSettings():
    def __init__(self):
        self._guild_id = 1
        self.primary_rating_command = "elo" #Done
        self.secondary_rating_command = "elo2" #Done
        self.primary_leaderboard_name = "leaderboard1"
        self.secondary_leaderboard_on = False
        self.secondary_leaderboard_name = "leaderboard2"
        self.primary_leaderboard_secondary_rating_on = False
        self.secondary_leaderboard_secondary_rating_on = False
        self.primary_rating_display_text = ""
        self.secondary_rating_display_text = ""
        self.primary_rating_description_text = ""
        self.secondary_rating_description_text = ""
        self.primary_leaderboard_num_secondary_players = 0
        self.secondary_leaderboard_num_secondary_players = 0
        #This is the amount of time that players have to queue in the joining channel before Queuebot closes the channel and makes the rooms
        self.joining_time = timedelta(hours=2)
        self.extension_time = timedelta(minutes=5)
        
        self.should_ping = True #Done
        self.create_voice_channels = True #Done
        self.roles_have_power = set() #Done
        
        self.send_scoreboard_text = True
        self.room_open_time = 10
        self.lockdown_on = True #Done
        
        self.roles_can_see_primary_leaderboard_rooms = set() #Done
        self.roles_can_see_secondary_leaderboard_rooms = set() #Done
        self.created_channel_name = "Room"
        self.rating_command_on = True
        self.rating_command_primary_rating_embed_title = 'Set title with !queuebot_setup'
        self.rating_command_secondary_rating_embed_title = 'Set title with !queuebot_setup'
        self.show_rating = True
        self.type_mapping = {'primary_rating_command':str,
                             'secondary_rating_command':str,
                             'primary_leaderboard_name':str,
                             'secondary_leaderboard_on':bool,
                             'secondary_leaderboard_name':str,
                             'primary_leaderboard_secondary_rating_on':bool,
                             'secondary_leaderboard_secondary_rating_on':bool,
                             'primary_rating_display_text':str,
                             'secondary_rating_display_text':str,
                             'primary_leaderboard_num_secondary_players':int,
                             'secondary_leaderboard_num_secondary_players':int,
                             'joining_time':timedelta,
                             'extension_time':timedelta,
                             'should_ping':bool,
                             'create_voice_channels':bool,
                             'roles_have_power':set,
                             'send_scoreboard_text':bool,
                             'room_open_time':int,
                             'lockdown_on':bool,
                             'roles_can_see_primary_leaderboard_rooms':set,
                             'roles_can_see_secondary_leaderboard_rooms':set,
                             'created_channel_name':str,
                             'rating_command_on':bool,
                             'rating_command_primary_rating_embed_title':str,
                             'rating_command_secondary_rating_embed_title':str,
                             'show_rating':bool,
                             'primary_rating_description_text':str,
                             'secondary_rating_description_text':str
                             }
    def set_guild_id(self, guild_id):
        self._guild_id = guild_id
    def get_guild_id(self):
        return self._guild_id

        
    def __contains__(self, key):
        if key in {'type_mapping', 'command_descriptions', '_guild_id', 'guild_id'}:
            return False
        return key in self.__dict__
    
    def is_addable(self, key):
        return key in {'roles_have_power', "roles_can_see_primary_leaderboard_rooms", "roles_can_see_secondary_leaderboard_rooms"}
        
    def is_removable(self, key):
        return self.is_addable(key)
    
    def get_setting_text(self, k, v):
        typing = self.type_mapping[k]
        if typing is bool:
            return f"`{k}`: {'Yes' if v else 'No'}"
        if typing is set:
            return f"`{k}`: {', '.join(v)}"
        if typing is timedelta:
            return f"`{k}`: {int(v.total_seconds()//60)} minutes"
        return f"`{k}`: {v}"
    
    
    def settings_display(self):
        all_messages = []
        cur_msg = "`Setting Name`   :   Setting Value\n\n"
        for k,v in self.__dict__.items():
            if k not in self:
                continue
            cur_str = self.get_setting_text(k,v)
            if len(cur_msg) + len(cur_str) >= 2000:
                all_messages.append(cur_msg)
                cur_msg = ""
            cur_msg += cur_str + "\n"
        
        ending_str = """\n Do `!queuebot_setup <setting_name> <new_setting_value>` to change these settings"""
        if len(cur_msg) + len(ending_str) >= 2000:
            all_messages.append(cur_msg)
            cur_msg = ""
        cur_msg += ending_str
        
        all_messages.append(cur_msg)
        return all_messages
    
    
    def set_item(self, key, value, add_term=True):
        key=key.lower()
        if key in self:
            typing = self.type_mapping[key]
            if typing is str:
                if len(value) > 100:
                    return f"{key} has a maximum character limit of 100"
                self.__dict__[key] = value
                save_all_guild_settings()
                return f"`{key}` set to **{value}**"
            
            elif typing is bool:
                if value.lower() in {'yes', 'y', 'true', 'on'}:
                    self.__dict__[key] = True
                    save_all_guild_settings()
                    return f"`{key}` set to **Yes**"
                elif value.lower() in {'no', 'n', 'false', 'off'}:
                    self.__dict__[key] = False
                    save_all_guild_settings()
                    return f"`{key}` set to **No**"
                else:
                    return f"`{key}` not set. Valid options are **Yes** or **No**"
                
            elif typing is int:
                if not value.isnumeric():
                    return f"`{key}` setting must be a number"
                value = int(value)
                
                if key == 'room_open_time':
                    if value > 59:
                        return f"`{key}` setting is a minute, must be between 0 and 59"
                else:
                    if value > 100:
                        return f"`{key}` setting is must be 100 or less"
                self.__dict__[key] = value
                save_all_guild_settings()
                return f"`{key}` set to **{value}**"
            
            elif typing is timedelta:
                if not value.isnumeric():
                    return f"`{key}` setting must be a number in minutes"
                value = int(value)
                ONE_WEEK_MINUTES = 10080
                if value > ONE_WEEK_MINUTES:
                    return f"`{key}` setting must be less than {ONE_WEEK_MINUTES} - that's one week in minutes"
                self.__dict__[key] = timedelta(minutes=value)
                save_all_guild_settings()
                return f"`{key}` set to **{int(self.__dict__[key].total_seconds()//60)} minutes**"
            
            elif typing is set:
                if len(value) > 100:
                    if add_term:
                        return f"Items added to `{key}` have a maximum character limit of 100"
                    else:
                        return f"Items removed from `{key}` have a maximum character limit of 100"
                else:
                    if add_term:
                        if len(self.__dict__[key]) >= 100:
                            return f"**Cannot add {value}** to `{key}` because there is a 100 limit"
                        self.__dict__[key].add(value)
                        save_all_guild_settings()
                        return f"**{value}** added to `{key}`"
                    else:
                        if value in self.__dict__[key]:
                            self.__dict__[key].remove(value)
                            save_all_guild_settings()
                            return f"**{value}** removed from `{key}`"
                        else:
                            return f"**{value}** not in `{key}`"
                        
    def get_valid_leaderboard_types(self):
        valid_leaderboard_types = []
        if len(self.primary_leaderboard_name.strip()) > 0:
            valid_leaderboard_types.append(self.primary_leaderboard_name)
        
        if self.secondary_leaderboard_on:
            if len(self.secondary_leaderboard_name.strip()) > 0:
                valid_leaderboard_types.append(self.secondary_leaderboard_name)
        return valid_leaderboard_types
    
    def get_parsing_formatted_leaderboard_types(self):
        return [leaderboard_type.lower().strip() for leaderboard_type in self.get_valid_leaderboard_types()]
    
    def mogi_bot_defaults(self, ctx):
        self._guild_id = get_guild_id(ctx)
        self.primary_rating_command = "None" #Done
        self.secondary_rating_command = "None" #Done
        self.primary_leaderboard_name = "mogi"
        self.secondary_leaderboard_on = False
        self.secondary_leaderboard_name = "None"
        self.primary_leaderboard_secondary_rating_on = False
        self.secondary_leaderboard_secondary_rating_on = False
        self.primary_rating_display_text = ""
        self.secondary_rating_display_text = ""
        self.primary_rating_description_text = ""
        self.secondary_rating_description_text = ""
        self.primary_leaderboard_num_secondary_players = 0
        self.secondary_leaderboard_num_secondary_players = 0
        #This is the amount of time that players have to queue in the joining channel before Queuebot closes the channel and makes the rooms
        self.joining_time = timedelta(hours=2)
        self.extension_time = timedelta(minutes=5)
        
        self.should_ping = True #Done
        self.create_voice_channels = False #Done
        self.roles_have_power = set() #Done
        
        self.send_scoreboard_text = True
        self.room_open_time = 10
        self.lockdown_on = False #Done
        
        self.roles_can_see_primary_leaderboard_rooms = set() #Done
        self.roles_can_see_secondary_leaderboard_rooms = set() #Done
        self.created_channel_name = "Room"
        self.rating_command_on = True
        self.rating_command_primary_rating_embed_title = 'Set title with !queuebot_setup'
        self.rating_command_secondary_rating_embed_title = 'Set title with !queuebot_setup'
        self.show_rating = False
        save_all_guild_settings()
        
GUILD_SETTINGS = defaultdict(GuildSettings)


def has_guild_settings(ctx) -> bool:
    global GUILD_SETTINGS
    if isinstance(ctx, str):
        return ctx in GUILD_SETTINGS
    if ctx.guild is None:
        return False
    return str(get_guild_id(ctx)) in GUILD_SETTINGS

def has_guild_settings_check():
    return commands.check(check_has_guild_settings)

async def check_has_guild_settings(ctx):
    global GUILD_SETTINGS
    if not has_guild_settings(ctx):
        raise NoGuildSettings("No guild settings")
    return True




command_descriptions = {'primary_rating_command':"This is the name of the **command** to look up and send in an embed player's primary ratings, if you have *rating_command_on* turned on.",
                     'secondary_rating_command':"If you use a secondary rating, this is the name of the **command** to look up and send in an embed player's secondary ratings, if you have *rating_command_on* turned on.",
                     'primary_leaderboard_name':"This is the name of the primary leaderboard type. It is used to specify which leaderboard should be used when events are started or scheduled. In some cases, it may be used by the rating command if you have *rating_command_on* turned on.",
                     'secondary_leaderboard_on':"<on/off> - If you have a secondary leaderboard, turn this on. Note: this is not the same as having a secondary rating on your primary leaderboard. This is if you have an entirely different leaderboard.",
                     'secondary_leaderboard_name':"This is the name of the secondary leaderboard type. It is used to specify which leaderboard should be used when events are started or scheduled. In some cases, it may be used by the rating command if you have *rating_command_on* turned on.",
                     'primary_leaderboard_secondary_rating_on':"For your primary (or only) leaderboard, turn on if you want to use multiple ratings. This is used in conjunction with the *primary_leaderboard_num_secondary_players* setting, so read that for more details.",
                     'secondary_leaderboard_secondary_rating_on':"For your secondary leaderboard, turn on if you want to use multiple ratings. This is used in conjunction with the *secondary_leaderboard_num_secondary_players* setting, so read that for more details.",
                     'primary_rating_display_text':"This is name for player's primary ratings (shown when squads sign up, when list is shown, etc).",
                     'secondary_rating_display_text':"If you use secondary ratings, this is name for player's secondary ratings (shown when squads sign up, when list is shown, etc).",
                     'primary_leaderboard_num_secondary_players':"**Read carefully:** You can configure the bot to use multiple ratings at once for teams when they queue. This setting specifies that, when someone creates a squad, the last **x** players tagged will use the secondary rating, and the rest (the author and the other people tagged) will use the primary rating. This setting is for the queues started using the primary leaderboard.",
                     'secondary_leaderboard_num_secondary_players':"See description for *primary_leaderboard_num_secondary_players*. This setting is the secondary leaderboard version of that setting.",
                     'joining_time':"**Only for events run using the event scheduler:** This is the number of minutes before the event start time that queueing opens up.",
                     'extension_time':"**Only for events run using the event scheduler:** If there aren't a perfect number of teams to evenly split into rooms, this is the number of minutes the bot will extend the queueing time. Note that queueing will end during the extension time if there are a perfect number of teams to fill rooms. Set to 0 if you don't want an extension time.",
                     'should_ping':"<on/off> - Bot should ping @ here when mogi starts",
                     'create_voice_channels':"<on/off> - Bot should create voice channels for each individual team.",
                     'show_rating':"If rating should be shown in the list, or when players do `!squad`, or when teams confirm. When channels are created, ratings will be shown regardless of this setting.",
                     'roles_have_power':"<add/remove> <role name> - this adds or removes a role name. People who have any of these roles will have elevated powers, including starting and ending queues, removing squads, **and modifying queuebot settings**. Note that server administrators will always have power, even if they have none of these roles.",
                     'send_scoreboard_text':"<on/off> - If the `!scoreboard` command text should be sent in the created channels. Useful if you use 255MP's RandomBot.",
                     'room_open_time':"This setting is not in use.",
                     'lockdown_on':"<on/off> - Bot should lockdown the queueing channel when rooms are created, and should unlock the channel when Queueing starts",
                     'roles_can_see_primary_leaderboard_rooms':"These roles will be able to see the created rooms (and voice channels if enabled) when a queue for the primary leaderboard is started.",
                     'roles_can_see_secondary_leaderboard_rooms':"These roles will be able to see the created rooms (and voice channels if enabled) when a queue for the secondary leaderboard is started.",
                     'created_channel_name':"Created text and voice channels will start with this name.",
                     'rating_command_on':"<on/off> - If the rating lookup **command** is turned on. (The rating lookup command is *primary_rating_command*. If you have a second rating, `secondary_rating_command` is the secondary rating lookup command.)",
                     'rating_command_primary_rating_embed_title':"If `rating_command_on` is on, this sets what the title of the embed should be when a **primary** rating lookup is performed.",
                     'rating_command_secondary_rating_embed_title':"If `rating_command_on` is on, this sets what the title of the embed should be when a **secondary** rating lookup is performed.",
                     'primary_rating_description_text':"You'll normally want to leave this blank, unless you have a secondary rating being used in the queue as well. This is a description put in parentheses after player names who queue with the primary rating (shown when squads sign up, when list is shown, etc). It also is put in front of the primary rating name.",
                     'secondary_rating_description_text':"You'll want to have this set if you have a secondary rating being used in the queue as well. This is a description put in parentheses after player names who queue with the secondary rating (shown when squads sign up, when list is shown, etc). It also is put in front of the secondary rating name."}
def ensure_command_descriptions_accurate():
    default_settings = GuildSettings()
    for setting_name in default_settings.__dict__:
        if setting_name in default_settings:
            if setting_name not in command_descriptions:
                print(setting_name)
                
            assert setting_name in command_descriptions
            
    for setting_name in command_descriptions:
        assert setting_name in default_settings
        
def ensure_all_guilds_settings_patched():
    default_settings = GuildSettings()
    for guild_settings in GUILD_SETTINGS.values():
        for setting_name in default_settings.__dict__:
            if setting_name in default_settings: #We overloaded the in function for special functionality
                assert setting_name in guild_settings
                assert setting_name in default_settings.type_mapping
                
        for setting_name in guild_settings.__dict__:
            if setting_name in guild_settings: #We overloaded the in function for special functionality
                assert setting_name in default_settings
                
        assert guild_settings.type_mapping == default_settings.type_mapping
                
                
        
def information():
    all_messages = []
    cur_msg = """Here is the command to configure Queuebot's settings: `!queuebot_setup <setting_name> (add/remove) <setting_value>`
Here are 6 examples:
`!queuebot_setup create_voice_channels yes`
`!queuebot_setup should_ping yes`
`!queuebot_setup joining_time 45`
`!queuebot_setup rating_name elo`
`!queuebot_setup roles_have_power add Staff`
`!queuebot_setup roles_have_power remove Staff`

**For clarification on some of the vague settings**, this is how players are displayed when they confirm:
- Supposing the player queued with a primary rating: **PLAYERNAME (primary_rating_description_text) (RATING primary_rating_description_text primary_rating_display_text)**
- Supposing the player queued with a secondary rating: **PLAYERNAME (secondary_rating_description_text) (RATING secondary_rating_description_text primary_rating_display_text)**
Of course, this is all configurable. Just leave them blank if you don't want these advanced settings to show when squads are shown/lists are shown.


**These are the things you can configure and a description of what they do:**\n"""
    for k,v in command_descriptions.items():
        cur_str = f"`{k}`: {v}"
        if len(cur_msg) + len(cur_str) >= 2000:
            all_messages.append(cur_msg)
            cur_msg = ""
        cur_msg += cur_str + "\n"
    all_messages.append(cur_msg)
    return all_messages
                    



def get_guild_settings(ctx) -> GuildSettings:
    global GUILD_SETTINGS
    if isinstance(ctx, str):
        return GUILD_SETTINGS[ctx]
    if isinstance(ctx, int):
        return GUILD_SETTINGS[str(ctx)]
    return GUILD_SETTINGS[str(get_guild_id(ctx))]

def delete_settings(ctx):
    global GUILD_SETTINGS
    if isinstance(ctx, str):
        del GUILD_SETTINGS[ctx]
    elif isinstance(ctx, int):
        del GUILD_SETTINGS[str(ctx)]
    else:
        del GUILD_SETTINGS[str(get_guild_id(ctx))]


def default_settings(ctx) -> GuildSettings:
    delete_settings(ctx)
    
    return get_guild_settings(ctx)


async def hasroles(ctx, settings=None):
    if ctx.guild is None:
        return False
    if ctx.author.guild_permissions.administrator:
        return True
    if ctx.author.id == BAD_WOLF_ID:
        return True
    roles_have_power = get_guild_settings(ctx).roles_have_power if settings is None else settings
    for rolename in roles_have_power:
        for role in ctx.author.roles:
            if role.name == rolename:
                return True
    raise commands.MissingAnyRole(roles_have_power)

def has_roles_check():
    return commands.check(hasroles)

        
class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        #Load in the schedule from the pkl
        #self.load_pkl_schedule()

    @commands.command()
    @commands.guild_only()
    @carrot_prohibit_check()
    @commands.cooldown(1, 30, commands.BucketType.member)
    @has_guild_settings_check()
    @has_roles_check()
    async def queuebot_settings(self, ctx):
        """Displays how your Queuebot is currently configured"""        
        guild_settings = get_guild_settings(ctx)
        to_send = guild_settings.settings_display()
        for msg in to_send:
            await ctx.send(msg)
            
    @commands.command()
    @commands.guild_only()
    @carrot_prohibit_check()
    @commands.cooldown(1, 5, commands.BucketType.member)
    @has_guild_settings_check()
    @has_roles_check()
    async def reset_settings(self, ctx):
        """WARNING: Completely resets your server's settings - cannot undo! This does **not** reset your Sheet settings (those are different settings)."""
        delete_settings(ctx)
        await ctx.send("Settings reset to default.")
        
            
    @commands.command()
    @commands.guild_only()
    @carrot_prohibit_check()
    @commands.cooldown(1, 60, commands.BucketType.member)
    @commands.cooldown(1, 60, commands.BucketType.guild)
    @has_roles_check()
    async def queuebot_settings_help(self, ctx):
        """Tutorial for how to configure Queuebot"""
        for msg in information():
            await ctx.send(msg)
    
    
    @commands.command()
    @commands.max_concurrency(number=1,wait=True)
    @commands.guild_only()
    @carrot_prohibit_check()
    @commands.cooldown(1, 5, commands.BucketType.member)
    @has_roles_check()
    async def queuebot_setup(self, ctx, setting_name:str, setting_value:str):
        """Changes how Queuebot is currently configured - !queuebot_settings_help to learn how to use"""
        guild_settings = get_guild_settings(ctx)
        guild_settings.set_guild_id(str(get_guild_id(ctx)))
        if setting_name not in guild_settings:
            await ctx.send(f"`{setting_name}` is not a valid setting. Do `!queuebot_settings_help` for what you can configure.")
            return
        
        if guild_settings.is_addable(setting_name):
            args = ctx.message.content.split()[2:]
            if args[0].lower() not in {'add', 'remove'}:
                await ctx.send(f"This command requires you to specify if you want to add or remove that item from the list. Try this instead: `!queuebot_setup {setting_name} add {setting_value}` OR  `!queuebot_setup {setting_name} remove {setting_value}`")
                return
            if len(args) < 2:
                await ctx.send(f"This command requires you to specify if you want to add or remove that item from the list. Try this instead: `!queuebot_setup {setting_name} add Staff` OR  `!queuebot_setup {setting_name} remove Staff`")
                return
            is_adding = args[0].lower() == 'add'
            term = " ".join(args[1:])
            info_text = guild_settings.set_item(setting_name, term, is_adding)
            if info_text is None:
                info_text = "An unknown error occurred."
            await ctx.send(info_text)
                
        else:
            info_text = guild_settings.set_item(setting_name, setting_value)
            if info_text is None:
                info_text = "An unknown error occurred."
            await ctx.send(info_text)
        
    @commands.command()
    @carrot_prohibit_check()
    @commands.cooldown(1, 60, commands.BucketType.member)
    async def queuebot_invite(self, ctx):
        await ctx.send(QUEUEBOT_INVITE_LINK)
            
            

def version_1_patch(all_guild_settings):
    temp_guild_settings = GuildSettings()
    for guild_setting in all_guild_settings.values():
        if 'rating_command_primary_rating_embed_title' not in guild_setting.__dict__:
            guild_setting.rating_command_primary_rating_embed_title = temp_guild_settings.rating_command_primary_rating_embed_title
        if 'rating_command_secondary_rating_embed_title' not in guild_setting.__dict__:
            guild_setting.rating_command_secondary_rating_embed_title = temp_guild_settings.rating_command_secondary_rating_embed_title
        
        guild_setting.type_mapping['rating_command_primary_rating_embed_title'] = str
        guild_setting.type_mapping['rating_command_secondary_rating_embed_title'] = str

def version_2_patch(all_guild_settings):
    for guild_setting in all_guild_settings.values():
        if 'primary_leaderboard_type' in guild_setting.__dict__:
            guild_setting.primary_leaderboard_name = guild_setting.primary_leaderboard_type
            del guild_setting.__dict__['primary_leaderboard_type']
        if 'secondary_leaderboard_type' in guild_setting.__dict__:
            guild_setting.secondary_leaderboard_name = guild_setting.secondary_leaderboard_type
            del guild_setting.__dict__['secondary_leaderboard_type']
        
        guild_setting.type_mapping['primary_leaderboard_name'] = str
        guild_setting.type_mapping['secondary_leaderboard_name'] = str
        if 'primary_leaderboard_type' in guild_setting.type_mapping:
            del guild_setting.type_mapping['primary_leaderboard_type']
        if 'secondary_leaderboard_type' in guild_setting.type_mapping:
            del guild_setting.type_mapping['secondary_leaderboard_type']
            
def version_3_patch(all_guild_settings):
    temp_guild_settings = GuildSettings()
    for guild_setting in all_guild_settings.values():
        if 'show_rating' not in guild_setting.__dict__:
            guild_setting.show_rating = temp_guild_settings.show_rating
        
        guild_setting.type_mapping['show_rating'] = bool
        
def version_4_patch(all_guild_settings):
    for guild_id, guild_setting in all_guild_settings.items():
        if '_guild_id' not in guild_setting.__dict__:
            guild_setting._guild_id = guild_id
            
#Adding description text for when players/teams ratings are displayed
#Also changed one name for clarity
def version_5_patch(all_guild_settings):        
    for guild_setting in all_guild_settings.values():
        if 'primary_leaderboard_rating_description_text' not in guild_setting.__dict__:
            guild_setting.primary_leaderboard_rating_description_text = ""
        if 'secondary_leaderboard_rating_description_text' not in guild_setting.__dict__:
            guild_setting.secondary_leaderboard_rating_description_text = ""
        
        guild_setting.type_mapping['primary_leaderboard_rating_description_text'] = str
        guild_setting.type_mapping['secondary_leaderboard_rating_description_text'] = str
        
        
        if 'send_table_text' in guild_setting.__dict__:
            guild_setting.send_scoreboard_text = guild_setting.send_table_text
            del guild_setting.__dict__['send_table_text']
        
        guild_setting.type_mapping['send_scoreboard_text'] = bool
        if 'send_table_text' in guild_setting.type_mapping:
            del guild_setting.type_mapping['send_table_text']
            
            
def version_6_patch(all_guild_settings):        
    for guild_setting in all_guild_settings.values():
        
        
        if 'rating_name' in guild_setting.__dict__:
            guild_setting.primary_rating_command = guild_setting.rating_name
            del guild_setting.__dict__['rating_name']
            
        if 'secondary_rating_name' in guild_setting.__dict__:
            guild_setting.secondary_rating_command = guild_setting.secondary_rating_name
            del guild_setting.__dict__['secondary_rating_name']
            
        guild_setting.type_mapping['primary_rating_command'] = str
        guild_setting.type_mapping['secondary_rating_command'] = str
            
        
        if 'rating_name' in guild_setting.type_mapping:
            del guild_setting.type_mapping['rating_name']
            
        if 'secondary_rating_name' in guild_setting.type_mapping:
            del guild_setting.type_mapping['secondary_rating_name']
            
            
            
def version_7_patch(all_guild_settings):        
    for guild_setting in all_guild_settings.values():
        
        if 'primary_leaderboard_rating_description_text' in guild_setting.__dict__:
            guild_setting.primary_rating_description_text = guild_setting.primary_leaderboard_rating_description_text
            del guild_setting.__dict__['primary_leaderboard_rating_description_text']
            
        if 'secondary_leaderboard_rating_description_text' in guild_setting.__dict__:
            guild_setting.secondary_rating_description_text = guild_setting.secondary_leaderboard_rating_description_text
            del guild_setting.__dict__['secondary_leaderboard_rating_description_text']
            
        guild_setting.type_mapping['secondary_rating_description_text'] = str
        guild_setting.type_mapping['primary_rating_description_text'] = str
            
        
        if 'primary_leaderboard_rating_description_text' in guild_setting.type_mapping:
            del guild_setting.type_mapping['primary_leaderboard_rating_description_text']
            
        if 'secondary_leaderboard_rating_description_text' in guild_setting.type_mapping:
            del guild_setting.type_mapping['secondary_leaderboard_rating_description_text']
            
            

        
        
        
        
def save_all_guild_settings():
    global GUILD_SETTINGS
    pkl_dump_path = "guildsettings_backup.pkl"
    with open(pkl_dump_path, "wb") as pickle_out:
        try:
            p.dump(GUILD_SETTINGS, pickle_out)
        except:
            print("Could not dump pickle for guild settings.")
            

def load_all_guild_settings():
    global GUILD_SETTINGS
    try:
        with open("guildsettings_backup.pkl", "rb") as pickle_in:
            try:
                temp = p.load(pickle_in)
                if temp == None:
                    temp = defaultdict(lambda: GuildSettings())
                GUILD_SETTINGS = temp
            except:
                print("Could not read in pickle for guildsettings_backup.pkl data.")
                GUILD_SETTINGS = defaultdict(lambda: GuildSettings())
    except:
        print("guildsettings_backup.pkl does not exist, so no guild settings loaded in. Will create when a guild makes settings.")         
        GUILD_SETTINGS = defaultdict(lambda: GuildSettings())
        
    version_1_patch(GUILD_SETTINGS)
    version_2_patch(GUILD_SETTINGS)
    version_3_patch(GUILD_SETTINGS)
    version_4_patch(GUILD_SETTINGS)
    version_5_patch(GUILD_SETTINGS)
    version_6_patch(GUILD_SETTINGS)
    version_7_patch(GUILD_SETTINGS)
    
    ensure_command_descriptions_accurate()
    ensure_all_guilds_settings_patched()
    save_all_guild_settings()
    
    
        
def setup(bot):
    load_all_guild_settings()
    bot.add_cog(Settings(bot))
    
