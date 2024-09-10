import os
import pytz
from dotenv import load_dotenv

from aiogram import Router, types
from aiogram.filters import CommandStart,Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramAPIError
from datetime import datetime, timedelta
from bot_send.datadase.engine import session_maker
from bot_send.datadase.models import ChannelVisits
from datetime import datetime, timezone
from bot_send.app.handler_text import *

router = Router()

user_data = {}
load_dotenv()

ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")
CRYPTO_WALLET_ADDRESS = os.getenv("CRYPTO_WALLET_ADDRESS")
PAYMENT_URL = os.getenv("PAYMENT_URL")




def get_local_time():
    local_tz = pytz.timezone('Europe/Moscow')
    utc_now = datetime.now(timezone.utc)  # Текущее время в UTC с временной зоной
    local_now = utc_now.astimezone(local_tz)
    return local_now.replace(microsecond=0)


async def send_welcome_message(bot, chat_id, username):
    photo_file_id = 'AgACAgIAAxkBAAICqmbgL_VxUJkjogRZBrYgJDHmOlw7AAKQ4zEbVJsAAUuseFx6Cvu_jgEAAwIAA3kAAzYE'

    try:
        photo_message = await bot.send_photo(chat_id=chat_id, photo=photo_file_id)
        print(f"Фото отправлено пользователю {chat_id}")
    except TelegramAPIError as e:
        print(f"Ошибка при отправке фото: {e}")
        photo_message = None

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Получить бесплатную консультацию 🚀", callback_data="free_consultation")],
        [InlineKeyboardButton(text="💼 Выбрать мастер-класс", callback_data="select_master_class")],
        # [InlineKeyboardButton(text="❌ Отменить все сессии", callback_data="cancel_all_sessions")],
        [InlineKeyboardButton(text="🟢 Обратная связь", callback_data="request_callback")]
    ])

    welcome_message = (
        f"Добро пожаловать 🌟*{username}*🌟 в удивительный мир WEB 3.0 проектов!"
    )

    welcome_message_sent = await bot.send_message(chat_id=chat_id, text=welcome_message, reply_markup=markup,
                                                  parse_mode="Markdown")

    return photo_message.message_id if photo_message else None, welcome_message_sent.message_id


@router.message(CommandStart())
async def send_welcome(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username

    # Инициализация данных пользователя
    user_data[user_id] = {
        "username": username,
        "welcome_message_id": None,
        "photo_message_id": None,
        "selected_master_class": None,
        "selected_date": None,
        "selected_time": None,
        "messages_to_delete": [],
        "awaiting_callback_message": False,
        "action_count": 0  # Добавляем поле для подсчета действий
    }

    await message.delete()
    photo_message_id, welcome_message_id = await send_welcome_message(message.bot, message.chat.id, username)

    user_data[user_id]["photo_message_id"] = photo_message_id
    user_data[user_id]["welcome_message_id"] = welcome_message_id

    async with session_maker() as session:
        visit = ChannelVisits(
            id_te=user_id,
            name=username,
            description="Пользователь начал работу с ботом",
            user_actions=0,  # Начальное значение
            created=get_local_time(),  # Время создания в локальной зоне
            updated=get_local_time()  # Время обновления в локальной зоне
        )
        session.add(visit)
        await session.commit()


@router.callback_query()
async def process_callback_query(callback_query: types.CallbackQuery):
    data = callback_query.data
    user_id = callback_query.from_user.id
    chat_id = callback_query.message.chat.id
    bot = callback_query.message.bot

    messages_to_delete = user_data[user_id].get("messages_to_delete", [])
    for message_id in messages_to_delete:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
            print(f"Удалено сообщение {message_id} в чате {chat_id}")
        except TelegramAPIError as e:
            print(f"Ошибка при удалении сообщения {message_id}: {e}")

    user_data[user_id]["messages_to_delete"] = []
    # Логика для выбора даты и времени
    if data == "select_date_time":
        today = datetime.now().date()
        date_buttons = [
            InlineKeyboardButton(
                text=(today + timedelta(days=i)).strftime('%d-%m-%Y'),
                callback_data=f"select_class_date_{(today + timedelta(days=i)).strftime('%Y-%m-%d')}"
            ) for i in range(1, 8)
        ]
        date_rows = [date_buttons[i:i + 2] for i in range(0, len(date_buttons), 2)]
        date_markup = InlineKeyboardMarkup(inline_keyboard=date_rows)
        message = await callback_query.message.answer(
            "📅 Выберите удобный день для мастер-класса.",
            reply_markup=date_markup
        )
        await callback_query.answer()

    elif data.startswith("select_class_date_"):
        selected_date = data.split("_")[3]
        user_data[user_id]["selected_date"] = selected_date

        time_options = start_time
        time_buttons = [
            InlineKeyboardButton(text=f"{hour}:00", callback_data=f"time_class_{selected_date}_{hour}_00")
            for hour in time_options
        ]
        time_rows = [time_buttons[i:i + 3] for i in range(0, len(time_buttons), 3)]
        time_markup = InlineKeyboardMarkup(inline_keyboard=time_rows)

        message = await callback_query.message.answer(
            f"🕒 Вы выбрали дату: {selected_date}. Теперь выберите удобное время для мастер-класса.",
            reply_markup=time_markup
        )
        await callback_query.answer()

    elif data.startswith("time_class_"):
        parts = data.split("_")
        selected_date, selected_hour = parts[2], parts[3]
        selected_time = f"{selected_hour}:00"
        selected_master_class = user_data[user_id]["selected_master_class"]

        await callback_query.message.answer(
            f"✅ Ваш мастер-класс успешно забронирован на {selected_date} в {selected_time}."
        )

        await bot.send_message(
            ADMIN_USER_ID,
            f"🗓️ **Новый мастер-класс**:\n"
            f"📲 Пользователь: @{user_data[user_id]['username']}\n"
            f"📅 Дата: {selected_date}\n"
            f"🕒 Время: {selected_time}\n"
            f"💼 Мастер-класс: {selected_master_class}\n"
            f"🔔 Пожалуйста, подготовьтесь к встрече."
        )

        # Обновляем данные в базе данных
        async with session_maker() as session:
            visit = ChannelVisits(
                id_te=user_id,
                name=user_data[user_id]["username"],
                description=f"Пользователь забронировал мастер-класс {selected_master_class} на {selected_date} в {selected_time}",
                user_actions=4,  # Можно увеличить количество действий
                created=get_local_time(),  # Время создания в локальной зоне
                updated=get_local_time()
            )
            session.add(visit)
            await session.commit()

        await callback_query.answer()

    if data == "free_consultation":
        today = datetime.now().date()
        date_buttons = [
            InlineKeyboardButton(
                text=(today + timedelta(days=i)).strftime('%d-%m-%Y'),
                callback_data=f"select_consultation_date_{(today + timedelta(days=i)).strftime('%Y-%m-%d')}"
            ) for i in range(1, 8)
        ]
        date_rows = [date_buttons[i:i + 2] for i in range(0, len(date_buttons), 2)]
        date_markup = InlineKeyboardMarkup(inline_keyboard=date_rows)
        message = await callback_query.message.answer(
            "📅 Выберите удобный день для бесплатной консультации. Вы можете выбрать дату из предложенных вариантов.",
            reply_markup=date_markup
        )
        user_data[user_id]["messages_to_delete"].append(message.message_id)
        await callback_query.answer()

        async with session_maker() as session:
            visit = ChannelVisits(
                id_te=user_id,
                name=user_data[user_id]["username"],
                description="Пользователь выбрал дату для бесплатной консультации",
                user_actions=1,
                created=get_local_time(),  # Время создания в локальной зоне
                updated=get_local_time()
            )
            session.add(visit)
            await session.commit()

    elif data.startswith("select_consultation_date_"):
        selected_date = data.split("_")[3]
        user_data[user_id]["selected_date"] = selected_date

        time_options = start_time
        time_buttons = [
            InlineKeyboardButton(text=f"{hour}:00", callback_data=f"time_consultation_{selected_date}_{hour}_00")
            for hour in time_options
        ]
        time_rows = [time_buttons[i:i + 3] for i in range(0, len(time_buttons), 3)]
        time_markup = InlineKeyboardMarkup(inline_keyboard=time_rows)

        message = await callback_query.message.answer(
            f"🕒 Вы выбрали дату: {selected_date}. Теперь выберите удобное время для консультации из предложенных вариантов.",
            reply_markup=time_markup
        )
        user_data[user_id]["messages_to_delete"].append(message.message_id)
        await callback_query.answer()

    elif data.startswith("time_consultation_"):
        parts = data.split("_")
        selected_date, selected_hour = parts[2], parts[3]
        selected_time = f"{selected_hour}:00"

        await callback_query.message.answer(
            f"✅ Ваша консультация успешно забронирована на {selected_date} в {selected_time}. За час до встречи вы получите напоминание со ссылкой на конференц-звонок."
        )

        await bot.send_message(
            ADMIN_USER_ID,
            f"🗓️ **Новая бесплатная консультация**:\n"
            f"📲 Пользователь: @{user_data[user_id]['username']}\n"
            f"📅 Дата: {selected_date}\n"
            f"🕒 Время: {selected_time}\n"
            f"🔔 Пожалуйста, подготовьтесь к встрече с пользователем."
        )

        # Обновляем данные пользователя в базе данных
        async with session_maker() as session:
            visit = ChannelVisits(
                id_te=user_id,
                name=user_data[user_id]["username"],
                description=f"Пользователь забронировал консультацию на {selected_date} в {selected_time}",
                user_actions=2,
                created=get_local_time(),  # Время создания в локальной зоне
                updated=get_local_time()
            )
            session.add(visit)
            await session.commit()

        await callback_query.answer()

    elif data == "select_master_class":
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="• Light (30 мин) - стоимость $150", callback_data="select_master_class_light")],
            [InlineKeyboardButton(text="• Standart (60 мин) - стоимость $300",
                                  callback_data="select_master_class_standard")],
            [InlineKeyboardButton(text="• Premium (120 мин) - стоимость $900",
                                  callback_data="select_master_class_premium")]
        ])
        message = await callback_query.message.answer(
            text=mast_class,
            reply_markup=markup, parse_mode='Markdown'
        )
        user_data[user_id]["messages_to_delete"].append(message.message_id)
        await callback_query.answer()

    elif data.startswith("select_master_class_"):
        master_class = data.split("_")[3]
        user_data[user_id]["selected_master_class"] = master_class

        if master_class == 'light':
            additional_text = light
        elif master_class == 'standard':
            additional_text = standard
        elif master_class == 'premium':
            additional_text = premium

        await callback_query.message.answer(additional_text, parse_mode='Markdown')

        # Добавляем запись в базу данных о выбранном мастер-классе
        async with session_maker() as session:
            visit = ChannelVisits(
                id_te=user_id,
                name=user_data[user_id]["username"],
                description=f"Пользователь выбрал мастер-класс: {master_class}",
                user_actions=3,
                created=get_local_time(),  # Время создания в локальной зоне
                updated=get_local_time()
            )
            session.add(visit)
            await session.commit()

        payment_markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Сервис bestchange.ru", url=PAYMENT_URL)],
            [InlineKeyboardButton(text="Отправить чек", callback_data="send_payment_receipt")]
        ])
        await callback_query.message.answer(
            f"💳 Для завершения покупки произведите оплату.\n\n"
            f"Номер кошелька *(USDT **TRC-20**)*: *{CRYPTO_WALLET_ADDRESS}*\n\n"
            '(можете воспользоватся сервисом *bestchange*)\n\n'
            "После оплаты отправьте скан или фото вашего чека, чтобы мы могли подтвердить получение.",
            reply_markup=payment_markup,
            parse_mode="Markdown"
        )
        await callback_query.answer()


    elif data == "send_payment_receipt":
        user_data[user_id]["awaiting_payment_receipt"] = True
        await callback_query.message.answer(
            "📸 Пожалуйста, отправьте фото или скан вашего чека оплаты. Мы проверим его и подтвердим получение."
        )
        await callback_query.answer()

    elif data == "cancel_all_sessions":
        user_data[user_id]["selected_master_class"] = None
        user_data[user_id]["selected_date"] = None
        user_data[user_id]["selected_time"] = None

        await callback_query.message.answer(
            "❌ Все ваши запланированные сессии были отменены. Вы можете выбрать новые даты и время или заказать мастер-классы в любое время."
        )
        await callback_query.answer()

    elif data == "request_callback":
        await callback_query.message.answer(
            "Напишите Ваш вопрос или предложение, мы свяжемся с вами в ближайшее время."
        )
        user_data[user_id]["awaiting_callback_message"] = True
        await callback_query.answer()


@router.message()
async def handle_text_messages(message: types.Message):
    user_id = message.from_user.id
    bot = message.bot

    if user_data.get(user_id, {}).get("awaiting_callback_message"):
        # Отправка сообщения админу
        await bot.send_message(
            ADMIN_USER_ID,
            f"🗨️ **Обратная связь от пользователя** @{user_data[user_id]['username']}:\n\n"
            f"**Сообщение:**\n{message.text}\n\n"
            f"🕒 **Дата и время:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"Пожалуйста, ответьте на сообщение как можно скорее."
        )

        # Подтверждение получения сообщения
        await message.answer(text=messa_answer
                             )

        # Сбрасываем состояние ожидания
        user_data[user_id]["awaiting_callback_message"] = False

    elif user_data.get(user_id, {}).get("awaiting_payment_receipt"):
        # Отправка изображения чека админу
        if message.photo:
            # Если сообщение содержит фото
            photo = message.photo[-1]  # Получаем самое качественное изображение
            await bot.send_photo(
                ADMIN_USER_ID,
                photo=photo.file_id,
                caption=f"💸 **Чек оплаты от пользователя** @{user_data[user_id]['username']}:\n\n"
                        f"🕒 **Дата и время:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                        f"Пожалуйста, проверьте чек и подтвердите получение."
            )
        elif message.document:
            # Если сообщение содержит документ (например, PDF)
            document = message.document
            await bot.send_document(
                ADMIN_USER_ID,
                document=document.file_id,
                caption=f"💸 **Чек оплаты от пользователя** @{user_data[user_id]['username']}:\n\n"
                        f"🕒 **Дата и время:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                        f"Пожалуйста, проверьте чек и подтвердите получение."
            )

        # После отправки чека добавляем кнопки для выбора даты и времени
        await message.answer(
            "✅ Ваш чек успешно отправлен куратору. Теперь выберите, пожалуйста, удобное время и забронируйте мастер-класс.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Выбрать дату и время", callback_data="select_date_time")]
                ]
            )
        )

        user_data[user_id]["awaiting_payment_receipt"] = False
