# Slaydify-uslubidagi Telegram bot

Hozir ishlaydi: **Taqdimot yaratish** (mavzu → slaydlar soni → til → dizayn → .pptx), hisob, referal, ishlar tarixi, admin buyruqlari.
Qolgan bo'limlar (animatsion slayd, test, referat, mustaqil ish) keyingi qadamda qo'shiladi.

## Ishga tushirish
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # BOT_TOKEN va AI kalitini yozing
python bot.py
```

## Bepul AI kalit
- Gemini: https://aistudio.google.com/apikey  → `AI_PROVIDER=gemini`
- Groq: https://console.groq.com/keys → `AI_PROVIDER=groq`
- Claude (eng yaxshi sifat, pullik): `AI_PROVIDER=claude`

## Admin buyruqlari (ADMIN_IDS ga o'z ID'ingizni yozing)
`/stats`, `/addcredit <id> <soni>`, `/broadcast <matn>`

## 24/7 ishlatish: Oracle Cloud (bepul) + GitHub Actions avtomatik deploy

`git push` qilsangiz, GitHub Actions kodni serverga yuboradi va botni o'zi qayta ishga tushiradi.
Bot polling rejimida ishlaydi, shuning uchun serverda port ochish shart emas.

### 1. Oracle serverini olish
1. https://cloud.oracle.com da ro'yxatdan o'ting (karta tekshiruv uchun so'raladi).
2. Compute → Instances → Create instance. Image: **Ubuntu 22.04**, Shape: **VM.Standard.E2.1.Micro** (Always Free) yoki Ampere A1.
3. SSH kalitni yarating (Oracle taklif qiladi) va **private key** faylini saqlab qo'ying.
4. Instance ishga tushgach, **Public IP** ni yozib oling.

### 2. Serverni bir martalik sozlash
```bash
ssh -i oracle.key ubuntu@SERVER_IP
# kodni yuklab, skriptni ishga tushiring (yoki skript matnini nano bilan yarating)
bash setup_server.sh
nano ~/slaydify-bot/.env     # BOT_TOKEN va AI kalitni yozing
```
Skript Python muhiti, `.env` shabloni va `slaydify` systemd xizmatini (o'chsa o'zi qayta yonadi) yaratadi.

### 3. GitHub sozlash
Repo → Settings → Secrets and variables → Actions → New repository secret:

| Secret | Qiymati |
|---|---|
| `SSH_HOST` | Serverning public IP si |
| `SSH_USER` | `ubuntu` |
| `SSH_KEY` | private key fayl matni (BEGIN... dan END... gacha to'liq) |
| `SSH_PORT` | ixtiyoriy, odatda 22 |

### 4. Deploy
```bash
git init && git add . && git commit -m "bot"
git branch -M main
git remote add origin https://github.com/SIZNING_NOM/slaydify-bot.git
git push -u origin main
```
Repo'dagi **Actions** bo'limida deploy jarayonini ko'rasiz. Keyin har `git push` botni yangilaydi.
**Repo'ni Private qiling.** `.env` GitHub'ga chiqmaydi (`.gitignore` da), kalitlar faqat serverda turadi.

### Foydali buyruqlar (serverda)
```bash
sudo systemctl status slaydify      # holati
sudo journalctl -u slaydify -f      # jonli loglar
sudo systemctl restart slaydify     # qayta ishga tushirish
```
