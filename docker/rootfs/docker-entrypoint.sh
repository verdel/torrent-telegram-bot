#!/bin/sh

if [ -f /opt/transmission-telegram-bot/config.yml.j2 ];then
    j2 --filter /opt/j2cli/env_json.py -o /opt/transmission-telegram-bot/config.yml /opt/transmission-telegram-bot/config.yml.j2
    rm /opt/transmission-telegram-bot/config.yml.j2
fi

python -m transmission_telegram_bot.bot -c /opt/transmission-telegram-bot/config.yml