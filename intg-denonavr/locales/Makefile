LOCALES = de fr en
PO_FILES = $(foreach loc,$(LOCALES),$(loc)/LC_MESSAGES/intg-denonavr.po)
MO_FILES = $(PO_FILES:.po=.mo)

all: $(MO_FILES)

%.mo: %.po
	msgfmt -o $@ $<

update_po:
	xgettext -d intg-denonavr -o intg-denonavr2.pot --from-code=UTF-8 --language=Python --keyword=_ --keyword=_n:1,2 --keyword=__ --keyword=_a --copyright-holder="Unfolded Circle ApS" --package-name "Denon AVR Integration" ../*.py
	$(foreach po,$(PO_FILES),msgmerge --update $(po) intg-denonavr2.pot;)

clean:
	rm -f */*/*.mo

.PHONY: all update_po clean
