import re
import random

def parse_dice_command(cmd: str):
    cmd = cmd.strip().lower()
    if not cmd.startswith('/d'):
        return None, False
    cmd = cmd[1:]

    adv_match = re.match(r'^d20([+-]\d+)?\s+(adv|advantage|dis|disadvantage)$', cmd)
    if adv_match:
        mod_str = adv_match.group(1)
        modifier = int(mod_str) if mod_str else 0
        adv_type = adv_match.group(2)
        is_adv = adv_type.startswith('adv')
        rolls = [random.randint(1, 20), random.randint(1, 20)]
        chosen = max(rolls) if is_adv else min(rolls)
        total = chosen + modifier
        desc = "преимуществом" if is_adv else "помехой"
        roll_str = f"{rolls[0]}, {rolls[1]}"
        if modifier == 0:
            return f"🎲 Бросок d20 с {desc}: [{roll_str}] → выбран {chosen} → {total}", True
        else:
            return f"🎲 Бросок d20 с {desc}: [{roll_str}] → выбран {chosen} {modifier:+d} = {total}", True

    empty_match = re.match(r'^d([+-]\d+)?$', cmd)
    if empty_match:
        mod_str = empty_match.group(1)
        modifier = int(mod_str) if mod_str else 0
        roll = random.randint(1, 20)
        total = roll + modifier
        if modifier == 0:
            return f"🎲 Результат броска d20: {roll}", True
        else:
            return f"🎲 Результат броска d20: {roll} {modifier:+d} = {total}", True

    single_match = re.match(r'^d(\d+)([+-]\d+)?$', cmd)
    if single_match:
        sides = int(single_match.group(1))
        mod_str = single_match.group(2)
        modifier = int(mod_str) if mod_str else 0
        if sides < 2:
            return "❌ Куб должен иметь минимум 2 грани", False
        if sides > 100:
            return "❌ Слишком много граней (максимум 100)", False
        roll = random.randint(1, sides)
        total = roll + modifier
        if modifier == 0:
            return f"🎲 Результат броска d{sides}: {roll}", True
        else:
            return f"🎲 Результат броска d{sides}: {roll} {modifier:+d} = {total}", True

    multi_match = re.match(r'^(\d+)d(\d+)([+-]\d+)?$', cmd)
    if multi_match:
        count = int(multi_match.group(1))
        sides = int(multi_match.group(2))
        mod_str = multi_match.group(3)
        modifier = int(mod_str) if mod_str else 0
        if sides < 2:
            return "❌ Куб должен иметь минимум 2 грани", False
        if sides > 100:
            return "❌ Слишком много граней (максимум 100)", False
        if count < 1:
            return "❌ Количество кубиков должно быть не менее 1", False
        if count > 100:
            return "❌ Слишком много кубиков (максимум 100)", False
        rolls = [random.randint(1, sides) for _ in range(count)]
        total = sum(rolls) + modifier
        roll_str = ", ".join(map(str, rolls))
        if modifier == 0:
            return f"🎲 Результат броска {count}d{sides}: [{roll_str}] = {total}", True
        else:
            return f"🎲 Результат броска {count}d{sides}: [{roll_str}] = {sum(rolls)} {modifier:+d} = {total}", True

    return None, False

def special_roll(cmd: str):
    cmd = cmd.lower()
    if cmd == '/roll':
        num = random.randint(0, 100)
        return f"🎲 Случайное число (0–100): {num}", True
    if cmd == '/attack':
        roll = random.randint(1, 20)
        if roll == 1:
            return f"⚔️ Куб атаки: {roll} — Промах (крит. промах)", True
        if roll == 20:
            return f"⚔️ Куб атаки: {roll} — Крит", True
        return f"⚔️ Куб атаки: {roll} — Попадание", True
    if cmd == '/defense':
        roll = random.randint(1, 20)
        if roll == 1:
            return f"🛡️ Куб защиты: {roll} — Провал (крит. провал)", True
        if roll == 20:
            return f"🛡️ Куб защиты: {roll} — Крит (крит. успех)", True
        return f"🛡️ Куб защиты: {roll} — Успех" if roll >= 10 else f"🛡️ Куб защиты: {roll} — Провал", True
    if cmd == '/double':
        roll = random.randint(1, 6)
        if roll <= 3:
            return f"🔁 Куб удвоения: {roll} → Пусто", True
        else:
            return f"🔁 Куб удвоения: {roll} → ×2", True
    return None, False

def normalize_command(raw: str) -> str:
    lower = raw.lower()
    if lower == '/кпре':
        return '/d20 adv'
    if lower == '/кпом':
        return '/d20 dis'
    if lower.startswith('/к'):
        rest = raw[2:]
        return '/d' + rest
    return raw
