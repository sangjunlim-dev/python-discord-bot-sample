import os
import asyncio
import asyncpg
import discord

import random

from datetime import datetime
from discord.ext import commands

# INTENTS
intents = discord.Intents.default()
intents.members = True

# CREATE bot with custom command_prefix
bot = commands.Bot(command_prefix='.', intents=intents)

# bot ready for usage
@bot.event
async def on_ready():
    print(bot.user.name + ' is ready.')


# initialize database
async def initialize():
    await bot.wait_until_ready()

    # Connect to postgres database
    bot.db = await asyncpg.connect(os.environ["DATABASE_URL"])

    # CREATE table
    await bot.db.execute(
        "CREATE TABLE IF NOT EXISTS guildData (guild_id bigint, user_id bigint, lvl int, exp int, cumulative_exp int, recent_msg text, PRIMARY KEY (guild_id, user_id))"
    )


# new user joined the server
@bot.event
async def on_member_join(member):
    name = member.display_name
    await member.send(f"{name} welcome!")


# user message typed
@bot.event
async def on_message(message):
    if not message.author.bot:

        # time message is typed
        # FORMAT - December 3rd AM 03:07 = 1203 0307
        msg_date = str(datetime.now())
        current_message_time = msg_date[5:7] + msg_date[8:10] + " " + msg_date[11:13] + msg_date[14:16]

        # CREATE user in database, if it is user's first message
        cursor = await bot.db.execute(
            "INSERT INTO guildData (guild_id, user_id, lvl, exp, cumulative_exp, recent_msg) VALUES ($1,$2,$3,$4,$5,$6) ON CONFLICT DO NOTHING",
            message.guild.id, message.author.id, 1, 0, 0, current_message_time
        )

        # FETCH channel id
        channel_enable_query = await bot.db.fetch(
            f"SELECT enable FROM channel WHERE channel_id = {message.channel.id}"
        )
        channel_enable = channel_enable_query[0]["enable"]

        # FETCH recent_msg timestamp
        past_message_time_query = await bot.db.fetch(
            f"SELECT recent_msg FROM guildData WHERE user_id = {message.author.id}"
        )
        past_message_time = past_message_time_query[0]["recent_msg"]

        # checking user is able to earn XP
        # CONDITION - Eligible to earn XP once per minute
        past_date, past_time = past_message_time[:4], past_message_time[5:]
        current_date, current_time = current_message_time[:4], current_message_time[5:]
        allow_xp = False

        # WARNING: only take account same calendar year - need to fix the month ( 1 < 12 )
        if int(past_date) < int(current_date):
            allow_xp = True
        elif int(past_date) == int(current_date):
            if int(past_time) + 1 <= int(current_time):
                allow_xp = True
            else:
                allow_xp = False

        # UPDATE user's level and exp
        if int(cursor[-1]) == 0 and channel_enable and allow_xp:

            # FETCH user's current xp
            current_exp_query = await bot.db.fetch(
                f"SELECT exp, cumulative_exp, lvl FROM guildData WHERE user_id = {message.author.id}"
            )
            current_exp = current_exp_query[0]["exp"]
            current_cumulative_exp = current_exp_query[0]["cumulative_exp"]
            current_lvl = current_exp_query[0]["lvl"]

            # xp randomly given between range
            # DEFAULT - xp given between 50xp to 99xp
            xp = random.randrange(50, 99)
            updated_exp = current_exp + xp
            updated_cumulative_exp = current_cumulative_exp + xp

            # UPDATE user's level
            # DEFAULT - 100xp per level (linear)
            if updated_cumulative_exp >= current_lvl * 100:
                updated_exp = updated_cumulative_exp - (current_lvl * 100)
                await bot.db.execute(
                    f"UPDATE guildData SET lvl = lvl + 1, exp = {updated_exp} WHERE guild_id = $1 AND user_id = $2",
                    message.guild.id, message.author.id)

                # Notify user by sending DM
                await message.author.send(f"Level Up to lv.{current_lvl + 1}!")

            await bot.db.execute(
                f"UPDATE guildData SET exp = {updated_exp}, cumulative_exp = $1, recent_msg = $2 WHERE guild_id = $3 AND user_id = $4",
                updated_cumulative_exp, current_message_time, message.guild.id, message.author.id)

    await bot.process_commands(message)


# display personal information
# COMMAND USAGE - [command_prefix]info
@bot.command()
# user can only call the command n-time every cooldown
# DEFAULT - 1 per 30seconds
@commands.cooldown(1, 30, commands.cooldowns.BucketType.user)
async def info(ctx):
    usr_id = ctx.author.id
    usr_name = ctx.message.author.name

    # could fetch all information all at once using query.

    # FETCH user's rank
    rank_query = await bot.db.fetch(
        "SELECT rank FROM (SELECT *, ROW_NUMBER() OVER(ORDER BY lvl DESC) AS rank FROM guildData) AS derive WHERE user_id = $1",
        usr_id
    )
    rank = rank_query[0]["rank"]

    # FETCH user's lvl
    lvl_query = await bot.db.fetch("SELECT lvl FROM guildData where user_id = $1", usr_id)
    lvl = lvl_query[0]["lvl"]

    # FETCH user's exp
    exp_query = await bot.db.fetch("SELECT exp FROM guildData WHERE user_id = $1", usr_id)
    exp = exp_query[0]["exp"]

    # CREATE embed
    # change file and image accordingly for usage
    likelion_logo_file = discord.File("static/likelion-logo.png", filename='likelion-logo.png')

    embed = discord.Embed(
        colour=discord.Colour.from_rgb(255, 158, 27)
    )

    orange_box = int(round((exp / 100) * 10))
    white_box = 10 - orange_box

    embed.set_thumbnail(url="attachment://likelion-logo.png")
    embed.set_author(name=f"{usr_name}", icon_url=ctx.message.author.avatar_url)
    # rank
    embed.add_field(name=":crown: **Ranking**", value=f"#{rank}", inline=False)
    # progress bar
    embed.add_field(name="**Progress**", value=orange_box * ":orange_square:" + white_box * ":white_large_square:",
                    inline=False)
    # level
    embed.add_field(name="**Level**", value=f"lv.{lvl}", inline=True)
    # experience
    embed.add_field(name="**Experience**", value=f"{exp}xp", inline=True)

    # send message with embed
    await ctx.send(embed=embed, file=likelion_logo_file)


# display leaderboard
# COMMAND USAGE - [command_prefix]leaderboard
@bot.command()
async def leaderboard(ctx):
    # FETCH top 10 record sorted by level
    leaders_query = await bot.db.fetch(
        "SELECT user_id FROM guildData WHERE guild_id = $1 ORDER BY cumulative_exp DESC LIMIT 10", ctx.guild.id
    )

    # CREATE embed
    embed = discord.Embed(
        colour=discord.Colour.from_rgb(255, 158, 27)
    )
    embed.set_author(name="Leaderboard: TOP 10")
    embed.description = ""

    r = 1
    for i in leaders_query:
        p = ctx.guild.get_member(i[0])
        embed.description += f"**{r}**. {p.mention}\n\n"
        r += 1

    # send message with embed
    await ctx.send(embed=embed)

# info command cooldown error handling
@info.error
async def error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        msg = "Please try this command again in {:.0f}s".format(error.retry_after)
        await ctx.send(msg)


bot.loop.create_task(initialize())
bot.run(os.environ["TOKEN"])

asyncio.run(bot.db.close())
