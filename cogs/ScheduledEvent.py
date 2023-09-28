from cogs import GuildSettings

class Scheduled_Event():
    def __init__(self, leaderboard_type, team_size, teams_per_room, queue_close_time, started, start_channel_id,
                 server_id):
        self.leaderboard_type = leaderboard_type
        self.team_size = team_size
        self.teams_per_room = teams_per_room
        self.queue_close_time = queue_close_time
        self.started = started
        self.start_channel_id = start_channel_id
        self.server_id = server_id

    def get_event_announcement_str(self):
        epoch = int(self.queue_close_time.timestamp())
        return f"{self.leaderboard_type} {self.team_size}v{self.team_size} @ <t:{epoch}:F> ~ <t:{epoch}:R>"

    def get_event_str(self, bot):
        guild_settings = GuildSettings.get_guild_settings(self.server_id)

        # < t: 1695855960:f >
        queue_close_time_discord_str = f"<t:{int(self.queue_close_time.timestamp())}:f>"
        queue_open_time = self.queue_close_time - guild_settings.joining_time
        queue_open_time_discord_str = f"<t:{int(queue_open_time.timestamp())}:f>"

        channel = None
        try:
            channel = bot.get_channel(self.start_channel_id)
        except:
            pass
        return f"{self.leaderboard_type} {self.team_size}v{self.team_size}, {self.teams_per_room} teams per room, queueing in {'#invalid-channel' if channel is None else channel.mention}" + "\n\t\t" + f"\- Queueing opens at {queue_open_time_discord_str}" + "\n\t\t" + f"\- Queueing closes at {queue_close_time_discord_str}"

