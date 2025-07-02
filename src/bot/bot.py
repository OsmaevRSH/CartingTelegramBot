import logging
from datetime import date
from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    ConversationHandler, CallbackQueryHandler
)
from src.parsers.parsers import ArchiveParser, RaceParser, FullRaceInfoParser
from src.models.models import ParsingError
from src.database.db import init_db, save_competitor, get_user_competitors, get_competitor_by_key, delete_competitor, get_all_competitors, get_best_competitors, get_best_competitors_today
import json

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

try:
    from config.config import BOT_TOKEN
    if not BOT_TOKEN:
        print("❌ Не установлен BOT_TOKEN!")
        print("Установи переменную окружения BOT_TOKEN или добавь в файл .env")
        exit(1)
except ImportError:
    print("❌ Не найден файл config/config.py!")
    print("Создай файл config/config.py на основе config/config.py.example")
    exit(1)

# Инициализируем парсеры
archive_parser = ArchiveParser()
race_parser = RaceParser()
full_race_parser = FullRaceInfoParser()

# -------------------- Conversation states --------------------
SELECT_USER, SELECT_DATE, SHOW_RACES, SHOW_CARTS = range(4)


def _format_lap_times_table(lap_times_json: str) -> str:
    """Форматирует данные о кругах в виде красивой таблицы"""
    if not lap_times_json:
        return "📊 Данные о кругах недоступны"
    
    try:
        lap_times = json.loads(lap_times_json)
        if not lap_times:
            return "📊 Нет данных о кругах"
        
        # Компактная таблица для мобильных устройств
        table = "```\n"
        table += f"{'#':^2}  {'Время':<8}  {'S1':<8}  {'S2':<8}  {'S3':<8}  {'S4':<8}\n"
        table += f"{'--':^2}  {'--------':<8}  {'--------':<8}  {'--------':<8}  {'--------':<8}  {'--------':<8}\n"
        
        for lap in lap_times:
            lap_num = lap['lap_number']
            lap_time = lap['lap_time'] or "-"
            sector1 = lap['sector1'] or "-"
            sector2 = lap['sector2'] or "-"
            sector3 = lap['sector3'] or "-"
            sector4 = lap['sector4'] or "-"
            
            # Для стартового круга показываем только S2, S3, S4
            if lap_num == 0:
                lap_label = "S"
                s1_display = "-"
            else:
                lap_label = f"{lap_num}"
                s1_display = sector1
            
            # Компактное форматирование с левым выравниванием времени
            table += f"{lap_label:^2}  {lap_time:<8}  {s1_display:<8}  {sector2:<8}  {sector3:<8}  {sector4:<8}\n"
        
        table += "```"
        return table
        
    except json.JSONDecodeError:
        return "❌ Ошибка при чтении данных о кругах"




async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок"""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)


async def _set_default_commands(app: Application) -> None:
    """Устанавливаем команды бота"""
    await app.bot.set_my_commands([
        BotCommand("add", "Добавить заезд"),
        BotCommand("stats", "Статистика пользователя"),
        BotCommand("best", "Рейтинг гонщиков"),
        BotCommand("best_today", "Рейтинг за сегодня"),
    ])


# =============================================================
#  Команда /add   (добавить заезд)
# =============================================================

# helpers ------------------------------------------------------

def _build_keyboard(rows):
    """Утилита для быстрого создания InlineKeyboardMarkup."""
    return InlineKeyboardMarkup([[InlineKeyboardButton(text, callback_data=data) for text, data in row] for row in rows])


def _send_user_keyboard(target, context):
    """Отрисовывает клавиатуру выбора пользователя в сообщении/колбэке target."""
    users_ordered = context.user_data.get("user_options", [])
    if not users_ordered:
        # safety-fallback: получаем админов чата
        chat_id = target.message.chat.id if hasattr(target, "message") else target.chat_id
        users_ordered = [context.bot.get_chat_member(chat_id, chat_id).user]
    keyboard = _build_keyboard([[(u.full_name or u.username or str(u.id), f"user_{u.id}")] for u in users_ordered])
    if isinstance(target, Update):
        return target.message.reply_text("Кого записываем?", reply_markup=keyboard)
    else:
        return target.edit_message_text("Кого записываем?", reply_markup=keyboard)


# step 0 – entry ------------------------------------------------

async def add_race_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Точка входа в сценарий добавления заезда."""
    chat_id = update.effective_chat.id

    # Пытаемся получить список администраторов (хотя бы они гарантированно доступны)
    try:
        admins = await context.bot.get_chat_administrators(chat_id)
        users = [adm.user for adm in admins]
    except Exception:
        users = []

    # Добавляем инициатора в начало списка, избегаем дубликатов по id
    initiator = update.effective_user
    users_dict = {initiator.id: initiator}
    for u in users:
        users_dict.setdefault(u.id, u)

    users_ordered = list(users_dict.values())
    # сохраняем список, чтобы можно было вернуться
    context.user_data["user_options"] = users_ordered

    # Строим клавиатуру – одна кнопка на пользователя
    keyboard = _build_keyboard([[(u.full_name or u.username or str(u.id), f"user_{u.id}")] for u in users_ordered])

    await update.message.reply_text("Кого записываем?", reply_markup=keyboard)
    return SELECT_USER


# step 1 – user selected ---------------------------------------

async def select_user_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = int(query.data.split("_", 1)[1])
    context.user_data["selected_user"] = user_id

    # сохраняем имя выбранного пользователя
    sel_user = next((u for u in context.user_data["user_options"] if u.id == user_id), None)
    context.user_data["selected_user_name"] = sel_user.full_name or sel_user.username if sel_user else str(user_id)

    # Получаем архив заездов
    try:
        day_races = await archive_parser.parse()
    except ParsingError as e:
        await query.edit_message_text(f"❌ Ошибка парсинга архива: {e}")
        return ConversationHandler.END

    # Отделяем сегодняшнюю дату
    today = date.today()
    today_dr = next((dr for dr in day_races if dr.date.date() == today), None)
    other_dates = [dr for dr in day_races if dr.date.date() != today]
    context.user_data["other_dates"] = other_dates

    # показываем первую страницу
    await _send_date_page(query, context, today_exists=bool(today_dr), page=0)
    return SELECT_DATE


# helpers ------------------------------------------------------

PAGE_SIZE = 10


async def _send_date_page(query, context, today_exists: bool, page: int):
    dates = context.user_data["other_dates"]
    context.user_data["last_page"] = page
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    slice_dates = dates[start:end]

    rows = []
    if today_exists:
        rows.append([("Сегодня", "date_today")])

    # кнопки дат
    for idx, dr in enumerate(slice_dates, start=start):
        rows.append([(dr.date.strftime("%d.%m.%Y"), f"date_{idx}")])

    # пагинация
    nav = []
    if start > 0:
        nav.append(("« Назад", f"page_{page-1}"))
    if end < len(dates):
        nav.append(("Вперёд »", f"page_{page+1}"))
    if nav:
        rows.append(nav)

    # кнопка назад к пользователям
    rows.append([("← Назад к выбору пользователя", "back_users")])

    keyboard = _build_keyboard(rows)
    user_text = context.user_data.get("selected_user_name", "")
    subtitle = f"Пользователь: {user_text}\n"
    text = subtitle + ("Выберите дату заезда:" if slice_dates else "Нет данных для отображения")
    await query.edit_message_text(text, reply_markup=keyboard)


# step 2 – pagination ------------------------------------------

async def date_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    page = int(query.data.split("_", 1)[1])
    await _send_date_page(query, context, today_exists=True, page=page)
    return SELECT_DATE


# step 3 – date chosen -----------------------------------------

async def select_date_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    key = query.data.split("_", 1)[1]

    if key == "today":
        sel_date = date.today()
        # ищем в кэше other_dates или парсим заново
        dr_list = context.user_data.get("other_dates", [])
        day_race = next((dr for dr in dr_list if dr.date.date() == sel_date), None)
        if day_race is None:
            # fallback – перезапрос
            day_races = await archive_parser.parse()
            day_race = next((dr for dr in day_races if dr.date.date() == sel_date), None)
    else:
        idx = int(key)
        day_race = context.user_data["other_dates"][idx]

    if not day_race:
        await query.edit_message_text("❌ Заезды не найдены")
        return ConversationHandler.END

    # сохраняем выбранную дату и список заездов
    date_text = "Сегодня" if key == "today" else day_race.date.strftime("%d.%m.%Y")
    # Для сохранения в БД всегда используем реальную дату
    actual_date = date.today().strftime("%d.%m.%Y") if key == "today" else day_race.date.strftime("%d.%m.%Y")
    context.user_data["selected_date_text"] = date_text
    context.user_data["selected_date_actual"] = actual_date
    context.user_data["current_races"] = day_race.races

    # показываем список заездов (до 10 для начала)
    buttons = [[(f"Заезд {r.number}", f"race_{idx}")] for idx, r in enumerate(day_race.races[:10])]
    # добавляем кнопку назад
    buttons.append([("← Назад к выбору даты", "back_dates")])

    keyboard = _build_keyboard(buttons)
    header = f"Пользователь: {context.user_data.get('selected_user_name','')}\nДата: {date_text}"
    await query.edit_message_text(f"{header}\nВыберите заезд:", reply_markup=keyboard)

    return SHOW_RACES


# step 4 – back to dates ---------------------------------------

async def back_to_dates_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    # вернуться на первую страницу (или сохранённую)
    page = context.user_data.get("last_page", 0)
    await _send_date_page(query, context, today_exists=True, page=page)
    return SELECT_DATE


# step 5 – back to user list ------------------------------------

async def back_to_users_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await _send_user_keyboard(query, context)
    return SELECT_USER


# step 4b – race selected --------------------------------------

async def race_selected_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    idx = int(query.data.split("_", 1)[1])
    races_list = context.user_data.get("current_races", [])
    if idx >= len(races_list):
        await query.edit_message_text("❌ Не удалось найти заезд")
        return ConversationHandler.END

    race = races_list[idx]

    # Парсим результаты выбранного заезда
    try:
        carts = await race_parser.parse(race.href)
    except ParsingError as e:
        await query.edit_message_text(f"❌ Ошибка парсинга: {e}")
        return ConversationHandler.END

    context.user_data["current_carts"] = carts
    context.user_data["selected_race_number"] = race.number
    context.user_data["selected_race_href"] = race.href

    # build cart buttons
    cart_buttons = [[(f"Карт {c.number} ⏱ {c.best_lap}", f"cart_{idx}")] for idx, c in enumerate(carts[:10])]
    cart_buttons.append([("← Назад к выбору заезда", "back_races")])

    keyboard = _build_keyboard(cart_buttons)

    header = (
        f"Пользователь: {context.user_data.get('selected_user_name','')}\n"
        f"Дата: {context.user_data.get('selected_date_text','')}\n"
        f"Заезд: {race.number}"
    )

    await query.edit_message_text(f"{header}\nВыберите карт:", reply_markup=keyboard)
    return SHOW_CARTS


# step 4c – cart selected --------------------------------------

async def cart_selected_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    idx = int(query.data.split("_",1)[1])
    carts = context.user_data.get("current_carts", [])
    if idx >= len(carts):
        await query.edit_message_text("❌ Не удалось найти карт")
        return ConversationHandler.END

    cart = carts[idx]
    
    # Получаем href выбранного заезда
    race_href = context.user_data.get("selected_race_href", "")
    
    # Получаем полную информацию о заезде
    try:
        await query.edit_message_text("🔄 Получаю детальную информацию о заезде...")
        competitors = await full_race_parser.parse(race_href, carts)
        
        # Находим выбранного конкурента
        selected_competitor = None
        for competitor in competitors:
            if competitor.num == cart.number:
                selected_competitor = competitor
                break
        
        if not selected_competitor:
            await query.edit_message_text("❌ Не удалось найти детальную информацию о выбранном карте")
            return ConversationHandler.END
        
        # Сохраняем полную информацию о конкуренте
        competitor_data = {
            'id': selected_competitor.id,
            'num': selected_competitor.num,
            'name': selected_competitor.name,
            'pos': selected_competitor.pos,
            'laps': selected_competitor.laps,
            'theor_lap': selected_competitor.theor_lap,
            'best_lap': selected_competitor.best_lap,
            'binary_laps': selected_competitor.binary_laps,
            'theor_lap_formatted': selected_competitor.theor_lap_formatted,
            'display_name': selected_competitor.display_name,
            'gap_to_leader': selected_competitor.gap_to_leader,
            'lap_times': selected_competitor.lap_times,
        }
        
        save_competitor(
            user_id=query.from_user.id,
            date=context.user_data.get("selected_date_actual",""),
            race_number=context.user_data.get("selected_race_number",""),
            race_href=race_href,
            competitor_data=competitor_data
        )

        resp = (
            "✅ **ЗАЕЗД СОХРАНЁН** ✅\n\n"
            f"👤 Пользователь: {context.user_data.get('selected_user_name','')}\n"
            f"📅 Дата: {context.user_data.get('selected_date_text','')}\n"
            f"🏁 Заезд: {context.user_data.get('selected_race_number','')}\n"
            f"🏎️ Карт: {selected_competitor.num}\n"
            f"⏱️ Лучший круг: {selected_competitor.best_lap}\n\n"
            "🎉 Данные успешно сохранены с детальной информацией о кругах!"
        )
        await query.edit_message_text(resp)
        
    except ParsingError as e:
        # Если не удалось получить полную информацию, возвращаем ошибку
        await query.edit_message_text(f"❌ Ошибка получения детальных данных: {str(e)[:100]}")
        return ConversationHandler.END
    
    return ConversationHandler.END


# back to races from carts --------------------------------------

async def back_to_races_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # reuse previously built list of races
    races = context.user_data.get("current_races", [])
    buttons = [[(f"Заезд {r.number}", f"race_{idx}")] for idx, r in enumerate(races[:10])]
    buttons.append([("← Назад к выбору даты", "back_dates")])
    keyboard = _build_keyboard(buttons)

    header = (
        f"Пользователь: {context.user_data.get('selected_user_name','')}\n"
        f"Дата: {context.user_data.get('selected_date_text','')}"
    )
    await query.edit_message_text(f"{header}\nВыберите заезд:", reply_markup=keyboard)
    return SHOW_RACES


# команда /stats – показать статистику пользователя
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику выбранного пользователя"""
    chat_id = update.effective_chat.id

    # Получаем всех пользователей, у которых есть заезды
    all_competitors = get_all_competitors()
    if not all_competitors:
        await update.message.reply_text("📊 Пока нет сохранённых заездов.")
        return

    # Получаем уникальных пользователей
    user_ids = set()
    for comp in all_competitors:
        user_ids.add(comp[0])  # user_id - первый элемент

    # Пытаемся получить информацию о пользователях
    try:
        admins = await context.bot.get_chat_administrators(chat_id)
        users_info = {adm.user.id: adm.user for adm in admins}
    except:
        users_info = {}

    # Добавляем инициатора
    initiator = update.effective_user
    users_info[initiator.id] = initiator

    # Создаем список пользователей для выбора
    users_list = []
    for user_id in user_ids:
        if user_id in users_info:
            user = users_info[user_id]
            users_list.append((user.full_name or user.username or f"ID:{user_id}", f"stats_user_{user_id}"))
        else:
            users_list.append((f"ID:{user_id}", f"stats_user_{user_id}"))

    if not users_list:
        await update.message.reply_text("📊 Не найдено пользователей с заездами.")
        return

    # Создаем клавиатуру
    keyboard = _build_keyboard([users_list[i:i+1] for i in range(len(users_list))])
    await update.message.reply_text("👤 Выберите пользователя для просмотра статистики:", reply_markup=keyboard)


def main() -> None:
    """Главная функция для запуска бота"""
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()

    # инициализируем БД
    init_db()

    # Регистрируем системное меню команд
    application.post_init = _set_default_commands

    # Handler for /add command conversation
    conv = ConversationHandler(
        entry_points=[CommandHandler("add", add_race_command)],
        states={
            SELECT_USER: [CallbackQueryHandler(select_user_callback, pattern=r"^user_\d+$")],
            SELECT_DATE: [
                CallbackQueryHandler(date_page_callback, pattern=r"^page_\d+$"),
                CallbackQueryHandler(select_date_callback, pattern=r"^date_.*$"),
                CallbackQueryHandler(back_to_users_callback, pattern=r"^back_users$"),
            ],
            SHOW_RACES: [
                CallbackQueryHandler(back_to_dates_callback, pattern=r"^back_dates$"),
                CallbackQueryHandler(race_selected_callback, pattern=r"^race_\d+$"),
            ],
            SHOW_CARTS: [
                CallbackQueryHandler(back_to_races_callback, pattern=r"^back_races$"),
                CallbackQueryHandler(cart_selected_callback, pattern=r"^cart_\d+$"),
            ],
        },
        fallbacks=[],
    )
    application.add_handler(conv)

    # команда /stats – показать статистику пользователя
    application.add_handler(CommandHandler("stats", stats_command))
    


    # обработчик выбора пользователя для статистики
    async def stats_user_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        # Извлекаем user_id и страницу из callback_data
        data_parts = query.data.split("_")
        user_id = int(data_parts[2])
        page = int(data_parts[3]) if len(data_parts) > 3 else 0
        
        # Получаем данные пользователя
        competitors = get_user_competitors(user_id)
        
        if competitors:
            # Пытаемся получить имя пользователя
            try:
                chat_member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
                user_name = chat_member.user.full_name or chat_member.user.username or f"ID:{user_id}"
            except:
                user_name = f"ID:{user_id}"
            
            # Формируем простое сообщение без таблицы
            text = f"📊 **СТАТИСТИКА {user_name.upper()}** 📊\n\n"
            text += f"📈 Всего заездов: {len(competitors)}\n\n"
            text += "💡 Выберите заезд для детального просмотра:"
            
            # Пагинация по 10 заездов
            start_idx = page * 10
            end_idx = start_idx + 10
            page_competitors = competitors[start_idx:end_idx]
            
            # Добавляем кнопки для детального просмотра
            rows = []
            for comp_data in page_competitors:
                date, race_number, race_href, competitor_id, num, name, pos, laps, theor_lap, best_lap, binary_laps, theor_lap_formatted, display_name, gap_to_leader, lap_times_json = comp_data
                
                race_part = race_number.strip()
                if not race_part.lower().startswith("заезд") and not race_part.startswith("З"):
                    race_part = f"Заезд {race_part}"
                
                button_text = f"{date[:5]} {race_part[:12]} #{num} | {pos} место | {best_lap}"
                key = f"{date}|{race_number}|{num}|{user_id}"
                rows.append([(button_text, f"view_stats_{key}")])
            
            # Добавляем кнопки навигации
            nav_buttons = []
            if page > 0:
                nav_buttons.append(("◀️ Назад", f"stats_user_{user_id}_{page-1}"))
            if end_idx < len(competitors):
                nav_buttons.append(("Вперёд ▶️", f"stats_user_{user_id}_{page+1}"))
            
            if nav_buttons:
                rows.append(nav_buttons)
            
            keyboard = _build_keyboard(rows)
            await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
        else:
            await query.edit_message_text(f"📊 У пользователя ID:{user_id} нет сохранённых заездов.")

    application.add_handler(CallbackQueryHandler(stats_user_callback, pattern=r"^stats_user_\d+(_\d+)?$"))

    # команда /best – общий рейтинг
    async def best_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать рейтинг лучших гонщиков"""
        competitors = get_best_competitors(20)
        
        if not competitors:
            await update.message.reply_text("🏆 Пока нет данных для рейтинга.")
            return
        
        text = "🏆 **РЕЙТИНГ ЛУЧШИХ ГОНЩИКОВ** 🏆\n"
        text += "```\n"
        text += f"{'#':^2} {'Гонщик':<22} {'Карт':<6} {'Время':<8}\n"
        text += f"{'--':^2} {'----------------------':<22} {'------':<6} {'--------':<8}\n"
        
        chat_id = update.effective_chat.id
        
        for i, comp in enumerate(competitors, 1):
            user_id, date, race_number, num, name, display_name, theor_lap, theor_lap_formatted, best_lap, pos = comp
            
            # Пытаемся получить настоящее имя пользователя
            show_name = "Неизвестный"
            
            # Сначала пробуем имя из заезда
            if name and name.strip() and not display_name.startswith("Карт #"):
                show_name = name[:22]
            else:
                # Пытаемся получить имя через Telegram API
                try:
                    chat_member = await context.bot.get_chat_member(chat_id, user_id)
                    if chat_member.user.full_name:
                        show_name = chat_member.user.full_name[:22]
                    elif chat_member.user.username:
                        show_name = f"@{chat_member.user.username}"[:22]
                    else:
                        show_name = f"ID:{user_id}"[:22]
                except:
                    show_name = f"ID:{user_id}"[:22]
            
            cart_num = f"#{num}"[:6]  # Увеличили до 6 символов
            text += f"{i:^2} {show_name:<22} {cart_num:<6} {best_lap:<8}\n"
        text += "```\n"
        text += "⏱️ Рейтинг по лучшему кругу"
        
        await update.message.reply_text(text, parse_mode='Markdown')

    application.add_handler(CommandHandler("best", best_command))

    # команда /best_today – рейтинг за сегодня
    async def best_today_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать рейтинг лучших гонщиков за сегодня"""
        from datetime import date
        today = date.today().strftime("%d.%m.%Y")
        
        competitors = get_best_competitors_today(today, 20)
        
        if not competitors:
            await update.message.reply_text("🏆 Сегодня заездов не было.")
            return
        
        text = f"🏆 **РЕЙТИНГ ЗА СЕГОДНЯ ({today})** 🏆\n"
        text += "```\n"
        text += f"{'#':^2} {'Гонщик':<22} {'Карт':<6} {'Время':<8}\n"
        text += f"{'--':^2} {'----------------------':<22} {'------':<6} {'--------':<8}\n"
        
        chat_id = update.effective_chat.id
        
        for i, comp in enumerate(competitors, 1):
            user_id, date, race_number, num, name, display_name, theor_lap, theor_lap_formatted, best_lap, pos = comp
            
            # Пытаемся получить настоящее имя пользователя
            show_name = "Неизвестный"
            
            # Сначала пробуем имя из заезда
            if name and name.strip() and not display_name.startswith("Карт #"):
                show_name = name[:22]
            else:
                # Пытаемся получить имя через Telegram API
                try:
                    chat_member = await context.bot.get_chat_member(chat_id, user_id)
                    if chat_member.user.full_name:
                        show_name = chat_member.user.full_name[:22]
                    elif chat_member.user.username:
                        show_name = f"@{chat_member.user.username}"[:22]
                    else:
                        show_name = f"ID:{user_id}"[:22]
                except:
                    show_name = f"ID:{user_id}"[:22]
            
            cart_num = f"#{num}"[:6]  # Увеличили до 6 символов
            text += f"{i:^2} {show_name:<22} {cart_num:<6} {best_lap:<8}\n"
        text += "```\n"
        text += "⏱️ Рейтинг по лучшему кругу за сегодня"
        
        await update.message.reply_text(text, parse_mode='Markdown')

    application.add_handler(CommandHandler("best_today", best_today_command))

    # обработчик просмотра заезда через статистику
    async def view_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        key = query.data.split("_", 2)[2]
        d, rn, cn, user_id = key.split("|")
        user_id = int(user_id)
        
        # Получаем данные заезда
        comp_data = get_competitor_by_key(user_id, d, rn, cn)
        
        if comp_data:
            # Показываем полную информацию
            date, race_number, race_href, competitor_id, num, name, pos, laps, theor_lap, best_lap, binary_laps, theor_lap_formatted, display_name, gap_to_leader, lap_times_json = comp_data
            
            # Показываем имя только если оно не дублирует номер карта
            name_line = ""
            if name.strip() and not display_name.startswith("Карт #"):
                name_line = f"👤 Имя: {name}\n"
            
            # Форматируем основную информацию
            basic_info = (
                f"📅 Дата: {date}\n"
                f"🏁 Заезд: {race_number}\n"
                f"🏎️ Карт: {num}\n"
                f"{name_line}"
                f"🏆 Позиция: {pos}\n"
                f"⏱️ Лучший круг: {best_lap}\n"
                f"🔬 Теоретический круг: {theor_lap_formatted}\n"
                f"📊 Отставание: {gap_to_leader}\n"
                f"🔄 Кругов: {laps}\n\n"
            )
            
            # Добавляем таблицу кругов
            lap_table = _format_lap_times_table(lap_times_json)
            
            text = basic_info + "📋 Данные по кругам:\n" + lap_table
        else:
            text = "❌ Данные заезда не найдены"
        
        buttons = [
            [("← Назад к статистике", f"stats_user_{user_id}")],
        ]
        await query.edit_message_text(text, reply_markup=_build_keyboard(buttons), parse_mode='Markdown')

    application.add_handler(CallbackQueryHandler(view_stats_callback, pattern=r"^view_stats_"))

    # -------- inline callbacks for старой системы /my ----------

    async def view_race_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        key = query.data.split("_",1)[1]
        d, rn, cn = key.split("|")
        
        # Сначала проверяем новую таблицу с полной информацией
        comp_data = get_competitor_by_key(query.from_user.id, d, rn, cn)
        
        if comp_data:
            # Показываем полную информацию
            date, race_number, race_href, competitor_id, num, name, pos, laps, theor_lap, best_lap, binary_laps, theor_lap_formatted, display_name, gap_to_leader, lap_times_json = comp_data
            
            # Показываем имя только если оно не дублирует номер карта
            name_line = ""
            if name.strip() and not display_name.startswith("Карт #"):
                name_line = f"👤 Имя: {name}\n"
            
            # Форматируем основную информацию
            basic_info = (
                f"📅 Дата: {date}\n"
                f"🏁 Заезд: {race_number}\n"
                f"🏎️ Карт: {num}\n"
                f"{name_line}"
                f"🏆 Позиция: {pos}\n"
                f"⏱️ Лучший круг: {best_lap}\n"
                f"🔬 Теоретический круг: {theor_lap_formatted}\n"
                f"📊 Отставание: {gap_to_leader}\n"
                f"🔄 Кругов: {laps}\n\n"
            )
            
            # Добавляем таблицу кругов
            lap_table = _format_lap_times_table(lap_times_json)
            
            text = basic_info + "📋 Данные по кругам:\n" + lap_table
        else:
            text = "❌ Данные заезда не найдены"
        
        buttons = [
            [("🗑 Удалить", f"askdel_{key}")],
            [("← Назад", "back_my")],
        ]
        await query.edit_message_text(text, reply_markup=_build_keyboard(buttons), parse_mode='Markdown')


    async def delete_race_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        key = query.data.split("_",1)[1]
        d, rn, cn = key.split("|")
        
        # Удаляем запись
        ok_competitor = delete_competitor(query.from_user.id, d, rn, cn)
        
        if ok_competitor:
            await query.edit_message_text("✅ Запись удалена")
        else:
            await query.edit_message_text("❌ Не удалось удалить (уже удалена)")


    async def cancel_my_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отмена в диалоге /my.

        Если есть ключ заезда, возвращаем подробности по нему,
        иначе выводим стандартное сообщение об отмене."""
        query = update.callback_query
        await query.answer()

        parts = query.data.split("_", 1)
        if len(parts) == 2 and "|" in parts[1]:
            key = parts[1]
            d, rn, cn = key.split("|")
            
            # Проверяем новую таблицу с полной информацией
            comp_data = get_competitor_by_key(query.from_user.id, d, rn, cn)
            
            if comp_data:
                date, race_number, race_href, competitor_id, num, name, pos, laps, theor_lap, best_lap, binary_laps, theor_lap_formatted, display_name, gap_to_leader, lap_times_json = comp_data
                
                # Показываем имя только если оно не дублирует номер карта
                name_line = ""
                if name.strip() and not display_name.startswith("Карт #"):
                    name_line = f"👤 Имя: {name}\n"
                
                text = (
                    f"📅 Дата: {date}\n"
                    f"🏁 Заезд: {race_number}\n"
                    f"🏎️ Карт: {num}\n"
                    f"{name_line}"
                    f"🏆 Позиция: {pos}\n"
                    f"⏱️ Лучший круг: {best_lap}\n"
                    f"🔬 Теоретический круг: {theor_lap_formatted}\n"
                    f"📊 Отставание: {gap_to_leader}\n"
                    f"🔄 Кругов: {laps}"
                )
            else:
                text = "❌ Данные заезда не найдены"

            buttons = [
                [("🗑 Удалить", f"askdel_{key}")],
                [("← Назад", "back_my")],
            ]
            await query.edit_message_text(text, reply_markup=_build_keyboard(buttons))
        else:
            await query.edit_message_text("Действие отменено")

    # ---------- ask delete confirmation ----------

    async def ask_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        key = query.data.split("_", 1)[1]
        d, rn, cn = key.split("|")

        # Проверяем новую таблицу с полной информацией
        comp_data = get_competitor_by_key(query.from_user.id, d, rn, cn)
        
        if comp_data:
            date, race_number, race_href, competitor_id, num, name, pos, laps, theor_lap, best_lap, binary_laps, theor_lap_formatted, display_name, gap_to_leader, lap_times_json = comp_data
            
            # Показываем имя только если оно не дублирует номер карта
            name_line = ""
            if name.strip() and not display_name.startswith("Карт #"):
                name_line = f"👤 Имя: {name}\n"
            
            confirm_text = (
                f"📅 Дата: {date}\n"
                f"🏁 Заезд: {race_number}\n"
                f"🏎️ Карт: {num}\n"
                f"{name_line}"
                f"🏆 Позиция: {pos}\n"
                f"⏱️ Лучший круг: {best_lap}\n"
                f"🔬 Теоретический круг: {theor_lap_formatted}\n"
                f"📊 Отставание: {gap_to_leader}\n"
                f"🔄 Кругов: {laps}\n\n"
                "❓ Точно удалить запись?"
            )
        else:
            confirm_text = (
                f"📅 Дата: {d}\n"
                f"🏁 Заезд: {rn}\n"
                f"🏎️ Карт: {cn}\n\n"
                "❓ Точно удалить запись?"
            )

        buttons = [[("🗑 Удалить", f"del_{key}"), ("Отмена", f"cancel_{key}")]]
        await query.edit_message_text(confirm_text, reply_markup=_build_keyboard(buttons))

    # ---------- back to list of my races ----------

    async def back_my_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Возвращаемся к списку сохранённых заездов пользователя."""
        query = update.callback_query
        await query.answer()

        # Получаем данные пользователя
        competitors = get_user_competitors(query.from_user.id)
        
        if competitors:
            # Показываем полную информацию
            rows = []
            for comp_data in competitors[:20]:
                date, race_number, race_href, competitor_id, num, name, pos, laps, theor_lap, best_lap, binary_laps, theor_lap_formatted, display_name, gap_to_leader, lap_times_json = comp_data
                
                race_part = race_number.strip()
                if not race_part.lower().startswith("заезд") and not race_part.startswith("З"):
                    race_part = f"Заезд {race_part}"
                
                text = f"{date} | {race_part} | {display_name} 🏆{pos} ⏱{best_lap}"
                key = f"{date}|{race_number}|{num}"
                rows.append([(text, f"view_{key}")])
            
            await query.edit_message_text("🏁 Ваши заезды:", reply_markup=_build_keyboard(rows))
        else:
            await query.edit_message_text("У вас ещё нет сохранённых заездов.")

    application.add_handler(CallbackQueryHandler(view_race_callback, pattern=r"^view_"))
    application.add_handler(CallbackQueryHandler(ask_delete_callback, pattern=r"^askdel_"))
    application.add_handler(CallbackQueryHandler(delete_race_callback, pattern=r"^del_"))
    application.add_handler(CallbackQueryHandler(cancel_my_callback, pattern=r"^cancel_"))
    application.add_handler(CallbackQueryHandler(back_my_callback, pattern=r"^back_my$"))

    # Обработчик ошибок
    application.add_error_handler(error_handler)

    # Запускаем бота
    print("🚀 Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main() 