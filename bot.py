import telebot
from telebot import types
import sqlite3
import os
from os.path import join, dirname
from dotenv import load_dotenv
from data import db_session
from data.User import User
from data.StreetArt import StreetArt
from data.Districts import Districts
from data.Authors import Authors
from data.StreetArtAuthors import StreetArtAuthors
from data.Visited import Visited
from sqlalchemy import func
from get_photo_file import get_photo_file, get_group_photo_files
from renders_map import render_some_points_map

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

TOKEN = os.getenv('BOT_TOKEN')
ADMINS = os.getenv('ADMINS').split(';')
bot = telebot.TeleBot(TOKEN)

db_session.global_init('data_base.sqlite')


def webAppKeyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    web_app_test = types.WebAppInfo("https://leostrykov.github.io/murm-art-map/")
    one_butt = types.KeyboardButton(text="Карта артов", web_app=web_app_test)
    keyboard.add(one_butt)

    return keyboard


# команда start, регистрация пользователя и приветствие
@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(message.chat.id, f'''
    **Привет {message.from_user.first_name}\.**
    Я — бот \- путеводитель по муралам Мурманска
    Что же я могу?\n
        — Расскажу вам о самых интересных и значимых объектах\.
        — Помогу найти ближайший арт \- объект и проложить к нему маршрут\. Просто отправь мне свою геолокацию\.
        — Буду рад уведомить вас о новых событиях и открытиях, связанных с искусством\.''', parse_mode='MarkdownV2',
                     reply_markup=webAppKeyboard())
    db_sess = db_session.create_session()
    if not db_sess.query(User).filter(User.tg_id == message.from_user.id).first():
        user = User(username=message.from_user.username, tg_id=message.from_user.id)
        db_sess.add(user)
        db_sess.commit()
        db_sess.close()


# команда help
@bot.message_handler(commands=['help'])
def help_message(message):
    bot.send_message(message.chat.id,
                     'Отправьте свою геолокацию для нахождения ближайшего арт-объекта'
                     '\n/map - для открытия карты стрит артов с номерами и '
                     'сортировкой по районам\nВведите '
                     'номер арта из карты и получите о нём информацию и постройте к нему маршрут',
                     reply_markup=webAppKeyboard())


# команда mailing доступна только для администраторов. Для добавления администратора в .env ADMINS добавьте user_id
@bot.message_handler(commands=['mailing'])
def mailing(message):
    if str(message.from_user.id) in ADMINS:
        murkup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        murkup.add(types.KeyboardButton('Отмена'))
        bot.send_message(message.chat.id, 'Отправьте сообщение для рассылки.', reply_markup=murkup)
        bot.register_next_step_handler(message, mailing_for_users)


def mailing_for_users(message):
    if message.text != 'Отмена':
        db_sess = db_session.create_session()
        recipients = db_sess.query(User).filter(User.tg_id != message.from_user.id).all()
        if message.content_type == 'photo':
            bot.send_message(message.from_user.id, 'Рассылка в процессе. Пожалуйста, подождите.')
            photo_mailing = message.photo
            for person_id in recipients:
                bot.send_photo(person_id.tg_id, photo_mailing[0].file_id, message.caption)
        elif message.content_type == 'text':
            text_mailing = message.text
            for person_id in recipients:
                bot.send_message(person_id.tg_id, text_mailing)
        else:
            bot.send_message(message.chat.id, 'Формат сообщения не поддерживается.'
                                              'Только фото или фото с текстом или текст.')
        bot.delete_message(message.chat.id, message.message_id + 1)
        bot.send_message(message.chat.id, 'Рассылка окончена', reply_markup=types.ReplyKeyboardRemove())
        db_sess.close()
    else:
        bot.send_message(message.chat.id, 'Рассылка отменена', reply_markup=types.ReplyKeyboardRemove())


# определение местоположения пользователя
@bot.message_handler(content_types=['location'])
def get_location(message):
    user_longitude = message.location.longitude
    user_latitude = message.location.latitude
    db_sess = db_session.create_session()

    user = db_sess.query(User).filter(User.tg_id == message.from_user.id).first()
    art = db_sess.query(StreetArt).filter(
        StreetArt.longitude.between(user_longitude - 0.0006, user_longitude + 0.0006),
        StreetArt.latitude.between(user_latitude - 0.0006, user_latitude + 0.0006)).order_by(
        func.pow(StreetArt.longitude - user_longitude, 2) + func.pow(StreetArt.latitude - user_latitude, 2)).first()

    # подтверждение пользователя в точке
    if art is not None:
        authors = db_sess.query(Authors).join(StreetArtAuthors).filter(StreetArtAuthors.art_id == art.id).all()
        bot.send_media_group(message.chat.id, get_group_photo_files(art.photo))
        bot.send_message(message.chat.id,
                         f'{art.name}\nАвторы: {" ".join([i.name for i in authors])}\n'
                         f'Адрес: {art.address}\n{art.about}', reply_markup=webAppKeyboard())
        # повышение рейтинга, если пользователь не приходил раньше
        if not db_sess.query(Visited).filter(Visited.user_id == user.id, Visited.art_id == art.id).first():
            db_sess.add(Visited(user_id=user.id, art_id=art.id))
            db_sess.commit()
    else:
        closer_art = db_sess.query(StreetArt).order_by(
            func.pow(StreetArt.longitude - user_longitude, 2) +
            func.pow(StreetArt.latitude - user_latitude, 2)).limit(5).all()
        murcup = types.InlineKeyboardMarkup()
        line = []
        for point in closer_art:
            line.append(types.InlineKeyboardButton(point.id, callback_data=point.id))
        murcup.row(*line)
        bot.send_photo(message.chat.id, render_some_points_map(closer_art, (user_longitude, user_latitude)),
                       "Вот несколько ближайших от вас артов", reply_markup=murcup)
    db_sess.close()


# тип контента текст, вывод информации об объекте по его id
@bot.message_handler(content_types=['text', 'web_app_data'])
def text(message):
    content = None
    if message.content_type == 'web_app_data':
        content = message.web_app_data.data
    elif message.content_type == 'text':
        content = message.text
    db_sess = db_session.create_session()
    if content.isnumeric():
        art = db_sess.query(StreetArt).filter(StreetArt.id == content).first()
        if art is not None:
            murkup = types.InlineKeyboardMarkup()
            murkup.add(types.InlineKeyboardButton('Построить машрут',
                                                  url=f'https://yandex.ru/maps/?rtext='
                                                      f'~{art.latitude},{art.longitude}&rtt=pd'))
            authors = db_sess.query(Authors).join(StreetArtAuthors).filter(StreetArtAuthors.art_id == art.id).all()
            bot.send_media_group(message.chat.id, get_group_photo_files(art.photo))
            bot.send_message(message.chat.id,
                             f'{art.name}\nАвторы: {" ".join([i.name for i in authors])}\n'
                             f'Адрес: {art.address}\n{art.about}', reply_markup=murkup)
            db_sess.close()
        else:
            bot.send_message(message.chat.id, 'Не существующий мурал')


bot.polling(non_stop=True, interval=1, timeout=0)
