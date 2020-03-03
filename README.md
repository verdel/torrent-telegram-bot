# Transmission Telegram Bot

What is this?
-------------
With transmission telegram bot, you can manage your Transmission torrent client. You can add, delete and list torrent entry. 

To get started create `config.yml` file with your favourite text editor. Add your bot token ID, allowed user or chat ID (not username), transmission url, username and password etc.

Installation
------------
on most UNIX-like systems, you'll probably need to run the following
`install` commands as root or by using sudo*

**from source**
```console
pip install git+http://github.com/verdel/trasnmission-telegram-bot
```
**or**
```console
git clone git://github.com/verdel/trasnmission-telegram-bot
cd trasnmission-telegram-bot
python setup.py install
```

as a result, the ``ttbot`` executable will be installed into a system ``bin``
directory

Configuration
-------------
To customize bot, create `config.yml`, then add one or more of the variables. For an example, see ``config.example.yml`` in ``conf/`` folder.

Usage
-----
Create telegram bot with **@BotFather**. 
Create transmission telegram bot configuration file. And start you bot.

To start bot use command:
```console
ttbot -c config.yml
```
Now you can start interacting with your bot.

#### Add torrent file to download queque
Just send torrent file to you bot and choose download category. The folder where the files will be uploaded depends on the category you select. The categories and folders that correspond to them are described in the configuration file.

#### List or delete torrent file
Just use reply keyboard button of bot:

**⬇️List Downloading** - List torrents with downloading status

**📄List All** - List all torrents

**❌Delete** - Delete torrent

Contributing
------------

1. Check the open issues or open a new issue to start a discussion around
   your feature idea or the bug you found
2. Fork the repository and make your changes
3. Open a new pull request

If your PR has been waiting a while, feel free to [ping me on Twitter][twitter].

Use this software often? <a href="https://saythanks.io/to/valeksandrov@me.com" target="_blank"><img src="https://img.shields.io/badge/Say%20Thanks-!-1EAEDB.svg" align="center" alt="Say Thanks!"></a>
:smiley:


[twitter]: http://twitter.com/verdel