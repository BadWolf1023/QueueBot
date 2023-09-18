'''
Created on Apr 16, 2021

@author: willg
'''

from discord.ext import commands
from ExtraChecks import carrot_prohibit_check, owner_or_permissions, guild_manually_managed_for_elo

class MogiBotDefaults(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.cooldown(1, 60, commands.BucketType.member)
    @commands.guild_only()
    @carrot_prohibit_check()
    @commands.max_concurrency(number=1,wait=True)
    @owner_or_permissions(administrator=True)
    @guild_manually_managed_for_elo()
    async def easy_mogibot_setup(self, ctx):
        """IMPORTANT: DO !help easy_mogibot_setup BEFORE RUNNING THIS.
        This will set your server settings to be similar to MogiBot. This will erase both your rating settings and your guild settings, so use with caution. This command should only be used by clans or other basic servers who want to quickly and easily set up Queuebot to gather for wars."""
        await self.bot.get_cog('Elo').mogi_bot_defaults(ctx)
        await self.bot.get_cog('Queue').mogi_bot_defaults(ctx)
        await ctx.send("Changed various server settings. If you don't want to ping when you start a mogi, do `!queuebot_setup should_ping no`")
        await ctx.send(f"If you want to gather a lineup, do `!mogi` in the channel you want to gather in.")
    
def setup(bot):
    bot.add_cog(MogiBotDefaults(bot))