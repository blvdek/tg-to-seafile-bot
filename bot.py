from functools import partial
import os
import sys
import json
import io

from loguru import logger
from dotenv import load_dotenv
from requests.exceptions import RequestException

from telegram import Update
from telegram.ext import Application, CallbackContext, ConversationHandler, CommandHandler, MessageHandler, filters
from telegram.constants import ParseMode

import seafileapi


load_dotenv()

TG_TOKEN: str | None = os.getenv('TG_TOKEN')
SEAFILE_URL: str | None = os.getenv('SEAFILE_URL')
SEAFILE_EMAIL: str | None = os.getenv('SEAFILE_EMAIL')
SEAFILE_PASSWORD: str | None = os.getenv('SEAFILE_PASSWORD')
SEAFILE_REPO: str | None = os.getenv('SEAFILE_REPO')

UPLOAD_FILES: int = 0
with open('messages_text.json', 'rb') as file:
    MESSAGES_TEXT: dict = json.load(file)


def check_env() -> None:
    variables = (
        TG_TOKEN,
        SEAFILE_URL,
        SEAFILE_EMAIL,
        SEAFILE_PASSWORD,
    )
    if not all(variables):
        logger.critical('Missing environment variables.')
        sys.exit()


async def upload(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    logger.debug(f'{user.id} sent /upload. Start uploading files conversation.')
    await update.message.reply_text(MESSAGES_TEXT['upload'])
    return UPLOAD_FILES


async def upload_files(update: Update, context: CallbackContext, repo: seafileapi.Repo) -> int:
    message = await update.message.reply_text(MESSAGES_TEXT['upload_file_start'], parse_mode=ParseMode.HTML)
    if update.effective_message.photo:
        file = await update.message.effective_attachment[-1].get_file()
    else:
        file = await update.message.effective_attachment.get_file()
    file_name: str = f'{file.file_unique_id}.{file.file_path.split(".")[-1]}'
    logger.debug(f'Start uploading file with name "{file_name}".')
    seafile_dir = repo.get_dir('/')
    try:
        with io.BytesIO() as buff:
            await file.download_to_memory(buff)
            buff.seek(0)
            seafile_dir.upload(buff, file_name)
    except RequestException:
        raise RequestException
    except IOError:
        raise IOError
    logger.debug(f'File with name "{file_name}" uploaded succesfully.')
    await message.edit_text(MESSAGES_TEXT['upload_file_success'])
    return ConversationHandler.END


async def cancel(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    logger.debug(f'User {user.id} canceled the conversation.')
    await update.message.reply_text(MESSAGES_TEXT['cancel'])
    return ConversationHandler.END



def main() -> None:
    check_env()
    application: Application = Application.builder().token(TG_TOKEN).build()
    client: seafileapi.SeafileApiClient = seafileapi.connect(SEAFILE_URL, SEAFILE_EMAIL, SEAFILE_PASSWORD)
    repo: seafileapi.Repo = client.repos.get_repo(SEAFILE_REPO)
    conversation_handler: ConversationHandler = ConversationHandler(
        entry_points=[CommandHandler('upload', upload)],
        states={
            UPLOAD_FILES: [MessageHandler(filters.PHOTO, partial(upload_files, repo=repo))]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    application.add_handler(conversation_handler)
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
