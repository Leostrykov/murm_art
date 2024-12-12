def get_photo_file(filename: str):
    return open(f'./data/photos/{filename.split(";")[0]}', 'rb').read()


def get_group_photo_files(filenames: str):
    files_data = []
    for i in filenames.split(';'):
        files_data.append(open(f'./data/photos/{i}', 'rb').read())
    return files_data