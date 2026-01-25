import discord
from discord.ext import commands
import subprocess, os, psutil, time, asyncio, shlex

# --- 1. CONFIGURATION ---
TOKEN = os.environ.get('TOKEN', '').strip() 

# I've updated this to YOUR ID based on your previous logs
MY_ID = 1042714088461877288 
ADMIN_ID = 1464867612289663090      
ADMIN_LOG_CH = 1464868612895408200  

TERMINALS = {
    1464858173822472202: 1, 1464858215224311809: 2, 1464858281376874657: 3,
    1464858304550539315: 4, 1464858320236969984: 5, 1464858336192364634: 6,
    1464858351958626576: 7, 1464858374188306649: 8, 1464858389711421647: 9,
    1464858409294631139: 10, 1464858440571813908: 11, 1464858464462569768: 12,
    1464858487354953881: 13, 1464858519592374404: 14, 1464858543684587786: 15,
    1464858560386302134: 16, 1464858578971262996: 17, 1464858596880679075: 18,
    1464858615776149625: 19, 1464858635166417017: 20, 1464858655433294043: 21,
    1464858681790300202: 22, 1464858698001289347: 23, 1464858716116357235: 24,
    1464858734332219504: 25
}

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all(), help_command=None)
active_procs = {} 
nano_sessions = {}

# --- 2. COMMANDS (RQ, HELP, KILL) ---

@bot.command()
async def jhlp(ctx):
    # Global Admin Check
    if ctx.author.id == MY_ID or ctx.author.guild_permissions.administrator:
        emb = discord.Embed(title="👑 Nebula Admin Panel", color=0xff0000)
        emb.add_field(name="Commands", value="`!status` - RAM/CPU\n`!e` - Kill current terminal bot\n`!nano <file>` - Edit files", inline=False)
        await ctx.send(embed=emb)

@bot.command()
async def e(ctx):
    if ctx.channel.id in active_procs:
        proc = active_procs[ctx.channel.id]
        try:
            proc.terminate()
            await ctx.send("🧹 **Son Bot Terminated.**")
        except:
            await ctx.send("❌ Failed to kill process.")
        del active_procs[ctx.channel.id]
    else:
        await ctx.send("❓ No active process found in this terminal.")

@bot.command()
async def rq(ctx):
    if ctx.channel.id in TERMINALS:
        t_num = TERMINALS[ctx.channel.id]
        path = f"term{t_num}/rq{t_num}.txt"
        if not os.path.exists(path): return await ctx.send("📝 `rq.txt` is empty.")
        with open(path, "r") as f: await ctx.send(f"📋 **T-{t_num} Requirements:**\n```\n{f.read()}\n```")

@bot.command()
async def rqadd(ctx, lib: str):
    if ctx.channel.id in TERMINALS:
        t_num = TERMINALS[ctx.channel.id]
        if not os.path.exists(f"term{t_num}"): os.makedirs(f"term{t_num}")
        with open(f"term{t_num}/rq{t_num}.txt", "a") as f: f.write(f"\n{lib}")
        await ctx.send(f"➕ Added `{lib}` to T-{t_num}.")

# --- 3. THE SHELL-BYPASS ENGINE ---

@bot.event
async def on_message(message):
    if message.author.bot: return
    cid = message.channel.id
    is_admin = message.author.guild_permissions.administrator or message.author.id == MY_ID

    if cid in TERMINALS:
        t_num = TERMINALS[cid]
        if not (discord.utils.get(message.author.roles, name=f"terminal-{t_num}") or is_admin): return
        t_path = f"term{t_num}"
        if not os.path.exists(t_path): os.makedirs(t_path)

        if cid in nano_sessions:
            fname = nano_sessions[cid]
            with open(f"{t_path}/{fname}", 'w') as f: f.write(message.content.strip('`'))
            await message.channel.send(f"📝 `{fname}` saved.")
            del nano_sessions[cid]
            return

        if not message.content.startswith("!"):
            args = shlex.split(message.content)
            try:
                # FIXED: Force use of python3 and bypass broken /bin/sh
                if args[0] in ["python", "python3"]:
                    # We use create_subprocess_exec to avoid the broken shell
                    proc = await asyncio.create_subprocess_exec(
                        "python3", *args[1:], 
                        stdout=asyncio.subprocess.PIPE, 
                        stderr=asyncio.subprocess.STDOUT, 
                        cwd=t_path
                    )
                    active_procs[cid] = proc
                    await message.channel.send(f"🚀 **Son Bot Starting in T-{t_num}...**")
                    
                    # Log streaming
                    async def stream():
                        while True:
                            line = await proc.stdout.readline()
                            if line:
                                await message.channel.send(f"```fix\n[LOG]: {line.decode().strip()}\n```")
                            else: break
                        await message.channel.send("🏁 **Process Finished.**")
                    
                    asyncio.create_task(stream())
                else:
                    # Internal LS for broken shell
                    if args[0] == "ls":
                        files = os.listdir(t_path)
                        await message.channel.send(f"📂 **T-{t_num} Files:** `" + "`, `".join(files) + "`" if files else "Empty.")
            except Exception as e: await message.channel.send(f"❌ **System Error:** `{e}`")

    await bot.process_commands(message)

@bot.event
async def on_ready():
    print(f"Nebula V5.3 Live. 384GB Cluster Ready.")

bot.run(TOKEN)
