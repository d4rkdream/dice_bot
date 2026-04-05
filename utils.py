async def reply_with_mention(vk, peer_id, user_id, text):
    from database import db
    nickname = await db.get_name(peer_id, user_id)
    if nickname:
        mention = f"[id{user_id}|{nickname}]"
        full_text = f"{mention}, {text}"
    else:
        full_text = text
    vk.method("messages.send", {"peer_id": peer_id, "message": full_text, "random_id": 0})
