import discord
from discord.ext import commands, tasks
import subprocess, os, psutil, time, asyncio, shlex
from flask import Flask
from threading import Thread

# --- 1. CONFIGURATION ---
# GITHUB SAFE: This pulls the token from your VPS environment variables
TOKEN = os.environ.get('TOKEN', '').strip() 

ADMIN_ID = 1464867612289663090      
ADMIN_LOG_CH = 1464868612895408200  
DASHBOARD_CH = 1464858968345149551  

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

# --- 2. UTILS ---
def get_size(bytes):
    for unit in ["", "K", "M", "G", "T"]:
        if bytes < 1024: return f"{bytes:.2f}{unit}B"
        bytes /= 1024

async def stream_output(process, channel, t_num):
    while True:
        line = await process.stdout.readline()
        if line:
            clean_line = line.decode().strip()
            if clean_line:
                await channel.send(f"```fix\n[TERM-{t_num}]: {clean_line}\n```")
        else: break
    await channel.send(f"🏁 **Terminal {t_num} process finished.**")

# --- 3. REQ (RQ) COMMANDS ---
@bot.command()
async def rq(ctx):
    if ctx.channel.id in TERMINALS:
        t_num = TERMINALS[ctx.channel.id]
        path = f"term{t_num}/rq{t_num}.txt"
        if not os.path.exists(path): return await ctx.send("📝 Requirement list is empty.")
        with open(path, "r") as f: await ctx.send(f"📋 **T-{t_num} Requirements:**\n```\n{f.read()}\n```")

@bot.command()
async def rqadd(ctx, lib: str):
    if ctx.channel.id in TERMINALS:
        t_num = TERMINALS[ctx.channel.id]
        if not os.path.exists(f"term{t_num}"): os.makedirs(f"term{t_num}")
        with open(f"term{t_num}/rq{t_num}.txt", "a") as f: f.write(f"\n{lib}")
        await ctx.send(f"➕ Added `{lib}` to T-{t_num}.")

@bot.command()
async def rqrmv(ctx, lib: str):
    if ctx.channel.id in TERMINALS:
        t_num = TERMINALS[ctx.channel.id]
        path = f"term{t_num}/rq{t_num}.txt"
        if os.path.exists(path):
            with open(path, "r") as f: lines = f.readlines()
            with open(path, "w") as f: [f.write(l) for l in lines if l.strip() != lib]
            await ctx.send(f"➖ Removed `{lib}`.")

# --- 4. CORE ENGINE ---
@bot.event
async def on_message(message):
    if message.author.bot: return
    cid = message.channel.id
    is_admin = message.author.guild_permissions.administrator or message.author.id == 1042714088461877288

    if cid in TERMINALS:
        t_num = TERMINALS[cid]
        if not (discord.utils.get(message.author.roles, name=f"terminal-{t_num}") or is_admin): return
        t_path = f"term{t_num}"
        if not os.path.exists(t_path): os.makedirs(t_path)

        if cid in nano_sessions:
            fname = nano_sessions[cid]
            if fname == "bot.py" and not is_admin: return await message.channel.send("❌ Access Denied.")
            with open(f"{t_path}/{fname}", 'w') as f: f.write(message.content.strip('`'))
            await message.channel.send(f"📝 `{fname}` saved.")
            del nano_sessions[cid]
            return

        if not message.content.startswith("!"):
            args = shlex.split(message.content)
            try:
                # Shell Bypass for broken /bin/sh
                if args[0] == "ls":
                    files = os.listdir(t_path)
                    await message.channel.send(f"📂 **Files:** `" + "`, `".join(files) + "`" if files else "Empty.")
                elif args[0] in ["python", "python3"]:
                    proc = await asyncio.create_subprocess_exec(*args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=t_path)
                    active_procs[cid] = proc
                    await message.channel.send(f"🚀 **Running Python in T-{t_num}...**")
                    asyncio.create_task(stream_output(proc, message.channel, t_num))
                else:
                    out = subprocess.check_output(args, stderr=subprocess.STDOUT, text=True, cwd=t_path)
                    await message.channel.send(f"```bash\n{out[:1900] or 'Success.'}\n```")
            except Exception as e: await message.channel.send(f"❌ **Error:** `{e}`")

    await bot.process_commands(message)

# --- 5. MANAGEMENT ---
@bot.command()
async def status(ctx):
    mem = psutil.virtual_memory()
    emb = discord.Embed(title="🛰️ Nebula Cluster Status", color=0x00ff00)
    emb.add_field(name="🧠 Memory Usage", value=f"`{get_size(mem.used)} / 384GB`", inline=False)
    emb.add_field(name="⚙️ CPU Load", value=f"`{psutil.cpu_percent()}%`", inline=False)
    await ctx.send(embed=emb)

@bot.command()
async def nano(ctx, file: str):
    if ctx.channel.id in TERMINALS or ctx.author.guild_permissions.administrator:
        nano_sessions[ctx.channel.id] = file
        await ctx.send(f"📥 Send code for `{file}` now.")

@bot.command()
async def e(ctx):
    if ctx.channel.id in active_procs:
        active_procs[ctx.channel.id].terminate()
        await ctx.send("🧹 Process terminated.")

@bot.event
async def on_ready():
    print(f"Nebula V5.2 Live on 384GB Cluster.")

bot.run(TOKEN)
