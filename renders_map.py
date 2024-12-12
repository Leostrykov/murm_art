def render_some_points_map(art_data, user_coords: tuple = None, z: int = 15):
    coords = [f'{i.longitude},{i.latitude},pm2rdm{i.id}' for i in art_data]
    map_link = ''
    if user_coords is not None:
        map_link = f'https://static-maps.yandex.ru/1.x/?l=map&lang=ru_RU&size=300,' \
                   f'300&scale=1.0&pt={user_coords[0]},{user_coords[1]},ya_ru~{"~".join(coords)}&z={z}'
    else:
        map_link = f'https://static-maps.yandex.ru/1.x/?l=map&lang=ru_RU&size=300,' \
                   f'300&scale=1.0&pt={"~".join(coords)}&z={z}'
    return map_link