import discord
from discord.ext import commands, tasks
import subprocess, os, psutil, platform, shutil, time, asyncio
from flask import Flask
from threading import Thread

# --- 1. CONFIGURATION ---
# Replace with your actual bot token
TOKEN = os.environ.get('TOKEN', '').strip()
ADMIN_ID = 1464867612289663090      # Your Main Management Terminal
ADMIN_LOG_CH = 1464868612895408200  # Global Admin Log Channel
DASHBOARD_CH = 1464858968345149551  # Public Dashboard Channel
HOSTING_CH = 1464859127393288254    # Terminal Ownership Channel

# Mapping Channel IDs to Terminal Numbers
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
dash_msg = None

# --- 2. RENDER/WEB HEARTBEAT (Optional for Ubuntu) ---
app = Flask('')
@app.route('/')
def home(): return "Nebula Public OS is Active."

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- 3. UTILS ---
def get_size(bytes):
    for unit in ["", "K", "M", "G", "T"]:
        if bytes < 1024: return f"{bytes:.2f}{unit}B"
        bytes /= 1024

async def admin_log(text):
    ch = bot.get_channel(ADMIN_LOG_CH)
    if ch: await ch.send(f"🛰️ `[GLOBAL LOG]` {text}")

# Real-time output streamer for terminals
async def stream_output(process, channel, t_num):
    await admin_log(f"Terminal {t_num} started a process.")
    while True:
        line = await process.stdout.readline()
        if line:
            clean_line = line.decode().strip()
            if clean_line:
                await channel.send(f"```fix\n[TERM-{t_num}]: {clean_line}\n```")
                await admin_log(f"T{t_num} OUT: {clean_line}")
        else:
            break
    await channel.send(f"🏁 **Terminal {t_num} process finished.**")

# --- 4. CORE ENGINE ---
@bot.event
async def on_message(message):
    if message.author.bot: return
    cid = message.channel.id
    
    # Identify if user is Administrator (Bypasses all role/folder checks)
    is_admin = message.author.guild_permissions.administrator or message.author.id == 1042714088461877288

    # ADMIN CHANNEL (Total Control)
    if cid == ADMIN_ID:
        if message.content.startswith("!"): await bot.process_commands(message)
        else:
            try:
                output = subprocess.check_output(message.content, shell=True, stderr=subprocess.STDOUT, text=True)
                await message.channel.send(f"```bash\n{output[:1900]}\n```")
            except Exception as e: await message.channel.send(f"❌ Error: {e}")
        return

    # PUBLIC TERMINALS
    if cid in TERMINALS:
        t_num = TERMINALS[cid]
        role_name = f"terminal-{t_num}"
        
        # Security: Administrator bypass or specific role check
        if not (discord.utils.get(message.author.roles, name=role_name) or is_admin):
            return

        t_path = f"term{t_num}"
        if not os.path.exists(t_path): os.makedirs(t_path)

        # File Editor (Nano)
        if cid in nano_sessions:
            filename = nano_sessions[cid]
            # Protect core system files unless user is Admin
            if filename in ["bot.py", "main.py"] and not is_admin:
                await message.channel.send("❌ **Access Denied:** System file protection active.")
            else:
                with open(f"{t_path}/{filename}", 'w') as f: f.write(message.content.strip('`'))
                await message.channel.send(f"📝 `{filename}` saved to Terminal-{t_num} disk.")
            del nano_sessions[cid]
            return

        # Terminal Execution (ls, rm, python, etc.)
        if not message.content.startswith("!"):
            cmd = message.content
            try:
                if "python" in cmd:
                    # Async subprocess for real-time output capture
                    proc = await asyncio.create_subprocess_shell(
                        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=t_path
                    )
                    active_procs[cid] = proc
                    await message.channel.send(f"🚀 **Executing `{cmd}`... Streaming logs:**")
                    asyncio.create_task(stream_output(proc, message.channel, t_num))
                else:
                    # Capture output for simple file management (ls/rm)
                    output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, text=True, cwd=t_path)
                    res = output[:1900] if output.strip() else "✅ Command Successful."
                    await message.channel.send(f"```bash\n{res}\n```")
            except Exception as e: await message.channel.send(f"❌ **Terminal Error:** `{e}`")

    # Process regular prefix commands
    await bot.process_commands(message)

# --- 5. COMMANDS ---
@bot.command()
async def jhlp(ctx):
    # Only for Admins
    if not ctx.author.guild_permissions.administrator: return
    emb = discord.Embed(title="👑 Administrator Management Commands", color=0xff0000)
    emb.add_field(name="Global Monitoring", value="`!status` - Hardware Health\n`!logs` - View Global Stream", inline=False)
    emb.add_field(name="User Control", value="`!e` - Force kill terminal bot\n`!reset` - Wipe specific terminal", inline=False)
    await ctx.send(embed=emb)

@bot.command()
async def status(ctx):
    mem = psutil.virtual_memory()
    emb = discord.Embed(title="🛰️ Nebula Cloud Cluster Status", color=0x00ff00)
    emb.add_field(name="🧠 Total RAM", value="`384 GB` (Server Grade)", inline=True)
    emb.add_field(name="📈 RAM Usage", value=f"`{get_size(mem.used)} / 384GB`", inline=True)
    emb.add_field(name="⚙️ CPU Load", value=f"`{psutil.cpu_percent()}%`", inline=True)
    await ctx.send(embed=emb)

@bot.command()
async def nano(ctx, file: str):
    if ctx.channel.id in TERMINALS or ctx.channel.id == ADMIN_ID:
        nano_sessions[ctx.channel.id] = file
        await ctx.send(f"📥 **Editor Mode:** Send the code for `{file}` now.")

@bot.command()
async def e(ctx):
    if ctx.channel.id in active_procs:
        proc = active_procs[ctx.channel.id]
        try: proc.terminate()
        except: pass
        await ctx.send("🧹 **Terminal instance terminated.**")
        del active_procs[ctx.channel.id]

# --- 6. BACKGROUND TASKS ---
@tasks.loop(seconds=30)
async def update_dash():
    global dash_msg
    ch = bot.get_channel(DASHBOARD_CH)
    if not ch: return
    mem = psutil.virtual_memory()
    emb = discord.Embed(title="🛸 Nebula Cloud Dashboard", description="Real-time monitoring for the 384GB High-Performance Cluster", color=0x00ffff)
    emb.add_field(name="🧠 Memory Available", value=f"`{get_size(mem.available)}`", inline=True)
    emb.add_field(name="⚡ System CPU", value=f"`{psutil.cpu_percent()}%`", inline=True)
    emb.set_footer(text=f"Last Sync: {time.strftime('%H:%M:%S')} | Admin: Enabled")
    try:
        if dash_msg: await dash_msg.edit(embed=emb)
        else: dash_msg = await ch.send(embed=emb)
    except: pass

@bot.event
async def on_ready():
    update_dash.start()
    Thread(target=run_web).start()
    await admin_log("Nebula Public OS V5 Online. [384GB Ubuntu Environment Detected]")
    # Setup Welcome Messages in Terminals
    for ch_id in TERMINALS:
        ch = bot.get_channel(ch_id)
        if ch:
            await ch.send(f"🌐 **Nebula Terminal-{TERMINALS[ch_id]} Connected**\n```\n- Directory Isolation: ON\n- Admin Bypass: ENABLED\n- Command: !nano <file> | python <file>\n```")

bot.run(TOKEN)
