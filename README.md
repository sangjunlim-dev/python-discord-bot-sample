# Setting Up
1. Go to [Discord Developer Portal](https://discord.com/developers/applications) and press "New Application" to create an app. 
2. After creating the app, go to **Bot** section under SETTINGS and press Build-A-Bot to create a bot. 
3. Go to URL Generator under SETTINGS > OAuth2 and check off **bot** under SCOPES and **Administrator** under BOT PERMISSIONS. 
4. Copy and move to the URL generated below to import the bot created to your chosen server. 
> TOKEN that will be used in the code can be found under SETTINGS > Bot

<br>

# Requirements 
You will need Python 3.6 or later and PostgreSQL versions 9.5 to 14. 
```
pip3 install -r requirements.txt
```

# Database
For PostgreSQL, we used *aysncpg* instead of *psycopg2* because it is faster and it is an asyncio variant. <br>
There are mainly two ways to connect to PostgreSQL Database using asyncpg. 
```Python
import asyncio
import asyncpg

connection = await asyncpg.connect(
    user='USER', 
    password='PASSWORD',
    database='DATABASE', 
    host='localhost'
)

connection = await asyncpg.connect(
    'postgresql://USER:PASSWORD@HOST/DATABASE'
)
```
## Access Database
Retrieve data from database by passing a query into functions.
When you **fetch** from the database, it returns List of Records, which the type is dictionary. When you **execute** query from database, it return status string. 
```Python
# Fetch
data = await bot.db.fetch(
    "SELECT column FROM table WHERE condition"
)
datum = data[0]["column"]


# Execute
status_str = await bot.db.execute(
    "INSERT INTO table (a) VALUES (100)"
)
status_str == "INSERT 0 1" # True
```

## Schema
Tables can be altered accordingly. 
> To find Server, Channel, User ID in Discord, first go to User Settings > Advanced and enable Developer Mode. Then, simply right-click on Server, Channel or User and press 'Copy ID'. 

<br>

- ### guildData
|Attribute|Data Type|Description|
|:--:|:--:|:--:|
|guild_id|BIGINT|guild id|
|user_id|BIGINT|user's id|
|lvl|INT|user's level|
|exp|INT|current experience of the user|
|cumulative_exp|INT|cumulative xp of the user|
|recent_msg|TEXT|timestamp of user's most recent message<br>(01.03 15:13 = 0103 1513)|

<br>

- ### channel
|Attribute|Data Type|Description|
|:--:|:--:|:--:|
|channel_id|BIGINT|channel id|
|enable|INT|0 or 1<br>0 for channels that user can't earn xp<br>1 for channels that user can earn xp


# Features
### 1. Custom Command Prefix
Replace COMMAND_PREFIX with your choice. 
```Python
bot = commands.Bot(command_prefix='COMMAND_PREFIX', intents=intents)
```