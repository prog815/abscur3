"""
Конфигурационный файл валютных пар для проекта AbsCur3.
Список всех 141 пары, доступной через Twelve Data API.
"""

CURRENCY_PAIRS = [
    # Format: (symbol, currency_group, currency_base, currency_quote)
    ("AFN/USD", "Minor", "Afghanistan Afghani", "US Dollar"),
    ("AUD/CAD", "Minor", "Australian Dollar", "Canadian Dollar"),
    ("AUD/CHF", "Minor", "Australian Dollar", "Swiss Franc"),
    ("AUD/EUR", "Minor", "Australian Dollar", "Euro"),
    ("AUD/GBP", "Minor", "Australian Dollar", "British Pound"),
    ("AUD/JPY", "Minor", "Australian Dollar", "Japanese Yen"),
    ("AUD/NZD", "Minor", "Australian Dollar", "New Zealand Dollar"),
    ("AUD/USD", "Major", "Australian Dollar", "US Dollar"),
    ("AZN/RUB", "Minor", "Azerbaijani Manat", "Russian Ruble"),
    ("BGN/RUB", "Minor", "Bulgarian Lev", "Russian Ruble"),
    ("BHD/INR", "Minor", "Baharain Dinar", "Indian Rupee"),
    ("BMD/USD", "Major", "Bermudian Dollar", "US Dollar"),
    ("BYN/USD", "Minor", "Belarusian Ruble", "US Dollar"),
    ("CAD/AUD", "Minor", "Canadian Dollar", "Australian Dollar"),
    ("CAD/CHF", "Minor", "Canadian Dollar", "Swiss Franc"),
    ("CAD/COP", "Minor", "Canadian Dollar", "Colombian Peso"),
    ("CAD/EUR", "Minor", "Canadian Dollar", "Euro"),
    ("CAD/GBP", "Minor", "Canadian Dollar", "British Pound"),
    ("CAD/JPY", "Minor", "Canadian Dollar", "Japanese Yen"),
    ("CAD/NZD", "Minor", "Canadian Dollar", "New Zealand Dollar"),
    ("CAD/USD", "Major", "Canadian Dollar", "US Dollar"),
    ("CHF/AUD", "Minor", "Swiss Franc", "Australian Dollar"),
    ("CHF/CAD", "Minor", "Swiss Franc", "Canadian Dollar"),
    ("CHF/EUR", "Minor", "Swiss Franc", "Euro"),
    ("CHF/GBP", "Minor", "Swiss Franc", "British Pound"),
    ("CHF/JPY", "Minor", "Swiss Franc", "Japanese Yen"),
    ("CHF/NZD", "Minor", "Swiss Franc", "New Zealand Dollar"),
    ("CHF/USD", "Major", "Swiss Franc", "US Dollar"),
    ("CNY/CNH", "Minor", "Chinese Yuan", "Chinese Yuan (Offshore)"),
    ("CNY/MNT", "Minor", "Chinese Yuan", "Mongolian Tugrik"),
    ("CZK/PLN", "Minor", "Czech Koruna", "Polish Zloty"),
    ("CZK/USD", "Minor", "Czech Koruna", "US Dollar"),
    ("EUR/AMD", "Minor", "Euro", "Armenian Dram"),
    ("EUR/AOA", "Minor", "Euro", "Angolan kwanza"),
    ("EUR/AUD", "Minor", "Euro", "Australian Dollar"),
    ("EUR/CAD", "Minor", "Euro", "Canadian Dollar"),
    ("EUR/CHF", "Minor", "Euro", "Swiss Franc"),
    ("EUR/GBP", "Minor", "Euro", "British Pound"),
    ("EUR/GEL", "Minor", "Euro", "Georgian lari"),
    ("EUR/JPY", "Minor", "Euro", "Japanese Yen"),
    ("EUR/NZD", "Minor", "Euro", "New Zealand Dollar"),
    ("EUR/TJS", "Minor", "Euro", "Tajikistani somoni"),
    ("EUR/USD", "Major", "Euro", "US Dollar"),
    ("FKP/USD", "Major", "Falkland Islands Pound", "US Dollar"),
    ("GBP/AUD", "Minor", "British Pound", "Australian Dollar"),
    ("GBP/CAD", "Minor", "British Pound", "Canadian Dollar"),
    ("GBP/CHF", "Minor", "British Pound", "Swiss Franc"),
    ("GBP/EUR", "Minor", "British Pound", "Euro"),
    ("GBP/JPY", "Minor", "British Pound", "Japanese Yen"),
    ("GBP/NPR", "Minor", "British Pound", "Nepalese Rupee"),
    ("GBP/NZD", "Minor", "British Pound", "New Zealand Dollar"),
    ("GBP/USD", "Major", "British Pound", "US Dollar"),
    ("GEL/RUB", "Minor", "Georgian lari", "Russian Ruble"),
    ("GIP/USD", "Major", "Gibraltar Pound", "US Dollar"),
    ("HUF/EUR", "Minor", "Hungarian Forint", "Euro"),
    ("HUF/USD", "Minor", "Hungarian Forint", "US Dollar"),
    ("IDR/AUD", "Minor", "Indonesian Rupiah", "Australian Dollar"),
    ("IDR/CHF", "Minor", "Indonesian Rupiah", "Swiss Franc"),
    ("IDR/EUR", "Minor", "Indonesian Rupiah", "Euro"),
    ("IDR/GBP", "Minor", "Indonesian Rupiah", "British Pound"),
    ("IDR/USD", "Minor", "Indonesian Rupiah", "US Dollar"),
    ("ILS/BGN", "Minor", "Israeli Shekel", "Bulgarian Lev"),
    ("ILS/COP", "Minor", "Israeli Shekel", "Colombian Peso"),
    ("ILS/PEN", "Minor", "Israeli Shekel", "Peru Sol"),
    ("ILS/UAH", "Minor", "Israeli Shekel", "Ukrainian Hryvnia"),
    ("ILS/UYU", "Minor", "Israeli Shekel", "Uruguayan Peso"),
    ("INR/BRL", "Minor", "Indian Rupee", "Brazil Real"),
    ("IQD/USD", "Minor", "Iraqi Dinar", "US Dollar"),
    ("IRR/USD", "Minor", "Iranian Rial", "US Dollar"),
    ("JOD/EUR", "Minor", "Jordan Dinar", "Euro"),
    ("JOD/GBP", "Minor", "Jordan Dinar", "British Pound"),
    ("JOD/USD", "Minor", "Jordan Dinar", "US Dollar"),
    ("JPY/AUD", "Minor", "Japanese Yen", "Australian Dollar"),
    ("JPY/CAD", "Minor", "Japanese Yen", "Canadian Dollar"),
    ("JPY/CHF", "Minor", "Japanese Yen", "Swiss Franc"),
    ("JPY/EUR", "Minor", "Japanese Yen", "Euro"),
    ("JPY/GBP", "Minor", "Japanese Yen", "British Pound"),
    ("JPY/NZD", "Minor", "Japanese Yen", "New Zealand Dollar"),
    ("JPY/TRY", "Minor", "Japanese Yen", "Turkish Lira"),
    ("JPY/USD", "Major", "Japanese Yen", "US Dollar"),
    ("KGS/RUB", "Minor", "Kyrgyzstan som", "Russian Ruble"),
    ("KWD/EUR", "Minor", "Kuwaiti Dinar", "Euro"),
    ("KWD/MYR", "Minor", "Kuwaiti Dinar", "Malaysian Ringgit"),
    ("KWD/SGD", "Minor", "Kuwaiti Dinar", "Singapore Dollar"),
    ("KWD/USD", "Minor", "Kuwaiti Dinar", "US Dollar"),
    ("MDL/RUB", "Minor", "Moldovan Leu", "Russian Ruble"),
    ("MYR/USD", "Minor", "Malaysian Ringgit", "US Dollar"),
    ("NZD/AUD", "Minor", "New Zealand Dollar", "Australian Dollar"),
    ("NZD/CAD", "Minor", "New Zealand Dollar", "Canadian Dollar"),
    ("NZD/CHF", "Minor", "New Zealand Dollar", "Swiss Franc"),
    ("NZD/EUR", "Minor", "New Zealand Dollar", "Euro"),
    ("NZD/GBP", "Minor", "New Zealand Dollar", "British Pound"),
    ("NZD/JPY", "Minor", "New Zealand Dollar", "Japanese Yen"),
    ("NZD/USD", "Major", "New Zealand Dollar", "US Dollar"),
    ("PHP/USD", "Minor", "Philippine Peso", "US Dollar"),
    ("PLN/UAH", "Minor", "Polish Zloty", "Ukrainian Hryvnia"),
    ("RUB/AMD", "Minor", "Russian Ruble", "Armenian Dram"),
    ("RUB/BRL", "Minor", "Russian Ruble", "Brazil Real"),
    ("RUB/VND", "Minor", "Russian Ruble", "Vietnamese Dong"),
    ("SDR/RUB", "Minor", "Special Drawing Rights", "Russian Ruble"),
    ("SDR/TRY", "Minor", "Special Drawing Rights", "Turkish Lira"),
    ("SGD/KWD", "Minor", "Singapore Dollar", "Kuwaiti Dinar"),
    ("SHP/USD", "Major", "Saint Helena Pound", "US Dollar"),
    ("SYP/USD", "Minor", "Syrian Pound", "US Dollar"),
    ("THB/GBP", "Minor", "Thai Baht", "British Pound"),
    ("THB/USD", "Minor", "Thai Baht", "US Dollar"),
    ("TJS/RUB", "Minor", "Tajikistani somoni", "Russian Ruble"),
    ("TRY/UAH", "Minor", "Turkish Lira", "Ukrainian Hryvnia"),
    ("UAH/KZT", "Minor", "Ukrainian Hryvnia", "Kazakh Tenge"),
    ("UAH/PLN", "Minor", "Ukrainian Hryvnia", "Polish Zloty"),
    ("UAH/USD", "Minor", "Ukrainian Hryvnia", "US Dollar"),
    ("USD/AFN", "Minor", "US Dollar", "Afghanistan Afghani"),
    ("USD/AOA", "Minor", "US Dollar", "Angolan kwanza"),
    ("USD/AUD", "Major", "US Dollar", "Australian Dollar"),
    ("USD/AWG", "Major", "US Dollar", "Aruban Florin"),
    ("USD/BTN", "Major", "US Dollar", "Bhutanese Ngultrum"),
    ("USD/CAD", "Major", "US Dollar", "Canadian Dollar"),
    ("USD/CDF", "Major", "US Dollar", "Congolese Franc"),
    ("USD/CHF", "Major", "US Dollar", "Swiss Franc"),
    ("USD/CVE", "Major", "US Dollar", "Cape Verdean Escudo"),
    ("USD/EUR", "Major", "US Dollar", "Euro"),
    ("USD/GBP", "Major", "US Dollar", "British Pound"),
    ("USD/GYD", "Major", "US Dollar", "Guyanese Dollar"),
    ("USD/JPY", "Major", "US Dollar", "Japanese Yen"),
    ("USD/LRD", "Major", "US Dollar", "Liberian Dollar"),
    ("USD/MNT", "Minor", "US Dollar", "Mongolian Tugrik"),
    ("USD/MRU", "Major", "US Dollar", "Mauritanian Ouguiya"),
    ("USD/NZD", "Major", "US Dollar", "New Zealand Dollar"),
    ("USD/RUB", "Minor", "US Dollar", "Russian Ruble"),
    ("USD/SBD", "Major", "US Dollar", "Solomon Islands Dollar"),
    ("USD/SLE", "Major", "US Dollar", "Sierra Leonean Leone"),
    ("USD/SRD", "Major", "US Dollar", "Surinamese Dollar"),
    ("USD/STN", "Major", "US Dollar", "São Tomé and Príncipe Dobra"),
    ("USD/TJS", "Minor", "US Dollar", "Tajikistani somoni"),
    ("USD/TMT", "Minor", "US Dollar", "Turkmenistan manat"),
    ("USD/TOP", "Major", "US Dollar", "Tongan Pa'anga"),
    ("USD/VES", "Major", "US Dollar", "Venezuelan Bolívar Soberano"),
    ("USD/WST", "Major", "US Dollar", "Samoan Tala"),
    ("VND/USD", "Minor", "Vietnamese Dong", "US Dollar"),
    ("XDR/USD", "Major", "Special Drawing Rights", "US Dollar"),
]

# Утилитарные функции для работы со списком пар
def get_all_symbols():
    """Возвращает список всех символов (пар)"""
    return [pair[0] for pair in CURRENCY_PAIRS]

def get_symbols_by_group(group):
    """Возвращает символы по группе (Major/Minor)"""
    return [pair[0] for pair in CURRENCY_PAIRS if pair[1] == group]

def get_major_pairs():
    """Возвращает список мажорных пар"""
    return get_symbols_by_group("Major")

def get_minor_pairs():
    """Возвращает список минорных пар"""
    return get_symbols_by_group("Minor")

def get_pair_info(symbol):
    """Возвращает информацию о конкретной паре"""
    for pair in CURRENCY_PAIRS:
        if pair[0] == symbol:
            return {
                "symbol": pair[0],
                "currency_group": pair[1],
                "currency_base": pair[2],
                "currency_quote": pair[3]
            }
    return None

# Дополнительные константы для удобства
MAJOR_PAIRS = get_major_pairs()
MINOR_PAIRS = get_minor_pairs()
ALL_SYMBOLS = get_all_symbols()

if __name__ == "__main__":
    # Тестовая проверка
    print(f"Всего пар: {len(ALL_SYMBOLS)}")
    print(f"Мажорных пар: {len(MAJOR_PAIRS)}")
    print(f"Минорных пар: {len(MINOR_PAIRS)}")
    print(f"\nПример информации по USD/RUB: {get_pair_info('USD/RUB')}")