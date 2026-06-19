from datetime import datetime
def log(message, level="info", system="unknown"):
    """Логирует сообщение с определенным уровнем"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}][{system}][{level.upper()}] {message}")