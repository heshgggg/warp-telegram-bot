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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет приветственное сообщение при вызове команды /start."""
    await update.message.reply_text(
        "Добро пожаловать! Я могу генерировать для вас конфигурации WireGuard, используя Cloudflare WARP. "
        "Просто отправьте команду /generate."
    )

async def generate_wg_config(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Генерирует и отправляет файл WireGuard .conf."""
    message = await update.message.reply_text("Генерирую ваш конфиг WireGuard, пожалуйста, подождите...")
    chat_id = update.message.chat_id
    temp_file_path = None # Инициализируем, чтобы избежать UnboundLocalError

    try:
        config_string = await generate_wireguard_config_full()

        # Создаём временный файл для .conf
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.conf', delete=False) as temp_file:
            temp_file.write(config_string)
            temp_file_path = temp_file.name

        # Отправляем документ
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
            text=f"Извините, не удалось сгенерировать конфиг прямо сейчас."
        )
    except Exception as e:
        logger.exception(f"Произошла непредвиденная ошибка для пользователя {chat_id}:")
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message.message_id,
            text="При генерации вашего конфига произошла непредвиденная ошибка. Пожалуйста, попробуйте позже."
        )
    finally:
        # Удаляем временный файл
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

def main() -> None:
    """Запускает бота."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не найден в файле .env. Пожалуйста, установите его.")
        return

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("generate", generate_wg_config))

    # Запускаем бота, пока пользователь не нажмёт Ctrl-C
    logger.info("Бот запущен. Нажмите Ctrl-C для остановки.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()