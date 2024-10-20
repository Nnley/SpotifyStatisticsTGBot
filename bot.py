# TODO: organize bot into folders and files
import logging
import os

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware

from db.crud import UserManager
from services.spotify_service import SpotifyService, TimeRange

from config import load_environment_variables
load_environment_variables()

BOT_API_TOKEN = os.getenv('BOT_API_TOKEN')
if not BOT_API_TOKEN:
    raise ValueError('BOT_API_TOKEN is not set')

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_API_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    if message.get_args() and message.get_args() == 'success':
        return await message.answer('Вы успешно прошли авторизацию')
    
    user_id = message.from_user.id
    user = UserManager.get_or_create_user(user_id)
    if user.refresh_token is None:
        await message.answer('Привет! Чтобы получить статистику, Вам необходимо авторизоваться через Spotify. Для этого введите команду /auth.')
    else: 
        await message.answer('Список команд можно увидеть, написав /help.')      
        
  
@dp.message_handler(commands=['help'])
async def help(message: types.Message):
    await message.reply("Доступные команды: /stats, /auth")


@dp.message_handler(commands=['auth'])
async def auth(message: types.Message):
    user_id = message.from_user.id
    user = UserManager.get_or_create_user(user_id)
    if user.refresh_token is None:
        auth_link = f'{os.getenv("SPOTIFY_AUTH_URL")}/{user_id}'
        
        keyboard = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton(text='Авторизоваться', url=auth_link) # type: ignore
        keyboard.add(button)
        
        await message.answer('Для авторизации нажмите на кнопку ниже:', reply_markup=keyboard)
    else:
        await message.answer('Вы уже авторизованы.')


# TODO: rewrite and refactor all that shitty code
@dp.inline_handler()
async def inline_handler(query: types.InlineQuery):
    user_id = query.from_user.id
    user = UserManager.get_or_create_user(user_id)
    if user.refresh_token is None:
        results = []
        results.append(
            types.InlineQueryResultArticle(
                id='1',
                title='Моя статистика',
                description='Чтобы получить статистику, Вам необходимо авторизоваться в боте через Spotify.',
                input_message_content=types.InputTextMessageContent(
                    message_text='Чтобы получить статистику, Вам необходимо авторизоваться в боте через Spotify.',                  
                ),
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton(
                        text='Авторизоваться',
                        callback_data='auth',
                    ) # type: ignore
                )
            )
        )
        await query.answer(results, cache_time=1, is_personal=True)
    else:
        spotify_service = SpotifyService()
        
        user_top_tracks_month = spotify_service.get_user_top_tracks(user_id, TimeRange.SHORT_TERM)
        user_top_tracks_half_year = spotify_service.get_user_top_tracks(user_id, TimeRange.MEDIUM_TERM)
        user_profile = spotify_service.get_user_profile(user_id)
        
        top_tracks_month_message_text = ''
        top_tracks_half_year_message_text = ''
        
        if user_top_tracks_month is not None and user_profile is not None:
            top_tracks_month_message_text = f"Статистика {user_profile.get('display_name')} ({user_profile.get('country')}) в Spotify за месяц:\n\n"
            
            top_tracks_month_message_text += '\n'.join([f"{i + 1}. {track.get('name')} - {track.get('artist')}" for i, track in enumerate(user_top_tracks_month)])
        else: 
            top_tracks_month_message_text += 'Возникла ошибка при получении статистики.'
        
        if user_top_tracks_half_year is not None and user_profile is not None:
            top_tracks_half_year_message_text = f"Статистика {user_profile.get('display_name')} ({user_profile.get('country')}) в Spotify за пол года:\n\n"
            
            top_tracks_half_year_message_text += '\n'.join([f"{i + 1}. {track.get('name')} - {track.get('artist')}" for i, track in enumerate(user_top_tracks_half_year)])
        else: 
            top_tracks_half_year_message_text += 'Возникла ошибка при получении статистики.'
            
        results = []
        results.append(
            types.InlineQueryResultArticle(
                id='1',
                title='Статистика',
                description='Посмотреть топ моих самых прослушиваемых треков за месяц',
                input_message_content=types.InputTextMessageContent(
                    message_text=top_tracks_month_message_text,
                ),
            ),
        )
        results.append(
            types.InlineQueryResultArticle(
                id='2',
                title='Статистика',
                description='Посмотреть топ моих самых прослушиваемых треков за пол года',
                input_message_content=types.InputTextMessageContent(
                    message_text=top_tracks_half_year_message_text,
                ),
            ),
        )
        await query.answer(results, cache_time=1, is_personal=True)


if __name__ == '__main__':
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)