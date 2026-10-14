# Sentinel Agent

**Senin özel, gizli ve süper zeki self-hosted AI ajanın.**  
Ollama + multi-agent. Hiçbir ücretli API yok. Veri dışarı çıkmaz.

## Ne yapabilir?

- **Seninle konuşur** (Telegram + CLI) — telefon ve PC’den
- Seni tanır, tercihlerini ve projelerini hatırlar (kişisel hafıza)
- Kod incelemesi (gece de çalışır)
- Defensive güvenlik taraması (kod + website)
- Hata ayıklama
- İzin kontrollü kod yazma / düzeltme / push
- WhatsApp bildirimleri (CallMeBot)

## Hızlı Başlangıç

```bash
# 1. Bağımlılıklar
pip install -r requirements.txt

# 2. .env ayarla
cp .env.example .env
# Ollama modelini, Telegram token + user_id’yi doldur

# 3. Test
python -m scripts.run test

# 4. CLI’dan sohbet (PC)
python -m scripts.run chat

# 5. Telegram botu başlat (telefon + PC)
python -m scripts.run telegram
```

## Telegram Kurulumu (Önerilen — en güvenli & iki yönlü)

1. Telegram’da **@BotFather**’a git → `/newbot` → isim ver → **token** al
2. **@userinfobot**’a mesaj at → kendi **user_id**’ni al
3. `.env` dosyasına koy:

```env
TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_ALLOWED_USER_ID=123456789   # sadece sen
```

4. Çalıştır:
```bash
python -m scripts.run telegram
```

Bot **sadece senin user_id’ne** cevap verir. Başkası yazsa “Yetkisiz” der.

## WhatsApp Bildirimleri (sadece giden)

1. `+34 644 21 99 05` numarasını rehbere ekle
2. `I allow callmebot to send me messages` yaz
3. Gelen API key’i `.env`’e koy

## Komutlar

```bash
python -m scripts.run chat                     # interaktif sohbet
python -m scripts.run chat "Adım Ahmet"        # tek mesaj
python -m scripts.run telegram                 # Telegram bot
python -m scripts.run review myfile.py
python -m scripts.run repo https://github.com/you/project.git
python -m scripts.run debug "TypeError: ..." --file app.py
python -m scripts.run website https://yoursite.com
python -m scripts.run fix app.py "null check ekle"
python -m scripts.run schedule                 # gece görevleri
python -m scripts.run permissions
python -m scripts.run test
```

## Kişisel Hafıza

Sentinel konuştukça seni öğrenir:
- Adın, projelerin, tercihler
- Geçmiş konuşmalar (vektör hafıza)
- “Hatırla: ...” veya “Öğren: ...” diyerek manuel de ekleyebilirsin

Her şey `./memory/personal` klasöründe kalır. Buluta gitmez.

## İzin Modeli

Varsayılan:
- Okuma, rapor, sohbet → serbest
- Dosya yazma, commit, push → **senin açık onayın olmadan asla**

## Güvenlik

- Telegram’da sadece senin user_id’n geçerli
- Tüm LLM çağrıları local Ollama
- Veri sadece senin sunucunda / bilgisayarında
- Yazma işlemleri permission gate’li

## License

MIT
