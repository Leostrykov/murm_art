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

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

TOKEN = os.getenv('BOT_TOKEN')
ADMINS = os.getenv('ADMINS').split(';')
bot = telebot.TeleBot(TOKEN)

db_session.global_init('data_base.sqlite')


# функция для выдачи достижения
# TODO убрать функцию достижений
def achievements(user, place, message, cursor):
    if user[4] == 0:
        bot.send_message(message.chat.id, 'Разблокировано достижение "Первый шаг"')
        cursor.execute('UPDATE users SET achievement_first_step = true WHERE user_id = %s' % message.from_user.id)


# команда start, регистрация пользователя и приветствие
@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(message.chat.id, f'Привет {message.from_user.first_name}')
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
                     'Отправьте свою геолокацию для нахождения ближайщего арта или для подверждения нахождения '
                     'на стрит арте\n/map - для открытия карты стрит артов с номерами и '
                     'сортировкой по районам\nВведите '
                     'номер арта и получите о нём информацию и постройте к нему машрут')


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
        recipients = db_sess.query(User).all()
        if message.content_type == 'photo':
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
    # cur.execute('''SELECT * FROM street_art
    #             WHERE
    #                 longitude BETWEEN (%s - 0.0003) AND (%s + 0.0003) AND
    #                 latitude BETWEEN (%s - 0.0003) AND (%s + 0.0003) AND
    #                 id <> %s
    #             ORDER BY (
    #                     (longitude - %s) * (longitude - %s) +
    #                     (latitude - %s) * (latitude - %s)
    #                 );
    #             ''' % (longitude, longitude, latitude, latitude, user_inf[7], longitude, longitude,
    #             latitude, latitude))

    arts = db_sess.query(StreetArt).filter(
        StreetArt.longitude.between(user_longitude - 0.0003, user_longitude + 0.0003),
        StreetArt.latitude.between(user_latitude - 0.0003, user_latitude + 0.0003)).order_by(
        func.pow(StreetArt.longitude - user_longitude, 2) + func.pow(StreetArt.latitude - user_latitude, 2)).first()

    # подтверждение пользователя в точке
    if arts is not None:
        bot.send_photo(message.chat.id, arts.photo, f'{arts.name}\n{arts.about}')
        # повышение рейтинга, если пользователь не приходил раньше
        if db_sess.query(Visited).filter(Visited.user_id == user.id, Visited.art_id == arts.id).first():
            bot.send_message(message.chat.id, 'Вы пришли в новое место')
            db_sess.add(Visited(user_id=user.id, art_id=arts.id))
            db_sess.commit()
    else:
        # нахождение ближайшего арта исключая недавно посещённый
        # cur.execute('''SELECT id, name, longitude, latitude, about, photo, address
        #             FROM street_art
        #             WHERE id <> %s
        #             ORDER BY (
        #                 (longitude - %s) * (longitude - %s) +
        #                 (latitude - %s) * (latitude - %s)
        #             ) ASC
        #             LIMIT 10;
        # ''' % (user_inf[7], longitude, longitude, latitude, latitude))
        closer_art = db_sess.query(StreetArt).order_by(
                        func.pow(StreetArt.longitude - user_longitude, 2) +
                        func.pow(StreetArt.latitude - user_latitude, 2)).limit(10).all()

        # TODO: Сделать отдельную функцию для генерации карты
        coords = [f'{i.longitude},{i.latitude},pm2rdm{i.id}' for i in closer_art]
        map_link = f'https://static-maps.yandex.ru/1.x/?l=map&lang=ru_RU&size=300,' \
                   f'300&scale=1.0&pt={user_longitude},{user_latitude},ya_ru~{"~".join(coords)}'
        bot.send_photo(message.chat.id, map_link, "Вот несколько ближайших от вас артов")
        # ""murkup = types.InlineKeyboardMarkup()
        #         murkup.add(types.InlineKeyboardButton('Построить машрут',
        #                                               url=f'https://yandex.ru/maps/?rtext='
        #                                                   f'~{closer_art[1]},{closer_art[2]}&rtt=pd'))
        #         bot.send_photo(message.chat.id,
        #                        f'https://static-maps.yandex.ru/1.x/?l=map&lang=ru_RU&'
        #                        f'size=300,300&scale=1.0&z=15&pt={closer_art[2]},{closer_art[1]},pm2rdm',
        #                        f"Ближайщий от вас арт: {closer_art[0]}\nАдрес:{closer_art[5]}", reply_markup=murkup)""


# команда map для отправки карты артов
@bot.message_handler(commands=['map'])
def map_streetart(message):
    db = sqlite3.connect('data_base.sqlite')
    cur = db.cursor()
    cur.execute('SELECT id, longitude, latitude  FROM street_art')
    coords = [f'{i[1]},{i[2]},pm2rdm{i[0]}' for i in cur.fetchall()]
    map_link = f'https://static-maps.yandex.ru/1.x/?l=map&lang=ru_RU&size=300,' \
               f'300&scale=1.0&pt={"~".join(coords)}'
    murkup = types.InlineKeyboardMarkup()
    murkup.add(types.InlineKeyboardButton('Первомайский округ', callback_data='pervomaisky'))
    murkup.add(types.InlineKeyboardButton('Октябрьский округ', callback_data='oktyabrsky'))
    murkup.add(types.InlineKeyboardButton('Ленинский округ', callback_data='leninsky'))
    murkup.add(types.InlineKeyboardButton('Сортировать по авторам', callback_data='authors'))
    bot.send_photo(message.chat.id, map_link, reply_markup=murkup)
    cur.close()
    db.close()


# нахождение всех авторов
@bot.callback_query_handler(func=lambda callback: True)
def map_sort(callback):
    db = sqlite3.connect('data_base.sqlite')
    cur = db.cursor()
    if callback.data == 'authors':
        cur.execute('''SELECT name FROM author''')
        murkup = types.ReplyKeyboardMarkup()
        for i in cur.fetchall():
            murkup.add(types.KeyboardButton(i[0]))
        bot.send_message(callback.message.chat.id, 'Выберите автора', reply_markup=murkup)
        bot.register_next_step_handler(callback.message, map_author_sort)
    elif callback.data == 'leninsky':
        cur.execute('SELECT id, longitude, latitude  FROM street_art WHERE district = "Ленинский"')
        coords = [f'{i[1]},{i[2]},pm2rdm{i[0]}' for i in cur.fetchall()]
        map_link = f'https://static-maps.yandex.ru/1.x/?l=map&lang=ru_RU&size=300,' \
                   f'300&z=14&pt={"~".join(coords)}'
        bot.send_photo(callback.message.chat.id, map_link)
    elif callback.data == 'oktyabrsky':
        cur.execute('SELECT id, longitude, latitude  FROM street_art WHERE district = "Октябрьский"')
        coords = [f'{i[1]},{i[2]},pm2rdm{i[0]}' for i in cur.fetchall()]
        map_link = f'https://static-maps.yandex.ru/1.x/?l=map&lang=ru_RU&size=300,' \
                   f'300&pt={"~".join(coords)}'
        bot.send_photo(callback.message.chat.id, map_link)
    elif callback.data == 'pervomaisky':
        cur.execute('SELECT id, longitude, latitude  FROM street_art WHERE district = "Первомайский"')
        coords = [f'{i[1]},{i[2]},pm2rdm{i[0]}' for i in cur.fetchall()]
        map_link = f'https://static-maps.yandex.ru/1.x/?l=map&lang=ru_RU&size=300,' \
                   f'300&z=14&pt={"~".join(coords)}'
        bot.send_photo(callback.message.chat.id, map_link)
    cur.close()
    db.close()


def map_author_sort(message):
    db = sqlite3.connect('data_base.sqlite')
    cur = db.cursor()
    cur.execute(f'SELECT id FROM author WHERE name = "{message.text}"')
    id_author = cur.fetchall()
    if id_author is not None:
        cur.execute('SELECT art_id FROM street_art_authors WHERE author_id = %s' % id_author[0])
        author_places = cur.fetchall()
        coords = []
        for i in author_places:
            cur.execute(f'SELECT longitude, latitude FROM street_art WHERE id = {i[0]}')
            place = cur.fetchone()
            coords.append(f'{place[0]},{place[1]},pm2rdm{i[0]}')
        map_link = f'https://static-maps.yandex.ru/1.x/?l=map&lang=ru_RU&size=300,' \
                   f'300&scale=1.0&pt={"~".join(coords)}'
        bot.send_photo(message.chat.id, map_link, reply_markup=types.ReplyKeyboardRemove())
    else:
        bot.send_message(message.chat.id, 'Автор не найден', reply_markup=types.ReplyKeyboardRemove())


# тип контента текст, вывод информации об объекте по его id
@bot.message_handler(content_types=['text'])
def text(message):
    db = sqlite3.connect('data_base.sqlite')
    cur = db.cursor()
    if message.text.isnumeric():
        cur.execute('''SELECT name, longitude, latitude, about, photo, address FROM street_art 
        WHERE id = %s''' % message.text)
        place = cur.fetchone()
        if place is not None:
            murkup = types.InlineKeyboardMarkup()
            murkup.add(types.InlineKeyboardButton('Построить машрут',
                                                  url=f'https://yandex.ru/maps/?rtext='
                                                      f'~{place[2]},{place[1]}&rtt=pd'))
            bot.send_photo(message.chat.id,
                           f'https://static-maps.yandex.ru/1.x/?l=map&lang=ru_RU&'
                           f'size=300,300&scale=1.0&z=15&pt={place[1]},{place[2]},pm2rdm',
                           f"{place[0]}\nАдрес:{place[5]}", reply_markup=murkup)
            cur.close()
            db.close()
        else:
            bot.send_message(message.chat.id, 'Не сущевствующий мурал')


bot.polling(non_stop=True, interval=1, timeout=0)
