# Импорт необходимых библиотек и модулей
import telebot as tb
import sqlite3
import config, utils

# Список id пользователей, имеющих статус "admin"
admins = set()

# Подключение БД и создание курсора
conn = sqlite3.connect('./db/database.db', check_same_thread=False)
cursor = conn.cursor()


# Все категории товаров в магазине
def all_cat():
    global category
    category = cursor.execute('SELECT * FROM Category').fetchall()


all_cat()

# Подключение бота по токену
bot = tb.TeleBot(config.TOKEN)

# Корзина
dict_basket = {}

# Информация для доставки
dict_address = {}


# Функция для приветствия пользователя
@bot.message_handler(commands=['start'])
def handler_start(message):
    bot.send_message(message.from_user.id, utils.text_hello(message.from_user.username))
    keyboard_start(message)


# Отображение стартовой клавиатуры
def keyboard_start(message):
    user_markup = tb.types.ReplyKeyboardMarkup(True)
    if message.from_user.id in admins:
        admin_panel(message)
    else:
        user_markup.row('О нас', "Сделать заказ", "Адреса магазинов")
        bot.send_message(message.from_user.id, 'Что именно вас интересует ?!', reply_markup=user_markup)


# Отображение категорий товаров
def show_category(message):
    user_markup = tb.types.ReplyKeyboardMarkup(True)
    cat_list = [i[0] for i in category]
    lenght = len(cat_list)
    c = lenght // 2 + 1
    start = 0
    stop = 2 if lenght >= 2 else lenght
    for i in range(c):
        user_markup.row(*[cat_list[j] for j in range(start, stop)])
        start += 2
        stop = stop + 2 if lenght >= stop + 2 else lenght
    return (user_markup, message)


# Функция для добавления строки "меню" "корзина" в user_markup принимает кортеж из двух значений "user_markup", "message"
def add_row_menu_basket(tuple):
    tuple[0].row("Меню", "Корзина")
    return bot.send_message(tuple[1].from_user.id, 'Выберите категорию:', reply_markup=tuple[0])


# Отображение корзины
def show_basket(message, user_id=None):
    if message.from_user.id not in dict_basket or dict_basket[message.from_user.id] == {}:
        clear_basket(message)
        return None
    else:
        basket_string = []
        total_price = 0
        for i, j in dict_basket[message.from_user.id].items():
            basket_string.append(f'{i} - {j["count"]}шт. - {j["price"] * j["count"]}р.')
            total_price += j['price'] * j['count']
        basket_string.append(f'Итого: {total_price}р.')
        if not user_id:
            user_id = message.from_user.id
        else:
            basket_string.append('')
            basket_string.append(f'Адрес доставки --- {dict_address[message.from_user.id]["address"]}')
            basket_string.append(f'Контактный телефон --- {dict_address[message.from_user.id]["phone_number"]}')
        bot.send_message(user_id, str(basket_string).replace("', '", "\n")[2:-2])
    return True


# Удаление товаров из корзины
def edit_basket(message):
    message_1 = message
    if show_basket(message) is None:
        return None

    def del_item(message):
        try:
            if message.text.lower() == 'очистить корзину':
                clear_basket(message)
                return None
            elif message.text.lower() == 'меню':
                keyboard_start(message)
                return None
            elif message.text.lower() == 'оформить заказ':
                checkout(message)
                return None
            if dict_basket[message.from_user.id][message.text]['count'] == 1:
                del dict_basket[message.from_user.id][message.text]
            else:
                dict_basket[message.from_user.id][message.text]['count'] -= 1
        except KeyError:
            pass
        edit_basket(message_1)

    user_markup = tb.types.ReplyKeyboardMarkup(True)
    user_markup.row("Меню", "Очистить корзину")
    user_markup.row("Оформить заказ")
    try:
        for i, j in dict_basket[message.from_user.id].items():
            user_markup.row(i)
        msg = bot.send_message(message.from_user.id,
                               'Чтобы удалить товар из корзины нажмите на него!\n Для оформления заказа выберите пункт "Оформить заказ"',
                               reply_markup=user_markup)
        bot.register_next_step_handler(msg, del_item)
    except KeyError:
        pass


# Оформление заказа
def checkout(message):
    user_markup = tb.types.ReplyKeyboardMarkup(True)
    user_markup.row('Все верно!', "Меню")
    show_basket(message)

    # Ввод адреса доставки
    def address(message):
        if message.text.lower() == 'все верно!':
            msg = bot.send_message(message.from_user.id, 'Введите адрес доставки(улица, дом)',
                                   reply_markup=tb.types.ReplyKeyboardRemove())

            def number_phone(message):
                dict_address[message.from_user.id] = {}
                dict_address[message.from_user.id]['address'] = message.text
                msg = bot.send_message(message.from_user.id, 'Введите контактный номер телефона',
                                       reply_markup=tb.types.ReplyKeyboardRemove())

                def add_number_phone(message):
                    dict_address[message.from_user.id]['phone_number'] = message.text
                    if admins != []:
                        for i in admins:
                            show_basket(message, i)
                    dict_basket[message.from_user.id].clear()
                    user_markup = tb.types.ReplyKeyboardMarkup(True)
                    user_markup.row("Меню")
                    msg = bot.send_message(message.from_user.id,
                                           'Ваш заказ оформлен, менеджер свяжется с вами в ближайщее время для подтверждения заказа.',
                                           reply_markup=user_markup)
                    bot.register_next_step_handler(msg, handler_text)

                bot.register_next_step_handler(msg, add_number_phone)

            bot.register_next_step_handler(msg, number_phone)
        else:
            handler_text(message)
            return None

    msg = bot.send_message(message.from_user.id, 'Проверьте ваш заказ:', reply_markup=user_markup)
    bot.register_next_step_handler(msg, address)


# Очистка корзины
def clear_basket(message):
    if message.from_user.id in dict_basket:
        dict_basket[message.from_user.id].clear()
    bot.send_message(message.from_user.id, 'Корзина пуста!')
    # keyboard_start(message)
    tuple_1 = show_category(message)
    msg_1 = add_row_menu_basket(tuple_1)
    bot.register_next_step_handler(msg_1, selected_category)


# Функция для брендов товаров в выбранной категории
def selected_category(message, admin=False):
    if call_menu(message):
        return None
    elif message.text.lower() == 'корзина':
        edit_basket(message)
        return None
    message_2 = message

    # Функция для отображения товаров в выбранном бренде
    def goods_in_brand(message, admin=False):
        if call_menu(message):
            return None
        elif message.text.lower() == 'корзина':
            edit_basket(message)
            return None
        elif message.text.lower() == 'назад':
            tuple_1 = show_category(message)
            msg_1 = add_row_menu_basket(tuple_1)
            bot.register_next_step_handler(msg_1, selected_category)
            return None
        message_1 = message

        # Добавление товара в корзину
        def append_goods(message, admin=False):
            if message.text.lower() == 'назад':
                selected_category(message_2)
                return None
            elif call_menu(message):
                return None
            elif message.text.lower() == 'оформить заказ':
                checkout(message)
                return None
            elif message.text.lower() == 'корзина':
                edit_basket(message)
                return None
            try:
                good = message.text[:-2].split(' --- ')
                good_name = good[0]
                good_price = dict_name[good_name]
            except:
                goods_in_brand(message_1)
                return None
            if message.from_user.id not in dict_basket:
                dict_basket[message.from_user.id] = {}
            if good_name in dict_basket[message.from_user.id]:
                dict_basket[message.from_user.id][good_name]['count'] += 1
            else:
                dict_basket[message.from_user.id][good_name] = {'price': good_price, 'count': 1}
            bot.send_message(message.from_user.id, f'Товар {good_name} добавлен в корзину')
            show_basket(message)
            goods_in_brand(message_1)

        brand = message.text
        user_markup = tb.types.ReplyKeyboardMarkup(True)
        if message.from_user.id in dict_basket and dict_basket[message.from_user.id] != {}:
            user_markup.row('Оформить заказ')
        dict_name = {}
        for i in cursor.execute(
                f'SELECT * FROM "{cat + "_1"}" WHERE brand_id = (SELECT brand_id FROM "{cat}" WHERE Название = "{brand}")').fetchall():
            user_markup.row(f'{i[1]} --- {i[2]}р.')
            dict_name[i[1]] = i[2]
        if len(dict_name) == 0:
            bot.send_message(message.from_user.id,
                             'Такого бренда нет или отсутствуют товары этого брэнда в данной категории')
            if not admin:
                selected_category(message_2)
            return None
        if admin:
            user_markup.row("Меню")
            return (user_markup, message, append_goods)
        user_markup.row("Назад", "Меню", "Корзина")
        msg = bot.send_message(message.from_user.id, 'Выберите товар:', reply_markup=user_markup)
        bot.register_next_step_handler(msg, append_goods)

    cat = message.text
    user_markup = tb.types.ReplyKeyboardMarkup(True)
    try:
        if len([user_markup.row(i[1]) for i in cursor.execute(f'SELECT * FROM "{cat}"').fetchall()]) == 0:
            if not admin:
                bot.send_message(message.from_user.id,
                                 'К сожалению, в данной категории пока нет товаров, мы добавим их позже.')
            raise sqlite3.OperationalError
    except sqlite3.OperationalError:
        if admin:
            return None
        tuple_1 = show_category(message)
        msg_1 = add_row_menu_basket(tuple_1)
        bot.register_next_step_handler(msg_1, selected_category)
        return None
    if admin:
        user_markup.row('Меню')
        return (user_markup, message, goods_in_brand)
    user_markup.row("Назад", "Меню", "Корзина")
    msg = bot.send_message(message.from_user.id, 'Выберите бренд товара:', reply_markup=user_markup)
    bot.register_next_step_handler(msg, goods_in_brand)


# Админ панель
def admin_panel(message):
    user_markup = tb.types.ReplyKeyboardMarkup(True)
    user_markup.row('Добавить категорию товаров', "Удалить категорию товаров")
    user_markup.row('Добавить товар в базу', "Удалить товар из базы")
    user_markup.row('Удалить бренд из базы')
    user_markup.row("Меню", "Выход из админ панели")
    msg = bot.send_message(message.from_user.id, 'Выберите действие', reply_markup=user_markup)
    bot.register_next_step_handler(msg, select_admin_menu)


# Функция для распределения пунктов админ панели по соответствующим функциям
def select_admin_menu(message):
    user_markup = tb.types.ReplyKeyboardMarkup(True)
    user_markup.row('Меню')
    if message.text.lower() == "добавить категорию товаров":
        msg = bot.send_message(message.from_user.id, 'Введите название новой категории',
                               reply_markup=user_markup)
        bot.register_next_step_handler(msg, add_cat)
    elif message.text.lower() == 'меню':
        keyboard_start(message)
        return None
    elif message.text.lower() == 'удалить категорию товаров':
        tuple_1 = show_category(message)
        tuple_1[0].row('Меню')
        msg_1 = bot.send_message(tuple_1[1].from_user.id, 'Выберите категорию, которую необходимо удалить',
                                 reply_markup=tuple_1[0])
        bot.register_next_step_handler(msg_1, drop_cat)
    elif message.text.lower() == 'добавить товар в базу':
        tuple_1 = show_category(message)
        tuple_1[0].row('Меню')
        # Добавить товар в базу
        message_1 = message

        def add_good(message):
            message_2 = message
            if message.text.lower() == 'меню':
                keyboard_start(message)
                return None
            cat = [i[0] for i in cursor.execute('SELECT * FROM "Category"').fetchall()]
            if message.text not in cat:
                add_cat(message, False)
            brand_in_cat = [i[1] for i in cursor.execute(f'SELECT * FROM "{message_2.text}"').fetchall()]

            def add_good_1(message):
                message_3 = message
                if message.text.lower() == 'меню':
                    keyboard_start(message)
                    return None
                brands = [i[1] for i in cursor.execute(f'SELECT * FROM "{message_2.text}"').fetchall()]
                if message.text not in brands:
                    max_brand_id = cursor.execute(f'SELECT MAX(brand_id) FROM "{message_2.text}"').fetchall()[0][0]
                    if max_brand_id is None:
                        max_brand_id = 0
                    cursor.execute(
                        f'INSERT INTO "{message_2.text}" VALUES({max_brand_id + 1}, "{message.text}")').fetchall()
                    conn.commit()

                def add_good_2(message):
                    if message.text.lower() == 'меню':
                        keyboard_start(message)
                        return None
                    good_date = [cursor.execute(
                        f'SELECT brand_id FROM "{message_2.text}" WHERE Название = "{message_3.text}"').fetchall()[0][0]] + message.text.split('---')
                    try:
                        if cursor.execute(
                                f'SELECT * FROM "{message_2.text}_1" WHERE "Название" = "{good_date[1]}"').fetchall():
                            raise sqlite3.OperationalError
                        cursor.execute(f'INSERT INTO "{message_2.text}_1" VALUES{tuple(good_date)}')
                        conn.commit()
                        user_markup = tb.types.ReplyKeyboardMarkup(True)
                        user_markup.row('Меню')
                        bot.send_message(message.from_user.id,
                                         f'Товар {good_date[1]} ценой {good_date[2]}р. успешно добавлен!',
                                         reply_markup=user_markup)
                    except sqlite3.OperationalError:
                        bot.send_message(message.from_user.id,
                                         f'Ошибка при добавлении товара!')
                        keyboard_start(message)

                msg = bot.send_message(message.from_user.id,
                                       'Введите данные по новому товару через три дефиса(Название---Цена)',
                                       reply_markup=tb.types.ReplyKeyboardRemove())
                bot.register_next_step_handler(msg, add_good_2)

            user_markup = tb.types.ReplyKeyboardMarkup(True)
            [user_markup.row(i) for i in brand_in_cat]
            user_markup.row('Меню')
            msg = bot.send_message(message.from_user.id, 'Выберите бренд или введите новый с клавиатуры',
                                   reply_markup=user_markup)
            bot.register_next_step_handler(msg, add_good_1)

        msg_1 = bot.send_message(tuple_1[1].from_user.id,
                                 'Выберите категорию, для добавления товара или введите новую с клавиатуры',
                                 reply_markup=tuple_1[0])
        bot.register_next_step_handler(msg_1, add_good)
    elif message.text.lower() == 'выход из админ панели':
        admins.remove(message.from_user.id)
        keyboard_start(message)
    elif message.text.lower() == 'удалить товар из базы':
        tuple_1 = show_category(message)
        tuple_1[0].row('Меню')
        msg_1 = bot.send_message(tuple_1[1].from_user.id, 'Выберите категорию, из которой нужно удалить товар',
                                 reply_markup=tuple_1[0])
        bot.register_next_step_handler(msg_1, selected_category_true)
    elif message.text.lower() == 'удалить бренд из базы':
        tuple_1 = show_category(message)
        tuple_1[0].row('Меню')
        msg_1 = bot.send_message(tuple_1[1].from_user.id, 'Выберите категорию, из которой нужно удалить бренд',
                                 reply_markup=tuple_1[0])
        bot.register_next_step_handler(msg_1, select_brand_for_delete)
    else:
        bot.send_message(message.from_user.id, 'Я тебя не понимаю, попробуй снова.')
        keyboard_start(message)


# Вызов функции selected_category с двумя параметрами
def selected_category_true(message):
    if call_menu(message):
        return None
    tuple_1 = selected_category(message, True)

    def good_in_brand_true(message):
        if call_menu(message):
            return None
        tuple_2 = tuple_1[2](message, True)

        def delete_good(message):
            if call_menu(message):
                return None
            n = cursor.execute(
                f'DELETE FROM "{tuple_1[1].text}_1" WHERE "Название" = "{message.text.split(" --- ")[0]}"')
            conn.commit()
            user_markup = tb.types.ReplyKeyboardMarkup(True)
            user_markup.row('Меню')
            if n.rowcount == 0:
                bot.send_message(message.from_user.id, f'Товар {message.text.split(" --- ")[0]} не найден!',
                                 reply_markup=user_markup)
            else:
                bot.send_message(message.from_user.id, f'Товар {message.text.split(" --- ")[0]} удален из базы!',
                                 reply_markup=user_markup)

        try:
            msg_1 = bot.send_message(message.from_user.id, 'Выберите товар, который необходимо удалить',
                                     reply_markup=tuple_2[0])
        except:
            admin_panel(message)
            return None
        bot.register_next_step_handler(msg_1, delete_good)

    try:
        msg_1 = bot.send_message(message.from_user.id, 'Выберите бренд, из которого необходимо удалить товар',
                                 reply_markup=tuple_1[0])
    except:
        bot.send_message(message.from_user.id, 'Непрвильно введенна категория товара для удаление!')
        admin_panel(message)
        return None
    bot.register_next_step_handler(msg_1, good_in_brand_true)

# удаление бренда
def select_brand_for_delete(message):
    if call_menu(message):
        return None
    tuple_1 = selected_category(message, True)
    def delete_brand(message):
        try:
            m = cursor.execute(f'SELECT "brand_id" FROM "{tuple_1[1].text}" WHERE "Название" = "{message.text}"').fetchall()[0][0]
        except IndexError:
            m = 0
        cursor.execute(f'DELETE FROM "{tuple_1[1].text}_1" WHERE "brand_id" = {m}')
        conn.commit()
        n = cursor.execute(f'DELETE FROM "{tuple_1[1].text}" WHERE "brand_id" = {m}')
        conn.commit()
        user_markup = tb.types.ReplyKeyboardMarkup(True)
        user_markup.row('Меню')
        if n.rowcount == 0:
            bot.send_message(message.from_user.id, f'Бренд {message.text.split(" --- ")[0]} не найден!',
                             reply_markup=user_markup)
        else:
            bot.send_message(message.from_user.id, f'Бренд {message.text.split(" --- ")[0]} и все связанные с ним товары удалены из базы!',
                             reply_markup=user_markup)

    try:
        msg_1 = bot.send_message(message.from_user.id, 'Выберите бренд, который необходимо удалить',
                                 reply_markup=tuple_1[0])
    except:
        bot.send_message(message.from_user.id, 'Непрвильно введенна категория товара для удаление!')
        admin_panel(message)
        return None
    bot.register_next_step_handler(msg_1, delete_brand)

# Добавить категорию
def add_cat(message, menu=True):
    if message.text.lower() == 'меню':
        admin_panel(message)
        return None
    new_cat = message.text
    try:
        cursor.execute(f'''CREATE TABLE "{new_cat}" (
        "brand_id"	INTEGER,
        "Название"	TEXT,
        PRIMARY KEY("brand_id")
    );''')
        conn.commit()
        cursor.execute(f'''CREATE TABLE "{new_cat}_1" (
        "brand_id"	INTEGER,
        "Название"	TEXT,
        "Цена"	INTEGER,
        FOREIGN KEY("brand_id") REFERENCES "{new_cat}"("brand_id")
    );''')
        conn.commit()
        cursor.execute(f'INSERT INTO Category VALUES ("{new_cat}");')
        conn.commit()
        all_cat()
        bot.send_message(message.from_user.id, f'Категория {new_cat} добавленна!')
    except sqlite3.OperationalError:
        bot.send_message(message.from_user.id, f'Категория {new_cat} уже существует!')
    if menu:
        admin_panel(message)


# Удалить категорию
def drop_cat(message):
    if message.text.lower() == 'меню':
        admin_panel(message)
        return None
    try:
        drop_cat = message.text
        cursor.execute(f'DROP TABLE "{drop_cat}";')
        conn.commit()
        cursor.execute(f'DROP TABLE "{drop_cat}_1";')
        conn.commit()
        cursor.execute(f'DELETE FROM Category WHERE "Название" = "{drop_cat}";')
        conn.commit()
        all_cat()
        bot.send_message(message.from_user.id, f'Категория {drop_cat} удаленна!')
    except sqlite3.OperationalError:
        bot.send_message(message.from_user.id, f'Категория {drop_cat} не существует!')

    admin_panel(message)


# Основной оброботчик
@bot.message_handler(content_types=['text'])
def handler_text(message):
    if message.text.lower() == 'о нас':
        bot.send_message(message.from_user.id, utils.text_about)
        keyboard_start(message)
    elif message.text.lower() == 'адреса магазинов':
        bot.send_message(message.from_user.id, utils.text_addresses)
        keyboard_start(message)
    elif message.text.lower() == 'сделать заказ':
        tuple_1 = show_category(message)
        msg_1 = add_row_menu_basket(tuple_1)
        bot.register_next_step_handler(msg_1, selected_category)
    elif message.text.lower() == 'меню':
        keyboard_start(message)
        # if message.from_user.id in admins:
        #     admin_panel(message)
        # else:
        #     keyboard_start(message)
    elif message.text == 'qwerty123':
        admins.add(message.from_user.id)
        admin_panel(message)
    else:
        bot.send_message(message.from_user.id, 'Я тебя не понимаю, попробуй снова.')
        keyboard_start(message)

    # keyboard_start(message)


# Функция для вызова меню, очистки корзины
def call_menu(message):
    if message.text.lower() == 'меню':
        handler_text(message)
        return True
    return False


bot.polling(none_stop=True)
