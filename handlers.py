import asyncio
from typing import Dict, Callable, Awaitable, Optional
from database import db
from dice_logic import parse_dice_command, special_roll, normalize_command

HELP_TEXT = """📚 Доступные команды:

Стандартные броски:
/d или /к — бросок d20
/dX или /кX — бросок кубика с любым числом граней X (2–100)
/dX+N или /кX+N — с модификатором
/NdX или /NкX — бросок нескольких кубиков (X 2–100, N 1–100)
/NdX+N или /NкX+N — с модификатором

Преимущество / Помеха (только d20):
/d20 adv, /d20 advantage, /к20 adv — с преимуществом
/d20 dis, /d20 disadvantage, /к20 dis — с помехой
/d adv, /к adv — тоже работает
Модификатор: /d20+2 adv

Специальные команды:
/roll — случайное число 0–100
/attack — куб атаки (промах/попадание/крит)
/defense — куб защиты (провал/успех/крит)
/double — куб удвоения (пусто/×2)

Профиль:
/имя НовоеИмя — задать своё имя
/имя — показать своё имя
/имена — показать список всех имён в беседе

Статистика:
/топ [дни] — топ участников по сообщениям и броскам (дни до 365)

Администрирование:
/вышедшие кик — удалить из БД вышедших (нужны права бота)

Прочее:
/помощь — это сообщение
"""

class CommandHandler:
    def __init__(self):
        self._commands: Dict[str, Callable] = {}

    def register(self, *aliases: str):
        def decorator(func: Callable[[dict, int, int], Awaitable[Optional[str]]]):
            for alias in aliases:
                self._commands[alias.lower()] = func
            return func
        return decorator

    async def dispatch(self, text: str, vk, peer_id: int, user_id: int) -> Optional[str]:
        # Сначала проверим команды без префикса
        lower = text.lower().split()[0] if text else ""
        if lower in self._commands:
            return await self._commands[lower](vk, peer_id, user_id)
        return None

handler = CommandHandler()

# ---------- Регистрация команд ----------
@handler.register("/помощь", "/кпомощь", "/help", "/кhelp")
async def cmd_help(vk, peer_id, user_id):
    return HELP_TEXT

@handler.register("/имена", "/кимена")
async def cmd_names(vk, peer_id, user_id):
    all_names = await db.get_all_names(peer_id)
    if not all_names:
        return "В этой беседе пока нет ни одного установленного имени."
    lines = ["Список имён в этой беседе:"]
    for uid, name in all_names:
        lines.append(f"{name} (id{uid})")
    return "\n".join(lines)

@handler.register("/топ", "/к топ")
async def cmd_top(vk, peer_id, user_id):
    # Здесь text может быть с параметром, поэтому обработаем отдельно
    return None  # обработаем позже в основном цикле

@handler.register("/вышедшие кик", "/к вышедшие кик")
async def cmd_kick_left(vk, peer_id, user_id):
    if peer_id <= 2000000000:
        return "Эта команда работает только в беседах."
    members = await get_conversation_members(vk, peer_id)
    if not members:
        return "Не удалось получить список участников. Убедитесь, что бот администратор беседы."
    left = await db.remove_left_users(peer_id, members)
    if left:
        return f"✅ Удалены данные о вышедших участниках: {len(left)} человек."
    else:
        return "Нет вышедших участников, данные в порядке."

@handler.register("/имя", "/кимя")
async def cmd_name(vk, peer_id, user_id):
    # Параметры обработаем отдельно
    return None

# Вспомогательная функция для получения участников (вынесена, чтобы не дублировать)
async def get_conversation_members(vk, peer_id):
    try:
        members = vk.method("messages.getConversationMembers", {"peer_id": peer_id})
        return {member["member_id"] for member in members["items"]}
    except Exception as e:
        print(f"Ошибка получения участников беседы {peer_id}: {e}")
        return set()
