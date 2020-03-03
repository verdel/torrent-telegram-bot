#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import sys
import time
import traceback
import transmission_telegram_bot.tools as tools
from transmission_telegram_bot.transmission import Transmission
from transmission_telegram_bot.db import DB
from base64 import b64encode
from emoji import emojize
from functools import wraps
from os import path
from threading import Thread
from telegram.ext.dispatcher import run_async
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton


cfg = None
transmission = None
updater = None
logger = None


def restricted(func):
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        chat_id = update.effective_chat.id
        if 'allow_chat' in cfg['telegram']:
            if cfg['telegram']['allow_chat']:
                allowed_chat = any(d['telegram_id'] == chat_id for d in cfg['telegram']['allow_chat'])
            else:
                allowed_chat = False
        else:
            allowed_chat = False

        if allowed_chat:
            return func(update, context, *args, **kwargs)
        else:
            context.bot.sendMessage(chat_id=update.message.chat_id,
                                    text=u'Oops! You are not allowed to interact with this bot.'
                                    )
            return
    return wrapped


@run_async
@restricted
def text_message_action(update, context):
    routes = {u'Downloading': {'func': list_torrent_action, 'kwargs': {'type': 'download'}},
              u'All': {'func': list_torrent_action, 'kwargs': {'type': 'all'}},
              u'Delete': {'func': delete_torrent_action}
              }
    try:
        route = next(v for k, v in routes.items() if k in update.effective_message.text)
    except Exception:
        unknown_command_action(update, context)
    else:
        if 'kwargs' in route:
            route['func'](update, context, **route['kwargs'])
        else:
            route['func'](update, context)


def get_torrents(update, context, **kwargs):
    global transmission
    torrents = []
    try:
        permission = tools.get_torrent_permission(config=cfg, chat_id=update.effective_chat.id)
    except Exception:
        error_action(update, context)
    if permission:
        if permission == 'personal':
            try:
                db = DB(cfg['db']['path'])
            except Exception:
                error_action(update, context)
            else:
                db_torrents = db.get_torrent_by_uid(update.effective_chat.id)
                if db_torrents:
                    for db_entry in db_torrents:
                        torrent = transmission.get_torrent(db_entry[1])
                        torrents.append(torrent)
        elif permission == 'all':
            torrents = transmission.get_torrents()
    return torrents


@run_async
@restricted
def download_torrent_action(update, context):
    keyboard = []
    file = context.bot.getFile(update.message.document.file_id)
    torrent_data = file.download_as_bytearray()
    torrent_data = b64encode(torrent_data).decode('utf-8')
    context.user_data.clear()
    context.user_data.update({'torrent_data': torrent_data})

    for transmission_path in cfg['transmission']['path']:
        keyboard.append([InlineKeyboardButton(transmission_path['category'], callback_data='download:{}'.format(transmission_path['dir']))])
    keyboard.append([InlineKeyboardButton('Cancel', callback_data='download:cancel')])
    try:
        context.bot.sendMessage(chat_id=update.effective_chat.id,
                                text='Which Plex category do you want to use for the downloaded torrent?',
                                reply_markup=InlineKeyboardMarkup(keyboard)
                                )
    except Exception:
        error_action(update, context)


@run_async
@restricted
def download_torrent_logic(update, context):
    global transmission
    callback_data = update.callback_query.data.replace('download:', '')
    if callback_data == 'cancel':
        context.bot.delete_message(message_id=update.callback_query.message.message_id,
                                   chat_id=update.callback_query.message.chat.id
                                   )
    else:
        try:
            result = transmission.add_torrent(torrent_data=context.user_data['torrent_data'], download_dir=callback_data)
        except Exception:
            error_action(update, context)
            context.bot.editMessageText(message_id=update.callback_query.message.message_id,
                                        chat_id=update.effective_chat.id,
                                        text='Error adding torrent file. Try again later.')

        if result:
            context.bot.editMessageText(message_id=update.callback_query.message.message_id,
                                        chat_id=update.effective_chat.id,
                                        text='Torrent "*{}*" added successfully'.format(result.name),
                                        parse_mode='Markdown')
            try:
                db = DB(cfg['db']['path'])
            except Exception:
                error_action(update, context)
            else:
                try:
                    db.add_torrent(update.callback_query.message.chat.id, result.id)
                except Exception:
                    error_action(update, context)

            logger.info('User {} {}({}) added a torrent file {} to the torrent client download queue with the path {}'.format(update.effective_user.first_name,
                                                                                                                              update.effective_user.last_name,
                                                                                                                              update.effective_user.username,
                                                                                                                              result.name,
                                                                                                                              callback_data
                                                                                                                              ))
        else:
            logger.error('An error occurred while adding a torrent file {} to the torrent client queue with the path {} by user {} {}({})'.format(result.name,
                                                                                                                                                  callback_data,
                                                                                                                                                  update.effective_user.first_name,
                                                                                                                                                  update.effective_user.last_name,
                                                                                                                                                  update.effective_user.username
                                                                                                                                                  ))
            context.bot.editMessageText(message_id=update.callback_query.message.message_id,
                                        chat_id=update.effective_chat.id,
                                        text='Error adding torrent file. Try again later.')


@run_async
@restricted
def delete_torrent_action(update, context):
    keyboard = []
    torrents = get_torrents(update, context)
    if len(torrents) > 0:
        for torrent in torrents:
            keyboard.append([InlineKeyboardButton(torrent.name, callback_data='delete:{}'.format(torrent.id))])
        keyboard.append([InlineKeyboardButton('Cancel', callback_data='delete:cancel')])
        try:
            context.bot.sendMessage(chat_id=update.effective_chat.id,
                                    text='Which torrent do you want to delete?',
                                    reply_markup=InlineKeyboardMarkup(keyboard)
                                    )
        except Exception:
            error_action(update, context)
    else:
        context.bot.sendMessage(chat_id=update.effective_chat.id,
                                text='At the moment, there are no torrents that you can delete.'
                                )


@run_async
@restricted
def delete_torrent_logic(update, context):
    global transmission
    callback_data = update.callback_query.data.replace('delete:', '')
    if callback_data == 'cancel':
        context.bot.delete_message(message_id=update.callback_query.message.message_id,
                                   chat_id=update.callback_query.message.chat.id
                                   )
    elif 'confirm' in callback_data:
        callback_data = callback_data.replace('confirm:', '')
        try:
            db = DB(cfg['db']['path'])
        except Exception:
            error_action(update, context)
        else:

            try:
                torrent_name = transmission.get_torrent(callback_data).name
                transmission.remove_torrent(torrent_id=callback_data)
            except Exception:
                error_action(update, context)
                context.bot.editMessageText(message_id=update.callback_query.message.message_id,
                                            chat_id=update.effective_chat.id,
                                            text='An error occurred while deleting the torrent {}. Try again later.'.format(torrent_name))
            else:
                try:
                    db.remove_torrent_by_id(callback_data)
                except Exception:
                    error_action(update, context)
                context.bot.editMessageText(message_id=update.callback_query.message.message_id,
                                            chat_id=update.effective_chat.id,
                                            text='Torrent "*{}*" was successfully deleted'.format(torrent_name),
                                            parse_mode='Markdown')
                logger.info('Torrent {} was successfully deleted by user {} {}({})'.format(torrent_name,
                                                                                           update.effective_user.first_name,
                                                                                           update.effective_user.last_name,
                                                                                           update.effective_user.username
                                                                                           ))
    else:
        try:
            torrent_name = transmission.get_torrent(callback_data).name
        except Exception:
            error_action(update, context)
        else:
            context.bot.editMessageText(message_id=update.callback_query.message.message_id,
                                        chat_id=update.callback_query.message.chat.id,
                                        text='Do you realy want to delete torrent "*{}*"'.format(torrent_name),
                                        reply_markup=make_delete_confirm_keyboard(callback_data),
                                        parse_mode='Markdown'
                                        )


@run_async
@restricted
def list_torrent_action(update, context, **kwargs):
    if 'type' in kwargs and kwargs.get('type') == 'download':
        torrents = []
        torrent_list = get_torrents(update, context, **kwargs)
        for torrent in torrent_list:
            if torrent.status == 'downloading':
                torrents.append(torrent)
    else:
        torrents = get_torrents(update, context, **kwargs)

    if len(torrents) > 0:
        try:
            for torrent in torrents:
                if not torrent.doneDate:
                    try:
                        eta = str(torrent.eta)
                    except ValueError:
                        eta = 'unknown'
                    torrent_info = u'*{}*\r\nStatus: {}\r\nProcent: {}%\r\nSpeed: {}/s\r\nETA: {}\r\nPeers: {}'.format(torrent.name,
                                                                                                                       torrent.status,
                                                                                                                       round(torrent.progress, 2),
                                                                                                                       tools.humanize_bytes(torrent.rateDownload),
                                                                                                                       eta,
                                                                                                                       torrent.peersSendingToUs
                                                                                                                       )
                else:
                    torrent_info = u'*{}*\r\nStatus: {}\r\nSpeed: {}/s\r\nPeers: {}\r\nRatio: {}'.format(torrent.name,
                                                                                                         torrent.status,
                                                                                                         tools.humanize_bytes(torrent.rateUpload),
                                                                                                         torrent.peersGettingFromUs,
                                                                                                         torrent.uploadRatio
                                                                                                         )
                context.bot.sendMessage(chat_id=update.effective_chat.id,
                                        text=torrent_info,
                                        parse_mode='Markdown'
                                        )
        except Exception:
            error_action(update, context)
    else:
        context.bot.sendMessage(chat_id=update.effective_chat.id,
                                text='The torrent list is empty')


def make_main_keyboard():
    custom_keyboard = [[u'{}List Downloading'.format(emojize(':arrow_down:', use_aliases=True))],
                       [u'{}List All'.format(emojize(':page_facing_up:', use_aliases=True))],
                       [u'{}Delete'.format(emojize(':cross_mark:', use_aliases=True))]]
    make_markup = ReplyKeyboardMarkup(custom_keyboard, resize_keyboard=True)
    return make_markup


def make_delete_confirm_keyboard(torrent_id):
    keyboard_array = InlineKeyboardMarkup([[InlineKeyboardButton('Confirm', callback_data='delete:confirm:{}'.format(torrent_id))],
                                           [InlineKeyboardButton('Cancel', callback_data='delete:cancel')]])
    return keyboard_array


@run_async
@restricted
def start_action(update, context):
    context.bot.sendMessage(chat_id=update.effective_chat.id,
                            text=u'Welcome. Now you can start working with the bot.',
                            reply_markup=make_main_keyboard()
                            )


@run_async
@restricted
def help_action(update, context):
    help_text = u'Send torrent file - Add a torrent to the torrent client download queue\r\n{}List Downloading - List download queue\r\n{}List All - List all torrent in the torrent client\r\n{}Delete - Complete delete torrent from torrent client and filesystem'.format(emojize(':arrow_down:', use_aliases=True),
                                                                                                                                                                                                                                                                             emojize(':page_facing_up:', use_aliases=True),
                                                                                                                                                                                                                                                                             emojize(':cross_mark:', use_aliases=True))
    context.bot.sendMessage(chat_id=update.effective_chat.id,
                            text=help_text
                            )


@run_async
@restricted
def unknown_command_action(update, context):
    context.bot.sendMessage(chat_id=update.effective_chat.id,
                            text='Unknown command.')


@run_async
@restricted
def unknown_doctype_action(update, context):
    context.bot.sendMessage(chat_id=update.effective_chat.id,
                            text='I only support working with files with the torrent extension.')


@run_async
def error_action(update, context):
    if update.effective_message:
        text = "Hey. I'm sorry to inform you that an error happened while I tried to handle your update. " \
               "My developer(s) will be notified."
        update.effective_message.reply_text(text)
        trace = ''.join(traceback.format_tb(sys.exc_info()[2]))
        payload = ''
        if update.effective_user:
            payload += f' with the user {(update.effective_user.id, update.effective_user.first_name)}'
        if update.effective_chat:
            payload += f' within the chat <i>{update.effective_chat.title}</i>'
        if update.effective_chat.username:
            payload += f' (@{update.effective_chat.username})'
        text = f"The error {context.error} happened{payload}. The full traceback:\n\n{trace}"
    logger.error(text)


class scheduled_checker_thread(Thread):
    def __init__(self, check_period):
        Thread.__init__(self)
        self.kill_received = False
        self.check_period = check_period

    def run(self):
        while not self.kill_received:
            check_torrent_download_status()
            time.sleep(self.check_period)


def has_live_threads(threads):
    return True in [t.isAlive() for t in threads]


def start_bot():
    updater.start_polling()


def check_torrent_download_status():
    global transmission
    try:
        db = DB(cfg['db']['path'])
    except Exception as exc:
        logger.error(('{}({})'.format(type(exc).__name__, exc)))
    else:
        try:
            torrents = db.list_uncomplete_torrents()
        except Exception as exc:
            logger.error(('{}({})'.format(type(exc).__name__, exc)))
        else:
            if torrents:
                for torrent in torrents:
                    try:
                        task = transmission.get_torrent(torrent[1])
                    except Exception:
                        db.remove_torrent_by_id(torrent[1])
                    else:
                        try:
                            if task.doneDate:
                                response = u'Torrent "*{}*" was successfully downloaded'.format(task.name)
                                db.complete_torrent(torrent[1])
                        except Exception as exc:
                            logger.error(('{}({})'.format(type(exc).__name__, exc)))
                        else:
                            if task.doneDate:
                                global updater
                                try:
                                    updater.bot.sendMessage(chat_id=torrent[0],
                                                            text=response,
                                                            parse_mode='Markdown'
                                                            )
                                except Exception as exc:
                                    logger.error(('{}({})'.format(type(exc).__name__, exc)))


def main():
    global cfg
    global transmission
    global updater
    global logger

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', required=True,
                        help='configuration file')
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()

    logger = tools.init_log(debug=args.debug)

    if not path.isfile(args.config):
        print('Transmission telegram bot configuration file {} not found'.format(args.config))
        logger.error('Transmission telegram bot configuration file {} not found'.format(args.config))
        sys.exit()

    logger.info('Starting transmission telegram bot')

    try:
        cfg = tools.get_config(args.config)
    except Exception as exc:
        logger.error('Config file error: {}'.format(exc))
        sys.exit(1)

    try:
        transmission = Transmission(address=cfg['transmission']['address'],
                                    port=cfg['transmission']['port'],
                                    user=cfg['transmission']['user'],
                                    password=cfg['transmission']['password'],
                                    debug=args.debug)
    except Exception as exc:
        logger.error('Transmission connection error: {}'.format(exc))

    try:
        DB(cfg['db']['path'])
    except Exception as exc:
        logger.error('SQLite DB connection error: {}'.format(exc))

    if 'proxy' in cfg['telegram']:
        REQUEST_KWARGS = {
            'proxy_url': cfg['telegram']['proxy']['url'],
            'urllib3_proxy_kwargs': {
                'username': cfg['telegram']['proxy']['username'],
                'password': cfg['telegram']['proxy']['password'],
            }
        }
        updater = Updater(token=cfg['telegram']['token'], use_context=True, request_kwargs=REQUEST_KWARGS)
    else:
        updater = Updater(token=cfg['telegram']['token'], use_context=True)

    dp = updater.dispatcher

    start_handler = CommandHandler('start', start_action)
    help_handler = CommandHandler('help', help_action)
    download_torrent_handler = MessageHandler(Filters.document.mime_type("application/x-bittorrent"), download_torrent_action)
    unknown_doctype_handler = MessageHandler(~ Filters.document.mime_type("application/x-bittorrent"), unknown_doctype_action)
    text_message_handler = MessageHandler(Filters.text, text_message_action)
    unknown_command_handler = MessageHandler(Filters.command, unknown_command_action)

    dp.add_handler(CallbackQueryHandler(callback=download_torrent_logic, pattern='.*download.*'))
    dp.add_handler(CallbackQueryHandler(callback=delete_torrent_logic, pattern='.*delete.*'))
    dp.add_handler(start_handler)
    dp.add_handler(help_handler)
    dp.add_handler(download_torrent_handler)
    dp.add_handler(text_message_handler)
    dp.add_handler(unknown_command_handler)
    dp.add_handler(unknown_doctype_handler)
    dp.add_error_handler(error_action)

    if 'schedule' in cfg:
        if 'check_period' in cfg['schedule']:
            check_period = int(cfg['schedule']['check_period'])
        else:
            check_period = 60
    else:
        check_period = 60

    t1 = Thread(target=start_bot)
    t1.start()

    t2 = scheduled_checker_thread(check_period)
    t2.start()

    threads = [t1, t2]

    while has_live_threads(threads):
        try:
            [t.join(1) for t in threads if t is not None and t.isAlive()]
        except KeyboardInterrupt:
            print("Sending kill to threads...")
            for t in threads:
                t.kill_received = True
            try:
                updater.stop()
            except Exception as exc:
                logger.error('%s' % ('{}({})'.format(type(exc).__name__, exc)))
                continue
    print('Exited')
    sys.exit(0)


if __name__ == '__main__':
    main()
