import argparse
import sys
import traceback
from base64 import b64decode, b64encode
from functools import wraps
from pathlib import Path
from textwrap import dedent
from typing import Coroutine

import sentry_sdk
from emoji import emojize
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    request,
)
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

import transmission_telegram_bot.tools as tools
from transmission_telegram_bot import _version
from transmission_telegram_bot.db import DB
from transmission_telegram_bot.transmission import Transmission


def restricted(func):
    @wraps(func)
    async def wrapped(update, context, *args, **kwargs):
        chat_id = update.effective_chat.id
        if "allow_chat" in cfg["telegram"]:
            if cfg["telegram"]["allow_chat"]:
                allowed_chat = any(d["telegram_id"] == chat_id for d in cfg["telegram"]["allow_chat"])
            else:
                allowed_chat = False
        else:
            allowed_chat = False

        if allowed_chat:
            return await func(update, context, *args, **kwargs)
        else:
            await context.bot.send_message(
                chat_id=update.message.chat_id,
                text="Oops! You are not allowed to interact with this bot.",
            )
            return

    return wrapped


@restricted
async def text_message_action(update, context):
    routes = {
        "Downloading": {"func": list_torrent_action, "kwargs": {"type": "download"}},
        "All": {"func": list_torrent_action, "kwargs": {"type": "all"}},
        "Delete": {"func": delete_torrent_action},
    }
    try:
        route = next(v for k, v in routes.items() if k in update.effective_message.text)
    except Exception:
        await unknown_command_action(update, context)
    else:
        if "kwargs" in route:
            await route["func"](update, context, **route["kwargs"])
        else:
            await route["func"](update, context)


async def get_torrents(update, context, **kwargs):
    global transmission
    torrents = []
    try:
        permission = tools.get_torrent_permission(config=cfg, chat_id=update.effective_chat.id)
    except Exception:
        await error_action(update, context)
        return []
    if permission:
        if permission == "personal":
            try:
                db = await DB.create(cfg["db"]["path"])
            except Exception:
                await error_action(update, context)
            else:
                db_torrents = await db.get_torrent_by_uid(update.effective_chat.id)
                if db_torrents:
                    for db_entry in db_torrents:
                        torrent = transmission.get_torrent(int(db_entry[1]))
                        torrents.append(torrent)
        elif permission == "all":
            torrents = transmission.get_torrents()
    return torrents


@restricted
async def download_torrent_action(update, context):
    keyboard = []
    file = await context.bot.getFile(update.message.document.file_id)
    torrent_data = await file.download_as_bytearray()
    torrent_data = b64encode(torrent_data).decode("utf-8")
    context.user_data.clear()
    context.user_data.update({"torrent_data": torrent_data})
    category = tools.get_torrent_category(config=cfg, chat_id=update.effective_chat.id)

    for transmission_path in cfg["transmission"]["path"]:
        if category:
            if transmission_path["category"] in category:
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            transmission_path["category"],
                            callback_data=f'download:{transmission_path["dir"]}',
                        )
                    ]
                )
        else:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        transmission_path["category"],
                        callback_data=f'download:{transmission_path["dir"]}',
                    )
                ]
            )
    keyboard.append([InlineKeyboardButton("Cancel", callback_data="download:cancel")])
    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Which Plex category do you want to use for the downloaded torrent?",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    except Exception:
        await error_action(update, context)


@restricted
async def download_torrent_logic(update, context):
    global transmission
    callback_data = update.callback_query.data.replace("download:", "")
    if callback_data == "cancel":
        await context.bot.delete_message(
            message_id=update.callback_query.message.message_id,
            chat_id=update.callback_query.message.chat.id,
        )
    else:
        try:
            result = transmission.add_torrent(
                torrent_data=b64decode(context.user_data["torrent_data"]),
                download_dir=callback_data,
            )
        except Exception:
            await error_action(update, context)
            await context.bot.editMessageText(
                message_id=update.callback_query.message.message_id,
                chat_id=update.effective_chat.id,
                text="Error adding torrent file. Try again later.",
            )
            return

        if result:
            await context.bot.editMessageText(
                message_id=update.callback_query.message.message_id,
                chat_id=update.effective_chat.id,
                text=f'Torrent "*{result.name}*" added successfully',
                parse_mode="Markdown",
            )
            try:
                db = await DB.create(cfg["db"]["path"])
            except Exception:
                await error_action(update, context)
            else:
                try:
                    await db.add_torrent(update.callback_query.message.chat.id, str(result.id))
                except Exception:
                    await error_action(update, context)

            logger.info(
                f"User {update.effective_user.first_name} "
                f"{update.effective_user.last_name}({update.effective_user.username}) "
                f"added a torrent file {result.name} to the torrent client download queue "
                f"with the path {callback_data}"
            )
        else:
            logger.error(
                f"An error occurred while adding a torrent file {result.name} "
                f"to the torrent client queue with the path {callback_data} "
                f"by user {update.effective_user.first_name} "
                f"{update.effective_user.last_name} ({update.effective_user.username})"
            )
            await context.bot.editMessageText(
                message_id=update.callback_query.message.message_id,
                chat_id=update.effective_chat.id,
                text="Error adding torrent file. Try again later.",
            )


@restricted
async def delete_torrent_action(update, context):
    keyboard = []
    torrents = await get_torrents(update, context)
    if len(torrents) > 0:
        for torrent in torrents:
            keyboard.append([InlineKeyboardButton(torrent.name, callback_data=f"delete:{torrent.id}")])
        keyboard.append([InlineKeyboardButton("Cancel", callback_data="delete:cancel")])
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Which torrent do you want to delete?",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        except Exception:
            await error_action(update, context)
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="At the moment, there are no torrents that you can delete.",
        )


@restricted
async def delete_torrent_logic(update, context):  # noqa: C901
    global transmission
    callback_data: str = update.callback_query.data.replace("delete:", "")
    if callback_data == "cancel":
        await context.bot.delete_message(
            message_id=update.callback_query.message.message_id,
            chat_id=update.callback_query.message.chat.id,
        )
    elif "confirm" in callback_data:
        callback_data = callback_data.replace("confirm:", "")
        try:
            db = await DB.create(cfg["db"]["path"])
        except Exception:
            await error_action(update, context)
        else:
            torrent_name = ""
            try:
                torrent_name = transmission.get_torrent(int(callback_data)).name
                transmission.remove_torrent(torrent_id=int(callback_data))
            except Exception:
                await error_action(update, context)
                if torrent_name != "":
                    await context.bot.editMessageText(
                        message_id=update.callback_query.message.message_id,
                        chat_id=update.effective_chat.id,
                        text=f"An error occurred while deleting the torrent {torrent_name}. Try again later.",
                    )
            else:
                try:
                    await db.remove_torrent_by_id(callback_data)
                except Exception:
                    await error_action(update, context)
                await context.bot.editMessageText(
                    message_id=update.callback_query.message.message_id,
                    chat_id=update.effective_chat.id,
                    text=f'Torrent "*{torrent_name}*" was successfully deleted',
                    parse_mode="Markdown",
                )
                logger.info(
                    f"Torrent {torrent_name} was successfully deleted by user "
                    f"{update.effective_user.first_name} {update.effective_user.last_name} "
                    f"({update.effective_user.username})"
                )
    else:
        try:
            torrent_name = transmission.get_torrent(int(callback_data)).name
        except Exception:
            await error_action(update, context)
        else:
            await context.bot.editMessageText(
                message_id=update.callback_query.message.message_id,
                chat_id=update.callback_query.message.chat.id,
                text=f'Do you realy want to delete torrent "*{torrent_name}*"',
                reply_markup=make_delete_confirm_keyboard(callback_data),
                parse_mode="Markdown",
            )


@restricted
async def list_torrent_action(update, context, **kwargs):
    if "type" in kwargs and kwargs.get("type") == "download":
        torrents = []
        torrent_list = await get_torrents(update, context, **kwargs)
        for torrent in torrent_list:
            if torrent.status == "downloading":
                torrents.append(torrent)
    else:
        torrents = await get_torrents(update, context, **kwargs)

    if len(torrents) > 0:
        try:
            for torrent in torrents:
                if not torrent.done_date:
                    try:
                        eta = str(torrent.eta)
                    except ValueError:
                        eta = "unknown"
                    torrent_info = dedent(
                        f"""
                        *{torrent.name}*
                        Status: {torrent.status}
                        Procent: {round(torrent.progress, 2)}%
                        Speed: {tools.humanize_bytes(torrent.rate_download)}/s
                        ETA: {eta}
                        Peers: {torrent.peers_sending_to_us}
                        """
                    )
                else:
                    torrent_info = dedent(
                        f"""
                        *{torrent.name}*
                        Status: {torrent.status}
                        Speed: {tools.humanize_bytes(torrent.rate_upload)}/s
                        Peers: {torrent.peers_getting_from_us}
                        Ratio: {torrent.upload_ratio}
                        """
                    )
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=torrent_info,
                    parse_mode="Markdown",
                )
        except Exception:
            await error_action(update, context)
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="The torrent list is empty")


def make_main_keyboard():
    custom_keyboard = [
        [f'{emojize(":arrow_down:", language="alias")}List Downloading'],
        [f'{emojize(":page_facing_up:", language="alias")}List All'],
        [f'{emojize(":cross_mark:", language="alias")}Delete'],
    ]
    make_markup = ReplyKeyboardMarkup(custom_keyboard, resize_keyboard=True)
    return make_markup


def make_delete_confirm_keyboard(torrent_id):
    keyboard_array = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Confirm", callback_data=f"delete:confirm:{torrent_id}")],
            [InlineKeyboardButton("Cancel", callback_data="delete:cancel")],
        ]
    )
    return keyboard_array


@restricted
async def start_action(update, context):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Welcome. Now you can start working with the bot.",
        reply_markup=make_main_keyboard(),
    )


@restricted
async def help_action(update, context):
    help_text = dedent(
        f"""
    Send torrent file - Add a torrent to the torrent client download queue
    {emojize(":arrow_down:", language="alias")}List Downloading - List download queue
    {emojize(":page_facing_up:", language="alias")}List All - List all torrent in the torrent client
    {emojize(":cross_mark:", language="alias")}Delete - Complete delete torrent from torrent client and filesystem
    """
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=help_text)


@restricted
async def unknown_command_action(update, context):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Unknown command.")


@restricted
async def unknown_doctype_action(update, context):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="I only support working with files with the torrent extension.",
    )


async def error_action(update, context):
    if update is None:
        logger.error(context.error)
        return

    if update.effective_message:
        text = "Hey. I'm sorry to inform you that an error happened while I tried to handle your update."
        await update.effective_message.reply_text(text)
        trace = "".join(traceback.format_tb(sys.exc_info()[2]))
        payload = ""
        if update.effective_user:
            payload += f" with the user {(update.effective_user.id, update.effective_user.first_name, update.effective_user.last_name)}"
        if update.effective_chat.username:
            payload += f" (@{update.effective_chat.username})"
        text = f"The error happened{payload}. The full traceback:\n\n{trace}"
        logger.error(text)


async def check_torrent_download_status(context):  # noqa: C901
    global transmission
    global db

    if isinstance(db, Coroutine):
        db = await db

    try:
        torrents = await db.list_uncomplete_torrents()
    except Exception as exc:
        logger.error(f"{type(exc).__name__}({exc})")
    else:
        if torrents:
            for torrent in torrents:
                try:
                    task = transmission.get_torrent(int(torrent[1]))
                except Exception:
                    await db.remove_torrent_by_id(torrent[1])
                else:
                    try:
                        if task.done_date:
                            await db.complete_torrent(torrent[1])
                    except Exception as exc:
                        logger.error(f"{type(exc).__name__}({exc})")
                    else:
                        if task.done_date:
                            response = f'Torrent "*{task.name}*" was successfully downloaded'
                            try:
                                notify_flag = False
                                try:
                                    chat = cfg["telegram"]["allow_chat"].get(torrent[0])
                                except Exception:
                                    notify_flag = False
                                else:
                                    if chat["notify"] == "personal":
                                        notify_flag = True
                                    if notify_flag:
                                        context.bot.send_message(
                                            chat_id=torrent[0],
                                            text=response,
                                            parse_mode="Markdown",
                                        )

                                notify_about_all = [
                                    chat["telegram_id"]
                                    for chat in cfg["telegram"]["allow_chat"]
                                    if chat["notify"] == "all"
                                ]
                                if notify_about_all:
                                    for telegram_id in notify_about_all:
                                        await context.bot.send_message(
                                            chat_id=telegram_id,
                                            text=response,
                                            parse_mode="Markdown",
                                        )
                            except Exception as exc:
                                logger.error(f"{type(exc).__name__}({exc})")


def main():
    global cfg
    global transmission
    global db
    global logger

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", required=True, help="configuration file")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    logger = tools.init_log(debug=args.debug)

    if not Path(args.config).is_file():
        logger.error(f"Transmission telegram bot configuration file {args.config} not found")
        sys.exit()

    logger.info("Starting transmission telegram bot")

    try:
        cfg = tools.get_config(args.config)
    except Exception as exc:
        logger.error(f"Config file error: {exc}")
        sys.exit(1)

    if "sentry" in cfg:
        sentry_sdk.init(
            dsn=cfg["sentry"]["dsn"],
            environment=cfg["sentry"]["environment"],
            release=_version.__version__,
            attach_stacktrace=True,
        )

    try:
        transmission = Transmission(
            address=cfg["transmission"]["address"],
            port=cfg["transmission"]["port"],
            user=cfg["transmission"]["user"],
            password=cfg["transmission"]["password"],
        )
    except Exception as exc:
        logger.error(f"Transmission connection error: {exc}")
        sys.exit(1)

    try:
        db = DB.create(cfg["db"]["path"])
    except Exception as exc:
        logger.error(f"{type(exc).__name__}({exc})")
        sys.exit(1)

    application = ApplicationBuilder().token(cfg["telegram"]["token"])

    if "proxy" in cfg["telegram"]:
        request_instance = request.HTTPXRequest(proxy_url=cfg["telegram"]["proxy"]["url"])
        application.request(request_instance).get_updates_request(request_instance)

    application = application.build()
    job_queue = application.job_queue

    start_handler = CommandHandler("start", start_action)
    help_handler = CommandHandler("help", help_action)
    download_torrent_handler = MessageHandler(
        filters.Document.MimeType("application/x-bittorrent"), download_torrent_action
    )
    unknown_doctype_handler = MessageHandler(
        ~filters.Document.MimeType("application/x-bittorrent"), unknown_doctype_action
    )
    text_message_handler = MessageHandler(filters.TEXT, text_message_action)
    unknown_command_handler = MessageHandler(filters.COMMAND, unknown_command_action)

    application.add_handler(CallbackQueryHandler(callback=download_torrent_logic, pattern=".*download.*"))
    application.add_handler(CallbackQueryHandler(callback=delete_torrent_logic, pattern=".*delete.*"))
    application.add_handler(start_handler)
    application.add_handler(help_handler)
    application.add_handler(download_torrent_handler)
    application.add_handler(text_message_handler)
    application.add_handler(unknown_command_handler)
    application.add_handler(unknown_doctype_handler)
    application.add_error_handler(error_action)

    if "schedule" in cfg:
        if "check_period" in cfg["schedule"]:
            check_period = int(cfg["schedule"]["check_period"])
        else:
            check_period = 60
        if "max_instances" in cfg["schedule"]:
            max_instances = int(cfg["schedule"]["max_instances"])
        else:
            max_instances = 1
    else:
        check_period = 60
        max_instances = 1

    if job_queue:
        job_queue.run_repeating(
            check_torrent_download_status,
            interval=check_period,
            first=10,
            job_kwargs={"max_instances": max_instances},
        )
    application.run_polling()
    db.close()


if __name__ == "__main__":
    main()
