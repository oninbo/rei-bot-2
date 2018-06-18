"""
Telegram bot module
"""

import time

import emoji
import os.path
import ssl
import telebot
from aiohttp import web
from configparser import ConfigParser

import logger
import messages
import texting_ai

CONFIG = ConfigParser()
CONFIG.read(os.path.join('data', 'config.ini'))

# webhook url
URL_BASE = "https://{}:{}".format(CONFIG['server']['ip'], CONFIG.getint('server', 'port'))
URL_PATH = "/{}/".format(CONFIG['telegram bot']['token'])

telebot.logger = logger.get_logger(__file__)

LOGGER = telebot.logger

BOT = telebot.TeleBot(CONFIG['telegram bot']['token'])

# server that will listen for new messages
APP = web.Application()

# time for bot to be "typing" in seconds
TYPING_TIME: int = 2

PRIVATE_MESSAGE = 'private'
TYPING = 'typing'
DOWN_VOTE = 'down vote'
UP_VOTE = 'up vote'


def set_proxy() -> None:
    """
    Sets the proxy
    :return: None
    """
    enabled = CONFIG.getboolean('proxy', 'enabled')
    if enabled:
        address = CONFIG['proxy']['address']
        port = CONFIG['proxy']['port']
        proxy_type = CONFIG['proxy']['type']
        if proxy_type == 'http':
            telebot.apihelper.proxy = {'http': f'http://{address}:{port}'}
        elif proxy_type == 'socks5':
            user = CONFIG['proxy']['user']
            password = CONFIG['proxy']['port']
            telebot.apihelper.proxy = {'https': f'socks5://{user}:{password}@{address}:{port}'}


set_proxy()


async def handle(request: web.Request) -> web.Response:
    """
    Process webhook calls
    :param request: request to handle
    :return: response for sender
    """
    if request.match_info.get('token') == BOT.token:
        request_body_dict = await request.json()
        update = telebot.types.Update.de_json(request_body_dict)
        BOT.process_new_updates([update])
        response = web.Response()
    else:
        response = web.Response(status=403)

    return response

APP.router.add_post('/{token}/', handle)


@BOT.message_handler(commands=['start'])
@BOT.message_handler(commands=['ask'])
def command_reply(message: telebot.types.Message) -> None:
    """
    Handler for /start and /ask commands
    Sends message back to user that sent /start or /ask command
    :param message: received message by bot from user
    :return: None
    """
    # TODO for /ask implement replying on previous message

    reply_message(message, texting_ai.PIPELINE.get_reply(message.text, no_empty_reply=True),
                  False if message.chat.type == PRIVATE_MESSAGE else True)


# Handle text messages
@BOT.message_handler(func=lambda message: True, content_types=['text'])
def text_reply(message: telebot.types.Message) -> None:
    """
    Handler for private and group text messages from users
    :param message: received message by bot from user
    :return: None
    """
    text = message.text
    is_reply = True
    no_empty_reply = True

    # if private message
    if message.chat.type == PRIVATE_MESSAGE:
        is_reply = False
    # TODO add forward handling
    # if group message and not a reply on bot's message
    elif not check_reply(BOT.get_me().id, message):
        no_empty_reply = False

    reply = texting_ai.PIPELINE.get_reply(text, no_empty_reply=no_empty_reply)
    if reply:
        reply_message(message, reply, is_reply)


def check_reply(_id: int, message: telebot.types.Message) -> bool:
    """
    Check if the message is a reply on given user's message
    :param _id: id of a user whose message was replied to
    :param message: message to check
    :return: True if message is a reply False otherwise
    """
    return message.reply_to_message and message.reply_to_message.from_user.id == _id


def make_voting_keyboard(likes: int, dislikes: int) -> telebot.types.InlineKeyboardMarkup:
    """
    Makes inline keyboard for grading message by likes and dislikes
    :param likes: number of likes to display
    :param dislikes: number of dislikes to display
    :return: keyboard that can be attached to message
    """
    keyboard = telebot.types.InlineKeyboardMarkup()
    callback_button_dislike = telebot.types.InlineKeyboardButton(
        text=f"{emoji.emojize(':thumbs_down:')} {dislikes}",
        callback_data=DOWN_VOTE)
    callback_button_like = telebot.types.InlineKeyboardButton(
        text=f"{emoji.emojize(':thumbs_up:')} {likes}",
        callback_data=UP_VOTE)
    keyboard.row(callback_button_dislike, callback_button_like)

    return keyboard


def reply_message(message: telebot.types.Message, reply: str, is_reply: bool) -> None:
    """
    Sends reply on message
    :param message: input message
    :param reply: text reply on message
    :param is_reply: True if reply_to() method should be used or False if send_message()
    :return: None
    """
    if not reply:
        LOGGER.error("empty reply in reply_message()")
        return

    if messages.CURRENT_GRADING_MESSAGE:
        old_message: telebot.types.Message = messages.CURRENT_GRADING_MESSAGE.message
        BOT.edit_message_reply_markup(chat_id=old_message.chat.id,
                                      message_id=old_message.message_id, reply_markup=None)

    BOT.send_chat_action(message.chat.id, TYPING)
    time.sleep(TYPING_TIME)

    keyboard = make_voting_keyboard(0, 0)

    if is_reply:
        new_message = BOT.reply_to(message, reply, reply_markup=keyboard)
    else:
        new_message = BOT.send_message(message.chat.id, reply, reply_markup=keyboard)

    messages.CURRENT_GRADING_MESSAGE = messages.GradableMessage(new_message, reply)


@BOT.callback_query_handler(func=lambda call: True)
def callback_inline(call: telebot.types.CallbackQuery) -> None:
    """Callback that
    is executed when a user presses a button on the message inline keyboard"""

    grading_message: messages.GradableMessage = messages.CURRENT_GRADING_MESSAGE
    message: telebot.types.Message = call.message

    # if the message is not the one that is currently grading
    # then remove keyboard
    if not grading_message or message.message_id != grading_message.message.message_id:
        BOT.edit_message_reply_markup(chat_id=message.chat.id,
                                      message_id=message.message_id, reply_markup=None)
        return

    if call.data in {DOWN_VOTE, UP_VOTE}:
        user_id = call.from_user.id
        if call.data == UP_VOTE:
            grading_message.up_vote(user_id)
        elif call.data == DOWN_VOTE:
            grading_message.down_vote(user_id)
        keyboard = make_voting_keyboard(grading_message.get_likes_num(), grading_message.get_dislikes_num())
        BOT.edit_message_reply_markup(chat_id=message.chat.id, message_id=message.message_id,
                                      reply_markup=keyboard)


# Remove webhook, it fails sometimes the set if there is a previous webhook
BOT.remove_webhook()

# Set webhook
BOT.set_webhook(url=URL_BASE + URL_PATH, certificate=open(CONFIG['ssl']['certificate'], 'r'))

# Build ssl context
CONTEXT = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
CONTEXT.load_cert_chain(CONFIG['ssl']['certificate'], CONFIG['ssl']['private key'])

# Start aiohttp server
web.run_app(
    APP,
    host=CONFIG['server']['ip'],
    port=CONFIG['server']['port'],
    ssl_context=CONTEXT,
)
