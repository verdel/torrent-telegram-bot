#!/bin/sh

if [ -f /opt/transmission-telegram-bot/config.yml.j2 ];then
    jinjanate -o /opt/transmission-telegram-bot/config.yml --quiet /opt/transmission-telegram-bot/config.yml.j2
    rm /opt/transmission-telegram-bot/config.yml.j2
fi

python -m transmission_telegram_bot.bot -c /opt/transmission-telegram-bot/config.yml