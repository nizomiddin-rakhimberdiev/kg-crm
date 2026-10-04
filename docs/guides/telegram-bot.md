# Telegram bot — bog'cha uchun qo'llanma

Radix CRM ota-onalar bilan **Telegram bot** orqali gaplashadi. Bot bepul,
xabar uzunligi cheklanmagan va deyarli har bir ota-onada Telegram bor.

Bot ikki ish qiladi:

1. **Bog'cha xabarlarini yetkazadi** — to'lov kvitansiyasi, qarz
   eslatmasi, muhim xabarnomalar.
2. **Ota-onaning shaxsiy kabineti** bo'ladi — u balansni, hisob-fakturalarni
   va kvitansiyalarni o'zi ko'radi, to'lovni telefonidan qiladi.

---

## 1. Eng muhim qoida: ulanmagan ota-ona xabar olmaydi

Botga **ota-onaning o'zi ulanishi** kerak — buni biz ham, siz ham uning
o'rniga qila olmaymiz. Telegram shunday ishlaydi: suhbat faqat odam botni
ochganda paydo bo'ladi.

Shuning uchun "ulanmagan" — xato emas, oddiy holat. Uni ekranda ko'rasiz:

- **Bola kartasi → Vasiylar** bo'limida har bir ota-ona yonida
  «Telegram ulangan» yoki «Telegram ulanmagan» yozuvi turadi.
- **Bildirishnomalar** sahifasida yuqorida: «10 ota-onadan 3 tasi
  Telegramga ulangan. Qolgan 7 tasi xabar olmaydi».

> **Maslahat.** Yangi bola qabul qilganingizda ulash havolasini darhol
> yuboring — birinchi qarz eslatmasi kerak bo'lganda kech bo'ladi.

---

## 2. Ota-onani ulash — ikki yo'l

### 1-yo'l: ulash havolasi (asosiy yo'l)

1. **Bolalar** → bolani oching → **Vasiylar** bo'limi.
2. Ota-ona yonidagi **«Ulash havolasi»** tugmasini bosing.
3. **«Nusxalash»** ni bosing va havolani ota-onaga yuboring — Telegram,
   SMS, WhatsApp yoki qog'ozda, farqi yo'q.
4. Ota-ona havolani bosadi → bot ochiladi → **«Start»** ni bosadi. Tamom.

**Havola bir martalik.** Ota-ona ulangandan keyin u ishlamay qoladi. Agar
havola boshqa odamga tushib qolgan deb o'ylasangiz, **«Yangi havola»**
tugmasini bosing — eski havola shu zahoti kuchini yo'qotadi.

> **Nega bir martalik:** havola oilaviy guruhga tashlanishi mumkin, xabarlar
> ichida esa bolaning ismi va qarz summasi bo'ladi.

### 2-yo'l: telefon raqami orqali

Ota-ona botni o'zi topib ochsa (`@bot_nomi` ni qidirib), bot undan telefon
raqamini so'raydi:

1. Ota-ona **«📱 Telefon raqamni yuborish»** tugmasini bosadi.
2. Agar bu raqam bog'chada **shu ota-ona nomida yozilgan** bo'lsa, bot
   darhol ulaydi.
3. Raqam topilmasa, bot «bu raqam topilmadi» deydi va bog'chadan havola
   so'rashni aytadi.

Shuning uchun vasiy telefon raqamini to'g'ri kiritish muhim: raqam
ulanishning kalitiga aylanadi.

> Telegram raqamni **o'zi tasdiqlaydi** — ota-ona uni qo'lda yozmaydi, va
> boshqa odamning kontaktini yuborib ulanib bo'lmaydi.

---

## 3. Ota-ona botda nima qila oladi

Ulangandan keyin pastda to'rtta tugma turadi:

| Tugma | Nimani ko'rsatadi |
|---|---|
| **💰 Balans** | Qarz yoki avans summasi, muddati o'tgan to'lov, keyingi to'lov sanasi |
| **🧾 Hisob-fakturalar** | Oxirgi 6 ta hisob-faktura va holati (to'langan / to'lanmagan / muddati o'tgan) |
| **💳 To'lash** | To'lov tugmasi — Payme yoki Click sahifasi ochiladi |
| **📄 Kvitansiyalar** | Oxirgi 5 to'lov: sanasi, summasi, usuli |

Bir nechta bolasi bo'lsa, bot har bir bola bo'yicha alohida ko'rsatadi.
Ikki xil bog'chada bolasi bo'lsa — ikkalasini ham, bog'cha nomi bilan.

Ota-ona **faqat o'z bolalarini** ko'radi.

### «💳 To'lash» tugmasi ishlashi uchun

**Sozlamalar → Onlayn to'lov** bo'limida Payme yoki Click kalitlaringiz
kiritilgan bo'lishi kerak. Pul to'g'ridan-to'g'ri **bog'chaning hisobiga**
tushadi va to'lov tizimga o'zi yoziladi — kassirning qo'lda yozishi shart
emas.

Kalitlar kiritilmagan bo'lsa, bot «bog'cha kassasida to'lang» deb javob
beradi.

---

## 4. Bog'cha ota-onaga nima yuboradi

| Xabar | Qachon ketadi | Qayerdan boshqariladi |
|---|---|---|
| **To'lov kvitansiyasi** | Kassir to'lovni yozgach, o'zi | Sozlamalar → «To'lov haqida xabar» |
| **Qarz eslatmasi** | Siz yuborganingizda | Qarzdorlar → «Hammasiga eslatma» |
| **Kelmagani haqida** | Bola «kelmadi» deb belgilansa | Sozlamalar → «Kelmagani haqida xabar» (sukut bo'yicha **o'chiq**) |

### Qarz eslatmasini yuborish

1. **Qarzdorlar** sahifasini oching.
2. Kerak bo'lsa summa yoki kun bo'yicha filtr qo'ying.
3. **«Hammasiga eslatma»** tugmasini bosing — tizim avval nechta xabar
   ketishini ko'rsatadi, keyin yuboradi.

Bir ota-ona **kuniga bir martadan ortiq** eslatma olmaydi (Sozlamalarda
o'zgartiriladi). Ikkinchi eslatma yangi ma'lumot bermaydi, bezovta qiladi.

---

## 5. Sozlamalar (Sozlamalar → Bildirishnomalar)

| Sozlama | Ma'nosi | Tavsiya |
|---|---|---|
| **Asosiy kanal** | Telegram yoki SMS | **Telegram** — bepul |
| **Yuborishni boshlash / tugatish (soat)** | Xabar yuboriladigan vaqt oynasi | 08:00 – 21:00 |
| **Kuniga eslatma soni** | Bir ota-onaga kunda nechta qarz eslatmasi | 1 |
| **To'lov haqida xabar** | Kvitansiya avtomatik ketadimi | Yoqilgan |
| **Kelmagani haqida xabar** | Bola kelmasa ota-onaga xabar | O'zingiz hal qilasiz |

**Vaqt oynasi** nima uchun kerak: kechasi kelgan xabar ota-onani uyg'otadi.
Oyna tashqarisida tayyor bo'lgan xabar **o'chib ketmaydi** — navbatda turadi
va ertalab ketadi.

---

## 6. Xabar yetib bordimi? — Bildirishnomalar sahifasi

Har bir yuborilgan xabar **Bildirishnomalar** sahifasida qoladi: kimga,
qanday matn, qaysi holatda.

| Holat | Ma'nosi |
|---|---|
| **Navbatda** | Hali yuborilmagan (masalan, vaqt oynasi tashqarisida) |
| **Yuborildi** | Telegramga topshirildi |
| **Yetkazildi** | Ota-ona oldi |
| **Xato** | Yetib bormadi — sababi yonida yoziladi |
| **Test rejimi** | **Hech kimga ketmagan** — bot hali ulanmagan |

> **«Test rejimi» ni jiddiy oling.** U xabarlar jurnalga yozilayotganini,
> lekin ota-onalarga **bormayotganini** anglatadi. Bunda sahifa tepasida
> qizil ogohlantirish turadi.

---

## 7. Ota-ona xabarlarni to'xtatsa

Botda **`/stop`** yozsa, xabarlar to'xtaydi — bu uning huquqi. U holda bola
kartasida yana «Telegram ulanmagan» ko'rinadi.

Qayta ulanish uchun yangi ulash havolasi yuboriladi yoki ota-ona telefon
raqamini qaytadan yuboradi.

Siz ham uzib qo'yishingiz mumkin: bola kartasida **«Uzish»** tugmasi.

---

## 8. Ko'p beriladigan savollar

**Bot pullikmi?**
Yo'q. Telegram xabarlari bepul va ular hisoblanmaydi. SMS pullik, lekin u
hozir o'chirilgan.

**Ota-onada Telegram bo'lmasa?**
Unda u xabar olmaydi. Kvitansiyani qog'ozda berishingiz yoki keyinchalik
SMS ni yoqishingiz mumkin (buning uchun shlyuz shartnomasi kerak).

**Bitta telefonda ikki bola — ikki marta ulash kerakmi?**
Yo'q. Ota-ona bir marta ulanadi, bot ikkala bolani ham ko'rsatadi.

**Ota-ona bolaning hamma ma'lumotini ko'radimi?**
Yo'q. Faqat pul bilan bog'liq ma'lumot: balans, hisob-fakturalar,
kvitansiyalar. Davomat jurnali, xodimlar, boshqa bolalar — ko'rinmaydi.

**Havolani boshqa odam bosib ulansa-chi?**
Havola bir martalik va kim ulanganini ko'rasiz. Shubha bo'lsa — «Uzish»,
keyin «Yangi havola».

**Bot ishlamay qolsa?**
Bildirishnomalar sahifasidagi ogohlantirishga qaraysiz. «Telegram bot
ulanmagan» deb yozilsa — bu bog'cha emas, texnik sozlama masalasi, bizga
murojaat qilasiz.

---

## 9. Boshlash uchun qisqa ro'yxat

- [ ] Sozlamalar → **Asosiy kanal = Telegram**
- [ ] Sozlamalar → **Onlayn to'lov**: Payme / Click kalitlari (to'lov tugmasi uchun)
- [ ] Vasiylarning telefon raqamlari to'g'ri kiritilganini tekshirish
- [ ] Har bir ota-onaga **ulash havolasi** yuborish
- [ ] **Bildirishnomalar** sahifasida qamrovni tekshirish: «N ota-onadan M tasi ulangan»
- [ ] Birinchi qarz eslatmasini kichik guruhga yuborib ko'rish
