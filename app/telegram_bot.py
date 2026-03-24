"""
Telegram Bot – Webhook mode (HuggingFace Spaces compatible).
HF blocks outbound connections, so we use webhook instead of polling.

To activate, open this URL once in your browser:
https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://YOUR_SPACE.hf.space/api/telegram/webhook
"""
import asyncio
import logging
import os

import httpx
from fastapi import APIRouter, Request

log = logging.getLogger("telegram_bot")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
SPACE_URL = os.getenv("SPACE_URL", "")
API = f"https://api.telegram.org/bot{TOKEN}"

router = APIRouter(prefix="/api/telegram", tags=["telegram"])
_state: dict = {}


# ── Helpers ────────────────────────────────────────────────────────────────

async def _post(method: str, **kwargs):
    if not TOKEN:
        return None
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(f"{API}/{method}", json=kwargs)
            return r.json()
    except Exception as e:
        log.warning(f"Telegram send failed: {e}")
        return None


async def send(chat_id, text: str, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    await _post("sendMessage", **payload)


async def send_menu(chat_id):
    await send(chat_id, "اختر من القائمة:", reply_markup={
        "keyboard": [
            ["🎬 فيديو جديد", "📊 الإحصائيات"],
            ["📹 الفيديوهات", "⏳ قائمة الانتظار"],
            ["� القنوات",    "�🚨 الأخطاء"],
        ],
        "resize_keyboard": True,
    })


async def _api(path: str, method="GET", json=None):
    port = os.getenv("PORT", "7860")
    async with httpx.AsyncClient(timeout=30) as client:
        if method == "POST":
            r = await client.post(f"http://localhost:{port}{path}", json=json,
                                  headers={"Content-Type": "application/json"})
        else:
            r = await client.get(f"http://localhost:{port}{path}")
        r.raise_for_status()
        return r.json()


# ── Webhook endpoints ──────────────────────────────────────────────────────

@router.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    if "message" in data:
        asyncio.create_task(handle_message(data["message"]))
    return {"ok": True}


@router.get("/set-webhook")
async def set_webhook():
    return {
        "instruction": "Open this URL in your browser to activate the bot:",
        "url": f"https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook?url={SPACE_URL}/api/telegram/webhook",
    }


# ── Handlers ───────────────────────────────────────────────────────────────

async def handle_start(chat_id):
    await send(chat_id,
        "👋 *مرحباً في Video Automation Bot*\n\n"
        "تحكم كامل في pipeline إنشاء الفيديوهات.")
    await send_menu(chat_id)


async def handle_stats(chat_id):
    try:
        s = await _api("/api/dashboard/stats")
        await send(chat_id,
            f"📊 *الإحصائيات*\n\n"
            f"📹 الإجمالي: *{s['total_videos']}*\n"
            f"✅ مكتملة: *{s['completed']}*\n"
            f"⚙️ قيد التنفيذ: *{s['in_progress']}*\n"
            f"❌ فشلت: *{s['failed']}*\n"
            f"⏳ في الانتظار: *{s['queue_size']}*\n"
            f"🚨 أخطاء: *{s['total_errors']}*")
    except Exception as e:
        await send(chat_id, f"❌ خطأ: {e}")


async def handle_queue(chat_id):
    try:
        s = await _api("/api/dashboard/stats")
        await send(chat_id,
            f"⏳ *قائمة الانتظار*\n\n"
            f"منتظرة: *{s['queue_size']}*\n"
            f"قيد التنفيذ: *{s['in_progress']}*")
    except Exception as e:
        await send(chat_id, f"❌ خطأ: {e}")


async def handle_videos(chat_id):
    try:
        videos = await _api("/api/videos")
        if not videos:
            await send(chat_id, "📭 لا توجد فيديوهات بعد.")
            return
        status_emoji = {"completed": "✅", "failed": "❌", "pending": "⏳",
                        "generating_script": "📝", "generating_chunks": "🎨",
                        "compiling": "🎞️", "script_ready": "📄"}
        lines = ["📹 *آخر الفيديوهات:*\n"]
        for v in videos[:10]:
            emoji = status_emoji.get(v["status"], "🔄")
            lines.append(
                f"{emoji} `{v['video_id'][-8:]}` {v['video_title'][:30]}\n"
                f"    _{v['status']}_ | {(v['created_at'] or '')[:10]}")
        await send(chat_id, "\n".join(lines))
    except Exception as e:
        await send(chat_id, f"❌ خطأ: {e}")


async def handle_video_detail(chat_id, video_id: str):
    try:
        v = await _api(f"/api/videos/{video_id}")
        status_emoji = {"completed": "✅", "failed": "❌", "pending": "⏳",
                        "generating_script": "📝", "generating_chunks": "🎨", "compiling": "🎞️"}
        emoji = status_emoji.get(v["status"], "�")
        msg = (f"{emoji} *{v['video_title']}*\n\n"
               f"🆔 `{v['video_id']}`\n"
               f"� الحالة: *{v['status']}*\n"
               f"🎬 المشاهد: {v['scene_count'] or '-'}\n"
               f"⏱ المدة: {v['total_duration'] or '-'}s\n"
               f"📅 أُنشئ: {(v['created_at'] or '')[:16]}\n")
        if v.get("final_video_url"):
            msg += f"🔗 [مشاهدة الفيديو]({v['final_video_url']})\n"
        if v.get("error_message"):
            msg += f"\n⚠️ الخطأ:\n`{v['error_message'][:200]}`"
        await send(chat_id, msg)
    except Exception as e:
        await send(chat_id, f"❌ لم يُعثر على الفيديو: {e}")


async def handle_logs(chat_id, video_id: str):
    try:
        logs = await _api(f"/api/videos/{video_id}/logs")
        if not logs:
            await send(chat_id, "� لا توجد سجلات.")
            return
        lines = [f"📋 *سجلات* `{video_id[-8:]}`\n"]
        for l in logs[-15:]:
            icon = "🔴" if l["level"] == "error" else "🔵"
            lines.append(f"{icon} `{l['timestamp'][11:19]}` [{l['agent']}] {l['message'][:80]}")
        await send(chat_id, "\n".join(lines))
    except Exception as e:
        await send(chat_id, f"❌ خطأ: {e}")


async def handle_channels(chat_id):
    try:
        channels = await _api("/api/channels")
        if not channels:
            await send(chat_id, "📭 لا توجد قنوات.")
            return
        lines = ["📡 *القنوات:*\n"]
        for c in channels:
            lines.append(f"• *{c['name']}* (`{c['channel_id']}`)\n"
                         f"  المجال: {c['niche']} | المدة: {c['target_duration']}s")
        await send(chat_id, "\n".join(lines))
    except Exception as e:
        await send(chat_id, f"❌ خطأ: {e}")


async def handle_errors(chat_id):
    try:
        errors = await _api("/api/dashboard/recent-errors")
        if not errors:
            await send(chat_id, "✅ لا توجد أخطاء!")
            return
        lines = ["🚨 *آخر الأخطاء:*\n"]
        for e in errors[:8]:
            lines.append(f"• `{e['workflow']}` › {e['node_name']}\n"
                         f"  {e['error_message'][:100]}\n"
                         f"  _{e['timestamp'][:16]}_")
        await send(chat_id, "\n".join(lines))
    except Exception as e:
        await send(chat_id, f"❌ خطأ: {e}")


# ── New video conversation ─────────────────────────────────────────────────

async def start_new_video(chat_id):
    _state[chat_id] = {"step": "title"}
    await send(chat_id, "🎬 *إنشاء فيديو جديد*\n\nأرسل *عنوان الفيديو*:")


async def handle_conversation(chat_id, text: str):
    state = _state.get(chat_id, {})
    step = state.get("step")

    if step == "title":
        state.update({"title": text, "step": "niche"})
        _state[chat_id] = state
        await send(chat_id, f"✅ العنوان: *{text}*\n\nاختر *المجال*:", reply_markup={
            "keyboard": [["finance", "tech"], ["health", "education"], ["entertainment", "other"]],
            "resize_keyboard": True, "one_time_keyboard": True})

    elif step == "niche":
        state.update({"niche": text, "step": "duration"})
        _state[chat_id] = state
        await send(chat_id, f"✅ المجال: *{text}*\n\nاختر *مدة الفيديو* (ثانية):", reply_markup={
            "keyboard": [["60", "90"], ["120", "180"], ["300"]],
            "resize_keyboard": True, "one_time_keyboard": True})

    elif step == "duration":
        try:
            duration = int(text)
        except ValueError:
            await send(chat_id, "❌ أرسل رقماً مثل 120")
            return
        state.update({"duration": duration, "step": "confirm"})
        _state[chat_id] = state
        await send(chat_id,
            f"📋 *ملخص:*\n\nالعنوان: *{state['title']}*\n"
            f"المجال: *{state['niche']}*\nالمدة: *{duration}s*\n\nهل تريد المتابعة؟",
            reply_markup={"keyboard": [["✅ تأكيد", "❌ إلغاء"]],
                          "resize_keyboard": True, "one_time_keyboard": True})

    elif step == "confirm":
        _state.pop(chat_id, None)
        if text == "✅ تأكيد":
            try:
                result = await _api("/api/videos", method="POST", json={
                    "video_title": state["title"], "niche": state["niche"],
                    "target_duration": state["duration"], "channel_id": "default"})
                await send(chat_id,
                    f"🚀 *تم إضافة الفيديو!*\n\n🆔 `{result['video_id']}`\n"
                    f"سيتم إشعارك عند الانتهاء ✅")
            except Exception as e:
                await send(chat_id, f"❌ فشل الإنشاء: {e}")
        else:
            await send(chat_id, "❌ تم الإلغاء.")
        await send_menu(chat_id)


# ── Message router ─────────────────────────────────────────────────────────

async def handle_message(message: dict):
    chat_id = message.get("chat", {}).get("id")
    text = (message.get("text") or "").strip()
    if not chat_id or not text:
        return

    if chat_id in _state:
        if text in ["❌ إلغاء", "/cancel"]:
            _state.pop(chat_id, None)
            await send(chat_id, "❌ تم الإلغاء.")
            await send_menu(chat_id)
        else:
            await handle_conversation(chat_id, text)
        return

    if text in ["/start", "/menu"]:             await handle_start(chat_id)
    elif text in ["/stats", "📊 الإحصائيات"]:  await handle_stats(chat_id)
    elif text in ["/videos", "📹 الفيديوهات"]: await handle_videos(chat_id)
    elif text in ["/queue", "⏳ قائمة الانتظار"]: await handle_queue(chat_id)
    elif text in ["/channels", "📡 القنوات"]:  await handle_channels(chat_id)
    elif text in ["/new", "🎬 فيديو جديد"]:    await start_new_video(chat_id)
    elif text in ["/errors", "🚨 الأخطاء"]:    await handle_errors(chat_id)
    elif text in ["❌ إلغاء", "/cancel"]:       await send_menu(chat_id)
    elif text.startswith("/video "):            await handle_video_detail(chat_id, text.split(" ", 1)[1].strip())
    elif text.startswith("/logs "):             await handle_logs(chat_id, text.split(" ", 1)[1].strip())
    else:
        await send(chat_id, "❓ أمر غير معروف.")
        await send_menu(chat_id)


# ── Notifications ──────────────────────────────────────────────────────────

async def notify_success(video_id: str, title: str, final_url: str, duration: float, scenes: int):
    if not CHAT_ID:
        return
    await send(int(CHAT_ID),
        f"✅ *فيديو جاهز!*\n\n*العنوان:* {title}\n*ID:* `{video_id}`\n"
        f"*المشاهد:* {scenes} | *المدة:* {duration}s\n🔗 [مشاهدة الفيديو]({final_url})")


async def notify_error(video_id: str, title: str, error: str):
    if not CHAT_ID:
        return
    await send(int(CHAT_ID),
        f"🚨 *خطأ في Pipeline*\n\n*العنوان:* {title}\n"
        f"*ID:* `{video_id}`\n*الخطأ:* `{error[:300]}`")


# ── No-op polling (webhook mode) ──────────────────────────────────────────

async def polling_loop():
    log.info("Bot in webhook mode – no polling needed.")
