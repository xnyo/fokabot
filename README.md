# FokaBot
## Asynchronous Ripple chat bot, delta-compatible

### What's this?
This is Ripple's in-game chat bot for delta (our new bancho server), completely standalone. With pep.py
(our previous bancho server), FokaBot was literally baked into the server itself. That solution was kinda handy,
but not very flexible (a simple change to the bot required a restart of the whole bancho server). With delta, we decided
to make FokaBot a completely standalone bot, communicating with delta through IRC and its API. FokaBot is written in
Python with asyncio.

### TODO list
- [x] Bot boilerplate (logging in, commands framework)
- [x] !roll and other general commands
- [x] !faq commands
- [x] !alert/!alertuser
- [x] Moderation commands (!moderated, !kick, !ban, !restrict, !unban, !silence, !removesilence)
- [ ] !system
- [ ] /np support and !bloodcat
- [ ] !last
- [ ] !mp
- [ ] !switchserver (?)

### LICENSE
&copy; 2019, the Ripple team