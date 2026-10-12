# 08 — Radix AI: xotira, yuz tanish, Telegram va kamera

Holat: backend `apps/memories` + frontend `features/memories` yetkazilgan (2026-10). Bu hujjat yangi qarorlarning manbai.

## 1. Nima qiladi
1. O'qituvchi bog'cha Telegram guruhiga rasm yuboradi → bot yuzlarni tanib, **faqat roziligi bor** bolalarning ota-onasiga rasm yuboradi (boshqa bolalar yuzi xiralashtiriladi).
2. Rasmlar saqlanadi; ota-ona `/photos`, `/photos week`, `/photos 2026-10-01` bilan vaqt bo'yicha oladi.
3. Kun tartibi (menyu, ovqat, mashg'ulot) belgilangan vaqtda ota-onalar botiga yuboriladi (`memories.dispatch_schedule`, har 5 daqiqa).
4. Kamera hodisalari (xodim qoidabuzarligi, yig'layotgan bola) `POST /camera-events` bilan keladi; rahbar Telegram'iga rasm dalili bilan ogohlantirish ketadi.

## 2. Qarorlar
- **Yuz tanish: OpenCV YuNet + SFace** (Apache-2.0), `FaceEngine` adapteri ortida; InsightFace keyin shu interfeys orqali almashtiriladi. Modellar: `python manage.py fetch_face_models` (`FACE_MODEL_DIR`, `--sha256` bilan tekshirish tavsiya etiladi).
- **Kamera tahlili** (xodim/yig'lash aniqlash) modeli bu repoda yo'q: `Detector` protokoli kengaytirish nuqtasi. Ulanish, qabul, ogohlantirish va ko'rib chiqish tayyor (§8).
- **Tenant yo'nalishi:** webhook'da tenant noma'lum, shuning uchun `telegram_chat` METADATA jadvali (`org OR platform` siyosati). Ulash tokeni `<org_hex>_<secret>`, bazada faqat SHA-256, 48 soat, bir martalik.

## 3. Xavfsizlik invariantlari
- Yuz vektori Fernet bilan shifrlangan (`MEMORIES_ENCRYPTION_KEY`, production'da majburiy); rozilik bekor qilinsa vektorlar o'chadi.
- Vektor faqat `FaceConsent` bor bola uchun; tasdiqlash/qo'lda belgilash ham rozilikni tekshiradi.
- Ishonchi past tegi (`suggested`) ota-onaga o'zi ketmaydi — odam tasdiqlaydi.
- Rasmlar ochiq URL'da emas: `GET /memory-photos/{id}/image` (tokenli, `Cache-Control: private, no-store`).
- Webhook: `X-Telegram-Bot-Api-Secret-Token` doimiy-vaqt solishtiruvi; sir yo'q bo'lsa 404 (fail-closed); throttle `telegram_webhook`.
- Kamera oqim manzili (login/parol) shifrlanadi, API javobida qaytmaydi.
- Yuklash: tur (JPEG/PNG/WebP), hajm (`MEMORIES_MAX_UPLOAD_BYTES`), dekodlashda 1600px chegarasi.
- Biometrik ma'lumot O'zbekiston hududida saqlanishi shart (launch gate, 01 §10).

## 4. Jadvallar (hammasida `organization_id` + RLS FORCE)
`face_consent`, `face_sample`, `memory_photo`, `photo_tag`, `day_schedule_item`, `camera`, `camera_event`, `telegram_pairing` (operatsion); `telegram_chat` (metadata).

## 5. API (`/api/v1/`, modul `memories`)
`memory-photos` (+`/image`, `/tag`, `/reprocess`), `photo-tags` (+`/confirm`, `/reject`), `face-consents` (+`/enroll`, `/revoke`), `schedule-items`, `cameras` (+`/token`, `/revoke-token`), `camera-ingest` (kamera tokeni bilan), `camera-events` (+`/acknowledge`, `/dismiss`, `/snapshot`), `telegram-chats` (+`/pairing`), `telegram/webhook`. RBAC: org_owner/director — to'liq, manager — o'qish/yaratish/yangilash, boshqalar — yo'q.

## 6. Til
Bot xabarlari `bot_messages.py` (gettext_lazy, uz/ru/en), til chatga biriktirilgan (`/language uz|ru|en`). Frontend matnlari `t()` + ru/en lug'at.

## 7. Keyingi qadamlar (hali yo'q)
Bola bo'yicha "nima yedi" jurnali; ota-ona uchun kunlik AI xulosa (LLM); to'lov/qarz eslatmalari botda; xodim/yig'lash aniqlash modeli (edge `Detector`); kayfiyat modelini o'qitish.

## 8. Kamerani ulash va kuzatuv

**Arxitektura.** Bulut kameraga hech qachon ulanmaydi. Bog'cha ichidagi `python -m edge.camera_worker` (yoki NVR/bulut webhook'i) Radix'ga faqat heartbeat, hodisa va (ixtiyoriy) so'nggi kadrni yuboradi. RTSP login/paroli bog'chadan chiqmaydi.

**Token.** Har kameraga alohida: `<org_hex>.<camera_hex>.<secret>`. Ochiq matn faqat `POST /cameras/{id}/token` javobida bir marta ko'rinadi (`connection`: `edge` | `webhook`); bazada `secret` ning SHA-256 xeshi. Yangi token eskisini bekor qiladi; `POST /cameras/{id}/revoke-token` o'chiradi. Tenant tokenning ichidagi tashkilotdan aniqlanadi va RLS kontekstida tekshiriladi; boshqa tashkilot ID'si bilan almashtirilgan token 401. Solishtirish doimiy-vaqtli; sabab oshkor qilinmaydi.

### Uch ulanish yo'li

1. **Bog'cha kompyuteri (RTSP)** — bitta kamera: `RADIX_SERVER`, `RADIX_CAMERA_TOKEN`, `RADIX_RTSP_URL`; `--test`, so'ng doimiy ishlash.
2. **NVR / ko'p kamera (ONVIF)** — `--onvif NVR_IP` oqim manzillarini topadi (WS-Security digest; javob `defusedxml` bilan o'qiladi, faqat `rtsp://` qabul qilinadi); `--nvr-template hikvision|dahua --nvr-host ... --channels N` sozlama skeletini beradi; `--config cameras.json` har kamera uchun alohida oqim ochadi (ko'pi bilan 32). Fayl ichida tokenlar bor: POSIX'da guruh/boshqalar o'qiy oladigan fayl rad etiladi; `PASTE_TOKEN`/`PAROL` to'ldirilmagan bo'lsa ishga tushmaydi.
3. **Webhook (NVR / bulut)** — `POST /api/v1/camera-webhook` (`Authorization: Bearer`, afzal) yoki, sarlavha sozlab bo'lmaydigan NVR uchun, `POST /api/v1/camera-webhook/<token>`. URL-token faqat `webhook` rejimidagi kameralarga ishlaydi va FAQAT hodisa yozadi (loglarga tushgani uchun kuzatuv kadrini yoza olmaydi). Qabul qilinadigan tana: JSON/form (`kind`, `severity`, `note|message|event|eventType|type|description`, fayl), xom `image/jpeg|png`, yoki XML — XML **parse qilinmaydi** (XXE yo'q), faqat `<eventType>` regex bilan olinadi. Izoh bosib bo'lmaydigan belgilardan tozalanadi, ≤400.

**Bulutli kameralar** (Hik-Connect, EZVIZ, Tapo): ularning bulut API'lari bu repoga **integratsiya qilinmagan** (kalit/shartnoma kerak, sinab bo'lmaydi). Yo'llar: kamera ilovasida RTSP/ONVIF'ni yoqib 1–2-yo'l, yoki tizim HTTP xabarnoma yuborsa 3-yo'l.

### Kuzatuv ("Kuzatuv" tabi)
Admin/rahbar (`memories.read`) ulangan kameralarning holati (Onlayn/Oflayn), yangi hodisalar soni va so'nggi kadrini ko'radi. Bu haqiqiy video emas: worker `--preview-every` (standart 15 s) da bitta kichraytirilgan JPEG yuboradi, serverda FAQAT so'nggisi saqlanadi (eskisi o'chadi), serverda ≥5 s oraliq.
Maxfiylik: kuzatuv har kamerada **standart o'chiq** (`preview_enabled`), `memories.update` huquqi bilan yoqiladi, yoqish/o'chirish auditga yoziladi; o'chirilsa fayl darhol o'chadi. `GET /cameras/{id}/preview` autentifikatsiyali, tenant bo'yicha izolyatsiyalangan, `Cache-Control: private, no-store`, `nosniff`. Heartbeat javobidagi `preview_wanted` worker'ga kadr yuborish-yubormaslikni aytadi.

**`POST /api/v1/camera-ingest`** (Bearer, JWT yo'q, throttle `camera_ingest` 600/daq): `kind` yo'q → heartbeat (+ yoqilgan bo'lsa kuzatuv kadri); `kind` bor → hodisa (rasm JPEG/PNG ≤5 MB, magic-bytes), kamera+tur bo'yicha 60 s cooldown, so'ng Telegram'da xodimlar chatiga rasm bilan ogohlantirish. `last_seen_at` ≤2 daqiqa → `is_online`.

**Cheklovlar.** Yig'lash va xodim qoidabuzarligi modeli kiritilmagan (`Detector` kengaytirish nuqtasi). ONVIF, NVR shablonlari va webhook haqiqiy qurilmada sinab ko'rilmagan (faqat sintetik javoblar bilan test qilingan). Kuzatuv jonli video emas; real vaqtli oqim uchun alohida shlyuz (masalan go2rtc) kerak bo'ladi.
