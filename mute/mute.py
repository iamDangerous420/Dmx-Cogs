
import time
import discord
from discord.ext import commands
from .utils.chat_formatting import *
from random import randint
from random import choice as randchoice
from .utils import checks
# import asyncio
# from __main__ import send_cmd_help
import logging
from cogs.utils.dataIO import dataIO
import os
import time
import re


try:
    from tabulate import tabulate
except Exception as e:
    raise RuntimeError("You must run `pip3 install tabulate`.") from e

UserInputError = commands.UserInputError

log = logging.getLogger('red.mute')

UNIT_TABLE = {'s': 1, 'm': 60, 'h': 60 * 60, 'd': 60 * 60 * 24}
UNIT_SUF_TABLE = {'sec': (1, ''),
                  'min': (60, ''),
                  'hr': (60 * 60, 's'),
                  'day': (60 * 60 * 24, 's')
                  }
DEFAULT_TIMEOUT = '10m'
PURGE_MESSAGES = 100  # for cmute


def _parse_time(time):
    if any(u in time for u in UNIT_TABLE.keys()):
        delim = '([0-9.]*[{}])'.format(''.join(UNIT_TABLE.keys()))
        time = re.split(delim, time)
        time = sum([_timespec_sec(t) for t in time if t != ''])
    return int(time)


def _timespec_sec(t):
    timespec = t[-1]
    if timespec.lower() not in UNIT_TABLE:
        raise ValueError('Unknown time unit "%c"' % timespec)
    timeint = float(t[:-1])
    return timeint * UNIT_TABLE[timespec]


def _generate_timespec(sec):
    timespec = []

    def sort_key(kt):
        k, t = kt
        return t[0]
    for unit, kt in sorted(UNIT_SUF_TABLE.items(), key=sort_key, reverse=True):
        secs, suf = kt
        q = sec // secs
        if q:
            if q <= 1:
                suf = ''
            timespec.append('%02.d%s%s' % (q, unit, suf))
        sec = sec % secs
    return ', '.join(timespec)


class mute:
    """Mute Users"""

    # --- Format
    # {
    # serverid : {
    #   memberid : {
    #       until : timestamp
    #       by : memberid
    #       reason: str
    #       }
    #    }
    # }
    # ---

    def __init__(self, bot):
        self.bot = bot
        self.location = 'data/mute/settings.json'
        self.json = compat_load(self.location)
        self.handles = {}
        self.role_name = 'Muted'
        bot.loop.create_task(self.on_load())

    @commands.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def cmute(self, ctx, user: discord.Member, duration: str=None, *, reason: str=None):
        """Same as mute but cleans up after itself and the target"""
        server = ctx.message.server
        colour = ''.join([randchoice('0123456789ABCDEF') for x in range(6)])
        colour = int(colour, 16)
        role = await self.setup_role(server, quiet=True)
        if not role:
            return

        if 'Mod' in self.bot.cogs:
            cog_mod = self.bot.get_cog('Mod')
            cog_mod_enabled = True

        self.json = dataIO.load_json(self.location)
        if server.id not in self.json:
            self.json[server.id] = {}

        if user.id in self.json[server.id]:
            msg = '***User was already Muted\nResetting Dat timer :timer: Boii...***'
        elif role in user.roles:
            msg = '**User was Muted but had no timer,** ***Muting dat bitch now!...***:hammer:'
        else:
            msg = '***Bam Muted :speak_no_evil: :pencil2:️:no_entry_sign: BABA BIITCCCH Now stay muted  :wave: !!~***.'

        if not duration:
            msg += ' \n***`Using default duration of {}`*** '.format(DEFAULT_TIMEOUT)
            duration = _parse_time(DEFAULT_TIMEOUT)
            timestamp = time.time() + duration
        elif duration.lower() in ['forever', 'inf', 'infinite']:
            duration = None
            timestamp = None
        else:
            duration = _parse_time(duration)
            timestamp = time.time() + duration

        if server.id not in self.json:
            self.json[server.id] = {}

        self.json[server.id][user.id] = {
            'until': timestamp,
            'by': ctx.message.author.id,
            'reason': reason
        }

        await self.bot.add_roles(user, role)
        dataIO.save_json(self.location, self.json)

        # schedule callback for role removal
        if duration:
            self.schedule_unmute(duration, user, reason)
        def is_user(m):
            return m == ctx.message or m.author == user

        try:
            await self.bot.purge_from(ctx.message.channel, limit=PURGE_MESSAGES + 1, check=is_user)
        except discord.errors.Forbidden:
            msg = '**Mute set**,But I require ***manage messages*** to clean up. **Please Assign Admin permissions To avoid errors such as these infuture** :thumbsup:'
        em = discord.Embed(description=msg, colour=discord.Colour(value=colour), timestamp=__import__('datetime').datetime.utcnow())
        await self.bot.say(embed=em)
        if cog_mod_enabled is True:
            if duration is None:
                await cog_mod.new_case(server, action="Cmuted forever 🙊♻", mod=ctx.message.author, user=user, reason=reason)
            if duration < 60:
                await cog_mod.new_case(server, action="Cmuted for {}s 🙊♻".format(duration), mod=ctx.message.author, user=user, reason=reason)
            if duration >= 60:
                if duration < 3600:
                    await cog_mod.new_case(server, action="Cmuted for {}M 🙊♻".format(duration/60).replace(".0", ""), mod=ctx.message.author, user=user, reason=reason)
            if duration >= 3600:
                if duration < 86400:
                    await cog_mod.new_case(server, action="Cmuted for {}H 🙊♻".format(duration/3600).replace(".0", ""), mod=ctx.message.author, user=user, reason=reason)
            if duration >= 86400:
                await cog_mod.new_case(server, action="Cmuted for {} Day(s) 🙊♻".format(duration/86400).replace(".0", ""), mod=ctx.message.author, user=user, reason=reason)
    @commands.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def mute(self, ctx, user: discord.Member, duration: str=None, *, reason: str=None):
        """Puts a user into timeout for a specified time period, with an optional reason.
       Time Units ==> s,m,h,d.
        Example: ~mute @Dumbass#4053 1.1h10m ***Enough bitching Hue dumbass!***"""

        server = ctx.message.server
        role = await self.setup_role(server)
        colour = ''.join([randchoice('0123456789ABCDEF') for x in range(6)])
        colour = int(colour, 16)

        if 'Mod' in self.bot.cogs:
            cog_mod = self.bot.get_cog('Mod')
            cog_mod_enabled = True

        if role is None:
            return

        self.json = dataIO.load_json(self.location)
        if server.id not in self.json:
            self.json[server.id] = {}

        if user.id in self.json[server.id]:
            msg = '***User was already Muted\nResetting Dat timer :timer: Boii...***'
        elif role in user.roles:
            msg = '**User was Muted but had no timer,** ***Muting dat bitch now!...***:hammer:'
        else:
            msg = '***Bam Muted :speak_no_evil: :pencil2:️:no_entry_sign: BABA BIITCCCH Now stay muted  :wave: !!~***.'

        if not duration:
            msg += ' \n***`Using default duration of {}`*** '.format(DEFAULT_TIMEOUT)
            duration = _parse_time(DEFAULT_TIMEOUT)
            timestamp = time.time() + duration
        elif duration.lower() in ['forever', 'inf', 'infinite']:
            duration = None
            timestamp = None
        else:
            duration = _parse_time(duration)
            timestamp = time.time() + duration
        if server.id not in self.json:
            self.json[server.id] = {}

        self.json[server.id][user.id] = {
            'until': timestamp,
            'by': ctx.message.author.id,
            'reason': reason
        }

        await self.bot.add_roles(user, role)
        dataIO.save_json(self.location, self.json)

        # schedule callback for role removal
        if duration:
            self.schedule_unmute(duration, user, reason)
        em = discord.Embed(description=msg, colour=discord.Colour(value=colour), timestamp=__import__('datetime').datetime.utcnow())
        em.set_thumbnail(url="https://cdn.discordapp.com/attachments/273424151795204107/289528782698840065/dont-speak.png")
        await self.bot.say(embed=em)
        if duration is None:
            duration = 'forever'
        if cog_mod_enabled is True:
            if duration is None:
                await cog_mod.new_case(server, action="Muted forever 🙊", mod=ctx.message.author, user=user, reason=reason)
            if duration < 60:
                await cog_mod.new_case(server, action="Muted for {}s 🙊".format(duration), mod=ctx.message.author, user=user, reason=reason)
            if duration >= 60:
                if duration < 3600:
                    await cog_mod.new_case(server, action="Muted for {}M 🙊".format(duration/60).replace(".0", ""), mod=ctx.message.author, user=user, reason=reason)
            if duration >= 3600:
                if duration < 86400:
                    await cog_mod.new_case(server, action="Muted for {}H 🙊".format(duration/3600).replace(".0", ""), mod=ctx.message.author, user=user, reason=reason)
            if duration >= 86400:
                await cog_mod.new_case(server, action="Muted for {} Day(s) 🙊".format(duration/86400).replace(".0", ""), mod=ctx.message.author, user=user, reason=reason)

    @commands.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def warn(self, ctx, user: discord.Member, *, reason: str=None):
        """Warns a user with boilerplate about the rules."""
        author = ctx.message.author
        server = ctx.message.server
        colour = ''.join([randchoice('0123456789ABCDEF') for x in range(6)])
        colour = int(colour, 16)

        if 'Mod' in self.bot.cogs:
            cog_mod = self.bot.get_cog('Mod')
            cog_mod_enabled = True

        if reason is None:
            msg = ":bangbang:  **Hey!!** {},**You're doing something that might get you** ***MUTED*** :zipper_mouth: *if you persist* :x: **Be sure to review the rules for {}** :thumbsup: .  ".format(user.mention, server.name)
            if cog_mod_enabled is True:
                await cog_mod.new_case(server, action="Warning ⚠", mod=ctx.message.author, user=user)
        else:
            msg = ":bangbang:  **Hey!!** {},**You're doing something that might get you** ***MUTED*** :zipper_mouth: *if you persist* :x:  **Specifically**, ***__{}__***. **Be sure to review the rules for {}** :thumbsup:.".format(user.mention, reason, server.name)
            if cog_mod_enabled is True:
                await cog_mod.new_case(server, action="Warning ⚠", mod=ctx.message.author, user=user, reason=reason)
        em = discord.Embed(description=msg, colour=discord.Colour(value=colour), timestamp=__import__('datetime').datetime.utcnow())
        avatar = self.bot.user.avatar_url if self.bot.user.avatar else self.bot.user.default_avatar_url
        em.set_author(name='Warning from {}'.format(author.name), icon_url=avatar)
        if server.icon_url:
            em.set_thumbnail(url=server.icon_url)
        await self.bot.say(embed=em)

    async def setup_role(self, server, quiet=False):
        role = discord.utils.get(server.roles, name=self.role_name)
        colour = ''.join([randchoice('0123456789ABCDEF') for x in range(6)])
        colour = int(colour, 16)
        if not role:
            if not (any(r.permissions.manage_roles for r in server.me.roles) and
                    any(r.permissions.manage_channels for r in server.me.roles)):
                msgg = "***The `Manage Roles` and `Manage Channels` permissions are required to use this command.***"
                em = discord.Embed(description=msg, colour=discord.Colour(value=colour))
                await self.bot.say(embed=em)
                return None
            else:
                msg = "**The {} role is inexistent**\n:raised_hand:***Creating it now wait up boi...***:raised_hand:\n".format(self.role_name)
                em = discord.Embed(description=msg, colour=discord.Colour(value=colour))
                if not quiet:
                    msgobj = await self.bot.say(embed=em)
                log.debug('Creating mute role :)')
                perms = discord.Permissions.none()
                role = await self.bot.create_role(server, name=self.role_name, permissions=perms)
                if not quiet:
                    eb = msg + '**Configurating channels** :smile:... '
                    msgobj = await self.bot.edit_message(msgobj, embed = discord.Embed(description=eb))
                for c in server.channels:
                    await self.on_channel_create(c, role)
                if not quiet:
                    e = eb + '\n**Andddd We** ***DONE DABBB***.'
                    e = discord.Embed(description= e)
                    e.set_thumbnail(url='https://goo.gl/yLyMgq')
                    msgobj = await self.bot.edit_message(msgobj, embed = e)
        return role


    @commands.command(pass_context=True, no_pm=True, name='listmuted', aliases=['lsmute','muted'])
    @checks.mod_or_permissions(manage_messages=True)
    async def list_muted(self, ctx):
        """Shows a table of muted users with time, mod and reason.
        Displays muted users, time remaining, responsible moderator and
        the reason for punishment, if any."""
        server = ctx.message.server
        server_id = server.id
        colour = ''.join([randchoice('0123456789ABCDEF') for x in range(6)])
        colour = int(colour, 16)
        if not (server_id in self.json and self.json[server_id]):
            emm = discord.Embed(description="No users are currently Muted.Sadly.", colour=discord.Color.purple())
            await self.bot.say(embed=emm)
            return

        def getmname(mid):
            member = discord.utils.get(server.members, id=mid)
            if member:
                if member.nick:
                    return '%s (%s)' % (member.nick, member)
                else:
                    return str(member)
            else:
                return '(member not present, id #%d)'

        headers = ['Member', 'Remaining', 'Muted by', 'Reason']
        table = []
        disp_table = []
        now = time.time()
        for member_id, data in self.json[server_id].items():
            member_name = getmname(member_id)
            punisher_name = getmname(data['by'])
            reason = data['reason']
            t = data['until']
            sort = t if t else float("inf")
            table.append((sort, member_name, t, punisher_name, reason))

        for _, name, rem, mod, reason in sorted(table, key=lambda x: x[0]):
            remaining = _generate_timespec(rem - now) if rem else 'forever'
            if not reason:
                reason = 'n/a'
            disp_table.append((name, remaining, mod, reason))

        msg = '```\n%s\n```' % tabulate(disp_table, headers)
        em = discord.Embed(description=msg, colour=discord.Colour(value=colour))
        await self.bot.say(embed=em)

    @commands.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def unmute(self, ctx, user: discord.Member, reason=None):
        """Removes mute from a user. Same as removing the role directly"""
        role = discord.utils.get(user.server.roles, name=self.role_name)
        sid = user.server.id
        server = ctx.message.server
        channel = ctx.message.channel
        colour = ''.join([randchoice('0123456789ABCDEF') for x in range(6)])
        colour = int(colour, 16)

        if 'Mod' in self.bot.cogs:
            cog_mod = self.bot.get_cog('Mod')
            cog_mod_enabled = True
        if role and role in user.roles and reason is not None:
            reason = reason
            if self.json[sid][user.id]['reason']:
                reason += self.json[sid][user.id]['reason']
            await self._unmute(user, reason)
            msg1 = '***Donee*** Unmuterinooo :speaking_head: :D'
            em = discord.Embed(description=msg1, colour=discord.Colour(value=colour))
            await self.bot.send_message(channel, embed=em)

        if role and role in user.roles:
            reason = '**Mute manually ended early by a pleb named =>** ***`{}`***. '.format(ctx.message.author.name)
            if self.json[sid][user.id]['reason']:
                reason += self.json[sid][user.id]['reason']
            await self._unmute(user, reason)
            msg1 = '***Donee*** Unmuterinooo :speaking_head: :D'
            em = discord.Embed(description=msg1, colour=discord.Colour(value=colour))
            await self.bot.send_message(channel, embed=em)
        else:
            msg = "**Hey Mate!** ***{} wasn't Muted*** :thinking:.".format(user.mention)
            em = discord.Embed(description=msg, colour=discord.Colour(value=colour))
            await self.bot.send_message(channel, embed=em)

        if cog_mod_enabled is True:
            await cog_mod.new_case(server, action="Unmute 🗣", mod=ctx.message.author, user=user, reason=reason)
    async def on_load(self):
        """Called when bot is ready and each time cog is (re)loaded"""
        await self.bot.wait_until_ready()
        # copy so we can delete stuff from the original
        for serverid, members in self.json.copy().items():
            server = discord.utils.get(self.bot.servers, id=serverid)
            if not server:
                del(self.json[serverid])
                continue
            role = discord.utils.get(server.roles, name=self.role_name)
            for member_id, data in members.items():
                until = data['until']
                if until:
                    duration = until - time.time()
                member = discord.utils.get(server.members, id=member_id)
                if until and duration < 0:
                    if member:
                        reason = 'Mute removal overdue, maybe bot was offline. '
                        if self.json[server.id][member_id]['reason']:
                            reason += self.json[server.id][member_id]['reason']
                        await self._unmute(member, reason)
                    else:  # member disappeared
                        del(self.json[server.id][member.id])
                elif member:
                    await self.bot.add_roles(member, role)
                    if until:
                        self.schedule_unmute(duration, member)
        dataIO.save_json(self.location, self.json)

    # Functions related to unmuting

    def schedule_unmute(self, delay, member, reason=None):
        """Schedules role removal, canceling and removing existing tasks if present"""
        handle = self.bot.loop.call_later(delay, self._unmute_cb, member, reason)
        sid = member.server.id
        if sid not in self.handles:
            self.handles[sid] = {}
        if member.id in self.handles[sid]:
            self.handles[sid][member.id].cancel()
        self.handles[sid][member.id] = handle

    def _unmute_cb(self, member, reason=None):
        """Regular function to be used as unmute callback"""
        def wrap(member, reason):
            return self._unmute(member, reason)
        self.bot.loop.create_task(wrap(member, reason))

    async def _unmute(self, member, reason=None):
        """Remove mute role, delete record and task handle"""
        server = member.server
        role = await self.setup_role(server)
        colour = ''.join([randchoice('0123456789ABCDEF') for x in range(6)])
        colour = int(colour, 16)
        role = discord.utils.get(member.server.roles, name=self.role_name)
        if role:
            # Has to be done first to prevent triggering on_member_update listener
            self._unmute_data(member)
            await self.bot.remove_roles(member, role)
            msg = '***__Your mute in `{}` has ended bitch__.***'.format(member.server.name)
            if reason:
                msg += "\n**Reason was:** {}".format(reason)
            em = discord.Embed(description=msg, colour=discord.Colour(value=colour))
            await self.bot.send_message(member, embed=em)
            return

    def _unmute_data(self, member):
        """Removes mute data entry and cancels any present callback"""
        self.json = dataIO.load_json(self.location)
        sid = member.server.id
        if sid in self.json and member.id in self.json[sid]:
            del(self.json[member.server.id][member.id])
            dataIO.save_json(self.location, self.json)

        if sid in self.handles and member.id in self.handles[sid]:
            self.handles[sid][member.id].cancel()
            del(self.handles[member.server.id][member.id])

    # Listeners

    async def on_channel_create(self, c, role=None):
        """Run when new channels are created and set up role permissions"""
        if c.is_private:
            return
        perms = discord.PermissionOverwrite()
        if c.type == discord.ChannelType.text:
            perms.send_messages = False
            perms.send_tts_messages = False
        elif c.type == discord.ChannelType.voice:
            perms.speak = False
        if not role:
            role = discord.utils.get(c.server.roles, name=self.role_name)
        await self.bot.edit_channel_permissions(c, role, perms)

    async def on_member_update(self, before, after):
        """Remove scheduled unmute when manually removed"""
        sid = before.server.id
        colour = ''.join([randchoice('0123456789ABCDEF') for x in range(6)])
        colour = int(colour, 16)
        role = discord.utils.get(before.server.roles, name=self.role_name)
        if not (sid in self.json and before.id in self.json[sid]):
            return
        if role and role in before.roles and role not in after.roles:
            msg = '**Your Mute in** ***`%s`*** ***was ended early by a moderator/admin Lucky basturd.***' % before.server.name
            if self.json[sid][before.id]['reason']:
                msg += '\n**Reason was:** ' + self.json[sid][before.id]['reason']
            em = discord.Embed(description=msg, colour=discord.Colour(value=colour))
            em.set_thumbnail(url='https://cdn.discordapp.com/attachments/273424151795204107/289528072527413248/talk-xxl.png')
            await self.bot.send_message(after, embed=em)
            self._unmute_data(after)
            return

    async def on_member_join(self, member):
        """Restore mute if muted user leaves/rejoins"""
        sid = member.server.id
        role = discord.utils.get(member.server.roles, name=self.role_name)
        if role:
            self.json = dataIO.load_json(self.location)
            if not (sid in self.json and member.id in self.json[sid]):
                return
            duration = self.json[sid][member.id]['until'] - time.time()
            if duration > 0:
                await self.bot.add_roles(member, role)
                reason = 'Re-Muted For rejoin ***Baba BITTCCHH***. '
                if self.json[sid][member.id]['reason']:
                    reason += self.json[sid][member.id]['reason']
                if member.id not in self.handles[sid]:
                    self.schedule_unmute(duration, member, reason)


def compat_load(path):
    data = dataIO.load_json(path)
    for server, punishments in data.items():
        for user, pdata in punishments.items():
            by = pdata.pop('givenby', None)  # able to read Kownlin json
            by = by if by else pdata.pop('by', None)
            pdata['by'] = by
            pdata['until'] = pdata.pop('until', None)
            pdata['reason'] = pdata.pop('reason', None)
    return data


def check_folder():
    if not os.path.exists('data/mute'):
        log.debug('Creating folder: data/mute')
        os.makedirs('data/mute')


def check_file():
    f = 'data/mute/settings.json'
    if dataIO.is_valid_json(f) is False:
        log.debug('Creating json: settings.json')
        dataIO.save_json(f, {})


def setup(bot):
    check_folder()
    check_file()
    n = mute(bot)
    bot.add_cog(n)
