'''
Created on Mar 7, 2021

@author: willg
'''
from CustomExceptions import NoCarrotAllowed, NotLounge, RatingManuallyManaged, NotBadWolf
from Shared import is_lounge, RATING_MANUALLY_MANAGED_GUILD_IDS, BAD_WOLF_ID, get_guild_id
from discord.ext import commands

def owner_or_permissions(**perms):
    original = commands.has_permissions(**perms).predicate
    async def extended_check(ctx):
        if ctx.guild is None:
            return False
        return ctx.author.id == BAD_WOLF_ID or await original(ctx)
    return commands.check(extended_check)


def lounge_only_check():
    return commands.check(exception_on_not_lounge)

async def exception_on_not_lounge(ctx):
    if not is_lounge(ctx):
        raise NotLounge("Not Lounge server.")
    return True


def guild_manually_managed_for_elo():
    return commands.check(is_rating_manually_managed)

async def is_rating_manually_managed(ctx):
    if get_guild_id(ctx) in RATING_MANUALLY_MANAGED_GUILD_IDS and ctx.author.id != BAD_WOLF_ID:
        raise RatingManuallyManaged("Carrot prefix not allowed.")
    return True

def badwolf_command_check():
    return commands.check(is_bad_wolf)

async def is_bad_wolf(ctx):
    if ctx.author.id != BAD_WOLF_ID:
        raise NotBadWolf("Author is not Bad Wolf.")
    return True       

        
        

def carrot_prohibit_check():
    return commands.check(carrot_prohibit)

async def carrot_prohibit(ctx):
    if ctx.message.content.startswith("^"):
        raise NoCarrotAllowed("Carrot prefix not allowed.")
    return True



