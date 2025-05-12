import requests
import json
import random
import os

POKEDEX_FILE = "pokedex.json"

def load_pokedex(filename=POKEDEX_FILE):
    """טוען את נתוני הפוקימונים מקובץ ה-JSON."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if "pokemons" not in data or not isinstance(data["pokemons"], list):
                print(f"אזהרה: קובץ {filename} פגום, מאתחל מבנה.")
                return {"pokemons": []}
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"קובץ {filename} לא נמצא או אינו קובץ JSON תקין. יוצר מבנה חדש.")
        return {"pokemons": []}

def save_pokedex(data, filename=POKEDEX_FILE):
    """שומר את נתוני הפוקימונים לקובץ ה-JSON."""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_all_pokemon_names():
    """מוריד רשימה של שמות כל הפוקימונים הזמינים מה-API."""
    print("מוריד רשימת פוקימונים זמינים מה-API...")
    url = "https://pokeapi.co/api/v2/pokemon?limit=1000" # הגדלנו את ה-limit לקבלת יותר פוקימונים
    try:
        response = requests.get(url)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        return [p['name'] for p in data['results']]
    except requests.exceptions.RequestException as e:
        print(f"שגיאה בהורדת רשימת הפוקימונים: {e}")
        return [] # החזר רשימה ריקה במקרה של שגיאה

def get_pokemon_details_from_api(pokemon_name):
    """מוריד פרטים מלאים של פוקימון ספציפי מה-API."""
    url = f"https://pokeapi.co/api/v2/pokemon/{pokemon_name.lower()}/"
    print(f"מוריד פרטים עבור '{pokemon_name}' מה-API...")
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()

    # חילוץ השדות שבחרת: שם, ID, סוגים (types), גובה, משקל.
    types = [t['type']['name'] for t in data['types']]

    return {
        "name": data['name'],
        "id": data['id'],
        "types": types,
        "height": data['height'], # גובה בדצימטרים
        "weight": data['weight']  # משקל בהקטוגרמים
    }

def display_pokemon_details(pokemon_details, source="מקומי"):
    """מציג את פרטי הפוקימון למשתמש."""
    print(f"\n--- פרטי פוקימון ({source}) ---")
    print(f"שם: {pokemon_details['name'].capitalize()}")
    print(f"מזהה: {pokemon_details['id']}")
    print(f"סוגים: {', '.join(t.capitalize() for t in pokemon_details['types'])}")
    print(f"גובה: {pokemon_details['height']} דצימטרים")
    print(f"משקל: {pokemon_details['weight']} הקטוגרמים")
    print("---------------------------")

def main_app_logic():
    """הלוגיקה הראשית של אפליקציית הפוקימונים."""
    pokedex_data = load_pokedex()
    all_pokemon_names = get_all_pokemon_names()

    if not all_pokemon_names:
        print("לא ניתן להשיג רשימת פוקימונים. אנא בדוק את חיבור האינטרנט ונסה שוב.")
        return

    while True:
        user_input = input("\nהאם תרצה לצייר פוקימון? (כן/לא): ").lower()

        if user_input == "כן":
            chosen_pokemon_name = random.choice(all_pokemon_names)

            found_pokemon = None
            for p in pokedex_data['pokemons']:
                if p['name'] == chosen_pokemon_name:
                    found_pokemon = p
                    break

            if found_pokemon:
                display_pokemon_details(found_pokemon, source="האוסף המקומי")
            else:
                try:
                    new_pokemon_details = get_pokemon_details_from_api(chosen_pokemon_name)
                    pokedex_data['pokemons'].append(new_pokemon_details)
                    save_pokedex(pokedex_data)
                    display_pokemon_details(new_pokemon_details, source="חדש - נשמר באוסף")
                except requests.exceptions.RequestException as e:
                    print(f"שגיאה בהורדת פרטי הפוקימון: {e}")
                except Exception as e:
                    print(f"אירעה שגיאה בלתי צפויה: {e}")

        elif user_input == "לא":
            print("להתראות! תודה ששיחקתם!")
            break
        else:
            print("קלט לא חוקי. אנא הקלד 'כן' או 'לא'.")

if __name__ == "__main__":
    main_app_logic()