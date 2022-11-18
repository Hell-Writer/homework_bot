class SendMessageError(Exception):
    """Проблема с отправкой сообщения в телеграмм."""

    pass


class ApiError(Exception):
    """Проблема с доступом или данными из API."""

    pass
