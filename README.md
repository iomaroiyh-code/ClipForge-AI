# ClipForge AI — Web App

تطبيق ويب يحوّل الفيديوهات الطويلة إلى مقاطع قصيرة باستخدام Streamlit وfaster-whisper وyt-dlp وFFmpeg.

## التشغيل محلياً

يتطلب Python 3.10 أو 3.11 وFFmpeg.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## النشر

يمكن نشره على خادم يدعم Docker وFFmpeg. يبني Dockerfile الموجود صورة التطبيق ويشغّل Streamlit على المنفذ 8501.

## ملاحظات
- استخدم فيديوهات تملك حقوقها أو لديك إذن بتنزيلها وإعادة استخدامها.
- yt-dlp قد لا يدعم كل المواقع بشكل دائم.
- أول تشغيل ينزّل نموذج Whisper وقد يستغرق بعض الوقت.
- هذا إصدار أولي؛ اقتراح المقاطع آلي وبسيط وليس ضماناً للانتشار.
