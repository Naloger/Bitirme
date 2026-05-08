#!/usr/bin/env python
# -*- coding: utf-8 -*-
from support_lib.Lemmatizer.turkish_chars import TURKISH_DIACRITICS_MAP, extend_turkish_diacritics

print('Turkish Diacritics Dictionary')
print('=' * 50)
print(f'Dictionary size: {len(TURKISH_DIACRITICS_MAP)} words\n')

print('Sample entries:')
for k, v in list(TURKISH_DIACRITICS_MAP.items())[:10]:
    print(f'  {k:20} → {v}')

print('\n' + '=' * 50)
print('Testing extend_turkish_diacritics()...\n')

# Test extending the dictionary
custom_words = {
    'isik': 'ışık',
    'cadir': 'çadır',
    'seyahat': 'seyahat',
}

print(f'Before extend: {len(TURKISH_DIACRITICS_MAP)} words')
extend_turkish_diacritics(custom_words)
print(f'After extend: {len(TURKISH_DIACRITICS_MAP)} words')

print('\nNew entries:', custom_words)
print('\nVerification:')
for k in custom_words:
    print(f'  {k} → {TURKISH_DIACRITICS_MAP.get(k, "NOT FOUND")}')

