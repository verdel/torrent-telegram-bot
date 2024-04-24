#!/bin/sh

if [ -f /opt/torrent-telegram-bot/config.yml.j2 ];then
    jinjanate -o /opt/torrent-telegram-bot/config.yml --quiet /opt/torrent-telegram-bot/config.yml.j2
    rm /opt/torrent-telegram-bot/config.yml.j2
fi

python -m torrent_telegram_bot.bot -c /opt/torrent-telegram-bot/config.yml