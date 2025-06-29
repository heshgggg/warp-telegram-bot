import logging
import asyncio
import tempfile
import os

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from config import TELEGRAM_BOT_TOKEN
from wireguard_generator import generate_wireguard_config_full, WireGuardGeneratorError

# Включаем логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

user_generation_status = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Добро пожаловать! Я могу генерировать для вас конфигурации WireGuard, используя Cloudflare WARP. "
        "Просто отправьте команду /generate."
    )


async def _generate_and_send_config(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id

    # Проверка, если уже идет генерация
    if user_generation_status.get(chat_id):
        await update.message.reply_text("Генерация уже выполняется. Пожалуйста, подождите завершения текущей задачи.")
        return

    user_generation_status[chat_id] = True  # Устанавливаем флаг генерации
    message = await update.message.reply_text("Генерирую ваш конфиг WireGuard, пожалуйста, подождите...")
    temp_file_path = None

    try:
        config_string = await generate_wireguard_config_full()

        with tempfile.NamedTemporaryFile(mode='w+', suffix='.conf', delete=False) as temp_file:
            temp_file.write(config_string)
            temp_file_path = temp_file.name

        await context.bot.send_document(
            chat_id=chat_id,
            document=open(temp_file_path, 'rb'),
            filename="warp_wireguard.conf",
            caption="Вот ваш файл конфигурации WireGuard."
        )
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message.message_id,
            text="Ваша конфигурация WireGuard была сгенерирована и отправлена!"
        )

    except WireGuardGeneratorError as e:
        logger.error(f"Ошибка генерации конфига для пользователя {chat_id}: {e}")
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message.message_id,
            text="Извините, не удалось сгенерировать конфиг прямо сейчас."
        )
    except Exception as e:
        logger.exception(f"Произошла непредвиденная ошибка для пользователя {chat_id}:")
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message.message_id,
            text="При генерации вашего конфига произошла непредвиденная ошибка. Пожалуйста, попробуйте позже."
        )
    finally:
        user_generation_status[chat_id] = False  # Сбрасываем флаг
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)



async def generate_wg_config(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Запускаем задачу параллельно, чтобы не блокировать другие
    asyncio.create_task(_generate_and_send_config(update, context))


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не найден в файле .env. Пожалуйста, установите его.")
        return

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("generate", generate_wg_config))

    logger.info("Бот запущен. Нажмите Ctrl-C для остановки.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
