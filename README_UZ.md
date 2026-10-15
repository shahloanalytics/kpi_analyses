# Security KPI — Avtozavod

Avtomobil zavodining qo‘riqlash bo‘limi uchun o‘zbekcha Streamlit platformasi.
BYD’ning rasmiy mahsuloti emas. Barcha vazn, maqsad va chegaralar **tasdiqlash uchun namuna**.

## 1. ZIP faylni oching

1. `Security_KPI_Cloud_Ready.zip` ustida sichqonchaning o‘ng tugmasini bosing.
2. **Extract All / Извлечь всё** ni tanlang.
3. `Security_KPI_Cloud_Ready` papkasini oching. Ichida `app.py` ko‘rinishi kerak.

## 2. GitHub’ga yuklang

1. https://github.com saytiga kiring.
2. Yangi **security-kpi** repository yarating. Haqiqiy ma’lumotlar uchun yopiq repository va tashkilot talablari asosida hosting tanlang.
3. **Add file → Upload files** ni bosing.
4. Ochilgan ZIP papkasining **ichidagi** fayl va papkalarni yuklang. ZIP faylining o‘zini yuklash dasturni ishga tushirmaydi.
5. `app.py` va `requirements.txt` repositoryning asosiy sathida bo‘lsin.
6. `data/sample.db`, `templates`, `assets` va `.streamlit/config.toml` saqlanganini tekshiring.
7. **Commit changes** ni bosing.

Agar `.streamlit` papkasi yuklanmasa: GitHub → Add file → Create new file → nomiga `.streamlit/config.toml` yozing va ZIP ichidagi config.toml matnini nusxalang. `assets/DejaVuSans.ttf` PDF uchun zarur.

## 3. Streamlit Cloud’da ishga tushiring

1. https://share.streamlit.io orqali kiring va GitHub hisobingizni ulang.
2. **Create app** tugmasini bosing.
3. Repository: `security-kpi`.
4. Branch: repositorydagi asosiy branch (odatda `main`).
5. Main file path: **app.py**.
6. Advanced settings’da **Python 3.12** tanlang.
7. **Deploy** ni bosing. Kutubxonalar `requirements.txt` orqali o‘rnatiladi.
8. Ilova manzili ochilgach, demo rejimida sinab ko‘ring.

Agar loyiha qo‘shimcha ichki papkaga yuklangan bo‘lsa, main file path ham shu papkani o‘z ichiga olishi kerak. Eng sodda variant — barcha loyiha fayllarini repository ildiziga yuklash.

## 4. Kompyuterda ishga tushirish

Terminalni loyiha papkasida oching:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Sinovlar:

```bash
python -m unittest discover -s tests -v
```

## 5. Birinchi demo sinovi: 5 daqiqa

1. Demo rol: **Ma’lumot kirituvchi**.
2. Davr: `2026-09`; daraja: **Smena boshlig‘i**; shablon: `shift-v1`; kod: `SM-01`.
3. Dashboard ochiladi. Baza 3 smena va 2 oy uchun 60 ta sun’iy yozuv bilan keladi.
4. **Excel / CSV yuklash** menyusida `Security_KPI_Namuna.xlsx` ni yuklab oling va yana import qiling.
5. 60 qatorni va farqlarni ko‘ring. Tasdiqlab yozing. Qatorlar soni ikki barobar bo‘lmaydi.
6. **Hisobotlar → Joriy hisobdan qoralama yaratish** tugmasini bosing.
7. Excel va PDF hisobotni yuklab oling.
8. `2026-10 / SM-02` da yetishmayotgan REPORT ma’lumotini; `2026-10 / SM-03` da qo‘llanilmaydigan RESPONSE mezonini ko‘ring.

Namuna metodika tasdiqlanmaguncha natija **Dastlabki hisob** bo‘lib turishi ataylab qilingan.

## 6. Metodika va tasdiqlashni sinash

1. Demo rolni Administratorga almashtiring.
2. Sozlamalarda tanlangan `shift-v1` metodikasini ko‘rib, tasdiqlash katagini belgilang va tasdiqlang.
3. Ma’lumot kirituvchi rolida `2026-09 / SM-01` uchun **yangi qoralama** yarating. Eski qoralama eski metodika holatini saqlaydi.
4. Tekshiruvchi rolida hisobotni oching va **Tekshirildi** deb belgilang.
5. Administrator rolida shu hisobotni **Tasdiqlang**.
6. Muallif, tekshiruvchi va tasdiqlovchi alohida kodlar bo‘lishi kerak.

Vazn yoki maqsadni o‘zgartirish yangi metodika versiyasi yaratadi. Yangi versiyaning ID sini importdagi `template` ustuniga kiriting. Eski davrlarning versiyasini o‘zgartirmang. Har bir shablon vaznlari 100% bo‘lishi kerak.

`na` mezonlar vazni qayta taqsimlanishi kerak bo‘lsa, administrator yangi versiyada shu qoidani belgilaydi va tasdiqlaydi. Bu tanlovsiz qolgan mezonlar avtomatik 100% ga ko‘tarilmaydi.

## 7. Hisoblar va rollarni sozlash (Secrets)

Parollar kodda yoki GitHub’da bo‘lmasin. Har bir foydalanuvchi uchun alohida parol xeshi yarating:

```bash
python auth.py
```

Parol terminalda ko‘rinmaydi. Chiqqan `pbkdf2_sha256$...` satrini nusxalang.
Streamlit Cloud → app sozlamalari → **Secrets** bo‘limiga quyidagi tuzilmani kiriting. `HASH_...` joylarini haqiqiy yaratilgan xeshlar bilan almashtiring:

```toml
[users.OP01]
role = "entry"
password_hash = "HASH_OPERATOR"

[users.RV01]
role = "reviewer"
password_hash = "HASH_REVIEWER"

[users.AD01]
role = "admin"
password_hash = "HASH_ADMIN"
```

Mahalliy ishlatishda ushbu matn `.streamlit/secrets.toml` faylida bo‘lishi mumkin. Bu faylni GitHub’ga yuklamang; `.gitignore` uni chetlatadi.

| Rol | Imkoniyat |
|---|---|
| entry | Ma’lumot kiritish/import, vazifa, qoralama yaratish, ko‘rish va eksport |
| reviewer | Ko‘rish/eksport, boshqa muallif hisobotini tekshirish |
| admin | Sozlamalar, kodlar, metodika, import, boshqa xodimlar tekshirgan hisobotni tasdiqlash, zaxira/tiklash |

Secrets bo‘lmasa, faqat DEMO baza ochiladi va rol tanlashga ruxsat beriladi. Bu ishlab chiqarish autentifikatsiyasi emas. Ishchi rejimda Secrets bo‘lmasa kirish bloklanadi.

Haqiqiy ishni boshlashdan oldin administrator Secrets sozlangan holda **Demo ma’lumotlarni tozalash va ishchi rejimga o‘tish** amalini bajarsin. Ro‘yxatdagi namuna kodlar o‘rniga kerakli haqiqiy anonim kodlarni qo‘shing. Ushbu versiya bitta tashkilot bazasi uchun; foydalanuvchilar kesimida alohida tashkilot izolyatsiyasi yo‘q.

## 8. Qanday ma’lumotlar kerak?

`templates/Malumotlar_Lugati.xlsx` va ilovadagi **KPI kartalari** barcha ustunlar uchun ma’no, manba, birlik, misol va majburiylikni ko‘rsatadi.

Asosiy import kaliti: **month + entity + template + metric**.

- `month`: `2026-09` kabi oy.
- `entity`: Sozlamalardagi kod.
- `template`: aynan tanlangan metodika ID si.
- `metric`: POST, PATROL, ACCESS, CARGO, RESPONSE, REPORT, ACTION, TRAIN, AUDIT, EQUIP.
- `plan`: rejalashtirilgan ish yoki tanlama tekshiruvlarning jami.
- `actual`: dalil bilan tasdiqlangan bajarilgan/mos ish.
- `state`: `ok`, `missing`, `na`.
- `evidence`: anonim hujjat/dalil kodi.
- `note`: izoh; `na` bo‘lsa sabab majburiy.
- `entered_by`, `checked_by`: manba muallifi va tekshiruvchisi. Fayldagi checked_by hisobotga “Tekshirildi” maqomini bermaydi. Tizim haqiqiy kirgan foydalanuvchini alohida qayd etadi.

Excel’da **faqat Oylik_natijalar** avtomatik import qilinadi. Boshqa sahifalar manbani tartibga solish va ma’lumot qanday tayyorlanishini tushuntirish uchun. Xodim/metodika Sozlamalarda, vazifalar Chora-tadbirlar menyusida yaratiladi. Hodisa jamlanmasidagi sonlarni RESPONSE satriga kiriting; platforma ikki manbani qo‘shib hodisalarni ikki marta hisoblamaydi.

## 9. Metodika

- Bajarilish = amalda / reja × 100.
- KPI balli = min(100, bajarilish / maqsadli daraja × 100).
- Vaznli hissa = ball × amaldagi vazn / 100.
- Kuzatilgan vaznli ball — faqat hisoblash mumkin bo‘lgan mezonlarning hissalari. Yetishmayotgan ma’lumotga avtomatik nol berilmaydi.
- Barcha majburiy mezonlar to‘liq bo‘lishi va metodika tasdiqlanishi kerak; aks holda yakuniy reyting yo‘q.
- Maxraj 0 bo‘lsa, asosli `na` yoki `missing`; avtomatik 100 ball yo‘q.
- Amalda > reja importni bloklaydi. Avval reja/amal ma’nosi va hujjatni tekshiring.
- Boshliq, o‘rinbosar va smena natijalari alohida. Boshliq natijasi smenaning natijasidan avtomatik ko‘chirilmaydi.
- Bo‘lim agregati uchun Dashboard’da **Smenalardan surat/maxrajlarni yig‘ish** ni tanlang. Manba smenalari bir-birini takrorlamasligi kerak; foizlarning oddiy o‘rtachasi olinmaydi. Majburiy manba smena yo‘q bo‘lsa yakuniy natija bloklanadi. Agregat uchun qoralamani Dashboard’dagi tegishli tugma bilan yarating.
- Namuna chegaralar: ≥90 yaxshi; ≥70 va <90 kuzatuvda; <70 e’tibor kerak. Bu chegaralar rasmiy zavod normasi emas.
- Hodisalar soni kamligi o‘z-o‘zidan yaxshi natija emas. Texnik ta’mir vakolatga kirmasa, faqat aniqlash/xabar berish baholanadi.
- Jarima, mukofot va ish haqi hisoblanmaydi.

## 10. Hisobotlar va tiklash

Qoralama yaratilgan vaqtda ma’lumotlar, metodika versiyasi, tahlil va vazifalar muzlatiladi. Manba yozuvlar keyin o‘zgarsa, **yangi qoralama** yarating. Mavjud tasdiqlangan nusxa yangilanmaydi. Excel hisobotida qiymatlar qasddan statik: tasdiqlangan natija qayta hisoblanib ketmasin.

Sozlamalar → **To‘liq JSON zaxira**. Zaxira maxfiy ish ma’lumotlarini o‘z ichiga olishi mumkin; tegishli joyda saqlang.

Tiklash operatsion ma’lumotlar, kodlar va metodikani almashtiradi. Mavjud hisobot/audit tarixi o‘chmaydi. Faqat zaxirada bo‘lgan hisobotlar qoralama holatida qaytariladi va qayta tekshiriladi; holatlari turlicha bo‘lgan bir xil hisobot ID uchun tiklash bloklanadi. Eski audit zaxirasi yangi restore hodisasida saqlanadi. JSON tiklash SQL tranzaksiyada bajariladi: xato bo‘lsa avvalgi baza saqlanadi.

## 11. Saqlash va cheklovlar

- `data/sample.db` — faqat sun’iy boshlang‘ich baza; GitHub’ga yuklash mumkin.
- Birinchi ishga tushishda u `data/security.db` ga nusxalanadi.
- Ishchi `security.db` va Secrets GitHub’ga yuklanmasin.
- SQLite bitta server fayli; ko‘p foydalanuvchili yuqori yuklama uchun PostgreSQL va tashkilotning autentifikatsiya tizimiga moslashtirish kerak.
- Streamlit Community Cloud mahalliy fayllarni doimiy saqlashni kafolatlamaydi. Har muhim o‘zgarishdan keyin JSON zaxira oling. Server fayli yo‘qolsa, namuna baza qayta ochilishi mumkin; zaxiradan tiklang.
- Audit ilova orqali o‘zgarishlarni qayd etadi; server fayliga bevosita huquqi bor administratorga qarshi kriptografik buzilmas jurnal emas.
- Bu foydalanuvchi tekshiruvi jarayoni; raqamli imzo yoki zavod tizimlariga avtomatik integratsiya emas.
- Maxfiy patrul yo‘nalishlari, zaif joylar, kameralar joylashuvi va kirish kodlari kerak emas.
- Haqiqiy zavod ma’lumotini tashqi hostingga yuklashdan avval tashkilotning ichki talablari asosida joylashtirish muhitini tanlang.

## 12. Fayllar

| Fayl/papka | Vazifasi |
|---|---|
| app.py | O‘zbekcha Streamlit interfeysi |
| metrics.py | KPI kartalari va formulalar |
| database.py | SQLite, rollar, audit, hisobot nusxalari |
| imports.py | Excel/CSV o‘qish, ustun tekshiruvi va farqlar |
| reports.py | Excel va Unicode PDF eksport |
| auth.py | Parol xeshlash va tekshirish |
| templates/ | To‘ldirilgan, bo‘sh shablon va lug‘at |
| data/sample.db | Namuna baza |
| assets/ | PDF shrifti va litsenziyasi |
| tests/ | Formula, import, rollar, eksport va UI sinovlari |

## Rasmiy deployment ma’lumotlari

- https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
- https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies
- https://docs.streamlit.io/develop/concepts/connections/connecting-to-data
