import nest_asyncio
import requests, os, asyncio, time
from tqdm import tqdm
from telethon.sync import TelegramClient
from telethon.tl.functions.messages import SendMessageRequest

nest_asyncio.apply()

# بيانات تيليغرام
api_id = 28420794
api_hash = "76124567461794b385b282f876fc81a3"
channel_username = "@narutooclsh"
notify_user_id = 7209819472

# بيانات الأنمي
anime_name = "Naruto Shippuden"
duration_minutes = 24
quality = "1080p"

uploaded_log = "uploaded.log"
used_links_file = "used_links.log"
links_file = "links.txt"

# تحويل روابط Google Drive
def convert_to_download_link(link):
    if "drive.google.com" in link and "/file/d/" in link:
        file_id = link.split("/file/d/")[1].split("/")[0]
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    return link

# تحميل الفيديو
def download_video(url, output_path):
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        with open(output_path, 'wb') as f, tqdm(total=total, unit='B', unit_scale=True, desc=f"⬇️ تحميل {output_path}") as bar:
            for chunk in r.iter_content(1024 * 1024):
                if chunk:
                    f.write(chunk)
                    bar.update(len(chunk))
    print(f"✅ تم تحميل {output_path} بنجاح.\n")

# شريط التقدم للرفع
progress_bar = None
def progress_callback(current, total):
    global progress_bar
    if progress_bar is None:
        progress_bar = tqdm(total=total, unit='B', unit_scale=True, desc="📤 رفع الفيديو")
    progress_bar.update(current - progress_bar.n)

# رفع الفيديو
async def upload_file(client, file_name, caption):
    global progress_bar
    try:
        progress_bar = None
        await client.send_file(
            entity=channel_username,
            file=file_name,
            caption=caption,
            supports_streaming=True,
            progress_callback=progress_callback
        )
        if progress_bar:
            progress_bar.close()
        print(f"✅ تم رفع {file_name} بنجاح.\n")
        return True
    except Exception as e:
        print(f"❌ فشل رفع {file_name}: {e}")
        return False

# إشعار خاص
async def notify(client, message):
    try:
        await client(SendMessageRequest(peer=notify_user_id, message=message))
    except Exception as e:
        print(f"⚠️ فشل إرسال إشعار: {e}")

# استئناف الحلقة
def get_episode_number():
    while True:
        try:
            value = input("🎞️ أدخل رقم أول حلقة: ").strip()
            if not value:
                raise ValueError("الإدخال فاضي.")
            return int(value)
        except ValueError:
            print("⚠️ الرجاء إدخال رقم صحيح.")

# عدد الحلقات
def get_number_of_episodes(max_episodes):
    while True:
        try:
            value = input(f"📦 كم حلقة تريد رفعها؟ (بحد أقصى {max_episodes}): ").strip()
            if not value:
                raise ValueError("الإدخال فاضي.")
            value = int(value)
            if value < 1 or value > max_episodes:
                raise ValueError("خارج النطاق.")
            return value
        except ValueError:
            print("⚠️ الرجاء إدخال رقم صحيح ضمن النطاق.")

# روابط مرفوعة مسبقًا
def load_uploaded_episodes():
    if os.path.exists(uploaded_log):
        with open(uploaded_log, "r") as f:
            return set(int(line.strip()) for line in f if line.strip().isdigit())
    return set()

def mark_episode_uploaded(ep_number):
    with open(uploaded_log, "a") as f:
        f.write(f"{ep_number}\n")

# روابط مستخدمة
def load_used_links():
    if os.path.exists(used_links_file):
        with open(used_links_file, "r") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def mark_link_used(link):
    with open(used_links_file, "a") as f:
        f.write(f"{link}\n")

# رفع الحلقات
async def upload_multiple_episodes():
    if not os.path.exists(links_file):
        print("❌ ملف الروابط غير موجود.")
        return

    with open(links_file, "r") as f:
        all_links = [convert_to_download_link(line.strip()) for line in f if line.strip()]

    used_links = load_used_links()
    filtered_links = []
    for link in all_links:
        if link not in used_links and link not in filtered_links:
            filtered_links.append(link)

    if not filtered_links:
        print("⚠️ لا توجد روابط جديدة للرفع.")
        return

    start_episode = get_episode_number()
    num_to_process = get_number_of_episodes(len(filtered_links))
    links = filtered_links[:num_to_process]
    uploaded = load_uploaded_episodes()

    async with TelegramClient("telethon_session", api_id, api_hash) as client:
        print("✅ تم تسجيل الدخول.\n")
        for idx, link in enumerate(links):
            episode_number = start_episode + idx
            if episode_number in uploaded:
                print(f"⏭️ الحلقة {episode_number} تم رفعها مسبقًا.")
                continue

            file_name = f"{anime_name} - الحلقة {episode_number}.mp4"
            try:
                download_video(link, file_name)
                time.sleep(1)

                caption = f"""🎬 **{anime_name}**
🧩 الحلقة: {episode_number}
🕒 المدة: {duration_minutes} دقيقة
📺 الجودة: {quality}

_تم الرفع بواسطة بوت يو أنمي ✅_"""

                success = await upload_file(client, file_name, caption)
                if success:
                    os.remove(file_name)
                    print("🗑️ تم حذف الملف بعد الرفع.\n")
                    mark_episode_uploaded(episode_number)
                    mark_link_used(link)
                    await notify(client, f"✅ تم رفع الحلقة {episode_number} من {anime_name} بنجاح.")
            except Exception as e:
                print(f"❌ خطأ في الحلقة {episode_number}: {e}")
                await notify(client, f"❌ خطأ في الحلقة {episode_number}: {e}")
                break  # لإتاحة خيار الاستئناف اليدوي لاحقًا

# تشغيل الدالة
await upload_multiple_episodes()
