import discord
from discord.ext import commands
from discord import app_commands
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from discord.ui import View, Button
import time
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread
import os
import json
import re
import typing
from typing import Optional

# Google Sheets Setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_json = json.loads(os.environ["GOOGLE_CREDS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
client = gspread.authorize(creds)
sheet = client.open("SCP Points Log").sheet1
activity_sheet = client.open("SCP Points Log").worksheet("Deployments")
morph_sheet = client.open("SCP Points Log").worksheet("Morphs")

# Constants
POINTS_LOG_CHANNEL_ID = 1387710159446474895
AUDIT_LOG_CHANNEL_ID = 1387713963550314577
ALLOWED_ROLES = [1395018313847013487]
DEPLOYMENT_ROLE = [1395875682810331318]
GUILD_ID = 995723132478427267

# Bot Setup
OWNER_ID = 719909192000864398
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=commands.when_mentioned_or("d!"), intents=intents)

deployment_tracker = {}

RULES = {
    1:
    "Do not false react to event-checks, i.e Reacting to a deployment message but not showing up at the deployment.",
    2: "Do not speak about unnecessary things.",
    3: "Do not mock or speak badly about allied and/or unallied factions.",
    4: "Spamming is not allowed.",
    5: "Do not ping Rogue unless an emergency.",
    6: "Do not be racist.",
    7:
    "You can be disrespectful in a jokingly manner, as long as you know the consequences.",
    8: "Respect every SCP:RP site staff member.",
    9:
    "DM advertising or advertising is not allowed without consent of the person you are advertising to / or without the consent of Rogue.",
    10:
    "Do not start an irrelevant or inappropriate topic to talk about in any channel.",
    11: "Do not add unnecessary reactions on announcements individually.",
    12: "Refrain from mocking each other.",
    13:
    "Don't date in here, if you intend to do that, dating is only between 2 people. Do it in DM's, the faction has nothing to do with it.",
    14: "Follow Discord TOS: https://discord.com/terms",
    15:
    "Follow Roblox TOS: https://en.help.roblox.com/hc/en-us/articles/115004647846-Roblox-Terms-of-Use",
    69: "Did ur dumbass really think this was a rule?",
    420: "What are you expecting to find here?",
    1917: "Theres 15 fucking rules, why tf are you checking for rule 1917",
    67: "I don't know what the meme is so uh yea",
}

PROTOCOLS = {
    1:
    "Act mature and professional at all times especially in formal situations. Joking should only be permitted when sites are in casual mode, and there should be no inappropriate content or behaviours being shared.",
    2:
    "If you are told to stop a behaviour by a HICOM, CO, or Site-Staff in game, please correct yourself and apologize to whoever was disturbed by the behaviour. Whether that be site-staff, other factions, Delta-0 members, or members of the public.",
    3:
    "Report Misbehaviour in-game to Mika directly as Mika overlooks professionalism and discipline. Do not be shy to reach out even if you are unsure if someone has broken a rule. All reports, serious or not, will be shared to other members of the HICOM team for overviewing.",
    4:
    "Under no circumstance should you mock, bully, behave inappropriately, be racist, sexist, homophobic, hateful, insensitive, offensive, or verbally abusive someone on site. This will NOT be taken lightly. This includes making comments on someone who is provoking you, or towards a person/site.",
    5:
    "If you react to a deployment, you show up. If for any reason you cannot attend, inform the host.",
    6:
    "Do not break in-site rules and use common sense otherwise there will be consequences.",
}

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.lower()

    # Check Rules with regex to match only rule followed by number 1-15
    rule_match = re.search(r"\brule\s*(\d{1,2})\b", content)
    if rule_match:
        rule_num = int(rule_match.group(1))
        if rule_num in RULES:
            await message.channel.send(RULES[rule_num])
            return  # stop further processing

    # Check Protocols
    protocol_match = re.search(r"\bprotocol\s*(\d{1,2})\b", content)
    if protocol_match:
        protocol_num = int(protocol_match.group(1))
        if protocol_num in PROTOCOLS:
            await message.channel.send(PROTOCOLS[protocol_num])
            return

    # Other keywords
    if "crazy" in content:
        await message.channel.send(
            "Crazy? I was crazy once. They locked me in a room. A rubber room. A rubber room? A rubber room filled with rats. And rats make me crazy.")

# Utility Functions

def is_allowed(interaction):
    return any(role.id in ALLOWED_ROLES for role in interaction.user.roles)

def get_points(discord_id):
    records = sheet.get_all_records()
    for i, row in enumerate(records, start=2):
        if str(row['Discord ID']) == str(discord_id):
            return int(row['Points'])
    return 0

def update_points(discord_id, discord_tag, points_to_add):
    records = sheet.get_all_records()
    for i, row in enumerate(records, start=2):
        if str(row['Discord ID']) == str(discord_id):
            new_points = int(row['Points']) + points_to_add
            sheet.update_cell(i, 3, new_points)
            return new_points
    sheet.append_row([str(discord_id), discord_tag, points_to_add])
    return points_to_add

def remove_points(discord_id, points_to_remove):
    records = sheet.get_all_records()
    for i, row in enumerate(records, start=2):
        if str(row['Discord ID']) == str(discord_id):
            new_points = max(0, int(row['Points']) - points_to_remove)
            sheet.update_cell(i, 3, new_points)
            return new_points


@bot.event
async def on_ready():
    print("✅ Bot is starting...")
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        bot.tree.copy_global_to(guild=discord.Object(id=GUILD_ID))
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"✅ Synced {len(synced)} slash commands to guild {GUILD_ID}")
    except Exception as e:
        print(f"❌ Sync failed: {e}")


@app_commands.guilds(discord.Object(id=GUILD_ID))
@bot.tree.command(name="cmds", description="List all commands")
async def cmds(interaction: discord.Interaction):
    commands_list = """
    **📜 Command List:**
    **Points**
    `/pointsadd` - Add points
    `/pointsremove` - Remove points
    `/points` - Check user points
    `/leaderboard` - Show leaderboard

    **Deployments**
    `/startdeploy` - Start deployment timer
    `/stopdeploy` - Stop deployment timer
    `/deploylog` - View deployment logs
    `/cleardeploy` - Clear a user's deployment logs
    `/log` - Log deployment attendees
    `/deployments` - Check deployment count
    `/clearlog` - Clear a user's deployment logs

    **Moderation**
    `/kick` - Kick a user
    `/ban` - Ban a user
    `/timeout` - Timeout a user
    `/purge` - Purge messages
    `/lockdown` - Lock a channel
    `/unlock` - Unlock a channel

    **Misc**
    `/virtus` - Shows Virtus morph channels
    `/416` - Shows 416 morph channels
    """
    await interaction.response.send_message(commands_list)

@app_commands.guilds(discord.Object(id=GUILD_ID))
@bot.tree.command(name="pointsadd", description="Add points to a user")
async def pointsadd(interaction: discord.Interaction, user: discord.User, amount: int):
    if not is_allowed(interaction):
        await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
        return
    total = update_points(user.id, user.name, amount)
    await interaction.response.send_message(f"✅ {amount} points added to {user.name}. Total: {total}", ephemeral=True)
    log_channel = bot.get_channel(POINTS_LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send(f"{amount} awarded to {user.mention}. Total points: {total}.")

@app_commands.guilds(discord.Object(id=GUILD_ID))
@bot.tree.command(name="pointsremove", description="Remove points from a user")
async def pointsremove(interaction: discord.Interaction, user: discord.User, amount: int):
    if not is_allowed(interaction):
        await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
        return
    total = remove_points(user.id, amount)
    await interaction.response.send_message(f"✅ {amount} points removed from {user.name}. Total: {total}", ephemeral=True)
    log_channel = bot.get_channel(POINTS_LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send(f"{amount} points removed from {user.mention}. Total points: {total}.")

@app_commands.guilds(discord.Object(id=GUILD_ID))
@bot.tree.command(name="points", description="Check your points")
async def points(interaction: discord.Interaction, user: discord.Member):
    total = get_points(user.id)
    await interaction.response.send_message(f"{user.mention} has {total} points.", ephemeral=False)

@app_commands.guilds(discord.Object(id=GUILD_ID))
@bot.tree.command(name="leaderboard", description="Show top point holders")
async def leaderboard(interaction: discord.Interaction):
    try:
        all_data = sheet.get_all_records()
        sorted_data = sorted(all_data, key=lambda x: x['Points'], reverse=True)
        embed = discord.Embed(title="📊 Leaderboard", color=discord.Color.gold())
        for i, row in enumerate(sorted_data[:10], start=1):
            embed.add_field(name=f"{i}.", value=f"<@{row['Discord ID']}> - {row['Points']} points", inline=False)
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error loading leaderboard: {e}")

@app_commands.guilds(discord.Object(id=GUILD_ID))
@bot.tree.command(name="startdeploy", description="Start deployment timer")
async def startdeploy(interaction: discord.Interaction):
    deployment_tracker[interaction.user.id] = time.time()
    await interaction.response.send_message(f"⏱️ Deployment started for {interaction.user.mention}.")

@app_commands.guilds(discord.Object(id=GUILD_ID))
@bot.tree.command(name="stopdeploy", description="Stop deployment timer")
async def stopdeploy(interaction: discord.Interaction):
    if interaction.user.id not in deployment_tracker:
        await interaction.response.send_message("❌ No deployment started.")
        return
    start_time = deployment_tracker.pop(interaction.user.id)
    duration = round((time.time() - start_time) / 60, 2)
    activity_sheet.append_row([str(interaction.user.id), interaction.user.name, f"{duration} minutes"])
    await interaction.response.send_message(f"✅ Deployment ended. Duration: {duration} minutes.")

@app_commands.guilds(discord.Object(id=GUILD_ID))
@bot.tree.command(name="deploylog", description="Show deployment log")
async def deploylog(interaction: discord.Interaction, user: discord.User = None):
    target = user or interaction.user
    logs = activity_sheet.get_all_records()
    message = f"Deployment Logs for {target.name}:\n"
    for row in logs:
        if str(row['Discord ID']) == str(target.id):
            message += f"- {row['Deployment Time']}\n"
    await interaction.response.send_message(message)

@app_commands.guilds(discord.Object(id=GUILD_ID))
@bot.tree.command(name="cleardeploy", description="Clear a user's deployment logs")
async def cleardeploy(interaction: discord.Interaction, user: discord.User):
    if not is_allowed(interaction):
        await interaction.response.send_message("Ask a HR or HICOM to do ts for u", ephemeral=True)
        return
    records = activity_sheet.get_all_records()
    updated = [row for row in records if str(row['Discord ID']) != str(user.id)]
    activity_sheet.clear()
    activity_sheet.append_row(["Discord ID", "Name", "Deployment Time"])
    for row in updated:
        activity_sheet.append_row([row['Discord ID'], row['Name'], row['Deployment Time']])
    await interaction.response.send_message(f"{user.name}'s deployment logs has been wiped'.")

#MODERATION
@app_commands.guilds(discord.Object(id=GUILD_ID))
@bot.tree.command(name="kick", description="Kick a user")
async def kick(interaction: discord.Interaction, user: discord.Member, reason: str):
    if not is_allowed(interaction):
        await interaction.response.send_message("why ru trying to kick someone bro ur not HR+.", ephemeral=True)
        return
    await user.kick(reason=reason)
    await interaction.response.send_message(f"{user.name} has been kicked. Reason: {reason}")

@app_commands.guilds(discord.Object(id=GUILD_ID))
@bot.tree.command(name="ban", description="Ban a user")
async def ban(interaction: discord.Interaction, user: discord.Member, reason: str):
    if not is_allowed(interaction):
        await interaction.response.send_message("Ur not special bro u dont got permission for ts", ephemeral=True)
        return
    await user.ban(reason=reason)
    await interaction.response.send_message(f"🔨 {user.name} has been banned. Reason: {reason}")

@app_commands.guilds(discord.Object(id=GUILD_ID))
@bot.tree.command(name="timeout", description="Timeout a member")
@app_commands.describe(member="Member to timeout", minutes="Duration in minutes")
async def timeout(interaction: discord.Interaction, member: discord.Member, minutes: int):
    duration = timedelta(minutes=minutes)
    await member.timeout(duration)
    await interaction.response.send_message(f"⏳ {member.mention} has been timed out for {minutes} minutes.")

@app_commands.guilds(discord.Object(id=GUILD_ID))
@bot.tree.command(name="purge", description="Delete a number of messages")
@app_commands.describe(amount="Number of messages to delete")
async def purge(interaction: discord.Interaction, amount: int):
    await interaction.channel.purge(limit=amount)
    await interaction.response.send_message(f"🧹 Deleted {amount} messages.")
    log_channel = bot.get_channel(AUDIT_LOG_CHANNEL_ID)
    await log_channel.send(f"🧹 {interaction.user.mention} purged {amount} messages in {interaction.channel.mention}")

# Deployment Log

@bot.tree.command(name="log", description="Log deployment attendees.")
@app_commands.describe(
    user1="Attendee 1",
    user2="Attendee 2 (optional)",
    user3="Attendee 3 (optional)",
    user4="Attendee 4 (optional)",
    user5="Attendee 5 (optional)"
)
async def log(
    interaction: discord.Interaction,
    user1: discord.Member,
    user2: Optional[discord.Member] = None,
    user3: Optional[discord.Member] = None,
    user4: Optional[discord.Member] = None,
    user5: Optional[discord.Member] = None,
):
    # Role check
    if not any(role.id in DEPLOYMENT_ROLE for role in interaction.user.roles):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return

    attendees = [user1]
    for user in (user2, user3, user4, user5):
        if user is not None:
            attendees.append(user)

    records = log_sheet.get_all_records()
    id_to_row = {str(row["Discord ID"]): (i + 2, row) for i, row in enumerate(records)}  # Google Sheet rows start at 2
    updated_mentions = []

    for member in attendees:
        member_id = str(member.id)
        if member_id in id_to_row:
            row_num, row = id_to_row[member_id]
            current_count = int(row.get("Deployment Count", 0))
            log_sheet.update_cell(row_num, 3, current_count + 1)
        else:
            log_sheet.append_row([member_id, str(member), 1])
        updated_mentions.append(member.mention)

    if updated_mentions:
        await interaction.response.send_message(f"Logged deployment for: {', '.join(updated_mentions)}")
    else:
        await interaction.response.send_message("No valid members found to log.", ephemeral=True)


@bot.tree.command(name="deployments", description="Check deployment count for yourself or another user.")
@app_commands.describe(user="User to check deployment count for (optional)")
async def deployments(interaction: discord.Interaction, user: Optional[discord.Member] = None):
    target = user or interaction.user
    user_id = str(target.id)
    records = log_sheet.get_all_records()

    for row in records:
        if str(row["Discord ID"]) == user_id:
            await interaction.response.send_message(f"{target.mention} has attended **{row['Deployment Count']}** deployments.")
            return

    await interaction.response.send_message(f"{target.mention} has no deployments logged yet.")

@bot.tree.command(name="clearlog", description="Clear a users deployment log.")
@app_commands.describe(user="The user whose deployment log you want to clear.")
async def clearlog(interaction: discord.Interaction, user: discord.Member):
    if not any(role.id in ALLOWED_ROLES for role in interaction.user.roles):
        await interaction.response.send_message("No perms gang", ephemeral=True)
        return

    records = log_sheet.get_all_records()
    for i, row in enumerate(records, start=2):
        if str(row["Discord ID"]) == str(user.id):
            log_sheet.update_cell(i, 3, 0)
            await interaction.response.send_message(f"Cleared deployment log for {user.mention}.")
            return

    await interaction.response.send_message("User not found", ephemeral=True)

# Ban and unban

@app_commands.guilds(discord.Object(id=GUILD_ID))
@bot.tree.command(name="unban", description="Unban a user")
@app_commands.describe(user_id="ID of the user to unban")
async def unban(interaction: discord.Interaction, user_id: int):
    user = await bot.fetch_user(user_id)
    await interaction.guild.unban(user)
    await interaction.response.send_message(f"✅ Unbanned {user.mention}.")

@app_commands.guilds(discord.Object(id=GUILD_ID))
@bot.tree.command(name="untimeout", description="Remove timeout from a member")
async def untimeout(interaction: discord.Interaction, member: discord.Member):
    await member.timeout(None)
    await interaction.response.send_message(f"✅ Timeout removed from {member.mention}.")

# MISC

@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.guilds(discord.Object(id=GUILD_ID))
@bot.tree.command(name="virtus", description="Access Virtus channels")
async def virtus(interaction: discord.Interaction):
    await interaction.response.send_message(
        "**Virtus Channels:**\n<#1387293873063202958>\n<#1394945387709730868>",)


@app_commands.guilds(discord.Object(id=GUILD_ID))
@bot.tree.command(name="416", description="Access 416 channels")
async def fouronesix(interaction: discord.Interaction):
    await interaction.response.send_message(
        "**416 Channels:**\n<#1394220165926752286>\n<#1394945444936810599>", )

# LOCKDOWN
@app_commands.guilds(discord.Object(id=GUILD_ID))
@bot.tree.command(name="lockdown", description="Lock a channel")
async def lockdown(interaction: discord.Interaction):
    if not is_allowed(interaction):
        await interaction.response.send_message("Sybau bro u dont have permission.", ephemeral=True)
        return
    overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
    overwrite.send_messages = False
    await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
    await interaction.response.send_message("🔒 Channel has been locked.")

@app_commands.guilds(discord.Object(id=GUILD_ID))
@bot.tree.command(name="unlock", description="Unlock a channel")
async def unlock(interaction: discord.Interaction):
    if not is_allowed(interaction):
        await interaction.response.send_message("u dont have perms.", ephemeral=True)
        return
    overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
    overwrite.send_messages = True
    await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
    await interaction.response.send_message("🔓 Channel has been unlocked.")

@app_commands.guilds(discord.Object(id=GUILD_ID))
@bot.tree.command(name="g", description="Send a message to #general-chat")
@app_commands.describe(message="The message to send")
async def g(interaction: discord.Interaction, message: str):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
        return
    channel = bot.get_channel(1248647511913136179)
    await channel.send(message)
    await interaction.response.send_message("✅ Sent to #general-chat.", ephemeral=True)

@app_commands.guilds(discord.Object(id=GUILD_ID))
@bot.tree.command(name="e", description="Event")
@app_commands.describe(message="The message to send")
async def g(interaction: discord.Interaction, message: str):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
        return
    channel = bot.get_channel(1309756614387044352)
    await channel.send(message)
    await interaction.response.send_message("✅ Sent to #events.", ephemeral=True)

@app_commands.guilds(discord.Object(id=GUILD_ID))
@bot.tree.command(name="n", description="Send a message to #major-news")
@app_commands.describe(message="The message to send")
async def n(interaction: discord.Interaction, message: str):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
        return
    channel = bot.get_channel(1309756493314261072)
    await channel.send(message)
    await interaction.response.send_message("✅ Sent to #major-news.", ephemeral=True)

# Flask app for keeping the bot alive
app = Flask('')

@app.route('/')
def home():
    return "I'm alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# keep alive and run the bot

keep_alive()
bot.run(os.environ["DISCORD_BOT_TOKEN"])




