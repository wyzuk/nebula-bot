import discord
from discord.ext import commands
import os, psutil, asyncio, shlex, shutil

TOKEN = os.environ.get('TOKEN', '').strip() 
MY_ID = 1042714088461877288 

TERMINALS = {id: i+1 for i, id in enumerate([
    1464858173822472202, 1464858215224311809, 1464858281376874657, 1464858304550539315,
    1464858320236969984, 1464858336192364634, 1464858351958626576, 1464858374188306649,
    1464858389711421647, 1464858409294631139, 1464858440571813908, 1464858464462569768,
    1464858487354953881, 1464858519592374404, 1464858543684587786, 1464858560386302134,
    1464858578971262996, 1464858596880679075, 1464858615776149625, 1464858635166417017,
    1464858655433294043, 1464858681790300202, 1464858698001289347, 1464858716116357235,
    1464858734332219504
])}

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all(), help_command=None)
active_procs = {} 
nano_sessions = {}

# --- 1. MANAGEMENT & RQ COMMANDS ---

@bot.command()
async def jhlp(ctx):
    if ctx.author.id == MY_ID or ctx.author.guild_permissions.administrator:
        emb = discord.Embed(title="🛸 Nebula Master Control", color=0x00ff00)
        emb.add_field(name="System", value="`!status` - 384GB Check\n`!e` - Kill Bot\n`!reset` - Wipe", inline=False)
        emb.add_field(name="Files", value="`!nano <file>` - Edit\n`!rq`, `!rqadd`, `!rqrmv` - Requirements", inline=False)
        await ctx.send(embed=emb)

@bot.command()
async def status(ctx):
    mem = psutil.virtual_memory()
    await ctx.send(f"🧠 **RAM:** `{mem.used // 1024**2}MB / 384GB` | ⚙️ **CPU:** `{psutil.cpu_percent()}%`")

@bot.command()
async def reset(ctx):
    if ctx.channel.id in TERMINALS:
        t_num = TERMINALS[ctx.channel.id]
        shutil.rmtree(f"term{t_num}", ignore_errors=True)
        os.makedirs(f"term{t_num}", exist_ok=True)
        await ctx.send(f"🧹 **Terminal-{t_num} Wiped.**")

@bot.command()
async def rq(ctx):
    if ctx.channel.id in TERMINALS:
        path = f"term{TERMINALS[ctx.channel.id]}/rq{TERMINALS[ctx.channel.id]}.txt"
        content = open(path).read() if os.path.exists(path) else "Empty."
        await ctx.send(f"📋 **Requirements:**\n```\n{content}\n```")

@bot.command()
async def rqadd(ctx, lib: str):
    if ctx.channel.id in TERMINALS:
        t_num = TERMINALS[ctx.channel.id]
        os.makedirs(f"term{t_num}", exist_ok=True)
        with open(f"term{t_num}/rq{t_num}.txt", "a") as f: f.write(f"\n{lib}")
        await ctx.send(f"➕ Added `{lib}`")

@bot.command()
async def rqrmv(ctx, lib: str):
    if ctx.channel.id in TERMINALS:
        path = f"term{TERMINALS[ctx.channel.id]}/rq{TERMINALS[ctx.channel.id]}.txt"
        if os.path.exists(path):
            lines = open(path).readlines()
            with open(path, "w") as f: [f.write(l) for l in lines if l.strip() != lib]
            await ctx.send(f"➖ Removed `{lib}`")

@bot.command()
async def e(ctx):
    if ctx.channel.id in active_procs:
        active_procs[ctx.channel.id].terminate()
        del active_procs[ctx.channel.id]
        await ctx.send("🧹 **Process Killed.**")

@bot.command()
async def nano(ctx, file: str):
    # Fixed Logic: Ensures extension if none provided, then asks for code
    if "." not in file:
        file = f"{file}.py"
    nano_sessions[ctx.channel.id] = file
    await ctx.send(f"📥 **Preparing `{file}`.** Send your code now.")

# --- 2. CORE LOGIC ---

@bot.event
async def on_message(message):
    if message.author.bot: return
    cid = message.channel.id

    if cid in nano_sessions:
        t_num = TERMINALS.get(cid)
        if t_num:
            with open(f"term{t_num}/{nano_sessions[cid]}", 'w') as f: f.write(message.content.strip('`'))
            await message.channel.send(f"✅ **Saved as `{nano_sessions[cid]}` in T-{t_num}.**")
            del nano_sessions[cid]
        return

    if message.content.startswith('!'):
        await bot.process_commands(message)
        return

    if cid in TERMINALS:
        t_num = TERMINALS[cid]
        t_path = f"term{t_num}"
        os.makedirs(t_path, exist_ok=True)
        try:
            args = shlex.split(message.content)
            # Internal Python Logic to bypass broken /bin/sh
            if args[0] == "ls":
                files = os.listdir(t_path)
                await message.channel.send(f"📂 **Files:** `" + "`, `".join(files) + "`")
            elif args[0] == "mkdir":
                os.makedirs(f"{t_path}/{args[1]}", exist_ok=True)
                await message.channel.send(f"📁 Created `{args[1]}`")
            elif args[0] == "rm":
                target = f"{t_path}/{args[1]}"
                if os.path.isfile(target): os.remove(target)
                else: shutil.rmtree(target)
                await message.channel.send(f"🗑️ Deleted `{args[1]}`")
            elif args[0] in ["python", "python3"]:
                proc = await asyncio.create_subprocess_exec("python3", *args[1:], stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT, cwd=t_path)
                active_procs[cid] = proc
                await message.channel.send(f"🚀 **Son Bot Starting...**")
                async def stream():
                    while True:
                        line = await proc.stdout.readline()
                        if line: await message.channel.send(f"```fix\n{line.decode().strip()}\n```")
                        else: break
                asyncio.create_task(stream())
        except Exception as e: await message.channel.send(f"❌ `{e}`")

@bot.event
async def on_ready():
    print("Nebula V5.7 Online. 384GB Cluster Ready.")

bot.run(TOKEN)
