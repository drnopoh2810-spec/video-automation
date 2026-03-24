---
title: Video Automation Dashboard
emoji: 🎬
colorFrom: blue
colorTo: purple
sdk: docker
app_file: app.py
pinned: false
---

# 🎬 Video Automation Dashboard

لوحة تحكم كاملة لأتمتة إنشاء الفيديوهات بالذكاء الاصطناعي.

---

## 🚀 خطوات النشر الكاملة

### 1. رفع المشروع على GitHub

```bash
cd video-automation-dashboard
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/video-automation-dashboard.git
git push -u origin main
```

---

### 2. إضافة Secrets في GitHub

اذهب إلى: `GitHub Repo → Settings → Secrets and variables → Actions → New repository secret`

| الاسم | القيمة |
|-------|--------|
| `HF_TOKEN` | Token من HuggingFace بصلاحية **write** – من [hf.co/settings/tokens](https://huggingface.co/settings/tokens) |
| `HF_SPACE_NAME` | اسم الـ Space مثلاً `ahmed/video-automation` |

---

### 3. إنشاء Space على HuggingFace

1. اذهب إلى [huggingface.co/new-space](https://huggingface.co/new-space)
2. اختر **Docker** كـ SDK
3. اتركه فارغاً – GitHub Actions سيرفع الكود تلقائياً

---

### 4. إضافة Variables في HuggingFace Space

اذهب إلى: `Space → Settings → Variables and secrets`

#### Secrets (مخفية ومشفرة)
| الاسم | من أين تحصل عليه |
|-------|-----------------|
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) |
| `ELEVENLABS_API_KEY` | [elevenlabs.io → Profile → API Keys](https://elevenlabs.io) |
| `HUGGINGFACE_API_KEY` | [hf.co/settings/tokens](https://huggingface.co/settings/tokens) – نفس الـ token |
| `CREATOMATE_API_KEY` | [creatomate.com → Settings → API](https://creatomate.com) |
| `SUPABASE_API_KEY` | Supabase → Project → Settings → API → `service_role` key |

#### Variables (عامة)
| الاسم | القيمة |
|-------|--------|
| `SUPABASE_URL` | `https://YOUR_PROJECT_ID.supabase.co` |
| `PORT` | `7860` |

---

### 5. Deploy تلقائي

بعد إضافة كل الـ Secrets، أي `git push` على `main` سيتم نشره تلقائياً على HuggingFace.

```bash
git add .
git commit -m "update"
git push
# ✅ GitHub Action يرفع تلقائياً على HuggingFace
```

---

## 🔑 إضافة API Keys من لوحة التحكم

يمكنك إضافة مفاتيح API مباشرة من الواجهة دون الحاجة لإعادة النشر:

`لوحة التحكم → إعدادات API → إضافة حساب`

يدعم النظام **عدة حسابات لكل خدمة** ويستخدم الأول النشط تلقائياً.

---

## 🤖 الوكلاء (Agents)

| الوكيل | الخدمة | الوظيفة |
|--------|--------|---------|
| ScriptAgent | Groq llama3-70b | توليد السكريبت |
| AudioAgent | ElevenLabs + Groq Whisper | تحويل النص لصوت + SRT |
| ImageAgent | HuggingFace SDXL | توليد الصور |
| VideoAgent | Creatomate | رندر المقاطع ودمجها |
| StorageAgent | Supabase | رفع الملفات |

---

## 🐳 تشغيل محلي بـ Docker

```bash
cp .env.example .env
# عدّل .env بمفاتيحك
docker compose up --build
# افتح http://localhost:7860
```

## تشغيل بدون Docker

```bash
pip install -r requirements.txt
cp .env.example .env
python app.py
```
