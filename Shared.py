'''
Created on Mar 7, 2021

@author: willg
'''
from datetime import timedelta
TESTING_SERVER_ID = 739733336871665696
BAD_WOLF_ID = 706120725882470460
TESTING=False
QUEUEBOT_INVITE_LINK = "https://discord.com/api/oauth2/authorize?client_id=803378682479640586&permissions=269667344&scope=bot"
MK7_GUILD_ID = 280462328603082753
MKW_ITEM_RAIN_LOUNGE_GUILD_ID = 678245545881501727
MKW_LOUNGE_GUILD_ID = 387347467332485122
MK8DX_ITALIA_GUILD_ID = 823704449608318997
MK8DX_ITALIA_TEST_GUILD_ID = 696464579131080785
MKW_LOUNGE_ML_CHANNEL_ID = 877668948433309756
MKW_LOUNGE_MLLU_CHANNEL_ID = 877668999490596864
MKT_LOUNGE_GUILD_ID = 816786965818245190



MKW_LOUNGE_RT_SQUAD_QUEUE_ROLE_STR = "<@&902602279859929128>"
MKW_LOUNGE_CT_SQUAD_QUEUE_ROLE_STR = "<@&902604481823383642>"

SERVER_ID_TO_IMPERSONATE = None
if TESTING:
    SERVER_ID_TO_IMPERSONATE = None
    
CACHING_TIME_SECONDS = 30
CACHING_TIME = timedelta(seconds=CACHING_TIME_SECONDS)
DISCORD_MAX_MESSAGE_LEN = 2000

RATING_MANUALLY_MANAGED_GUILD_IDS = {MK7_GUILD_ID, MKW_ITEM_RAIN_LOUNGE_GUILD_ID, MKW_LOUNGE_GUILD_ID, MK8DX_ITALIA_GUILD_ID, MK8DX_ITALIA_TEST_GUILD_ID}

def is_lounge(ctx):
    if isinstance(ctx, str):
        return str(MKW_LOUNGE_GUILD_ID) == ctx or (str(TESTING_SERVER_ID) == ctx if TESTING else False)
    elif isinstance(ctx, int):
        return MKW_LOUNGE_GUILD_ID == ctx or (TESTING_SERVER_ID == ctx if TESTING else False)
    return get_guild_id(ctx) == MKW_LOUNGE_GUILD_ID or (get_guild_id(ctx) == ctx if TESTING else False)


def isfloat(value):
    try:
        float(value)
        return True
    except ValueError:
        return False
    
def isint(value):
    try:
        int(value)
        return True
    except ValueError:
        return False
    
def get_guild_id(ctx):
    if SERVER_ID_TO_IMPERSONATE is None:
        return ctx.guild.id
    return SERVER_ID_TO_IMPERSONATE
