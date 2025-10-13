import os
from single import RaiParser

SCRIPT_PATH = os.path.abspath("scripts/single.py")
PROGRAMS = {
    "ilruggitodelconiglio": "https://www.raiplaysound.it/programmi/ilruggitodelconiglio"
}
for name, url in PROGRAMS.items():
    print(f"Generazione feed per {name}...")
    try:
        rai_parser = RaiParser(url, ".")
        rai_parser.process()
        original_file = f"{name}.xml"
        if not os.path.exists(original_file):
            print(f"Errore: Il file {original_file} non è stato generato correttamente!")
            continue
        new_file = f"feed_{name}.xml"
        os.rename(original_file, new_file)
        print(f"Feed XML salvato correttamente: {new_file}")
    except Exception as e:
        print(f"Errore generico per {name}: {e}")
