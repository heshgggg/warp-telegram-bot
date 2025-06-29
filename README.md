# Run bot
Install requirements
```bash
sudo apt install wireguard-tools python3 python3-pip && git clone https://github.com/heshgggg/warp-telegram-bot && cd warp-telegram-bot && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```
Create an `.env` file, then add a variable there with the bot token `TELEGRAM_BOT_TOKEN=<TOKEN>`
Afterwards you can launch the bot with the command
```bash
python3 bot.py
```
