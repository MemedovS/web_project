#config_reader.py

from aiogram.client.default import DefaultBotProperties
from aiogram import Bot
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from .datadase.engine import create_db, drop_db

async def on_startup():
    run_param = False  # Если True, база данных будет пересоздана
    if run_param:
        await drop_db()  # Удалить существующую базу данных

    await create_db()  # Создать базу данных


async def on_shutdown():
    print("Бот завершает работу")



class Settings(BaseSettings):
    token: SecretStr
    model_config = SettingsConfigDict(
        env_file='.env', env_file_encoding='utf-8', extra="ignore"
    )


secrets = Settings()

bot = Bot(
    token=secrets.token.get_secret_value(),
    default=DefaultBotProperties(parse_mode="HTML"),
)
