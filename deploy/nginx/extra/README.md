# Serverga xos qo'shimcha nginx yo'llari

Bu katalogdagi `*.conf` fayllari asosiy nginx'ning **443-server bloki
ichiga** qo'shiladi (`deploy/nginx/tls.conf` oxiridagi `include`).

Odatda katalog bo'sh bo'ladi va hech narsaga ta'sir qilmaydi.

**Nega mahsulot konfiguratsiyasidan tashqarida:** bu yerga yoziladigan
yo'llar faqat BITTA serverda mavjud bo'lgan konteynerlarga ishora
qiladi. Ularni `tls.conf` ga yozib qo'yish har bir mijoz o'rnatmasiga
o'sha serverda umuman mavjud bo'lmagan upstream'ga qaragan yo'lni
tarqatardi — va u `502` bilan tugardi.

## radix-crm.uz da nima bor

`private.conf` — `/private` dagi standalone demo nusxasiga proxy
(ADR-13, `compose.private-demo.yaml`). U git'da saqlanmaydi, chunki
faqat o'sha bitta serverga tegishli; namunasi `private.conf.example`
faylida.
