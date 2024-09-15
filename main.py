import discord
from discord.ext import commands
import yt_dlp
import asyncio
from discord_token import token

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

FFMPEG_OPTIONS = {'options': '-vn','before_options':'-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'}
YDL_OPTIONS = {'format': 'bestaudio', 'noplaylist': True}


class MusicBot(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.queue = []
        self.loop = False
        self.current_song = None

    # PLAY COMMAND
    @commands.hybrid_command(name="play", description="Play a song from YouTube.")
    async def play(self, ctx, *, search):
        voice_channel = ctx.author.voice.channel if ctx.author.voice else None
        if not voice_channel:
            return await ctx.send("You must be in a voice channel.")
        if not ctx.voice_client:
            await voice_channel.connect()
        async with ctx.typing():
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(f"ytsearch:{search}", download=False)
                if 'entries' in info:
                    info = info['entries'][0]
                url = info['url']
                title = info['title']
                self.queue.append((url, title))
                await ctx.send(f'Added to queue: **{title}**')
        if not ctx.voice_client.is_playing():
            await self.play_next(ctx)

    async def play_next(self, ctx):
        if self.queue:
            url, title = self.queue.pop(0)
            self.current_song = (url, title)
            try:
                source = discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS)
                ctx.voice_client.play(source, after=lambda _: self.client.loop.create_task(self.handle_after_play(ctx)))
                await ctx.send(f'Now playing: **{title}**')
            except Exception as e:
                await ctx.send(f"An error occurred while playing: {str(e)}")
        else:
            await ctx.send("The queue is empty.")

    async def handle_after_play(self, ctx):
        if self.loop and self.current_song:
            # Add the current song back to the start of the queue if looping is enabled
            self.queue.insert(0, self.current_song)
        await self.play_next(ctx)

    # SKIP COMMAND
    @commands.hybrid_command(name="skip", description="Skip to the next item in the queue.")
    async def skip(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await ctx.send("Skipped ⏭️")
        else:
            await ctx.send("There is no audio playing.")

    # LEAVE COMMAND
    @commands.hybrid_command(name="leave", description="Disconnect the bot to the voice channel.")
    async def leave(self, ctx):
        if ctx.voice_client:
            await ctx.send("Disconnected 🔌")
            await ctx.voice_client.disconnect()
            self.queue.clear()
        else:
            await ctx.send("I am not in a voice channel.")

    # JOIN COMMAND
    @commands.hybrid_command(name="join", description="Connect the bot to the voice channel.")
    async def join(self, ctx):
        voice_channel = ctx.author.voice.channel if ctx.author.voice else None
        if not voice_channel:
            return await ctx.send("You must be in a voice channel.")
        if not ctx.voice_client:
            await ctx.send("Type **/play** to begin or **/help** for a list of commands.")
            await voice_channel.connect()
        else:
            await ctx.send("I am already in a voice channel.")

    # PAUSE COMMAND
    @commands.hybrid_command(name="pause", description="Pause playback of audio.")
    async def pause(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            await ctx.send("Paused ⏯️")
            ctx.voice_client.pause()
        else:
            await ctx.send("There is no audio playing.")

    # RESUME COMMAND
    @commands.hybrid_command(name="resume", description="Resume playback of audio.")
    async def resume(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_paused():
            await ctx.send("Resumed ⏯️")
            ctx.voice_client.resume()
        else:
            await ctx.send("There is no audio paused.")

    # QUEUE COMMAND
    @commands.hybrid_command(name="queue", description="View the current queue.")
    async def queue(self, ctx):
        if not self.queue:
            await ctx.send("The queue is empty.")
        else:
            queue_list = '\n'.join([f"{i + 1}. {title}" for i, (_, title) in enumerate(self.queue)])
            await ctx.send(f'Current queue:\n\n{queue_list}')

    # LOOP COMMAND
    @commands.hybrid_command(name="loop", description="Loop the current audio.")
    async def loop(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            self.loop = not self.loop
            status = "enabled" if self.loop else "disabled"
            await ctx.send(f"Looping {status} 🔁")
        else:
            await ctx.send("There is no audio playing.")

    @commands.hybrid_command(name="clear", description="Clear the current queue.")
    async def clear(self, ctx):
        if self.queue:
            await ctx.send("Cleared the queue.")
            self.loop = False
            self.queue.clear()
        else:
            await ctx.send("The queue is empty.")

    # HELP COMMAND
    @commands.hybrid_command(name="help", description="View a list of commands.")
    async def help(self, ctx):
        await ctx.send(
            "Here is a list of the commands:\n\n"
            "**/join** - Connect the bot to the voice channel.\n"
            "**/leave** - Disconnect the bot to the voice channel.\n"
            "**/loop** - Loop the current audio.\n"
            "**/pause** - Pause playback of audio.\n"
            "**/play** - Play a song from YouTube.\n"
            "**/queue** - View the current queue.\n"
            "**/resume** - Resume playback of audio.\n"
            "**/skip** - Skip to the next item in the queue.\n"
            "**/clear** - Clear the current queue.\n"
            "**/help** - View a list of commands."
        )


client = commands.Bot(command_prefix="!", intents=intents)
client.remove_command('help')

@client.event
async def on_ready():
    await client.tree.sync()
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="/play"))

async def main():
    await client.add_cog(MusicBot(client))
    await client.start(token)

asyncio.run(main())