import html
import logging
from datetime import date
from telegram import (
    Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup,
    MenuButtonWebApp, WebAppInfo,
    BotCommandScopeDefault, BotCommandScopeAllGroupChats, BotCommandScopeAllChatAdministrators,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    ConversationHandler, CallbackQueryHandler, MessageHandler, filters
)
from core.parsers.parsers import ArchiveParser, RaceParser, FullRaceInfoParser
from core.models.models import ParsingError
from core.database.db import (
    init_db, save_competitor, get_user_competitors, get_competitor_by_key,
    delete_competitor, get_all_competitors, get_best_competitors, get_best_competitors_today,
    upsert_user_profile,
)
import json

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

try:
    from core.config.config import BOT_TOKEN
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ Не установлен BOT_TOKEN!")
        print("Установи переменную окружения BOT_TOKEN или добавь в файл .env")
        exit(1)
except ImportError:
    print("❌ Не найден модуль core.config.config!")
    exit(1)

archive_parser = ArchiveParser()
race_parser = RaceParser()
full_race_parser = FullRaceInfoParser()

SELECT_USER, SELECT_DATE, SHOW_RACES, SHOW_CARTS = range(4)
PAGE_SIZE = 10


# ────────────────────────── Formatters ──────────────────────────

def _format_lap_times_table(lap_times_json: str) -> str:
    """Форматирует данные о кругах в виде таблицы (HTML)."""
    if not lap_times_json:
        return "📊 Данные о кругах недоступны"
    try:
        lap_times = json.loads(lap_times_json)
        if not lap_times:
            return "📊 Нет данных о кругах"
        table = "<pre>\n"
        table += f"{'#':^2}  {'Время':<8}  {'S1':<8}  {'S2':<8}  {'S3':<8}  {'S4':<8}\n"
        table += f"{'--':^2}  {'--------':<8}  {'--------':<8}  {'--------':<8}  {'--------':<8}  {'--------':<8}\n"
        for lap in lap_times:
            lap_num = lap['lap_number']
            lap_time = lap['lap_time'] or "-"
            sector1 = lap['sector1'] or "-"
            sector2 = lap['sector2'] or "-"
            sector3 = lap['sector3'] or "-"
            sector4 = lap['sector4'] or "-"
            if lap_num == 0:
                lap_label = "S"
                s1_display = "-"
            else:
                lap_label = f"{lap_num}"
                s1_display = sector1
            table += f"{lap_label:^2}  {lap_time:<8}  {s1_display:<8}  {sector2:<8}  {sector3:<8}  {sector4:<8}\n"
        table += "</pre>"
        return table
    except json.JSONDecodeError:
        return "❌ Ошибка при чтении данных о кругах"


def _format_competitor_info(comp_data: tuple) -> str:
    """Форматирует данные заезда в HTML-текст."""
    comp_date, race_number, race_href, competitor_id, num, name, pos, laps, theor_lap, best_lap, binary_laps, theor_lap_formatted, display_name, gap_to_leader, lap_times_json = comp_data
    name_line = (
        f"👤 Имя: {html.escape(name)}\n"
        if name.strip() and not display_name.startswith("Карт #")
        else ""
    )
    basic_info = (
        f"📅 Дата: {html.escape(comp_date)}\n"
        f"🏁 Заезд: {html.escape(race_number)}\n"
        f"🏎️ Карт: {html.escape(str(num))}\n"
        f"{name_line}"
        f"🏆 Позиция: {pos}\n"
        f"⏱️ Лучший круг: {html.escape(str(best_lap))}\n"
        f"🔬 Теоретический круг: {html.escape(str(theor_lap_formatted))}\n"
        f"📊 Отставание: {html.escape(str(gap_to_leader))}\n"
        f"🔄 Кругов: {laps}\n\n"
    )
    lap_table = _format_lap_times_table(lap_times_json)
    return basic_info + "📋 Данные по кругам:\n" + lap_table


async def _render_leaderboard(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int, competitors: list, title: str
) -> str:
    """Рендерит HTML-текст таблицы лидеров в стиле F1."""
    MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}
    POSITION_STYLE = {1: "🔴", 2: "🟡", 3: "⚪️"}

    text = f"🏎️  <b>{html.escape(title)}</b>\n"
    text += "─────────────────────\n"

    for i, comp in enumerate(competitors, 1):
        user_id, comp_date, race_number, num, name, display_name, theor_lap, theor_lap_formatted, best_lap, pos = comp

        show_name = None
        if name and name.strip() and not display_name.startswith("Карт #"):
            show_name = name.strip()
        else:
            try:
                chat_member = await context.bot.get_chat_member(chat_id, user_id)
                if chat_member.user.full_name:
                    show_name = chat_member.user.full_name
                elif chat_member.user.username:
                    show_name = f"@{chat_member.user.username}"
            except Exception:
                pass
        if not show_name:
            show_name = f"ID:{user_id}"

        medal = MEDALS.get(i, f"{i}.")
        dot = POSITION_STYLE.get(i, "⚫️")

        text += (
            f"{medal} <b>{html.escape(show_name)}</b>\n"
            f"   {dot} Карт <code>#{html.escape(str(num))}</code>  ⏱ <code>{html.escape(str(best_lap))}</code>\n"
        )

        if i < len(competitors):
            text += "\n"

    text += "─────────────────────\n"
    return text


# ────────────────────────── Helpers ──────────────────────────

def _build_keyboard(rows):
    """Утилита для быстрого создания InlineKeyboardMarkup."""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(text, callback_data=data) for text, data in row] for row in rows]
    )


async def _send_message_with_thread(
    context: ContextTypes.DEFAULT_TYPE, update: Update, text: str,
    reply_markup=None, parse_mode=None
):
    """Отправляет сообщение с учётом thread_id для каналов с темами."""
    chat_id = update.effective_chat.id
    message_thread_id = None
    if update.effective_message and hasattr(update.effective_message, 'message_thread_id'):
        message_thread_id = update.effective_message.message_thread_id
    return await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup,
        parse_mode=parse_mode,
        message_thread_id=message_thread_id,
    )


async def _edit_message_with_thread(query, text: str, reply_markup=None, parse_mode=None):
    """Редактирует сообщение."""
    return await query.edit_message_text(
        text=text,
        reply_markup=reply_markup,
        parse_mode=parse_mode,
    )


async def _send_user_keyboard(query, context):
    """Отрисовывает клавиатуру выбора пользователя."""
    users_ordered = context.user_data.get("user_options", [])
    keyboard = _build_keyboard(
        [[(u.full_name or u.username or str(u.id), f"user_{u.id}")] for u in users_ordered]
    )
    await query.edit_message_text("Кого записываем?", reply_markup=keyboard)


async def _delete_command_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пытается удалить сообщение с командой."""
    chat_id = update.effective_chat.id
    try:
        message_to_delete = update.message or update.edited_message
        if message_to_delete:
            chat_member = await context.bot.get_chat_member(chat_id, context.bot.id)
            if chat_member.can_delete_messages or chat_member.status in ['administrator', 'creator']:
                await message_to_delete.delete()
            else:
                try:
                    await message_to_delete.set_reaction("🗑️")
                except Exception:
                    pass
    except Exception as e:
        logger.warning(f"Не удалось удалить команду: {e}")


# ────────────────────────── /add conversation ──────────────────────────

async def add_race_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Точка входа в сценарий добавления заезда."""
    chat_id = update.effective_chat.id
    await _delete_command_message(update, context)

    try:
        admins = await context.bot.get_chat_administrators(chat_id)
        users = [adm.user for adm in admins]
    except Exception:
        users = []

    initiator = update.effective_user
    users_dict = {initiator.id: initiator}
    for u in users:
        if u.id != context.bot.id:
            users_dict.setdefault(u.id, u)

    users_ordered = list(users_dict.values())
    context.user_data["user_options"] = users_ordered

    # Сохраняем Telegram-имена всех пользователей
    for u in users_ordered:
        name = u.full_name or u.username
        if name:
            upsert_user_profile(u.id, name)

    keyboard = _build_keyboard(
        [[(u.full_name or u.username or str(u.id), f"user_{u.id}")] for u in users_ordered]
    )
    await _send_message_with_thread(context, update, "Кого записываем?", reply_markup=keyboard)
    return SELECT_USER


async def select_user_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = int(query.data.split("_", 1)[1])
    context.user_data["selected_user"] = user_id

    sel_user = next((u for u in context.user_data["user_options"] if u.id == user_id), None)
    context.user_data["selected_user_name"] = (
        sel_user.full_name or sel_user.username if sel_user else str(user_id)
    )

    try:
        day_races = await archive_parser.parse()
    except ParsingError as e:
        await _edit_message_with_thread(query, f"❌ Ошибка парсинга архива: {e}")
        return ConversationHandler.END

    today = date.today()
    today_dr = next((dr for dr in day_races if dr.date.date() == today), None)
    other_dates = [dr for dr in day_races if dr.date.date() != today]

    context.user_data["today_dr"] = today_dr
    context.user_data["today_exists"] = bool(today_dr)
    context.user_data["other_dates"] = other_dates

    await _send_date_page(query, context, today_exists=bool(today_dr), page=0)
    return SELECT_DATE


async def _send_date_page(query, context, today_exists: bool, page: int):
    dates = context.user_data["other_dates"]
    context.user_data["last_page"] = page
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    slice_dates = dates[start:end]

    rows = []
    if today_exists:
        rows.append([("Сегодня", "date_today")])

    for idx, dr in enumerate(slice_dates, start=start):
        rows.append([(dr.date.strftime("%d.%m.%Y"), f"date_{idx}")])

    nav = []
    if start > 0:
        nav.append(("« Назад", f"page_{page-1}"))
    if end < len(dates):
        nav.append(("Вперёд »", f"page_{page+1}"))
    if nav:
        rows.append(nav)

    rows.append([("← Назад к выбору пользователя", "back_users")])

    keyboard = _build_keyboard(rows)
    user_text = context.user_data.get("selected_user_name", "")
    text = (
        f"Пользователь: {user_text}\n"
        + ("Выберите дату заезда:" if slice_dates or today_exists else "Нет данных для отображения")
    )
    await _edit_message_with_thread(query, text, reply_markup=keyboard)


async def _send_races_page(query, context, page: int):
    """Отправляет постраничный список заездов."""
    races = context.user_data.get("current_races", [])
    context.user_data["races_page"] = page

    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    slice_races = races[start:end]

    rows = []
    for idx, race in enumerate(slice_races, start=start):
        rows.append([(f"Заезд {race.number}", f"race_{idx}")])

    nav = []
    if start > 0:
        nav.append(("« Назад", f"races_page_{page-1}"))
    if end < len(races):
        nav.append(("Вперёд »", f"races_page_{page+1}"))
    if nav:
        rows.append(nav)

    rows.append([("← Назад к выбору даты", "back_dates")])

    keyboard = _build_keyboard(rows)
    header = (
        f"Пользователь: {context.user_data.get('selected_user_name','')}\n"
        f"Дата: {context.user_data.get('selected_date_text','')}\n"
        f"Всего заездов: {len(races)}"
    )
    await _edit_message_with_thread(query, f"{header}\nВыберите заезд:", reply_markup=keyboard)


async def date_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    page = int(query.data.split("_", 1)[1])
    today_exists = context.user_data.get("today_exists", False)
    await _send_date_page(query, context, today_exists=today_exists, page=page)
    return SELECT_DATE


async def races_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    page = int(query.data.split("_", 2)[2])
    await _send_races_page(query, context, page=page)
    return SHOW_RACES


async def select_date_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    key = query.data.split("_", 1)[1]

    if key == "today":
        day_race = context.user_data.get("today_dr")
        if day_race is None:
            try:
                day_races = await archive_parser.parse()
                day_race = next((dr for dr in day_races if dr.date.date() == date.today()), None)
            except ParsingError as e:
                await _edit_message_with_thread(query, f"❌ Ошибка парсинга: {e}")
                return ConversationHandler.END
        date_text = "Сегодня"
        actual_date = date.today().strftime("%d.%m.%Y")
    else:
        idx = int(key)
        day_race = context.user_data["other_dates"][idx]
        date_text = day_race.date.strftime("%d.%m.%Y")
        actual_date = date_text

    if not day_race:
        await _edit_message_with_thread(query, "❌ Заезды не найдены")
        return ConversationHandler.END

    context.user_data["selected_date_text"] = date_text
    context.user_data["selected_date_actual"] = actual_date
    context.user_data["current_races"] = day_race.races

    await _send_races_page(query, context, page=0)
    return SHOW_RACES


async def back_to_dates_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    page = context.user_data.get("last_page", 0)
    today_exists = context.user_data.get("today_exists", False)
    await _send_date_page(query, context, today_exists=today_exists, page=page)
    return SELECT_DATE


async def back_to_users_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await _send_user_keyboard(query, context)
    return SELECT_USER


async def race_selected_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    idx = int(query.data.split("_", 1)[1])
    races_list = context.user_data.get("current_races", [])
    if idx >= len(races_list):
        await _edit_message_with_thread(query, "❌ Не удалось найти заезд")
        return ConversationHandler.END

    race = races_list[idx]

    try:
        carts, race_html = await race_parser.parse_with_html(race.href)
    except ParsingError as e:
        await _edit_message_with_thread(query, f"❌ Ошибка парсинга: {e}")
        return ConversationHandler.END

    context.user_data["current_carts"] = carts
    context.user_data["current_race_html"] = race_html
    context.user_data["selected_race_number"] = race.number
    context.user_data["selected_race_href"] = race.href

    cart_buttons = [[(f"Карт {c.number} ⏱ {c.best_lap}", f"cart_{i}")] for i, c in enumerate(carts)]
    cart_buttons.append([("← Назад к выбору заезда", "back_races")])

    keyboard = _build_keyboard(cart_buttons)
    header = (
        f"Пользователь: {context.user_data.get('selected_user_name','')}\n"
        f"Дата: {context.user_data.get('selected_date_text','')}\n"
        f"Заезд: {race.number}"
    )
    await _edit_message_with_thread(query, f"{header}\nВыберите карт:", reply_markup=keyboard)
    return SHOW_CARTS


async def cart_selected_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    idx = int(query.data.split("_", 1)[1])
    carts = context.user_data.get("current_carts", [])
    if idx >= len(carts):
        await _edit_message_with_thread(query, "❌ Не удалось найти карт")
        return ConversationHandler.END

    cart = carts[idx]
    race_href = context.user_data.get("selected_race_href", "")
    cached_html = context.user_data.get("current_race_html")

    try:
        await _edit_message_with_thread(query, "🔄 Получаю детальную информацию о заезде...")
        competitors = await full_race_parser.parse(race_href, carts, html=cached_html)

        selected_competitor = next((c for c in competitors if c.num == cart.number), None)
        if not selected_competitor:
            await _edit_message_with_thread(
                query, "❌ Не удалось найти детальную информацию о выбранном карте"
            )
            return ConversationHandler.END

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

        try:
            save_result = save_competitor(
                user_id=context.user_data.get("selected_user"),
                date=context.user_data.get("selected_date_actual", ""),
                race_number=context.user_data.get("selected_race_number", ""),
                race_href=race_href,
                competitor_data=competitor_data,
            )
            user_name_safe = html.escape(context.user_data.get('selected_user_name', ''))
            date_safe = html.escape(context.user_data.get('selected_date_text', ''))
            race_safe = html.escape(str(context.user_data.get('selected_race_number', '')))

            if save_result:
                resp = (
                    "✅ <b>ЗАЕЗД СОХРАНЁН</b> ✅\n\n"
                    f"👤 Пользователь: {user_name_safe}\n"
                    f"📅 Дата: {date_safe}\n"
                    f"🏁 Заезд: {race_safe}\n"
                    f"🏎️ Карт: {selected_competitor.num}\n"
                    f"⏱️ Лучший круг: {html.escape(str(selected_competitor.best_lap))}\n\n"
                    "🎉 Данные успешно сохранены с детальной информацией о кругах!"
                )
            else:
                resp = (
                    "⚠️ <b>ЗАЕЗД УЖЕ СУЩЕСТВУЕТ</b> ⚠️\n\n"
                    f"👤 Пользователь: {user_name_safe}\n"
                    f"📅 Дата: {date_safe}\n"
                    f"🏁 Заезд: {race_safe}\n"
                    f"🏎️ Карт: {selected_competitor.num}\n\n"
                    "ℹ️ Этот заезд уже сохранен в базе данных"
                )
            await _edit_message_with_thread(query, resp, parse_mode=ParseMode.HTML)

        except Exception as e:
            error_msg = html.escape(str(e)[:100])
            if "readonly database" in str(e).lower():
                user_error = "❌ <b>ОШИБКА ПРАВ ДОСТУПА</b>\n\n🔒 База данных доступна только для чтения."
            elif "no such table" in str(e).lower():
                user_error = "❌ <b>ОШИБКА БАЗЫ ДАННЫХ</b>\n\n🗃️ Таблица не найдена."
            elif "constraint" in str(e).lower():
                user_error = "❌ <b>ОШИБКА ДУБЛИРОВАНИЯ</b>\n\n📋 Такой заезд уже существует в базе."
            else:
                user_error = f"❌ <b>ОШИБКА СОХРАНЕНИЯ</b>\n\n🔧 {error_msg}"
            await _edit_message_with_thread(query, user_error, parse_mode=ParseMode.HTML)

    except ParsingError as e:
        await _edit_message_with_thread(
            query, f"❌ Ошибка получения детальных данных: {html.escape(str(e)[:100])}"
        )
        return ConversationHandler.END

    return ConversationHandler.END


async def back_to_races_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    page = context.user_data.get("races_page", 0)
    await _send_races_page(query, context, page=page)
    return SHOW_RACES


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отменяет текущий диалог /add."""
    context.user_data.clear()
    await _send_message_with_thread(context, update, "❌ Действие отменено.")
    return ConversationHandler.END


# ────────────────────────── /stats ──────────────────────────

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику пользователя."""
    chat_id = update.effective_chat.id
    await _delete_command_message(update, context)

    all_competitors = get_all_competitors()
    if not all_competitors:
        await _send_message_with_thread(context, update, "📊 Пока нет сохранённых заездов.")
        return

    user_ids = {comp[0] for comp in all_competitors if comp[0] != context.bot.id}

    try:
        admins = await context.bot.get_chat_administrators(chat_id)
        users_info = {adm.user.id: adm.user for adm in admins if adm.user.id != context.bot.id}
    except Exception:
        users_info = {}

    initiator = update.effective_user
    if initiator.id != context.bot.id:
        users_info[initiator.id] = initiator

    users_list = []
    for user_id in user_ids:
        if user_id in users_info:
            user = users_info[user_id]
            users_list.append(
                (user.full_name or user.username or f"ID:{user_id}", f"stats_user_{user_id}")
            )
        else:
            users_list.append((f"ID:{user_id}", f"stats_user_{user_id}"))

    if not users_list:
        await _send_message_with_thread(context, update, "📊 Не найдено пользователей с заездами.")
        return

    keyboard = _build_keyboard([users_list[i:i+1] for i in range(len(users_list))])
    await _send_message_with_thread(
        context, update,
        "👤 Выберите пользователя для просмотра статистики:",
        reply_markup=keyboard,
    )


async def stats_user_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data_parts = query.data.split("_")
    user_id = int(data_parts[2])
    page = int(data_parts[3]) if len(data_parts) > 3 else 0

    competitors = get_user_competitors(user_id)

    if not competitors:
        await _edit_message_with_thread(query, f"📊 У пользователя ID:{user_id} нет сохранённых заездов.")
        return

    try:
        chat_member = await context.bot.get_chat_member(query.message.chat_id, user_id)
        user_name = chat_member.user.full_name or chat_member.user.username or f"ID:{user_id}"
    except Exception:
        user_name = f"ID:{user_id}"

    user_name_safe = html.escape(user_name.upper())
    text = f"📊 <b>СТАТИСТИКА {user_name_safe}</b> 📊\n\n"
    text += f"📈 Всего заездов: {len(competitors)}\n\n"
    text += "💡 Выберите заезд для детального просмотра:"

    start_idx = page * 10
    end_idx = start_idx + 10
    page_competitors = competitors[start_idx:end_idx]

    rows = []
    for comp_data in page_competitors:
        comp_date, race_number, race_href, competitor_id, num, name, pos, laps, theor_lap, best_lap, binary_laps, theor_lap_formatted, display_name, gap_to_leader, lap_times_json = comp_data
        race_part = race_number.strip()
        if not race_part.lower().startswith("заезд") and not race_part.startswith("З"):
            race_part = f"Заезд {race_part}"
        button_text = f"{comp_date[:5]} {race_part[:12]} #{num} | {pos} место | {best_lap}"
        key = f"{comp_date}|{race_number}|{num}|{user_id}"
        rows.append([(button_text, f"view_stats_{key}")])

    nav_buttons = []
    if page > 0:
        nav_buttons.append(("◀️ Назад", f"stats_user_{user_id}_{page-1}"))
    if end_idx < len(competitors):
        nav_buttons.append(("Вперёд ▶️", f"stats_user_{user_id}_{page+1}"))
    if nav_buttons:
        rows.append(nav_buttons)

    rows.append([("← Назад к выбору пользователя", "stats_back_users")])

    keyboard = _build_keyboard(rows)
    await _edit_message_with_thread(query, text, reply_markup=keyboard, parse_mode=ParseMode.HTML)


async def view_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    key = query.data.split("_", 2)[2]
    d, rn, cn, user_id_str = key.split("|")
    user_id = int(user_id_str)

    comp_data = get_competitor_by_key(user_id, d, rn, cn)
    text = _format_competitor_info(comp_data) if comp_data else "❌ Данные заезда не найдены"

    buttons = [
        [("🗑 Удалить", f"askdel_stats_{d}|{rn}|{cn}|{user_id}")],
        [("← Назад к статистике", f"stats_user_{user_id}")],
    ]
    await _edit_message_with_thread(
        query, text, reply_markup=_build_keyboard(buttons), parse_mode=ParseMode.HTML
    )


async def ask_delete_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    key = query.data.split("_", 2)[2]
    d, rn, cn, user_id_str = key.split("|")
    user_id = int(user_id_str)

    comp_data = get_competitor_by_key(user_id, d, rn, cn)
    if comp_data:
        comp_date, race_number, race_href, competitor_id, num, name, pos, laps, theor_lap, best_lap, binary_laps, theor_lap_formatted, display_name, gap_to_leader, lap_times_json = comp_data
        name_line = (
            f"👤 Имя: {html.escape(name)}\n"
            if name.strip() and not display_name.startswith("Карт #")
            else ""
        )
        confirm_text = (
            f"📅 Дата: {html.escape(comp_date)}\n"
            f"🏁 Заезд: {html.escape(race_number)}\n"
            f"🏎️ Карт: {html.escape(str(num))}\n"
            f"{name_line}"
            f"🏆 Позиция: {pos}\n"
            f"⏱️ Лучший круг: {html.escape(str(best_lap))}\n\n"
            "❓ Точно удалить запись?"
        )
    else:
        confirm_text = (
            f"📅 Дата: {html.escape(d)}\n"
            f"🏁 Заезд: {html.escape(rn)}\n"
            f"🏎️ Карт: {html.escape(cn)}\n\n"
            "❓ Точно удалить запись?"
        )

    buttons = [[("🗑 Удалить", f"del_stats_{key}"), ("Отмена", f"cancel_stats_{key}")]]
    await _edit_message_with_thread(
        query, confirm_text, reply_markup=_build_keyboard(buttons), parse_mode=ParseMode.HTML
    )


async def delete_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    key = query.data.split("_", 2)[2]
    d, rn, cn, user_id_str = key.split("|")
    user_id = int(user_id_str)

    try:
        ok = delete_competitor(user_id, d, rn, cn)
        if ok:
            await _edit_message_with_thread(
                query,
                "✅ <b>ЗАПИСЬ УДАЛЕНА</b>\n\n🗑️ Заезд успешно удален из базы данных",
                parse_mode=ParseMode.HTML,
            )
        else:
            await _edit_message_with_thread(
                query,
                "⚠️ <b>ЗАПИСЬ НЕ НАЙДЕНА</b>\n\n🔍 Возможно, запись уже была удалена ранее",
                parse_mode=ParseMode.HTML,
            )
    except Exception as e:
        if "readonly database" in str(e).lower():
            user_error = "❌ <b>ОШИБКА ПРАВ ДОСТУПА</b>\n\n🔒 База данных доступна только для чтения."
        else:
            user_error = f"❌ <b>ОШИБКА УДАЛЕНИЯ</b>\n\n🔧 {html.escape(str(e)[:100])}"
        await _edit_message_with_thread(query, user_error, parse_mode=ParseMode.HTML)


async def cancel_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена удаления — возвращаемся к просмотру заезда."""
    query = update.callback_query
    await query.answer()

    key = query.data.split("_", 2)[2]
    d, rn, cn, user_id_str = key.split("|")
    user_id = int(user_id_str)

    comp_data = get_competitor_by_key(user_id, d, rn, cn)
    text = _format_competitor_info(comp_data) if comp_data else "❌ Данные заезда не найдены"

    buttons = [
        [("🗑 Удалить", f"askdel_stats_{key}")],
        [("← Назад к статистике", f"stats_user_{user_id}")],
    ]
    await _edit_message_with_thread(
        query, text, reply_markup=_build_keyboard(buttons), parse_mode=ParseMode.HTML
    )


async def stats_back_to_users_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возврат к выбору пользователя в /stats."""
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    all_competitors = get_all_competitors()

    if not all_competitors:
        await _edit_message_with_thread(query, "📊 Пока нет сохранённых заездов.")
        return

    user_ids = {comp[0] for comp in all_competitors if comp[0] != context.bot.id}

    try:
        admins = await context.bot.get_chat_administrators(chat_id)
        users_info = {adm.user.id: adm.user for adm in admins if adm.user.id != context.bot.id}
    except Exception:
        users_info = {}

    caller = query.from_user
    if caller and caller.id != context.bot.id:
        users_info[caller.id] = caller

    users_list = []
    for user_id in user_ids:
        if user_id in users_info:
            user = users_info[user_id]
            users_list.append(
                (user.full_name or user.username or f"ID:{user_id}", f"stats_user_{user_id}")
            )
        else:
            users_list.append((f"ID:{user_id}", f"stats_user_{user_id}"))

    keyboard = _build_keyboard([users_list[i:i+1] for i in range(len(users_list))])
    await _edit_message_with_thread(
        query, "👤 Выберите пользователя для просмотра статистики:", reply_markup=keyboard
    )


# ────────────────────────── /best, /best_today ──────────────────────────

async def best_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать рейтинг лучших гонщиков."""
    try:
        await update.message.delete()
    except Exception:
        pass

    competitors = get_best_competitors(20)
    if not competitors:
        await _send_message_with_thread(context, update, "🏆 Пока нет данных для рейтинга.")
        return

    chat_id = update.effective_chat.id
    text = await _render_leaderboard(context, chat_id, competitors, "РЕЙТИНГ ЛУЧШИХ ГОНЩИКОВ")
    await _send_message_with_thread(context, update, text, parse_mode=ParseMode.HTML)


async def best_today_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать рейтинг лучших гонщиков за сегодня."""
    try:
        await update.message.delete()
    except Exception:
        pass

    today = date.today().strftime("%d.%m.%Y")
    competitors = get_best_competitors_today(today, 20)
    if not competitors:
        await _send_message_with_thread(context, update, "🏆 Сегодня заездов не было.")
        return

    chat_id = update.effective_chat.id
    text = await _render_leaderboard(context, chat_id, competitors, f"РЕЙТИНГ ЗА СЕГОДНЯ ({today})")
    await _send_message_with_thread(context, update, text, parse_mode=ParseMode.HTML)


# ────────────────────────── /app ──────────────────────────

async def app_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет сообщение с инлайн-кнопкой для открытия Mini App."""
    await _delete_command_message(update, context)

    bot_username = context.bot.username
    # Используем t.me deeplink — работает в каналах, группах и личных чатах.
    # Для этого в BotFather нужно зарегистрировать Mini App с shortname "app":
    #   /newapp → выбрать бота → shortname: app → URL: https://carting.ltheresi.com
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "🏎️ Открыть Mini App",
            url=f"https://t.me/{bot_username}/app",
        )
    ]])
    await _send_message_with_thread(
        context, update,
        "🏁 Нажми кнопку, чтобы открыть приложение карт-трекера:",
        reply_markup=keyboard,
    )


# ────────────────────────── Error handler ──────────────────────────

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    if update and hasattr(update, 'effective_message') and update.effective_message:
        try:
            error_msg = str(context.error)
            if "readonly database" in error_msg.lower():
                user_error = "❌ <b>ПРОБЛЕМА С БАЗОЙ ДАННЫХ</b>\n\n🔒 База данных недоступна для записи."
            elif "network" in error_msg.lower() or "connection" in error_msg.lower():
                user_error = "❌ <b>ПРОБЛЕМА С СЕТЬЮ</b>\n\n🌐 Нет связи с сервером карт."
            elif "parsing" in error_msg.lower():
                user_error = "❌ <b>ОШИБКА ОБРАБОТКИ ДАННЫХ</b>\n\n📄 Не удалось обработать данные с сайта."
            elif "timeout" in error_msg.lower():
                user_error = "❌ <b>ПРЕВЫШЕНО ВРЕМЯ ОЖИДАНИЯ</b>\n\n⏱️ Сервер слишком долго отвечает."
            else:
                user_error = "❌ <b>ТЕХНИЧЕСКАЯ ОШИБКА</b>\n\n🔧 Произошла непредвиденная ошибка."
            await update.effective_message.reply_text(user_error, parse_mode=ParseMode.HTML)
        except Exception:
            logger.error("Failed to send error message to user")


# ────────────────────────── Setup ──────────────────────────

async def _set_default_commands(app: Application) -> None:
    """Устанавливаем команды бота и кнопку Menu для WebApp."""
    commands = [
        BotCommand("add", "Добавить заезд"),
        BotCommand("stats", "Статистика пользователя"),
        BotCommand("best", "Рейтинг гонщиков"),
        BotCommand("best_today", "Рейтинг за сегодня"),
        BotCommand("app", "Открыть Mini App"),
    ]
    # Устанавливаем команды для всех контекстов
    await app.bot.set_my_commands(commands, scope=BotCommandScopeDefault())
    await app.bot.set_my_commands(commands, scope=BotCommandScopeAllGroupChats())
    await app.bot.set_my_commands(commands, scope=BotCommandScopeAllChatAdministrators())
    await app.bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(
            text="Mini App",
            web_app=WebAppInfo(url="https://carting.ltheresi.com"),
        )
    )


def main() -> None:
    """Главная функция для запуска бота."""
    application = Application.builder().token(BOT_TOKEN).build()
    init_db()
    application.post_init = _set_default_commands

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("add", add_race_command),
            MessageHandler(filters.Regex(r'^/add@\w+'), add_race_command),
        ],
        states={
            SELECT_USER: [
                CallbackQueryHandler(select_user_callback, pattern=r"^user_\d+$"),
            ],
            SELECT_DATE: [
                CallbackQueryHandler(date_page_callback, pattern=r"^page_\d+$"),
                CallbackQueryHandler(select_date_callback, pattern=r"^date_.*$"),
                CallbackQueryHandler(back_to_users_callback, pattern=r"^back_users$"),
            ],
            SHOW_RACES: [
                CallbackQueryHandler(back_to_dates_callback, pattern=r"^back_dates$"),
                CallbackQueryHandler(races_page_callback, pattern=r"^races_page_\d+$"),
                CallbackQueryHandler(race_selected_callback, pattern=r"^race_\d+$"),
            ],
            SHOW_CARTS: [
                CallbackQueryHandler(back_to_races_callback, pattern=r"^back_races$"),
                CallbackQueryHandler(cart_selected_callback, pattern=r"^cart_\d+$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_command),
        ],
    )
    application.add_handler(conv)

    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(MessageHandler(filters.Regex(r'^/stats@\w+'), stats_command))
    application.add_handler(CallbackQueryHandler(stats_user_callback, pattern=r"^stats_user_\d+(_\d+)?$"))

    application.add_handler(CommandHandler("best", best_command))
    application.add_handler(MessageHandler(filters.Regex(r'^/best@\w+'), best_command))
    application.add_handler(CommandHandler("best_today", best_today_command))
    application.add_handler(MessageHandler(filters.Regex(r'^/best_today@\w+'), best_today_command))

    application.add_handler(CommandHandler("app", app_command))
    application.add_handler(MessageHandler(filters.Regex(r'^/app@\w+'), app_command))

    application.add_handler(CallbackQueryHandler(view_stats_callback, pattern=r"^view_stats_"))
    application.add_handler(CallbackQueryHandler(ask_delete_stats_callback, pattern=r"^askdel_stats_"))
    application.add_handler(CallbackQueryHandler(delete_stats_callback, pattern=r"^del_stats_"))
    application.add_handler(CallbackQueryHandler(cancel_stats_callback, pattern=r"^cancel_stats_"))
    application.add_handler(CallbackQueryHandler(stats_back_to_users_callback, pattern=r"^stats_back_users$"))

    application.add_error_handler(error_handler)

    print("🚀 Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
