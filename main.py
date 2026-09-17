import logging
import os

import discord
from discord import app_commands

from objects.bot import MusicBot
from objects.exceptions import MusicCommandError, NoGuildError
from services import adService
from services.env import getEnv


class MusicCommandTree(app_commands.CommandTree):
    async def on_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        send = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message

        if isinstance(error, app_commands.CommandOnCooldown):
            await send(
                f"コマンドはクールダウン中です。 **{error.retry_after:.2f}** 秒後にお試しください。",
                ephemeral=True,
            )
            return
        elif isinstance(error, app_commands.MissingPermissions):
            await send("あなたにはこのコマンドを実行する権限がありません。", ephemeral=True)
            return
        elif isinstance(error, (NoGuildError, app_commands.NoPrivateMessage)):
            await send("このコマンドはこのチャンネルでは実行できません。", ephemeral=True)
            return
        elif isinstance(error, MusicCommandError):
            await send(str(error), ephemeral=True)
            return
        else:
            _log.exception("Unhandled error in app command", exc_info=error)
            await send(
                embed=discord.Embed(
                    title="エラーが発生しました！",
                    description=(
                        "予期せぬエラーが発生しました。しばらくしてもう一度お試しください。\n"
                        "問題が続く場合は [サポートサーバー](https://discord.gg/PN3KWEnYzX) までご連絡ください。"
                    ),
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )


intents = discord.Intents.none()
intents.guilds = True
intents.voice_states = True

bot = MusicBot(
    command_prefix="music!",
    intents=intents,
    member_cache_flags=discord.MemberCacheFlags.none(),
    max_messages=None,
)

bot.tree = MusicCommandTree(bot)

discord.utils.setup_logging(level=logging.INFO, root_logger=True)
_log = logging.getLogger("music")


@bot.event
async def on_ready():
    if not bot.user:
        return
    _log.info("Logged in as %s", bot.user.name)


@bot.event
async def setup_hook():
    for ext in ("cogs.music", "cogs.ping", "cogs.help"):
        await bot.load_extension(ext)

    adService.loadAds()

    if os.getenv("SYNC_COMMANDS") == "1":
        _log.info("Syncing application commands (SYNC_COMMANDS=1)")
        await bot.tree.sync()


if __name__ == "__main__":
    token = getEnv("discord")
    if not token:
        _log.critical("Discord token is not set. Exiting.")
        raise SystemExit(1)

    # log_handler=None: disable discord.py's own handler to avoid duplicate logs.
    bot.run(token, log_handler=None)
