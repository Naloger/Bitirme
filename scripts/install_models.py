"""install_models.py
Downloads non-pip model data after packages are installed in the venv.
- Downloads stanza Turkish model
- Downloads NLTK corpora used by the lemmatizer (wordnet, omw, punkt)

Run this using the project's venv python:
  .\\venv\\Scripts\\python.exe scripts\\install_models.py
"""
import sys

errors = []

# stanza download
try:
    import stanza  # type: ignore[import-not-found]
    try:
        stanza.download('tr')
        print('stanza: downloaded tr model')
    except Exception as e:
        print('stanza: failed to download tr model:', e)
        errors.append(('stanza', str(e)))
except Exception as e:
    print('stanza not installed or import error:', e)
    errors.append(('stanza_import', str(e)))

# nltk downloads
try:
    import nltk  # type: ignore[import-not-found]
    for pkg in ('wordnet', 'omw-1.4', 'punkt'):
        try:
            nltk.download(pkg)
            print(f'nltk: downloaded {pkg}')
        except Exception as e:
            print(f'nltk: failed to download {pkg}:', e)
            errors.append(('nltk_'+pkg, str(e)))
except Exception as e:
    print('nltk not installed or import error:', e)
    errors.append(('nltk_import', str(e)))

if errors:
    print('\nCompleted with errors:')
    for k, v in errors:
        print('-', k, v)
    sys.exit(2)

print('\nAll model downloads completed successfully')

