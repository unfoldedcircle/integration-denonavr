# Internationalization (i18n) for Denon AVR Integration

This directory contains translation files for the Denon AVR integration. The integration uses the Python [gettext](https://docs.python.org/3.11/library/gettext.html)
module for internationalization.

## Directory Structure

The locales directory is organized as follows:

```
locales/
├── en/
│   └── LC_MESSAGES/
│       └── intg-denonavr.po
├── de/
│   └── LC_MESSAGES/
│       └── intg-denonavr.po
├── fr/
│   └── LC_MESSAGES/
│       └── intg-denonavr.po
└── intg-denonavr.pot
```

- `intg-denonavr.pot`: The template file containing all translatable strings
- `<language>/LC_MESSAGES/intg-denonavr.po`: Translation files for each supported language

## Working with Translations

‼️ The translated texts in the setup-flow are not single texts in a specific language, but dictionaries with all
   available languages! 

Most language texts must be included as key value pairs. Example:

```json
{
  "label": {
    "en": "Good morning",
    "fr": "Bonjour",
    "de": "Guten Morgen"
  }
}
```

See the [Integration-API](https://github.com/unfoldedcircle/core-api/tree/main/integration-api) for more information.

To support these multi-language translations without too much boilerplate code, new shorthand functions are defined
in [setup_flow.py](../setup_flow.py) which complement the common `_` translation function:

- `_a`: create a translation dictionary for all available languages (instead a single translation with `_`).
- `_am`: same as `_a` but for longer texts concatenated by multiple message ids.
- `__`: passthrough function without translation, only for text extraction with `xgettext` and `_am` helper.

See "Usage in Code" below on how to use these functions.

This might change in the future and can be easily adapted when necessary with the defined shorthand functions:
replace the custom `_a` and `_am` functions with the common `_` translation function.

### Extracting Strings

To extract translatable strings from the source code, you can use the `xgettext` tool:

```shell
xgettext -d intg-denonavr -o intg-denonavr/locales/intg-denonavr.pot --from-code=UTF-8 --language=Python \
    --keyword=_ --keyword=_n:1,2 --keyword=__ --keyword=_a \
    --copyright-holder="Unfolded Circle ApS" --package-name "uc-integration-denon-avr" \
    intg-denonavr/*.py
```

### Creating or Updating Translation Files

To create or update translation files for a specific language:

```shell
# For new language
msginit -i locales/intg-denonavr.pot -o locales/<language>/LC_MESSAGES/intg-denonavr.po -l <language>

# For updating existing language
msgmerge -U locales/<language>/LC_MESSAGES/intg-denonavr.po locales/intg-denonavr.pot
```

### Compiling Translation Files

To compile the .po files into binary .mo files that can be used by the application:

```shell
msgfmt locales/<language>/LC_MESSAGES/intg-denonavr.po -o locales/<language>/LC_MESSAGES/intg-denonavr.mo
```

## Crowdin Integration

This i18n setup is compatible with Crowdin. You can:

1. Upload the `intg-denonavr.pot` file to Crowdin as the source file
2. Download the translated .po files from Crowdin and place them in the appropriate language directories
3. Compile the .po files to .mo files as described above

## Usage in Code

In Python code, use the i18n module as follows:

```python
from i18n import _, _n, _a, _am, __

# Simple translation
print(_("Hello, world!"))

# Pluralization
count = 5
print(_n("Found %d item", "Found %d items", count) % count)

# For setup-flow messages that expect a dictionary with language codes
setup_text = _a("Setup mode")

# For longer setup-flow messages consisting of multiple messages
long_setup_text = _am(
   __("Leave blank to use auto-discovery and click _Next_."),
   "\n\n",
   __("The device must be on the same network as the remote."),
)
```

# Resources

- https://docs.python.org/3.11/library/gettext.html
- https://crowdin.com/blog/2022/09/28/python-app-translation-tutorial
- https://phrase.com/blog/posts/translate-python-gnu-gettext/
- https://phrase.com/blog/posts/learn-gettext-tools-internationalization/
- https://lokalise.com/blog/beginners-guide-to-python-i18n/
