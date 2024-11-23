import telebot
from telebot import types
import sqlite3
import os
from os.path import join, dirname
from dotenv import load_dotenv

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

TOKEN = os.getenv('BOT_TOKEN')
ADMINS = os.getenv('ADMINS').split(';')
bot = telebot.TeleBot(TOKEN)


# функция для выдачи достижения
def achievements(user, place, message, cursor):
    if user[4] == 0:
        bot.send_message(message.chat.id, 'Разблокировано достижение "Первый шаг"')
        cursor.execute('UPDATE users SET achievement_first_step = true WHERE user_id = %s' % message.from_user.id)


# создание таблицы users если её нет
def create_table():
    db = sqlite3.connect('data_base.sqlite')
    cur = db.cursor()
    cur.execute(
        '''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY, 
        username VARCHAR(50), 
        user_id INT unique, 
        chat_id INT unique, 
        achievement_first_step BOOLEAN DEFAULT(0), 
        visited TEXT DEFAULT "[]", 
        rating INT DEFAULT(0), 
        last_art INT DEFAULT(0))''')
    db.commit()
    cur.close()
    db.close()


create_table()


# команда start, регистрация пользователя и привествие
@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(message.chat.id, f'Привет {message.from_user.first_name}')
    db = sqlite3.connect('data_base.sqlite')
    cur = db.cursor()
    cur.execute('''INSERT OR IGNORE INTO users (username, user_id, chat_id) VALUES ("%s", %s, %s)''' %
                (message.from_user.username, message.from_user.id, message.chat.id))
    db.commit()
    cur.close()
    db.close()


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
    if message.from_user.id in ADMINS:
        murkup = types.ReplyKeyboardMarkup()
        murkup.add(types.KeyboardButton('Отмена'))
        bot.send_message(message.chat.id, 'Отправьте сообщение для рассылки.', reply_markup=murkup)
        bot.register_next_step_handler(message, mailing_for_users)


def mailing_for_users(message):
    if message.text != 'Отмена':
        db = sqlite3.connect('data_base.sqlite')
        cur = db.cursor()
        if message.content_type == 'photo':
            cur.execute('SELECT chat_id FROM users')
            photo_mailing = message.photo
            for person_id in cur.fetchall():
                bot.send_photo(person_id[0], photo_mailing[0].file_id, message.caption)
        elif message.content_type == 'text':
            cur.execute('SELECT chat_id FROM users')
            text_mailing = message.text
            for person_id in cur.fetchall():
                bot.send_message(person_id[0], text_mailing)
        else:
            bot.send_message(message.chat.id, 'Формат сообщения не поддерживается.'
                                              'Только фото или фото с текстом или текст.')
        bot.send_message(message.chat.id, 'Рассылка окончена', reply_markup=types.ReplyKeyboardRemove())
        cur.close()
        db.close()
    else:
        bot.send_message(message.chat.id, 'Рассылка отменена', reply_markup=types.ReplyKeyboardRemove())


# определение местоположения пользователя
@bot.message_handler(content_types=['location'])
def get_location(message):
    longitude = message.location.longitude
    latitude = message.location.latitude
    db = sqlite3.connect('data_base.sqlite')
    cur = db.cursor()
    cur.execute('SELECT * FROM users WHERE user_id = %s' % message.from_user.id)
    user_inf = cur.fetchone()
    cur.execute('''SELECT * FROM street_art
                WHERE
                    longitude BETWEEN (%s - 0.0003) AND (%s + 0.0003) AND
                    latitude BETWEEN (%s - 0.0003) AND (%s + 0.0003) AND
                    id <> %s
                ORDER BY (
                        (longitude - %s) * (longitude - %s) +
                        (latitude - %s) * (latitude - %s)
                    );
                ''' % (longitude, longitude, latitude, latitude, user_inf[7], longitude, longitude, latitude, latitude))
    place_inf = cur.fetchone()
    # подверждение пользователя в точке
    if place_inf is not None and user_inf[7] != place_inf[0]:
        bot.send_photo(message.chat.id, place_inf[8], f'{place_inf[1]}\n{place_inf[4]}')
        # повышение рейтинга, если пользователь не приходил раньше
        visited_arts = json.loads(user_inf[5])
        if place_inf[0] not in visited_arts:
            bot.send_message(message.chat.id, 'Вы пришли в новое место')
            visited_arts.append(place_inf[0])
            cur.execute('UPDATE users SET visited = "%s", rating = rating + 1 WHERE user_id = %s'
                        % (json.dumps(visited_arts), message.from_user.id))
        achievements(user_inf, place_inf, message, cur)
        cur.execute('UPDATE users SET last_art = %s WHERE user_id = %s' %
                    (place_inf[0], message.from_user.id))
    else:
        # нахождение ближайшего арта исключая недавно посещённый
        cur.execute('''SELECT id, name, longitude, latitude, about, photo, address 
                    FROM street_art
                    WHERE id <> %s
                    ORDER BY (
                        (longitude - %s) * (longitude - %s) +
                        (latitude - %s) * (latitude - %s)
                    ) ASC
                    LIMIT 10;
        ''' % (user_inf[7], longitude, longitude, latitude, latitude))
        closer_art = cur.fetchall()
        coords = [f'{i[2]},{i[3]},pm2rdm{i[0]}' for i in closer_art]
        map_link = f'https://static-maps.yandex.ru/1.x/?l=map&lang=ru_RU&size=300,' \
                   f'300&scale=1.0&pt={longitude},{latitude},ya_ru~{"~".join(coords)}'
        bot.send_photo(message.chat.id, map_link, "Вот несколько ближайших от вас артов")
        # ""murkup = types.InlineKeyboardMarkup()
        #         murkup.add(types.InlineKeyboardButton('Построить машрут',
        #                                               url=f'https://yandex.ru/maps/?rtext='
        #                                                   f'~{closer_art[1]},{closer_art[2]}&rtt=pd'))
        #         bot.send_photo(message.chat.id,
        #                        f'https://static-maps.yandex.ru/1.x/?l=map&lang=ru_RU&'
        #                        f'size=300,300&scale=1.0&z=15&pt={closer_art[2]},{closer_art[1]},pm2rdm',
        #                        f"Ближайщий от вас арт: {closer_art[0]}\nАдрес:{closer_art[5]}", reply_markup=murkup)""

    db.commit()
    cur.close()
    db.close()


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
