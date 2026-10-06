from enum import Enum


class CountryEnum(str, Enum):
    ARMENIA = "am"
    AZERBAIJAN = "az"
    BELARUS = "by"
    GEORGIA = "ge"
    KAZAKHSTAN = "kz"
    KYRGYZSTAN = "kg"
    MOLDOVA = "md"
    RUSSIA = "ru"
    TAJIKISTAN = "tj"
    TURKMENISTAN = "tm"
    UZBEKISTAN = "uz"
    UKRAINE = "ua"
    OTHER = "other"