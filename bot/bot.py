from functools import partial, wraps
import sys
import io
import traceback
import json
import html

from loguru import logger

from telegram import Update, Message, File
from telegram.ext import (
    Application, CallbackContext, ConversationHandler,
    CommandHandler, MessageHandler, filters, ContextTypes
)
from telegram.constants import ParseMode

import seafileapi
import messages_text
from config import (
    TG_TOKEN, SEAFILE_URL, SEAFILE_EMAIL,
    SEAFILE_PASSWORD, SEAFILE_REPO, ALLOWED_IDS,
    DEVELOPER_CHAT_ID
)

UPLOAD_FILES: int = 0


def restricted(func):
    @wraps(func)
    async def wrapped(update, context, *args, **kwargs):
        user_id: int = update.effective_user.id
        if ALLOWED_IDS and user_id not in ALLOWED_IDS:
            logger.debug(f"Unauthorized access denied for {user_id}.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapped


def check_env() -> None:
    variables: tuple = (
        TG_TOKEN,
        SEAFILE_URL,
        SEAFILE_EMAIL,
        SEAFILE_PASSWORD,
        DEVELOPER_CHAT_ID,
    )
    if not all(variables):
        logger.critical('Missing environment variables.')
        sys.exit()


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception while handling an update:", exc_info=context.error)
    tb_list: list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string: str = "".join(tb_list)
    update_str: dict | str = update.to_dict() if isinstance(update, Update) else str(update)
    message: str = (
        f'An exception was raised while handling an update\n'
        f'<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}'
        '</pre>\n\n'
        f'<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n'
        f'<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n'
        f'<pre>{html.escape(tb_string)}</pre>'
    )
    await context.bot.send_message(
        chat_id=DEVELOPER_CHAT_ID,
        text=message,
        parse_mode=ParseMode.HTML
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id: int = update.effective_user.id
    logger.debug(f'{user_id} sent /help or /start.')
    await update.message.reply_text(messages_text.START, parse_mode=ParseMode.HTML)


@restricted
async def link(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id: int = update.effective_user.id
    logger.debug(f'{user_id} sent /link.')
    await update.message.reply_text(messages_text.LINK, parse_mode=ParseMode.HTML)


@restricted
async def upload(update: Update, context: CallbackContext) -> int:
    user_id: int = update.effective_user.id
    logger.debug(f'{user_id} sent /upload. Start uploading files conversation.')
    await update.message.reply_text(messages_text.UPLOAD, parse_mode=ParseMode.HTML)
    return UPLOAD_FILES


async def upload_files(update: Update, context: CallbackContext, repo: seafileapi.Repo) -> None:
    message: Message = await update.message.reply_text(
        messages_text.UPLOAD_START,
        parse_mode=ParseMode.HTML
    )
    if update.effective_message.photo:
        file: File = await update.message.effective_attachment[-1].get_file()
    else:
        file: File = await update.message.effective_attachment.get_file()
    file_name: str = f'{file.file_unique_id}.{file.file_path.split(".")[-1]}'
    logger.debug(f'Start uploading file with name "{file_name}".')
    seafile_dir: seafileapi.SeafDir = repo.get_dir('/')
    try:
        with io.BytesIO() as buff:
            await file.download_to_memory(buff)
            buff.seek(0)
            seafile_dir.upload(buff, file_name)
    except seafileapi.exceptions.ClientHttpError:
        await message.edit_text(messages_text.UPLOAD_ERROR, parse_mode=ParseMode.HTML)
        raise seafileapi.exceptions.ClientHttpError
    except IOError:
        await message.edit_text(messages_text.UPLOAD_ERROR, parse_mode=ParseMode.HTML)
        raise IOError
    logger.debug(f'File with name "{file_name}" uploaded succesfully.')
    await message.edit_text(messages_text.UPLOAD_SUCCESS, parse_mode=ParseMode.HTML)


async def cancel(update: Update, context: CallbackContext) -> int:
    user_id: int = update.effective_user.id
    logger.debug(f'User {user_id} canceled uploading conversation.')
    await update.message.reply_text(messages_text.CANCEL, parse_mode=ParseMode.HTML)
    return ConversationHandler.END


def main() -> None:
    check_env()
    application: Application = Application.builder().token(TG_TOKEN).build()
    client: seafileapi.SeafileApiClient = seafileapi.connect(
        SEAFILE_URL, SEAFILE_EMAIL, SEAFILE_PASSWORD
    )
    repo: seafileapi.Repo = client.repos.get_repo(SEAFILE_REPO)
    conversation_handler: ConversationHandler = ConversationHandler(
        entry_points=[CommandHandler('upload', upload)],
        states={
            UPLOAD_FILES: [MessageHandler(
                (filters.PHOTO | filters.VIDEO | filters.AUDIO | filters.Document.ALL),
                partial(upload_files, repo=repo)
            )]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    application.add_handler(CommandHandler(('start', 'help'), start))
    application.add_handler(CommandHandler('link', link))
    application.add_handler(conversation_handler)
    application.add_error_handler(error_handler)
    logger.info('Bot starts.')
    application.run_polling()
    logger.info('Bot stopped.')


if __name__ == '__main__':
    logger.add(
        'logs/{time}.log',
        format='{time} {level} {message}',
        level='DEBUG',
        rotation='128 MB',
        compression='zip'
    )
    main()
