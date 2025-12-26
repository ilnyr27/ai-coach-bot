# Быстрый деплой на Beget

## Шаг 1: Загрузка файлов

### Вариант A: Через FTP (FileZilla)
1. Скачай FileZilla: https://filezilla.ru/
2. Подключись к Beget:
   - Host: `ftp.beget.tech`
   - Username: твой логин Beget
   - Password: твой пароль
3. Загрузи `lichnosti_deploy.tar.gz` в домашнюю папку

### Вариант B: Через SSH (быстрее)
```bash
# На твоем компе
scp C:\Users\ilray\Claude\Lichnosti\lichnosti_deploy.tar.gz USERNAME@USERNAME.beget.tech:~/
```

---

## Шаг 2: SSH подключение

```bash
ssh USERNAME@USERNAME.beget.tech
```

Замени USERNAME на свой логин Beget.

---

## Шаг 3: Распаковка и настройка

```bash
# 1. Распаковать архив
mkdir -p ~/lichnosti
cd ~/lichnosti
tar -xzf ~/lichnosti_deploy.tar.gz

# 2. Проверить версию Python
python3 --version
# Должен быть Python 3.10+ (лучше 3.11 или 3.13)

# 3. Создать виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# 4. Обновить pip
pip install --upgrade pip

# 5. Установить зависимости
pip install -r requirements.txt

# 6. Создать .env файл
nano .env
```

**Вставь в .env (Shift+Insert):**
```
TELEGRAM_BOT_TOKEN=8471169770:AAEY2w9gGS1eh-x-XlVZlHuiulaf2wXgEgs
DEEPSEEK_API_KEY=sk-fafd2548b0e74dec951e77a7197a085a
DATABASE_URL=postgresql://postgres:Pofudu92pofudu92@db.fpackkversmdotxrsscv.supabase.co:5432/postgres?sslmode=require&connect_timeout=3
```

Сохрани: `Ctrl+X`, `Y`, `Enter`

```bash
# 7. Создать папки
mkdir -p logs
mkdir -p data/chroma_db

# 8. Сделать скрипт исполняемым
chmod +x start_bot.sh

# 9. Обновить пути в start_bot.sh
nano start_bot.sh
```

Замени пути на свои (твой домашний каталог).

---

## Шаг 4: Тестовый запуск

```bash
# Запустить бота вручную
./start_bot.sh
```

**Должно появиться:**
```
✅ Bot components initialized!
✅ Scheduler started with bot integration
✅ Bot is running!
```

Тестируй в Telegram! Если работает - останови: `Ctrl+C`

---

## Шаг 5: Настройка автозапуска (supervisor)

```bash
# 1. Проверить есть ли supervisor
ls ~/.supervisor/conf.d/

# Если папки нет - создать
mkdir -p ~/.supervisor/conf.d/

# 2. Отредактировать конфиг
nano supervisor_bot.conf
```

**Замени USERNAME на свой логин везде!**

```bash
# 3. Скопировать конфиг
cp supervisor_bot.conf ~/.supervisor/conf.d/ai_coach_bot.conf

# 4. Перезагрузить supervisor
supervisorctl reread
supervisorctl update
supervisorctl start ai_coach_bot

# 5. Проверить статус
supervisorctl status
```

Должно быть: `ai_coach_bot RUNNING`

---

## Шаг 6: Проверка логов

```bash
# Смотреть логи в реальном времени
tail -f ~/lichnosti/logs/bot.out.log

# Или ошибки
tail -f ~/lichnosti/logs/bot.err.log
```

---

## Полезные команды

```bash
# Остановить бота
supervisorctl stop ai_coach_bot

# Запустить
supervisorctl start ai_coach_bot

# Перезапустить
supervisorctl restart ai_coach_bot

# Обновить код (если что-то изменил)
cd ~/lichnosti
source venv/bin/activate
git pull  # если используешь git
pip install -r requirements.txt
supervisorctl restart ai_coach_bot
```

---

## Если что-то не работает

### Проблема: Python 3.13 нет на Beget
**Решение:** Используй Python 3.11
```bash
python3.11 -m venv venv
```

### Проблема: pip не устанавливает пакеты
**Решение:** Обнови pip и setuptools
```bash
pip install --upgrade pip setuptools wheel
```

### Проблема: ChromaDB не устанавливается
**Решение:** Установи зависимости системы
```bash
# Обратись в поддержку Beget для установки:
# - gcc
# - python3-dev
```

### Проблема: Бот не отвечает
**Решение:** Проверь логи
```bash
tail -50 ~/lichnosti/logs/bot.err.log
```

---

## Готово! 🚀

Бот работает 24/7 на Beget с автоматическим перезапуском при сбоях.
