import os
import aiosqlite
import asyncio
import discord
import random
import math

from datetime import datetime
from discord.ext import commands


intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix='.', intents=intents)


# database
async def initalise():
    await bot.wait_until_ready()
    # server.db
    bot.db = await aiosqlite.connect(os.environ['BOT_DATABASE'])
    await bot.db.execute(
        "CREATE TABLE IF NOT EXISTS guildData (guild_id int, user_id int, lvl int, exp int, cumulative_exp int, recent_msg text, PRIMARY KEY (guild_id, user_id))"
    )


# new member joined server
@bot.event
async def on_member_join(member):
    name = member.display_name
    await member.send(f"{name} welcome!")


# user message typed
@bot.event
async def on_message(message):
    if not message.author.bot:

        # time - recent_msg col
        # 1203 0307 = 12.03. 03:07
        msg_date = str(datetime.now())
        current_message_time = msg_date[5:7] + msg_date[8:10] + " " + msg_date[11:13] + msg_date[14:16]



        # user inital setting
        cursor = await bot.db.execute("INSERT OR IGNORE INTO guildData (guild_id, user_id, lvl, exp, cumulative_exp, recent_msg) VALUES (?,?,?,?,?,?)",
                                      (message.guild.id, message.author.id, 1, 0, 0, current_message_time))


        # channel id
        channel_enable_query = await bot.db.execute(f"SELECT enable FROM channel WHERE channel_id = {message.channel.id}")
        channel_enable_data = await channel_enable_query.fetchone()
        channel_enable = channel_enable_data[0]

        # retrieve most recent_msg timestamp
        past_message_time_query = await bot.db.execute(f"SELECT recent_msg FROM guildData WHERE user_id = {message.author.id}")
        past_message_time_data = await past_message_time_query.fetchone()
        past_message_time = past_message_time_data[0]

        # check if user is allow to earn xp (timestamp)
        past_date, past_time = past_message_time[:4], past_message_time[5:]
        current_date, current_time = current_message_time[:4], current_message_time[5:]
        allow_xp = False

        # WARNING: only take account same calendar year - need to fix the month ( 1 < 12 )
        if int(past_date) <= int(current_date):
            allow_xp = True
            pass
            if int(past_time) + 1 <= int(current_time):
                allow_xp = True



        # if ignored
        if cursor.rowcount == 0 and channel_enable and allow_xp:


            # LEVEL

            # user's current xp 
            current_exp_query = await bot.db.execute(
                f"SELECT exp, cumulative_exp, lvl FROM guildData WHERE user_id = {message.author.id}")
            current_exp_data = await current_exp_query.fetchone()
            current_exp = current_exp_data[0]
            current_cumulative_exp = current_exp_data[1]
            current_lvl = current_exp_data[2]

           # need cumulative xp?
           # curr_lvl + 1 * formula >


            xp = random.randrange(50, 99)
            updated_exp = current_exp + xp
            updated_cumulative_exp = current_cumulative_exp + xp

            # when user level up
            if updated_cumulative_exp >= current_lvl * 100:
                updated_exp = updated_cumulative_exp - (current_lvl * 100)
                await bot.db.execute(f"UPDATE guildData SET lvl = lvl + 1, exp = {updated_exp} WHERE guild_id = ? AND user_id = ?",
                                     (message.guild.id, message.author.id))

                # DM user when they level up
                await message.author.send(f"Level Up to lv.{current_lvl + 1}!")


            await bot.db.execute(f"UPDATE guildData SET exp = {updated_exp}, cumulative_exp =?, recent_msg = ? WHERE guild_id = ? AND user_id = ?",
                                 (updated_cumulative_exp, current_message_time, message.guild.id, message.author.id))



        await bot.db.commit()


    await bot.process_commands(message)


# display personal information
@bot.command()
@commands.cooldown(1, 30, commands.cooldowns.BucketType.user)
async def info(ctx):
    usr_id = ctx.author.id
    usr_name = ctx.message.author.name

    # NEED TO REFACTOR

    # rank
    rank_query = await bot.db.execute(
        f"SELECT rank FROM (SELECT *, ROW_NUMBER() OVER(ORDER BY lvl DESC) AS rank FROM guildData) WHERE user_id = {usr_id}"
    )
    rank_data = await rank_query.fetchone()
    rank = rank_data[0]

    # lvl
    lvl_query = await bot.db.execute(f"SELECT lvl FROM guildData where user_id = {usr_id}")
    lvl_data = await lvl_query.fetchone()
    lvl = lvl_data[0]

    # exp
    exp_query = await bot.db.execute(f"SELECT exp FROM guildData WHERE user_id = {usr_id}")
    exp_data = await exp_query.fetchone()
    exp = exp_data[0]


    # test embed
    likelion_logo_file = discord.File("static/likelion-logo.png", filename='likelion-logo.png')

    embed = discord.Embed(
        colour=discord.Colour.from_rgb(255, 158, 27)
    )

    orange_box = int(round((exp / 100) * 10))
    white_box = 10 - orange_box

    embed.set_thumbnail(url="attachment://likelion-logo.png")
    embed.set_author(name=f"{usr_name}", icon_url=ctx.message.author.avatar_url)
    embed.add_field(name=":crown: **Ranking**", value=f"#{rank}", inline=False)
    embed.add_field(name="**Progress**", value=orange_box * ":orange_square:" + white_box * ":white_large_square:", inline=False)
    embed.add_field(name="**Level**", value=f"lv.{lvl}", inline=True)
    embed.add_field(name="**Experience**", value=f"{exp}xp", inline=True)

    # display message
    await ctx.send(embed=embed, file=likelion_logo_file)





# leaderboard
@bot.command()
async def leaderboard(ctx):
    leaders_query = await bot.db.execute(
        f"SELECT user_id FROM guildData WHERE guild_id = {ctx.guild.id} ORDER BY cumulative_exp DESC LIMIT 10"
    )

    embed = discord.Embed(
        colour=discord.Colour.from_rgb(255, 158, 27)
    )
    embed.set_author(name="Leaderboard: TOP 10")
    embed.description = ""

    r = 1
    async for i in leaders_query:
        p = ctx.guild.get_member(i[0])
        embed.description += f"**{r}**. {p.mention}\n\n"
        r += 1

    # display leaderboard
    await ctx.send(embed=embed)









@info.error
async def error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        msg = "Please try this command again in {:.0f}s".format(error.retry_after)
        await ctx.send(msg)



# Bot is ready
@bot.event
async def on_ready():
    print(bot.user.name + ' is ready.')


bot.loop.create_task(initalise())
bot.run(os.environ['TOKEN'])
asyncio.run(bot.db.close())