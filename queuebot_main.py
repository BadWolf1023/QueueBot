import discord

from discord.ext import commands, tasks
import json

from cogs.Queue import elo_check
from itertools import cycle
from CustomExceptions import NoGuildSettings, NoCarrotAllowed, NotLounge, RatingManuallyManaged
import Shared
import asyncio




bot = commands.Bot(owner_id=Shared.BAD_WOLF_ID, command_prefix=('!', '^'), case_insensitive=True, intents=discord.Intents.all())
STARTED = False

initial_extensions = ['cogs.Queue', 'cogs.Elo', 'cogs.MogiBotDefaultSetup']
status_cycle = cycle(["Let's Squad Queue!", "!help for how to use bot", "!queuebot_invite for invite link"])


with open('./config.json', 'r') as cjson:
    config = json.load(cjson)

@bot.event
async def on_ready():
    print("on_ready called.")
    global STARTED
    if not STARTED:
        statuses.start()
        print("Logged in as {0.user}".format(bot))
        STARTED = True


@bot.event
async def on_command_error(ctx, error):
    if ctx.author.bot:
        return
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingRequiredArgument):
        try:
            await(await ctx.send("Your command is missing an argument: `%s`" %
                       str(error.param))).delete(delay=10)
        except discord.Forbidden:
            pass
        return
    if isinstance(error, commands.CommandOnCooldown):
        try:
            await(await ctx.send("This command is on cooldown; try again in %.0fs"
                       % error.retry_after)).delete(delay=5)
        except discord.Forbidden:
            pass

        return
    
    if isinstance(error, commands.MissingAnyRole):
        try:
            await(await ctx.send(f"You either need to be a server administrator, or have one of the following roles to use this command: `{', '.join(error.missing_roles)}`",
                             )
            
              ).delete(delay=10)
        except discord.Forbidden:
            pass
        return
    if isinstance(error, commands.BadArgument):
        try:
            await(await ctx.send("BadArgument Error: `%s`" % error.args)).delete(delay=10)
        except discord.Forbidden:
            pass
        return
    if isinstance(error, commands.BotMissingPermissions):
        try:
            await(await ctx.send("I need the following permissions to use this command: %s"
                       % ", ".join(error.missing_perms))).delete(delay=10)
        except discord.Forbidden:
            pass
        return
    if isinstance(error, commands.NoPrivateMessage):
        await(await ctx.send("You can't use this command in DMs!")).delete(delay=5)
        return
    if isinstance(error, commands.MissingPermissions):
        try:
            await(await ctx.send("You need the following permissions to use this command: %s"
                       % ", ".join(error.missing_perms))).delete(delay=10)
        except discord.Forbidden:
            pass
        return
    if isinstance(error, NoGuildSettings):
        try:
            await ctx.send("Contact a server admin to set up Queuebot's settings by doing `!queuebot_setup` - they'll probably want to read `!queuebot_settings_help` to understand how to use the command. Server admins must change at least one setting using `!queuebot_setup` before any queues can be started.\n\nIf you just added Queuebot to your server, you **must** read `!rating_help` (even if your rating is managed manually by Bad Wolf) for important permission requirements. **Queuebot won't work if you don't do the permissions required in** `!rating_help`.", delete_after=45)
        except discord.Forbidden:
            pass
        return
    if isinstance(error, NoCarrotAllowed):
        return
    
    if isinstance(error, NotLounge):
        return
    
    if isinstance(error, RatingManuallyManaged):
        try:
            await ctx.send("You cannot run this command because this server's rating settings are manually managed by Bad Wolf. If you need assistance, please contact Bad Wolf #1023 on Discord.")
        except discord.Forbidden:
            pass
        return
    
    
    if 'original' in error.__dict__:
        if isinstance(error.original, discord.Forbidden):
            #This should only run if bot can't send messages
            return
    
    try:
        await ctx.send("An unknown error happened. Contact Bad Wolf #1023 on Discord if this keeps happening.")
    except discord.Forbidden:
        pass

    
    raise error



@tasks.loop(seconds=20)
async def statuses():
    game = discord.Game(next(status_cycle))
    await bot.change_presence(status=discord.Status.online, activity=game)
    
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    if message.content.lower() == "!queuebot_invite" or message.content.lower() == "!invite":
        try:
            await message.channel.send("https://discord.com/api/oauth2/authorize?client_id=803378682479640586&permissions=269667344&scope=bot")
        except:
            pass
        return
    if message.guild is None:
        return
    
    await elo_check(bot, message)
    #We overrode bot's on_message function, so we must manually invoke process commands
    await bot.process_commands(message)



def main():
    for extension in initial_extensions:
        bot.load_extension(extension)

if __name__ == '__main__':
    main()

bot.run(config["token"])



