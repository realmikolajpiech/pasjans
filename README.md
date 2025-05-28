# Pasjans w Konsoli 🃏

Cześć! To mój projekt zaliczeniowy – klasyczna gra w Pasjansa, działająca w całości w konsoli. Starałem się, aby była funkcjonalna i możliwie estetyczna, jak na warunki terminalowe.

## Jak uruchomić?

Do uruchomienia gry potrzebny jest Python (projekt był tworzony i testowany na Pythonie 3.12.3)

1.  **Pobierz projekt:** Rozpakuj archiwum ZIP z projektem.
2.  **Zainstaluj biblioteki:**
    *   Upewnij się, że masz zainstalowany menedżer pakietów `pip`.
    *   Otwórz wiersz poleceń w katalogu, do którego rozpakowałeś projekt.
    *   Wykonaj komendę:
        ```bash
        pip install -r requirements.txt
        ```
        Spowoduje to instalację wszystkich wymaganych bibliotek, takich jak `rich` (do UI w konsoli) oraz `keyboard` (do obsługi sterowania).
3.  **Uruchom grę:**
    *   W tym samym terminalu, będąc w głównym katalogu projektu, wpisz:
        ```bash
        python pasjans.py
        ```
    *   (Jeśli główny plik skryptu ma inną nazwę, użyj tej właściwej nazwy).

Gra powinna się teraz uruchomić.

## Instrukcja Gry (Sterowanie)

Celem gry jest ułożenie wszystkich kart na czterech stosach końcowych (fundacjach), znajdujących się w prawym górnym rogu. Karty na stosach końcowych muszą być ułożone według koloru, w kolejności od Asa do Króla.

*   **Menu Główne:**
    *   `1` - Rozpocznij grę na poziomie **Łatwym** (dobieranie 1 karty ze stosu rezerwowego).
    *   `2` - Rozpocznij grę na poziomie **Trudnym** (dobieranie 3 kart, z możliwością użycia tylko wierzchniej).
    *   `ESC` - Wyjście z programu.
*   **Podczas Gry:**
    *   **Strzałki (← ↑ → ↓):** Nawigacja po planszy. Aktualnie wybrane karty lub miejsce docelowe są podświetlane.
        *   W kolumnach roboczych (tableau), strzałki `↑`/`↓` pozwalają na zaznaczenie sekwencji kart do przeniesienia (jeśli tworzą poprawny ciąg).
    *   **Enter:**
        *   *Pierwsze wciśnięcie:* Podnosi zaznaczoną kartę (lub sekwencję kart).
        *   *Drugie wciśnięcie:* Umieszcza podniesioną kartę/sekwencję w aktualnie wskazanym miejscu (jeśli ruch jest zgodny z zasadami gry).
    *   **Esc:**
        *   Jeśli karta/sekwencja jest "podniesiona", anuluje ten stan (karta wraca na pierwotne miejsce).
    *   **'s':** Dobiera kartę/karty ze stosu rezerwowego (stock pile).
    *   **'c':** Cofa ostatni wykonany ruch. Możliwe jest cofnięcie do 3 ostatnich ruchów (liczba dostępnych cofnięć jest wyświetlana).
    *   **Spacja:** Kończy bieżącą rozgrywkę i powraca do menu głównego. W przypadku wygranej również kończy grę.

### Podstawowe zasady przenoszenia kart:

*   **W kolumnach roboczych (tableau):**
    *   Karty układa się w porządku malejącym (np. 9 na 10, Dama na Króla).
    *   Kolory kart muszą być naprzemienne (np. czerwona na czarną, czarna na czerwoną).
    *   Można przenieść pojedynczą odkrytą kartę lub całą, poprawnie ułożoną sekwencję odkrytych kart.
    *   Na puste miejsce w kolumnie roboczej można położyć tylko Króla (lub sekwencję zaczynającą się od Króla).
    *   Po przeniesieniu ostatniej odkrytej karty z kolumny, karta znajdująca się pod nią (jeśli istnieje) zostaje odkryta.
*   **Na stosy końcowe (fundacje):**
    *   Karty układa się w porządku rosnącym (od Asa do Króla).
    *   Każdy stos końcowy musi zawierać karty tylko jednego koloru (np. same Kiery).
    *   Pierwszą kartą na stosie końcowym musi być As.

## Struktura Projektu i Opis Komponentów

Projekt został zorganizowany w celu zachowania przejrzystości kodu, mimo jego relatywnie dużej objętości.

*   **Główne pliki:**
    *   `pasjans.py`: Zawiera implementację całej logiki gry, interfejsu użytkownika oraz obsługi interakcji z graczem.
    *   `scores.json`: Plik tekstowy w formacie JSON, przechowujący ranking najlepszych wyników. Jest tworzony automatycznie przy pierwszej wygranej, jeśli nie istnieje.
    *   `requirements.txt`: Plik definiujący zależności projektu, używany przez `pip` do instalacji wymaganych bibliotek.

*   **Klasy:**
    *   `Card`:
        *   Reprezentuje pojedynczą kartę do gry.
        *   Przechowuje informacje o wartości (`value`), kolorze (`suit`) oraz stanie (zakryta/odkryta - `hidden`).
        *   Udostępnia metody pomocnicze, takie jak `is_red()` (sprawdza, czy karta jest koloru czerwonego) oraz `get_raw_data()` (używane do serializacji stanu karty na potrzeby funkcji cofania ruchu).
    *   `Game`:
        *   Główna klasa zarządzająca całą rozgrywką.
        *   Odpowiada za przechowywanie stanu gry: pozycje kart (w kolumnach roboczych, stosie rezerwowym, stosach końcowych), aktualne zaznaczenie kursora, liczbę wykonanych ruchów itp.
        *   **Kluczowe metody (wybrane):**
            *   `__init__()`: Konstruktor klasy, inicjalizuje podstawowe atrybuty.
            *   `_initialize_game_state()`: Resetuje stan gry i przygotowuje nowe rozdanie (tasowanie talii, rozmieszczenie kart na planszy).
            *   `_display_main_menu()`: Wyświetla menu startowe z opcją wyboru poziomu trudności oraz rankingiem.
            *   `display_game()`: Główna funkcja odpowiedzialna za renderowanie całego interfejsu gry w konsoli, w tym planszy, kart i komunikatów. Wykorzystuje bibliotekę `rich`.
            *   `display_tableau()`, `display_reserve_and_final_stacks()`: Metody pomocnicze do rysowania poszczególnych obszarów planszy.
            *   `move_selection_horizontal()`, `extend_selection()`: Implementują logikę poruszania kursorem i zaznaczania kart na planszy.
            *   `confirm_selection()`: Jedna z najbardziej złożonych metod, obsługująca logikę podnoszenia i upuszczania kart, walidację ruchów oraz transfer kart między różnymi strefami planszy.
            *   `reveal_reserve_card()`: Implementuje mechanikę dobierania kart ze stosu rezerwowego, uwzględniając wybrany poziom trudności.
            *   `_can_place_on_final()`, `_check_win_condition()`: Metody walidujące warunki gry, np. możliwość umieszczenia karty na stosie końcowym lub sprawdzenie warunku zwycięstwa.
            *   `_save_state_for_undo()`, `_restore_state_from_undo()`, `undo_last_move()`: Implementacja mechanizmu cofania ostatnich ruchów.
            *   `run()`: Główna pętla gry, która odbiera dane wejściowe od gracza i inicjuje odpowiednie akcje w grze.

*   **Wykorzystane biblioteki (zgodnie z `requirements.txt`):**
    *   `random`: Do tasowania talii kart.
    *   `colorama`: Używana pomocniczo do kolorowania tekstu w konsoli (choć `rich` pełni tu główną rolę).
    *   `keyboard`: Umożliwia przechwytywanie wciśnięć klawiszy w czasie rzeczywistym, co poprawia responsywność sterowania.
    *   `os`: Do czyszczenia ekranu konsoli (polecenia `cls` dla Windows, `clear` dla Linux/macOS).
    *   `json`: Do serializacji i deserializacji danych rankingu (zapis i odczyt z pliku `scores.json`).
    *   `datetime`: Do zapisu daty i godziny osiągnięcia wyniku w rankingu.
    *   `pyfiglet`: Do generowania dużych, stylizowanych napisów tekstowych ASCII (użyte dla tytułu "PASJANS").
    *   `copy` (funkcja `deepcopy`): Kluczowa dla mechanizmu cofania ruchów, tworzy pełne, niezależne kopie stanu gry.
    *   `collections` (konkretnie `deque`): Używane do przechowywania historii ostatnich ruchów. `deque` z ograniczoną długością automatycznie usuwa najstarsze elementy przy dodawaniu nowych, co jest idealne dla tej funkcjonalności.
    *   `rich`: Podstawowa biblioteka do tworzenia rozbudowanego interfejsu użytkownika w konsoli, obsługuje kolory, style tekstu, panele, tabele i inne elementy wizualne.

Kod został napisany z myślą o czytelności, jednak niektóre funkcje odpowiedzialne za logikę ruchów mogą być rozbudowane ze względu na złożoność zasad gry w Pasjansa.

Życzę miłej gry!
