import asyncio
import logging
from vk_api import VkApi
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from config import VK_TOKEN
from database import db
from handlers import handler, HELP_TEXT
from dice_logic import parse_dice_command, special_roll, normalize_command
from utils import reply_with_mention

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def process_message(vk, msg):
    text = msg.get("text", "").strip()
    if not text:
        return
    user_id = msg["from_id"]
    peer_id = msg["peer_id"]
    if user_id < 0:
        return

    # Обновляем активность (не бросок)
    await db.update_activity(peer_id, user_id, is_roll=False)

    # Спецобработка команд с параметрами: /топ N и /имя [значение]
    lower = text.lower()
    if lower.startswith('/топ') or lower.startswith('/к топ'):
        parts = text.split()
        days = 0
        if len(parts) > 1 and parts[1].isdigit():
            days = int(parts[1])
            if days > 365:
                days = 365
        top = await db.get_top(peer_id, days)
        if not top:
            await reply_with_mention(vk, peer_id, user_id, "Нет данных для статистики.")
            return
        period = f"за последние {days} дней" if days > 0 else "за всё время"
        lines = [f"📊 Топ участников {period}:"]
        lines.append("По сообщениям:")
        sorted_by_msg = sorted(top, key=lambda x: x[1], reverse=True)
        for i, (name, msg_cnt, _) in enumerate(sorted_by_msg[:10], 1):
            lines.append(f"{i}. {name} — {msg_cnt} сообщ.")
        lines.append("По броскам кубов:")
        sorted_by_roll = sorted(top, key=lambda x: x[2], reverse=True)
        for i, (name, _, roll_cnt) in enumerate(sorted_by_roll[:10], 1):
            lines.append(f"{i}. {name} — {roll_cnt} бросков")
        await reply_with_mention(vk, peer_id, user_id, "\n".join(lines))
        return

    if lower.startswith('/имя') or lower.startswith('/кимя'):
        prefix_len = 5 if lower.startswith('/кимя') else 4
        rest = text[prefix_len:].strip()
        if not rest:
            name = await db.get_name(peer_id, user_id)
            if name:
                await reply_with_mention(vk, peer_id, user_id, f"👤 Ваше имя в этой беседе: {name}")
            else:
                await reply_with_mention(vk, peer_id, user_id, "👤 У вас ещё нет имени. Установите: /имя ВашеИмя")
        else:
            if len(rest) > 32:
                await reply_with_mention(vk, peer_id, user_id, "❌ Имя слишком длинное (максимум 32 символа)")
            else:
                await db.set_name(peer_id, user_id, rest)
                await reply_with_mention(vk, peer_id, user_id, f"✅ Ваше имя в этой беседе установлено: {rest}")
        return

    # Проверка других зарегистрированных команд (без параметров)
    cmd_result = await handler.dispatch(text, vk, peer_id, user_id)
    if cmd_result:
        await reply_with_mention(vk, peer_id, user_id, cmd_result)
        return

    # Обработка бросков (возможно несколько команд в одном сообщении)
    tokens = text.split()
    results = []
    nickname = await db.get_name(peer_id, user_id)
    prefix = f"{nickname}: " if nickname else ""

    for token in tokens:
        if not token.startswith('/'):
            continue
        norm = normalize_command(token)
        special_res, ok = special_roll(norm)
        if ok:
            await db.update_activity(peer_id, user_id, is_roll=True)
            if prefix:
                special_res = special_res.replace('🎲', f'🎲 {prefix}').replace('⚔️', f'⚔️ {prefix}').replace('🛡️', f'🛡️ {prefix}').replace('🔁', f'🔁 {prefix}')
            results.append(special_res)
            continue
        dice_res, ok = parse_dice_command(norm)
        if ok:
            await db.update_activity(peer_id, user_id, is_roll=True)
            if prefix:
                dice_res = dice_res.replace('🎲', f'🎲 {prefix}')
            results.append(dice_res)
            continue
        results.append(f"❌ Неизвестная команда: `{token}`")

    if results:
        final_text = "\n".join(results)
        await reply_with_mention(vk, peer_id, user_id, final_text)

async def main():
    vk_session = VkApi(token=VK_TOKEN)
    vk = vk_session.get_api()
    # Получаем group_id
    try:
        group_info = vk.groups.getById()
        group_id = group_info[0]['id']
        logger.info(f"Group ID: {group_id}")
    except Exception as e:
        logger.error(f"Can't get group_id: {e}")
        return
    longpoll = VkBotLongPoll(vk_session, group_id=group_id)
    logger.info("Бот запущен")
    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_NEW and event.message and event.message.get("text"):
            asyncio.create_task(process_message(vk, event.message))

if __name__ == "__main__":
    asyncio.run(main())
