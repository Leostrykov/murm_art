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
from get_photo_file import get_photo_file
from renders_map import render_some_points_map

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

TOKEN = os.getenv('BOT_TOKEN')
ADMINS = os.getenv('ADMINS').split(';')
bot = telebot.TeleBot(TOKEN)

db_session.global_init('data_base.sqlite')


# команда start, регистрация пользователя и приветствие
@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(message.chat.id, f'''
    **Привет {message.from_user.first_name}\.**
    Я — бот \- путеводитель по муралам Мурманска
    Что же я могу?\n
        — Расскажу вам о самых интересных и значимых объектах\.
        — Помогу найти ближайший арт \- объект и проложить к нему маршрут\. Просто отправь мне свою геолокацию\.
        — Буду рад уведомить вас о новых событиях и открытиях, связанных с искусством\.''', parse_mode='MarkdownV2')
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
                     'номер арта тз карты и получите о нём информацию и постройте к нему маршрут')


# команда mailing доступна только для администраторов. Для добавления администратора в .env ADMINS добавьте user_id
@bot.message_handler(commands=['mailing'])
def mailing(message):
    if str(message.from_user.id) in ADMINS:
        murkup = types.ReplyKeyboardMarkup()
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
    arts = db_sess.query(StreetArt).filter(
        StreetArt.longitude.between(user_longitude - 0.0003, user_longitude + 0.0003),
        StreetArt.latitude.between(user_latitude - 0.0003, user_latitude + 0.0003)).order_by(
        func.pow(StreetArt.longitude - user_longitude, 2) + func.pow(StreetArt.latitude - user_latitude, 2)).first()

    # подтверждение пользователя в точке
    if arts is not None:
        bot.send_photo(message.chat.id, get_photo_file(arts.photo),
                       f'{arts.name}\n{arts.about}')
        # повышение рейтинга, если пользователь не приходил раньше
        if db_sess.query(Visited).filter(Visited.user_id == user.id, Visited.art_id == arts.id).first():
            bot.send_message(message.chat.id, 'Вы пришли в новое место')
            db_sess.add(Visited(user_id=user.id, art_id=arts.id))
            db_sess.commit()
    else:
        closer_art = db_sess.query(StreetArt).order_by(
                        func.pow(StreetArt.longitude - user_longitude, 2) +
                        func.pow(StreetArt.latitude - user_latitude, 2)).limit(5).all()

        # TODO: Сделать отдельную функцию для генерации карты
        bot.send_photo(message.chat.id, render_some_points_map(closer_art, (user_longitude, user_latitude)), "Вот несколько ближайших от вас артов")
    db_sess.close()


# TODO: Подумать о пользе фичи
# команда map для отправки карты артов
@bot.message_handler(commands=['map'])
def map_streetart(message):
    bot.delete_message(message.chat.id, message.message_id)
    bot.delete_message(message.chat.id, message.message_id - 1)
    db_sess = db_session.create_session()
    coords = [f'{i.longitude},{i.latitude},pm2rdm{i.id}' for i in db_sess.query(StreetArt).all()]
    map_link = f'https://static-maps.yandex.ru/1.x/?l=map&lang=ru_RU&size=300,' \
               f'300&scale=1.0&pt={"~".join(coords)}'
    murkup = types.InlineKeyboardMarkup()
    murkup.add(types.InlineKeyboardButton('Первомайский округ', callback_data='pervomaisky'))
    murkup.add(types.InlineKeyboardButton('Октябрьский округ', callback_data='oktyabrsky'))
    murkup.add(types.InlineKeyboardButton('Ленинский округ', callback_data='leninsky'))
    murkup.add(types.InlineKeyboardButton('Сортировать по авторам', callback_data='authors'))
    bot.send_photo(message.chat.id, map_link, reply_markup=murkup)
    db_sess.close()


# нахождение всех авторов
@bot.callback_query_handler(func=lambda callback: True)
def map_sort(callback):
    db_sess = db_session.create_session()
    if callback.data == 'authors':
        murkup = types.ReplyKeyboardMarkup()
        for i in db_sess.query(Authors.name).all():
            murkup.add(types.KeyboardButton(i.name))
        bot.send_message(callback.message.chat.id, 'Выберите автора', reply_markup=murkup)
        bot.register_next_step_handler(callback.message, map_author_sort)
    else:
        points = None
        if callback.data == 'leninsky':
            points = db_sess.query(StreetArt).join(Districts).filter(Districts.name == 'Ленинский')
        elif callback.data == 'oktyabrsky':
            points = db_sess.query(StreetArt).join(Districts).filter(Districts.name == 'Октябрьский')
        elif callback.data == 'pervomaisky':
            points = db_sess.query(StreetArt).join(Districts).filter(Districts.name == 'Первомайский')
        bot.send_photo(callback.message.chat.id, render_some_points_map(points, z=13))
    bot.delete_message(callback.message.chat.id, callback.message.message_id)
    db_sess.close()


def map_author_sort(message):
    db_sess = db_session.create_session()
    author = db_sess.query(Authors).filter(Authors.name == message.text).first()
    if author is not None:
        author_places = db_sess.query(StreetArt).join(StreetArtAuthors).filter(
            StreetArtAuthors.author_id == author.id).all()
        bot.send_photo(message.chat.id, render_some_points_map(author_places), reply_markup=types.ReplyKeyboardRemove())
    else:
        bot.send_message(message.chat.id, 'Автор не найден', reply_markup=types.ReplyKeyboardRemove())
    bot.delete_message(message.chat.id, message.message_id)


# тип контента текст, вывод информации об объекте по его id
@bot.message_handler(content_types=['text'])
def text(message):
    db_sess = db_session.create_session()
    if message.text.isnumeric():
        art = db_sess.query(StreetArt).filter(StreetArt.id == message.text).first()
        if art is not None:
            murkup = types.InlineKeyboardMarkup()
            murkup.add(types.InlineKeyboardButton('Построить машрут',
                                                  url=f'https://yandex.ru/maps/?rtext='
                                                      f'~{art.latitude},{art.longitude}&rtt=pd'))
            bot.send_photo(message.chat.id,
                           f'https://static-maps.yandex.ru/1.x/?l=map&lang=ru_RU&'
                           f'size=300,300&scale=1.0&z=15&pt={art.longitude},{art.latitude},pm2rdm',
                           f"{art.name}\nАдрес:{art.address}", reply_markup=murkup)
            db_sess.close()
        else:
            bot.send_message(message.chat.id, 'Не сущевствующий мурал')


bot.polling(non_stop=True, interval=1, timeout=0)
