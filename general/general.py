import discord
from discord.ext import commands
import random
from urllib.parse import quote_plus
from enum import Enum
from .utils.chat_formatting import *
from .utils.chat_formatting import escape_mass_mentions, italics, pagify
from random import randint
from random import choice
from random import choice as randchoice
import datetime
from __main__ import send_cmd_help
import re
import urllib
import time
import aiohttp
from .utils import checks
import asyncio
from cogs.utils.dataIO import dataIO
import io, os
from .utils.dataIO import fileIO
import logging


settings = {"POLL_DURATION" : 180}


class RPS(Enum):
    rock     = "\N{MOYAI}"
    paper    = "\N{PAGE FACING UP}"
    scissors = "\N{BLACK SCISSORS}"


JSON = 'data/away/away.json'


class RPSParser:
    def __init__(self, argument):
        argument = argument.lower()
        if argument == "rock":
            self.choice = RPS.rock
        elif argument == "paper":
            self.choice = RPS.paper
        elif argument == "scissors":
            self.choice = RPS.scissors
        else:
            raise


class General:
    """General commands."""

    def __init__(self, bot):
        self.bot = bot
        self.data = dataIO.load_json(JSON)
        self.stopwatches = {}
        self.settings = 'data/youtube/settings.json'
        self.youtube_regex = (
          r'(https?://)?(www\.)?'
          '(youtube|youtu|youtube-nocookie)\.(com|be)/'
          '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')

        self.settings_file = 'data/weather/weather.json'
        self.ball = ["Rn, yes", "It is certain", "It is decidedly so🤔", "Most likely👍", "Outlook good👍",
                     "Signs point to yes👍", "Without a doubt👍", "Yes👍", "Yes – definitely :P", "You may rely on it👍", "❌Reply hazy, try again❌",
                     "Ask again later🤔", "Better not tell you now", "Cannot predict now🤔", "Concentrate and ask again🤔",
                     "Don't count on it🤔", "My reply is no", "My sources say no", "Outlook not so good", "Very doubtful🤔"]
        self.poll_sessions = []

    async def listener(self, message):
        if not message.channel.is_private and self.bot.user.id != message.author.id:
            server = message.server
            channel = message.channel
            author = message.author
            ts = message.timestamp
            filename = 'data/seen/{}/{}.json'.format(server.id, author.id)
            if not os.path.exists('data/seen/{}'.format(server.id)):
                os.makedirs('data/seen/{}'.format(server.id))
            data = {}
            data['TIMESTAMP'] = '{} {}:{}:{}'.format(ts.date(), ts.hour, ts.minute, ts.second)
            data['MESSAGE'] = message.clean_content
            data['CHANNEL'] = channel.mention
            dataIO.save_json(filename, data)

    async def _get_local_time(self, lat, lng):
        settings = dataIO.load_json(self.settings_file)
        if 'TIME_API_KEY' in settings:
            api_key = settings['TIME_API_KEY']
            if api_key != '':
                payload = {'format': 'json', 'key': api_key, 'by': 'position', 'lat': lat, 'lng': lng}
                url = 'http://api.timezonedb.com/v2/get-time-zone?'
                headers = {'user-agent': 'Red-cog/1.0'}
                conn = aiohttp.TCPConnector(verify_ssl=False)
                session = aiohttp.ClientSession(connector=conn)
                async with session.get(url, params=payload, headers=headers) as r:
                    parse = await r.json()
                session.close()
                if parse['status'] == 'OK':
                    return datetime.datetime.fromtimestamp(int(parse['timestamp'])-7200).strftime('%Y-%m-%d %H:%M')
        return

    async def listener(self, message):
        if not message.channel.is_private:
            if message.author.id != self.bot.user.id:
                server_id = message.server.id
                data = dataIO.load_json(self.settings)
                if server_id not in data:
                    enable_delete = False
                    enable_meta = False
                    enable_url = False
                else:
                    enable_delete = data[server_id]['ENABLE_DELETE']
                    enable_meta = data[server_id]['ENABLE_META']
                    enable_url = data[server_id]['ENABLE_URL']
                if enable_meta:
                    url = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', message.content)
                    if url:
                        is_youtube_link = re.match(self.youtube_regex, url[0])
                        if is_youtube_link:
                            yt_url = "http://www.youtube.com/oembed?url={0}&format=json".format(url[0])
                            metadata = await self.get_json(yt_url)
                            if enable_url:
                                msg = '**Title:** _{}_\n**Uploader:** _{}_\n_YouTube url by {}_\n\n{}'.format(metadata['title'], metadata['author_name'], message.author.name, url[0])
                                if enable_delete:
                                    try:
                                        await self.bot.delete_message(message)
                                    except:
                                        pass
                            else:
                                if enable_url:
                                    x = '\n_YouTube url by {}_'.format(message.author.name)
                                else:
                                    x = ''
                                msg = '**Title:** _{}_\n**Uploader:** _{}_{}'.format(metadata['title'], metadata['author_name'], x)
                            await self.bot.send_message(message.channel, msg)

    async def listener(self, message):
        tmp = {}
        for mention in message.mentions:
            tmp[mention] = True
        if message.author.id != self.bot.user.id:
            for author in tmp:
                if author.id in self.data:
                    avatar = author.avatar_url if author.avatar else author.default_avatar_url
                    if self.data[author.id]['MESSAGE']:
                        em = discord.Embed(title=self.data[author.id]['MESSAGE'], color=discord.Color.orange())
                        em.set_author(name='{}\'s currently away And Says ↓⇓⟱'.format(author.display_name), icon_url=avatar)
                    else:
                        em = discord.Embed(color=discord.Color.purple())
                        em.set_author(name='{} is currently away'.format(author.display_name), icon_url=avatar)
                    await self.bot.send_message(message.channel, embed=em)

    @commands.command(pass_context=True, name="away", aliases=["afk"])
    async def _away(self, context, *message: str):
        """Tell the bot you're away or back."""
        author = context.message.author
        if author.id in self.data:
            del self.data[author.id]
            em = discord.Embed(title='Welcome back :space_invader: :D.', color=discord.Color.purple())
        else:
            self.data[context.message.author.id] = {}
            if len(str(message)) < 256:
                self.data[context.message.author.id]['MESSAGE'] = ' '.join(context.message.clean_content.split()[1:])
            else:
                self.data[context.message.author.id]['MESSAGE'] = True
            em = discord.Embed(title='__You\'re now set as away__ :wave: ,***Get out of here!*** :point_right:  :door: .', color=discord.Color.purple())
        dataIO.save_json(JSON, self.data)
        await self.bot.send_message(context.message.channel, embed=em)

    async def get_song_metadata(self, song_url):
        """
        Returns JSON object containing metadata about the song.
        """

        is_youtube_link = re.match(self.youtube_regex, song_url)

        if is_youtube_link:
            url = "http://www.youtube.com/oembed?url={0}&format=json".format(song_url)
            result = await self.get_json(url)
        else:
            result = {"title": "A song "}
        return result

    async def get_json(self, url):
        """
        Returns the JSON from an URL.
        Expects the url to be valid and return a JSON object.
        """
        async with aiohttp.get(url) as r:
            result = await r.json()
        return result

    @commands.command(pass_context=True, name='youtube', no_pm=True)
    async def _youtube(self, context, *, query: str):
        """Search on Youtube"""
        try:
            url = 'https://www.youtube.com/results?'
            payload = {'search_query': " ".join(query), 'hl': 'en'}
            headers = {'user-agent': 'Red-cog/1.0'}
            conn = aiohttp.TCPConnector(verify_ssl=False)
            session = aiohttp.ClientSession(connector=conn)
            async with session.get(url, params=payload, headers=headers) as r:
                result = await r.text()
            session.close()
            yt_find = re.findall(r'href=\"\/watch\?v=(.{11})', result)
            url = 'https://www.youtube.com/watch?v={}'.format(yt_find[0])
            metadata = await self.get_song_metadata(url)
            em = discord.Embed(title=metadata['author_name'], color=discord.Color.purple(), url=metadata['author_url'])
            em.set_author(name=metadata['title'], url=url)
            em.set_image(url=metadata['thumbnail_url'])
            # em.video.url = url
            # em.video.width = 480
            # em.video.height = 270
            await self.bot.say(embed=em)
        except Exception as e:
            message = 'Something went terribly wrong! [{}]'.format(e)
            await self.bot.say(message)

    @commands.group(pass_context=True, name='youtubetoggle', aliases=['ytoggle'])
    @checks.mod_or_permissions(administrator=True)
    async def _youtubetoggle(self, context):
        """
        Toggle metadata and preview features
        """
        data = dataIO.load_json(self.settings)
        server_id = context.message.server.id
        if server_id not in data:
            data[server_id] = {}
            data[server_id]['ENABLE_URL'] = False
            data[server_id]['ENABLE_DELETE'] = False
            data[server_id]['ENABLE_META'] = False
            dataIO.save_json(self.settings, data)
        if context.invoked_subcommand is None:
            await send_cmd_help(context)

    @_youtubetoggle.command(pass_context=True, name='url')
    async def _url(self, context):
        """
        Toggle showing url
        """
        data = dataIO.load_json(self.settings)
        server_id = context.message.server.id
        if data[server_id]['ENABLE_URL'] is False:
            data[server_id]['ENABLE_URL'] = True
            message = 'URL now enabled'
        elif data[server_id]['ENABLE_URL'] is True:
            data[server_id]['ENABLE_URL'] = False
            message = 'URL now disabled'
        else:
            pass
        dataIO.save_json(self.settings, data)
        await self.bot.say(message)

    @_youtubetoggle.command(pass_context=True, name='meta')
    async def _meta(self, context):
        """
        Toggle showing metadata
        """
        data = dataIO.load_json(self.settings)
        server_id = context.message.server.id
        if data[server_id]['ENABLE_META'] is False:
            data[server_id]['ENABLE_META'] = True
            message = 'Metadata now enabled'
        elif data[server_id]['ENABLE_META'] is True:
            data[server_id]['ENABLE_META'] = False
            message = 'Metadata now disabled'
        else:
            pass
        dataIO.save_json(self.settings, data)
        await self.bot.say('`{}`'.format(message))

    @_youtubetoggle.command(pass_context=True, name='delete')
    async def _delete(self, context):
        """
        Toggle deleting message
        """
        data = dataIO.load_json(self.settings)
        server_id = context.message.server.id
        if data[server_id]['ENABLE_DELETE'] is False:
            data[server_id]['ENABLE_DELETE'] = True
            message = 'Delete now enabled'
        elif data[server_id]['ENABLE_DELETE'] is True:
            data[server_id]['ENABLE_DELETE'] = False
            message = 'Delete now disabled'
        else:
            pass
        dataIO.save_json(self.settings, data)
        await self.bot.say('`{}`'.format(message))

    @commands.command(pass_context=True, name='weather', aliases=['we'])
    async def _weather(self, context, *arguments: str):
        """Get the weather!"""
        settings = dataIO.load_json(self.settings_file)
        api_key = settings['WEATHER_API_KEY']
        if len(arguments) == 0:
            message = 'No location provided.'
        elif api_key != '':
            try:
                payload = {'q': " ".join(arguments), 'appid': api_key}
                url = 'http://api.openweathermap.org/data/2.5/weather?'
                headers = {'user-agent': 'Red-cog/1.0'}
                conn = aiohttp.TCPConnector(verify_ssl=False)
                session = aiohttp.ClientSession(connector=conn)
                async with session.get(url, params=payload, headers=headers) as r:
                    parse = await r.json()
                session.close()
                lat = parse['coord']['lat']
                lng = parse['coord']['lon']
                local_time = await self._get_local_time(lat, lng)
                celcius = round(int(parse['main']['temp'])-273)+1
                fahrenheit = round(int(parse['main']['temp'])*9/5-459)+2
                temperature = '{0} Celsius / {1} Fahrenheit'.format(celcius, fahrenheit)
                humidity = str(parse['main']['humidity']) + '%'
                pressure = str(parse['main']['pressure']) + ' hPa'
                wind_kmh = str(round(parse['wind']['speed'] * 3.6)) + ' km/h'
                wind_mph = str(round(parse['wind']['speed'] * 2.23694)) + ' mph'
                clouds = parse['weather'][0]['description'].title()
                icon = parse['weather'][0]['icon']
                name = parse['name'] + ', ' + parse['sys']['country']
                city_id = parse['id']
                em = discord.Embed(title='Weather in :earth_americas: {} - {}'.format(name, local_time), color=discord.Color.blue(), description='\a\n', url='https://openweathermap.org/city/{}'.format(city_id))
                em.add_field(name=' :cloud: **Conditions**', value=clouds)
                em.add_field(name=':thermometer: **Temperature**', value=temperature)
                em.add_field(name=' :dash: **Wind**', value='{} / {}'.format(wind_kmh, wind_mph))
                em.add_field(name=' :compression: **Pressure**', value=pressure)
                em.add_field(name=' :sweat: **Humidity**', value=humidity)
                em.set_thumbnail(url='https://openweathermap.org/img/w/{}.png'.format(icon))
                em.add_field(name='\a', value='\a')
                em.add_field(name='\a', value='\a')
                em.set_footer(text='Weather data provided by OpenWeatherMap', icon_url='http://openweathermap.org/themes/openweathermap/assets/vendor/owm/img/icons/logo_16x16.png')
                await self.bot.say(embed=em)
            except KeyError:
                message = 'Location not found.'
                await self.bot.say('```{}```'.format(message))
        else:
            message = 'No API key set. Get one at http://openweathermap.org/'
            await self.bot.say('```{}```'.format(message))

    @commands.command(pass_context=True, name='weatherkey')
    @checks.is_owner()
    async def _weatherkey(self, context, key: str):
        """Acquire a key from  http://openweathermap.org/"""
        settings = dataIO.load_json(self.settings_file)
        settings['WEATHER_API_KEY'] = key
        dataIO.save_json(self.settings_file, settings)

    @commands.command(pass_context=True, name='timekey')
    @checks.is_owner()
    async def _timekey(self, context, key: str):
        """Acquire a key from https://timezonedb.com/api"""
        settings = dataIO.load_json(self.settings_file)
        settings['TIME_API_KEY'] = key
        dataIO.save_json(self.settings_file, settings)

    @commands.command()
    async def lenny(self):
        """This does stuff( ͡° ͜ʖ ͡°)!"""

        await self.bot.say("( ͡° ͜ʖ ͡°)")
    @commands.command()
    async def bangers(self):
        """Dangerous's playlist"""

        await self.bot.say(" Heres the playlist enjoy the tunes :musical_note: https://www.youtube.com/playlist?list=PL42LCVbTlLSywDEpoLDWdDdjZDVgNsD5A :musical_note: ")

    @commands.command(pass_context=True, no_pm=True, name='seen')
    async def _seen(self, context, username: discord.Member):
        '''seen <@username>'''
        server = context.message.server
        author = username
        filename = 'data/seen/{}/{}.json'.format(server.id, author.id)
        if dataIO.is_valid_json(filename):
            data = dataIO.load_json(filename)
            ts = data['TIMESTAMP']
            last_message = data['MESSAGE']
            channel = data['CHANNEL']
            em = discord.Embed(description='\a\n{}'.format(last_message), color=discord.Color.green())
            avatar = author.avatar_url if author.avatar else author.default_avatar_url
            em.set_author(name='{} was last seen on {} UTC'.format(author.display_name, ts), icon_url=avatar)
            em.add_field(name='\a', value='**Channel:** {}'.format(channel))
            await self.bot.say(embed=em)
        else:
            message = 'I haven\'t seen {} yet.'.format(author.display_name)
            await self.bot.say('{}'.format(message))

    @commands.command(pass_context=True)
    async def emoji(self, ctx, name: str):
        """Send a large custom emoji. 
        Bot must be in the server with the emoji"""
        for x in list(self.bot.get_all_emojis()):
            if x.name.lower() == name.lower():
                fdir ="data/moji/" + x.server.name
                fp = fdir + "/{0.name}.png".format(x)
                if not os.path.exists(fdir):
                    os.mkdir(fdir)
                if not os.path.isfile(fp):
                    async with aiohttp.get(x.url) as r:
                        img_bytes = await r.read()
                        img = io.BytesIO(img_bytes)
                        with open(fp, 'wb') as o:
                            o.write(img.read())
                        o.close()

#You can uncomment this line if you want c: 
                #await self.bot.delete_message(ctx.message)
                return await self.bot.send_file(ctx.message.channel, fp)

    @commands.group(pass_context=True)
    async def moji(self, ctx):
        """Various emoji operations"""
        if ctx.invoked_subcommand is None:
            return await send_cmd_help(ctx)

    @moji.command(pass_context=True)
    async def list(self, ctx, server: int = None):
        """List all available custom emoji"""
        server = server
        servers = list(self.bot.servers)
        if server is None:
            msg = "``` Available servers:"
            for x in servers:
                msg += "\n\t" + str(servers.index(x)) + ("- {0.name}".format(x))
            await self.bot.say(msg + "```")
        else:
            msg = "```Emojis for {0.name}".format(servers[server])
            for x in list(servers[server].emojis):
                msg += "\n\t" + str(x.name)
            await self.bot.say(msg + "```")

    @commands.command()
    async def penis(self, user : discord.Member):
        """Detects user's penis length
        This is 100% accurate."""
        if user.id == "187570149207834624":
            await self.bot.say("Dis penis too long 2 measure ( ͡° ͜ʖ ͡°)\n\nJk he has a micro pp")
            return

        random.seed(user.id)
        p = "8" + "="*random.randint(0, 50) + "D"
        await self.bot.say("Size: " + p)


    @commands.command(pass_context=True)
    async def quote(self, ctx, message_id = None):
        """Quotes a Message. If not specified, I will pick one for you"""
        if message_id is None:
            async for m in self.bot.logs_from(ctx.message.channel, limit=500):
                msg = m
        else:
            msg = await self.bot.get_message(ctx.message.channel, id = str(message_id))
        owner = msg.author.name+"#"+msg.author.discriminator+" ("+msg.id+")" 
        a = discord.Embed()
        a.description = msg.content
        avatar = msg.author.default_avatar_url if not msg.author.avatar else msg.author.avatar_url
        a.set_author(name=owner, icon_url=avatar)
        a.set_footer(text="Msg sent at ")
        a.timestamp = msg.timestamp
        a.colour = discord.Color.purple()
        await self.bot.send_message(msg.channel, embed = a)

    @commands.command(pass_context=True, aliases=["pick"])
    async def choose(self, ctx, *choices):
        """Chooses between multiple choices.
        To denote multiple choices, you should use double quotes.
        """
        channel = ctx.message.channel
        choices = [escape_mass_mentions(choice) for choice in choices]
        if len(choices) < 2:
            em = discord.Embed(title=':no_good: ***Not enough choices to pick from.***', color=discord.Color.purple())
        else:
            await self.bot.send_typing(channel)
            em = discord.Embed(title=(randchoice(choices)), color=discord.Color.purple())
        await self.bot.send_message(channel, embed = em)

    @commands.command(pass_context=True)
    async def ping(self,ctx):
        """Get the ping time fam"""
        channel = ctx.message.channel
        user = ctx.message.author
        colour = ''.join([randchoice('0123456789ABCDEF') for x in range(6)])
        colour = int(colour, 16)
        t1 = time.perf_counter()
        await self.bot.send_typing(channel)
        t2 = time.perf_counter()
        if user.nick is None:
            user.nick=user.name
        em = discord.Embed(description=":ping_pong:\n\n***{}ms Latency Detected :robot:***".format(round((t2-t1)*1000)), color=discord.Color.purple())
        em.set_thumbnail(url=self.bot.user.avatar_url)

        await self.bot.say(embed=em)
    @commands.command(pass_context=True)
    async def test(self, message):
        pingtime = time.time()
        pingms = await self.bot.say("pinging server...")
        ping = time.time() - pingtime
        await self.bot.edit_message(pingms, "It took **%.01f** secs" % (ping) + " to ping.")

    @commands.command(pass_context=True)
    async def flip(self, ctx, user : discord.Member=None):
        """Flips a coin... or a user.
        Defaults to coin.
        """
        if user != None:
            msg = ""
            if user.id == self.bot.user.id:
                user = ctx.message.author
                msg = "Nice try. You think this is funny? How about *this* instead:\n\n"
            char = "abcdefghijklmnopqrstuvwxyz"
            tran = "ɐqɔpǝɟƃɥᴉɾʞlɯuodbɹsʇnʌʍxʎz"
            table = str.maketrans(char, tran)
            name = user.display_name.translate(table)
            char = char.upper()
            tran = "∀qƆpƎℲפHIſʞ˥WNOԀQᴚS┴∩ΛMX⅄Z"
            table = str.maketrans(char, tran)
            name = name.translate(table)
            await self.bot.say(msg + "(╯°□°）╯︵ " + name[::-1])
        else:
            await self.bot.say("*flips a coin and... " + choice(["HEADS!*", "TAILS!*"]))

    @commands.command(pass_context=True, name='wikipedia', aliases=['wiki'])
    async def _wikipedia(self, context, *, query: str):
        """
        Get information from Wikipedia
        """
        try:
            url = 'https://en.wikipedia.org/w/api.php?'
            payload = {}
            payload['action'] = 'query'
            payload['format'] = 'json'
            payload['prop'] = 'extracts'
            payload['titles'] = ''.join(query).replace(' ', '_')
            payload['exsentences'] = '5'
            payload['redirects'] = '1'
            payload['explaintext'] = '1'
            headers = {'user-agent': 'Red-cog/1.0'}
            conn = aiohttp.TCPConnector(verify_ssl=False)
            session = aiohttp.ClientSession(connector=conn)
            async with session.get(url, params=payload, headers=headers) as r:
                result = await r.json()
            session.close()
            if '-1' not in result['query']['pages']:
                for page in result['query']['pages']:
                    title = result['query']['pages'][page]['title']
                    description = result['query']['pages'][page]['extract'].replace('\n', '\n\n')
                em = discord.Embed(title='Wikipedia: {}'.format(title), description='\a\n{}...\n\a'.format(description[:-3]), color=discord.Color.blue(), url='https://en.wikipedia.org/wiki/{}'.format(title.replace(' ', '_')))
                em.set_footer(text='Information provided by Wikpedia', icon_url='https://cdn.discordapp.com/attachments/269293047962009602/271785805020659713/1122px-Wikipedia-logo-v2.png')
                em.set_thumbnail(url='https://cdn.discordapp.com/attachments/269293047962009602/271785829142102017/250px-Wikipedia-logo-v2-en.png')
                await self.bot.say(embed=em)
            else:
                message = 'I\'m sorry, I can\'t find {}'.format(''.join(query))
                await self.bot.say('```{}```'.format(message))
        except Exception as e:
            message = 'Something went terribly wrong! [{}]'.format(e)
            await self.bot.say('```{}```'.format(message))

    @commands.command(name="8ball", aliases=["8"], pass_context=True)
    async def _8ball(self, ctx, *, question : str):
        """Ask DMX a question :P"""
        em = discord.Embed(title=question, color=ctx.message.author.color)
        em.set_author(name=ctx.message.author.name, icon_url=ctx.message.author.avatar_url)
        em.set_footer(text=randchoice(self.ball), icon_url='https://images-ext-1.discordapp.net/eyJ1cmwiOiJodHRwOi8vY29jaGlzZWJpbGxpYXJkcy5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMTUvMTAvOGJhbGwucG5nIn0.Zd5xXVHeFbamUjFRxvcv1yAJ9pM')
        await self.bot.say(embed=em)
    @commands.command(pass_context=True, no_pm=True, aliases=["gsinv"])
    async def gsinvite(self, ctx):
        """Get a invite to the current server"""

        colour = ''.join([randchoice('0123456789ABCDEF') for x in range(6)])
        colour = int(colour, 16)

        try:
            invite = await self.bot.create_invite(ctx.message.server)
        except:
            await self.bot.say("I do not have the `Create Instant Invite` Permission")
            return

        server = ctx.message.server

        randnum = randint(1, 10)
        empty = u"\u2063"
        emptyrand = empty * randnum

        data = discord.Embed(
            colour=discord.Colour(value=colour))
        data.add_field(name=server.name, value=invite, inline=False)

        if server.icon_url:
            data.set_thumbnail(url=server.icon_url)

        try:
            await self.bot.say(emptyrand, embed=data)
        except:
            await self.bot.say("I need the `Embed links` permission "
                               "to send this")


    @commands.command(pass_context=True, hidden = True, no_pm=True)
    async def pwincess(self, ctx):
        """Command special for pwincess <3"""
        user = ctx.message.author
        if user.id == "105899177401180160" or user.id == "187570149207834624":
            await self.bot.say(":two_hearts: <@105899177401180160> is my master, waifu and goddess. :heart_eyes: :heart:️ :ok_hand: :fire:️")
            return
        else:
            await self.bot.reply(":x: Sorry i only Reply to my master waifu goddess Pwincess :stuck_out_tongue:")

    @commands.command(name = "google", aliases=["g"], pass_context=True, no_pm=True)
    @commands.cooldown(5, 60, commands.BucketType.user)
    async def _google(self, ctx, text):
        """Its google, you search with it.
        Example: google A french pug
        Special search options are available; Image, Images, Maps
        Example: google image You know, for kids! > Returns first image"""
        search_type = ctx.message.content[len(ctx.prefix+ctx.command.name)+1:].lower().split(" ")
        option = {'User-Agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.1'}
        regex = [",\"ou\":\"([^`]*?)\"", "<h3 class=\"r\"><a href=\"\/url\?url=([^`]*?)&amp;", "<h3 class=\"r\"><a href=\"([^`]*?)\""]

        #Start of Image
        if search_type[0] == "image":
            search_valid = str(ctx.message.content[len(ctx.prefix+ctx.command.name)+1:].lower())
            if search_valid == "image":
                await self.bot.say(":neutralFace: Please ***actually search something*** :/")
            else:
                uri = "https://www.google.com/search?tbm=isch&tbs=isz:m&q="
                quary = str(ctx.message.content[len(ctx.prefix+ctx.command.name)+7:].lower())
                encode = urllib.parse.quote_plus(quary,encoding='utf-8',errors='replace')
                uir = uri+encode

                async with aiohttp.get(uir, headers = option) as resp:
                    test = await resp.content.read()
                    unicoded = test.decode("unicode_escape")
                    query_find = re.findall(regex[0], unicoded)
                    try:
                        url = query_find[0]
                        await self.bot.say(url)
                    except IndexError:
                        await self.bot.say(":interrobang: Your search yielded no results.")
            #End of Image
        #Start of Image random
        elif search_type[0] == "images":
            search_valid = str(ctx.message.content[len(ctx.prefix+ctx.command.name)+1:].lower())
            if search_valid == "image":
                await self.bot.say(":neutralFace: Please ***actually search something*** :/")
            else:
                uri = "https://www.google.com/search?tbm=isch&tbs=isz:m&q="
                quary = str(ctx.message.content[len(ctx.prefix+ctx.command.name)+7:].lower())
                encode = urllib.parse.quote_plus(quary,encoding='utf-8',errors='replace')
                uir = uri+encode
                async with aiohttp.get(uir, headers = option) as resp:
                    test = await resp.content.read()
                    unicoded = test.decode("unicode_escape")
                    query_find = re.findall(regex[0], unicoded)
                    try:
                        url = query_find[0]
                        await self.bot.say(url)
                    except IndexError:
                        await self.bot.say(":interrobang: Your search yielded no results.")
            #End of Image random
        #Start of Maps
        elif search_type[0] == "maps":
            search_valid = str(ctx.message.content[len(ctx.prefix+ctx.command.name)+1:].lower())
            if search_valid == "maps":
                await self.bot.say(":neutralFace: Please ***actually search something*** :/")
            else:
                uri = "https://www.google.com/maps/search/"
                quary = str(ctx.message.content[len(ctx.prefix+ctx.command.name)+6:].lower())
                encode = urllib.parse.quote_plus(quary,encoding='utf-8',errors='replace')
                uir = uri+encode
                await self.bot.say(uir)
            #End of Maps
        #Start of generic search
        else:
            uri = "https://www.google.com/search?q="
            quary = str(ctx.message.content[len(ctx.prefix+ctx.command.name)+1:])
            encode = urllib.parse.quote_plus(quary,encoding='utf-8',errors='replace')
            uir = uri+encode
            async with aiohttp.get(uir, headers = option) as resp:
                test = str(await resp.content.read())
                query_find = re.findall(regex[1], test)
                if query_find == []:
                    query_find = re.findall(regex[2], test)
                    try:
                        if re.search("\/url?url=", query_find[0]) == True:
                            query_find = query_find[0]
                            m = re.search("\/url?url=", query_find)
                            query_find = query_find[:m.start()] + query_find[m.end():]
                            decode = self.unescape(query_find)
                            await self.bot.say("Here is your link: {}".format(decode))
                        else:
                            decode = self.unescape(query_find[0])
                            await self.bot.say("Here is your link: {}".format(decode))
                    except IndexError:
                        await self.bot.say("Your search yielded no results.")
                elif re.search("\/url?url=", query_find[0]) == True:
                    query_find = query_find[0]
                    m = re.search("\/url?url=", query_find)
                    query_find = query_find[:m.start()] + query_find[m.end():]
                    decode = self.unescape(query_find)
                    await self.bot.say("Here is your link: {}".format(decode))
                else:
                    query_find = query_find[0]
                    decode = self.unescape(query_find)
                    await self.bot.say("Here is your link: {} ".format(decode))
            #End of generic search

    def unescape(self, msg):
        regex = ["<br \/>", "(?:\\\\[rn])", "(?:\\\\['])", "%25", "\(", "\)"]
        subs = ["\n", "", "'", "%", "%28", "%29"]

        for i in range(len(regex)):
            sub = re.sub(regex[i], subs[i], msg)
            msg = sub
        return msg

    @commands.command(pass_context=True,aliases=["av"])
    async def avatar(self, ctx, user : discord.Member = None):
        """Check out someones avatar !
        Or just cheack out your own by simply doing avatar.
        Big thanks to TEDDY real og."""
        colour = ''.join([randchoice('0123456789ABCDEF') for x in range(6)])
        colour = int(colour, 16)        
        if user is None:
            user = ctx.message.author
        if user.avatar_url is None:
            await self.bot.reply(":x: **User has no avatar**")
        em = discord.Embed(title="{}'s avatar ↓".format(user.name), colour=discord.Colour(value=colour), url=user.avatar_url)
        em.set_image(url=user.avatar_url)
        await self.bot.say(embed=em)

    @commands.command(pass_context=True)
    async def rps(self, ctx, your_choice : RPSParser):
        """Play rock paper scissors"""
        author = ctx.message.author
        player_choice = your_choice.choice
        red_choice = choice((RPS.rock, RPS.paper, RPS.scissors))
        cond = {
                (RPS.rock,     RPS.paper)    : False,
                (RPS.rock,     RPS.scissors) : True,
                (RPS.paper,    RPS.rock)     : True,
                (RPS.paper,    RPS.scissors) : False,
                (RPS.scissors, RPS.rock)     : False,
                (RPS.scissors, RPS.paper)    : True
               }

        if red_choice == player_choice:
            outcome = None # Tie
        else:
            outcome = cond[(player_choice, red_choice)]

        if outcome is True:
            await self.bot.say("**I chose** {} ***You win {}!***👍"
                               "".format(red_choice.value, author.mention))
        elif outcome is False:
            await self.bot.say("**I chose** {} **You** ***lose {}!***🙅 "
                               "".format(red_choice.value, author.mention))
        else:
            await self.bot.say("**I chose**{} ***We're square {}!***👊"
                               "".format(red_choice.value, author.mention))

    @commands.command(aliases=["sw"], pass_context=True)
    async def stopwatch(self, ctx):
        """Starts/stops stopwatch"""
        author = ctx.message.author
        if not author.id in self.stopwatches:
            self.stopwatches[author.id] = int(time.perf_counter())
            await self.bot.say(author.mention + " Stopwatch started!")
        else:
            tmp = abs(self.stopwatches[author.id] - int(time.perf_counter()))
            tmp = str(datetime.timedelta(seconds=tmp))
            await self.bot.say(author.mention + " Stopwatch stopped! Time: **" + tmp + "**")
            self.stopwatches.pop(author.id, None)

    @commands.command()
    async def lmgtfy(self, *, search_terms : str):
        """Creates a lmgtfy link"""
        search_terms = escape_mass_mentions(search_terms.replace(" ", "+"))
        await self.bot.say("https://lmgtfy.com/?q={}".format(search_terms))

    @commands.command(pass_context=True, no_pm=True, aliases=["uinfo"])
    async def userinfo(self, ctx, *, user: discord.Member=None):
        """Check your userinfo or someone elses :P"""
        author = ctx.message.author
        server = ctx.message.server
    
        colour = ''.join([randchoice('0123456789ABCDEF') for x in range(6)])
        colour = int(colour, 16)

        if not user:
            user = author

        roles = [x.name for x in user.roles if x.name != "@everyone"]

        if user.status == discord.Status.dnd:
            m = "<:vpDnD:236744731088912384>DND"
        if user.status == discord.Status.offline:
            m = "<:vpOffline:212790005943369728>Offline/Invisible"
        if user.status == discord.Status.online:
            m = "<:vpOnline:212789758110334977>Online"
        if user.status == discord.Status.idle:
            m = "<:vpAway:212789859071426561>Idle"
        elif user.game is not None and user.game.url is True:
            m = "<:vpStreaming:212789640799846400> {} Is streaming !!".format(user.name)
        joined_at = self.fetch_joined_at(user, server)
        since_created = (ctx.message.timestamp - user.created_at).days
        since_joined = (ctx.message.timestamp - joined_at).days
        user_joined = joined_at.strftime("%d %b %Y %H:%M")
        user_created = user.created_at.strftime("%d %b %Y %H:%M")

        created_on = "{}\n({} days ago)".format(user_created, since_created)
        joined_on = "{}\n({} days ago)".format(user_joined, since_joined)

        if user.game is None:
            game = "Playing ⇒ Nothing at all ¯\_(ツ)_/¯".format(user.name)
        elif user.game.url is None:
            game = ":video_game: Playing ⇒ {}".format(user.game)
        else:
            game = "<:vpStreaming:212789640799846400> Streaming ⇒  [{}]({})".format(user.game, user.game.url)

        if roles:
            roles = sorted(roles, key=[x.name for x in server.role_hierarchy
                                       if x.name != "@everyone"].index)
            roles = ", ".join(roles)
        else:
            roles = ":walking: Nothing to see here ¯\_(ツ)_/¯\n\n"
        if user.nick is not None:
            ggez = "{}".format(user.nick)
        if user.nick is None:
            ggez = "No NickName Found\n(╯°□°）╯︵ ┻━┻"

        if roles is None:
            user.colour = discord.Colour(value=colour)

        data = discord.Embed(description=game, colour=user.colour)
        data.add_field(name="Status", value=m)
        data.add_field(name="Joined Discord on", value=created_on)
        data.add_field(name="Nickname", value=ggez)
        data.add_field(name="Discriminator", value="#{}".format(user.discriminator))
        data.add_field(name="Highest role Colour", value="{}".format(user.colour))
        data.add_field(name="Joined this server on", value=joined_on)
        data.add_field(name="Roles", value=roles, inline=False)
        data.set_footer(text="Userinfo | User ID ⇒  " + user.id)


        if user.avatar_url:
            name = str(user)
            name = (name) if user.nick else name
            data.set_author(name=user.name, url=user.avatar_url)
            data.set_thumbnail(url=user.avatar_url)

        else:
            data.set_author(name=user.name)

        try:
            await self.bot.say(embed=data)
        except discord.HTTPException:
            await self.bot.say("I need the `Embed links` permission "
                               "to send this")

    @commands.command(pass_context=True, no_pm=True, aliases=["sinfo"])
    async def serverinfo(self, ctx):
        """Shows server's info"""
        server = ctx.message.server
        online = len([m.status for m in server.members
                      if m.status == discord.Status.online])
        idle = len([m.status for m in server.members
                      if m.status == m.status == discord.Status.idle])
        dnd = len([m.status for m in server.members
                      if m.status == discord.Status.dnd])
        total_users = len(server.members)
        text_channels = len([x for x in server.channels
                             if x.type == discord.ChannelType.text])
        voice_channels = len(server.channels) - text_channels
        passed = (ctx.message.timestamp - server.created_at).days
        created_at = ("***Since***  ***`{}.`*** ***That's over***  ***`{}`***  ***days ago!***"
                      "".format(server.created_at.strftime("%d %b %Y %H:%M"),
                                passed))

        colour = ''.join([randchoice('0123456789ABCDEF') for x in range(6)])
        colour = int(colour, 16)
        x = -1
        emojis =  []
        while x < len([r for r in ctx.message.server.emojis]) -1:
            x = x + 1
            emojis.append("<:{}:{}>".format([r.name for r in ctx.message.server.emojis][x], [r.id for r in ctx.message.server.emojis][x]))

        data = discord.Embed(
            description=created_at,
            colour=discord.Colour(value=colour))
        data.add_field(name="Region", value=str(server.region).upper())
        data.add_field(name="Users", value="{} (<:vpOnline:212789758110334977>{} Online Users)".format(total_users, online))
        data.add_field(name="Text Channels", value=text_channels)
        data.add_field(name="Voice Channels", value=voice_channels)
        data.add_field(name="Roles", value=len(server.roles))
        data.add_field(name="Owner", value=str(server.owner))
        data.add_field(name="Verification Level", value= str(server.verification_level))
        data.add_field(name="AFK Channel", value=str(server.afk_channel).upper())
        data.add_field(name="Afk Timeout", value="{}M".format(server.afk_timeout/60))
        data.add_field(name="Total emojis", value="{} ".format(len(server.emojis)))

        data.set_footer(text="🆔 Server ID ⇒  " + server.id)
        if server.icon_url:
            data.set_author(name=server.name, url=server.icon_url)
            data.set_thumbnail(url=server.icon_url)
        else:
            data.set_author(name=server.name)
        if server.emojis:
            emotes = discord.Embed(title="Emotes", description=" ".join(emojis), colour=discord.Colour(value=colour))
        else:
            emotes = discord.Embed(title="Emotes", description=":no_good: ", colour=discord.Colour(value=colour))

        try:
            await self.bot.say(embed=data)
            await self.bot.say(embed=emotes)
        except discord.HTTPException:
            server = ctx.message.server
            x = -1
            emojis =  []
            while x < len([r for r in ctx.message.server.emojis]) -1:
                x = x + 1
                emojis.append("<:{}:{}>".format([r.name for r in ctx.message.server.emojis][x], [r.id for r in ctx.message.server.emojis][x]))
            online = str(len([m.status for m in server.members if str(m.status) == "online" or str(m.status) == "idle"]))
            total_users = str(len(server.members))
            text_channels = len([x for x in server.channels if str(x.type) == "text"])
            voice_channels = len(server.channels) - text_channels

            data = "```python\n"
            data += "Server Name: {}\n".format(server.name)
            data += "ID: {}\n".format(server.id)
            data += "Region: {}\n".format(server.region)
            data += "Users: {}/{}\n".format(online, total_users)
            data += "Text channels: {}\n".format(text_channels)
            data += "Voice channels: {}\n".format(voice_channels)
            data += "Roles: {}\n".format(len(server.roles))
            data += "Verification Level: {}\n".format(str(server.verification_level))
            data += "Total emojis: {}\n".format(len(server.emojis))
            passed = (ctx.message.timestamp - server.created_at).days
            data += "Created: {} ({} days ago)\n".format(server.created_at, passed)
            data += "Owner: {}\n".format(server.owner)

            if server.icon_url != "":
                data += "Icon&Emojis:"
                data += "```"
                data += "{}\n".format(server.icon_url)
            if len(str(server.emojis)) < 6024 and server.emojis:
                data += " ".join([str(emoji) for emoji in server.emojis])
            else:
                data += "```"
            await self.bot.say(data)
            await self.bot.say("***ATTENTION*** **I am sending in This format because embed_links are not apart of my permissions Please enable all permissions including admininstrator to witness the bots full potential.**\n***(Btw info is missing lul)***")


    @commands.command(aliases=["ud"])
    async def urban(self, *, search_terms: str, definition_number: int = 1):
        """Urban Dictionary search

        Definition number must be between 1 and 10"""
        # definition_number is just there to show up in the help
        # all this mess is to avoid forcing double quotes on the user
        search_terms = search_terms.split(" ")
        colour = ''.join([randchoice('0123456789ABCDEF') for x in range(6)])
        colour = int(colour, 16)
        try:
            if len(search_terms) > 1:
                pos = int(search_terms[-1]) - 1
                search_terms = search_terms[:-1]
            else:
                pos = 0
            if pos not in range(0, 11):  # API only provides the
                pos = 0  # top 10 definitions
        except ValueError:
            pos = 0
        search_terms = "+".join(search_terms)
        url = "http://api.urbandictionary.com/v0/define?term=" + search_terms
        try:
            async with aiohttp.get(url) as r:
                result = await r.json()
            if result["list"]:
                definition = result['list'][pos]['definition']
                likes = result['list'][pos]['thumbs_up']
                da_link = result['list'][pos]['permalink']
                example = result['list'][pos]['example']
                dislikes = result['list'][pos]['thumbs_down']
                author = result['list'][pos]['author']

                defs = len(result['list'])
                msg = ("***Definition #{} out of {}:\n***{}\n\n"
                       "**Example:\n**{}".format(pos + 1, defs, definition, example))
                msg = pagify(msg, ["\n"])
                for page in msg:
                    em = discord.Embed(description=page, colour=discord.Colour(value=colour))
                    em.set_footer(text="Urban Dictionary | Likes 👍{} | Dislikes 👎{} | Creator {}".format(likes, dislikes, author),
                                  icon_url='https://images-ext-1.discordapp.net/eyJ1cmwiOiJodHRwczovL2kuaW1ndXIuY29tL3dxZFF3U0suanBnIn0.MVrzfDg61z-6jQ2guGiijCVYs9Q?width=80&height=80')
                    em.set_author(name="Definition For {}".format(search_terms),
                                  icon_url='https://encrypted-tbn1.gstatic.com/images?q=tbn:ANd9GcQjaR3MhX7A7YtV08NVATNK5XjGQIH95cHpVZGOfBeEgMqT5dyNjg', url=da_link)
                    em.set_thumbnail(
                        url="https://encrypted-tbn3.gstatic.com/images?q=tbn:ANd9GcTKnTyIjfRPfIe1JN9Sd3rfbg-Sw-hRag8EjGFVX_uLo2vKELGYzQ")
                    await self.bot.say(embed=em)

            else:
                await self.bot.say(":x: **Your** ***search terms gave no results.*** :no_good:")
        except IndexError:
            await self.bot.say("There is no definition #{}".format(pos + 1))
        except:
            await self.bot.say("Error.")
    @commands.command(pass_context=True, no_pm=True)
    async def poll(self, ctx, *text):
        """Starts/stops a poll
        Usage example:
        poll Is this a poll?;Yes;No;Maybe
        poll stop"""
        message = ctx.message
        if len(text) == 1:
            if text[0].lower() == "stop":
                await self.endpoll(message)
                return
        if not self.getPollByChannel(message):
            check = " ".join(text).lower()
            if "@everyone" in check or "@here" in check:
                await self.bot.reply("Well At least you tried but i have counter messures against that ¯\_(ツ)_/¯")
                return
            p = NewPoll(message, self)
            if p.valid:
                self.poll_sessions.append(p)
                await p.start()
            else:
                await self.bot.say("**Question** ***;option1;option2*** Etc")
        else:
            await self.bot.say(":raised_hand: :x: ***A poll Is currently active*** :x: :raised_hand: ")

    async def endpoll(self, message):
        if self.getPollByChannel(message):
            p = self.getPollByChannel(message)
            if p.author == message.author.id: # or isMemberAdmin(message)
                await self.getPollByChannel(message).endPoll()
            else:
                await self.bot.say("**Only Admins & Dangerous** can stop the poll.")
        else:
            await self.bot.say(":raised_hand: :x: ***No Ongoing poll.*** :raised_hand: :x:")

    def getPollByChannel(self, message):
        for poll in self.poll_sessions:
            if poll.channel == message.channel:
                return poll
        return False

    async def check_poll_votes(self, message):
        if message.author.id != self.bot.user.id:
            if self.getPollByChannel(message):
                    self.getPollByChannel(message).checkAnswer(message)

    def fetch_joined_at(self, user, server):
        """Just a special case for someone special :^)"""
        if user.id == "96130341705637888" and server.id == "133049272517001216":
            return datetime.datetime(2016, 1, 10, 6, 8, 4, 443000)
        else:
            return user.joined_at

class NewPoll():
    def __init__(self, message, main):
        self.channel = message.channel
        self.author = message.author.id
        self.client = main.bot
        self.poll_sessions = main.poll_sessions
        msg = message.content[6:]
        msg = msg.split(";")
        if len(msg) < 2: # Needs at least one question and 2 choices
            self.valid = False
            return None
        else:
            self.valid = True
        self.already_voted = []
        self.question = msg[0]
        msg.remove(self.question)
        self.answers = {}
        i = 1
        for answer in msg: # {id : {answer, votes}}
            self.answers[i] = {"ANSWER" : answer, "VOTES" : 0}
            i += 1

    async def start(self):
        msg = ":mailbox_with_mail: **POLL STARTED!**:mailbox_with_mail: \n\n**{}**\n\n".format(self.question)
        for id, data in self.answers.items():
            msg += "**{}. {}**\n".format(id, data["ANSWER"])
        msg += "\n**Type the freaken # To answer !**"
        await self.client.send_message(self.channel, msg)
        await asyncio.sleep(settings["POLL_DURATION"])
        if self.valid:
            await self.endPoll()

    async def endPoll(self):
        self.valid = False
        msg = ":postbox: **POLL ENDED!** :postbox: \n\n***{}***\n\n".format(self.question)
        for data in self.answers.values():
            msg += "***{} - {} votes***\n".format(data["ANSWER"], str(data["VOTES"]))
        await self.client.send_message(self.channel, msg)
        self.poll_sessions.remove(self)

    def checkAnswer(self, message):
        try:
            i = int(message.content)
            if i in self.answers.keys():
                if message.author.id not in self.already_voted:
                    data = self.answers[i]
                    data["VOTES"] += 1
                    self.answers[i] = data
                    self.already_voted.append(message.author.id)
        except ValueError:
            pass

def check_file():
    f = 'data/away/away.json'
    if not dataIO.is_valid_json(f):
        dataIO.save_json(f, {})
        print('Creating default away.json...')

    weather = {}
    weather['WEATHER_API_KEY'] = ''
    weather['TIME_API_KEY'] = ''

    f = "data/weather/weather.json"
    if not dataIO.is_valid_json(f):
        print("Creating default weather.json...")
        dataIO.save_json(f, weather)

    data = {}
    f = "data/youtube/settings.json"
    if not dataIO.is_valid_json(f):
        print("Creating default settings.json...")
        dataIO.save_json(f, data)



def check_folder():
    if not os.path.exists('data/seen'):
        print('Creating data/seen folder...')
        os.makedirs('data/seen')

    if not os.path.exists("data/moji"):
        print("Creating data/moji folder...")
        os.makedirs("data/moji")

    if not os.path.exists('data/away'):
        print('Creating data/away folder...')
        os.makedirs('data/away')

    if not os.path.exists("data/weather"):
        print("Creating data/weather folder...")
        os.makedirs("data/weather")

    if not os.path.exists("data/youtube"):
        print("Creating data/youtube folder...")
        os.makedirs("data/youtube")

def setup(bot):
    global logger
    check_folder()
    check_file()
    n = General(bot)
    bot.add_listener(n.check_poll_votes, "on_message")
    bot.add_listener(n.listener, 'on_message')
    loop = asyncio.get_event_loop()
    bot.add_cog(n)