from telebot.types import InputMediaPhoto


def get_photo_file(filename: str):
    return open(f'./data/photos/{filename.split(";")[0]}', 'rb').read()


def get_group_photo_files(filenames: str):
    files_data = []
    for i in filenames.split(';')[:-1]:
        files_data.append(InputMediaPhoto(open(f'./data/photos/{i}', 'rb')))
    return files_data
