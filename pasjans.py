import random
from colorama import Fore, Style
import keyboard
import os
import json
from datetime import datetime
from pyfiglet import Figlet
import copy
from collections import deque
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.table import Table

# Pojedyncza karta do gry
class Card:
    def __init__(self, value, suit, hidden=False):
        self.value = value
        self.suit = suit
        self.hidden = hidden

    def __repr__(self):
        return f"Card({self.value}{self.suit}{'H' if self.hidden else ''})"

    def is_red(self):
        return self.suit in "♥♦"
    
    # Zwraca surowe dane karty do zapisu stanu
    def get_raw_data(self):
        return [self.value, self.suit, self.hidden]

# Główna klasa zarządzająca logiką i stanem gry
class Game:
    VALUES = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
    SUITS = ["♠", "♥", "♦", "♣"]
    SCORES_FILE = "scores.json"
    CARD_WIDTH = 7
    CARD_HEIGHT = 5
    DRAW3_PARTIAL_WIDTH = 4
    MAX_UNDO_HISTORY = 3
    LEADERBOARD_TOP_N = 5

    # Inicjalizuje stan gry
    def __init__(self):
        self.deck_source_data = []
        self.tableau = [[] for _ in range(7)]
        self.reserve_stock = []
        self.waste_pile_draw1 = []
        self.waste_pile_draw3 = []
        self.visible_draw3_cards = [None, None, None]
        self.final_stacks = [[] for _ in range(4)]
        self.current_reserve_card_obj = None
        self.selected_cards_coords = []
        self.confirmed_selection = False
        self.original_selected_coords = []
        self.message = ""
        self.moving_final_card_obj = None
        self.move_count = 0
        self.game_over = False
        self.difficulty = None
        self.first_reveal_done = False
        self.game_state_history = deque(maxlen=self.MAX_UNDO_HISTORY)
        self.undo_actions_available = 0
        self.rich_console = Console()

    # Wyświetla tabelę najlepszych wyników
    def _display_leaderboard(self, new_score_timestamp=None):
        scores = []
        if os.path.exists(self.SCORES_FILE):
            try:
                with open(self.SCORES_FILE, 'r') as f:
                    scores = json.load(f)
                if not isinstance(scores, list):
                    scores = []
            except json.JSONDecodeError:
                scores = []

        if not scores:
            print("")
            self.rich_console.print(Panel(Text("Brak zapisanych wyników. Wygraj, aby się tu pojawić!", justify="center"), title="[dim]Tabela wyników[/dim]", border_style="dim white"))
            return False

        def sort_key(score):
            difficulty_order = {'trudny': 0, 'łatwy': 1}
            return (score.get('moves', float('inf')), difficulty_order.get(score.get('difficulty', 'łatwy'), 1))

        scores.sort(key=sort_key)

        table = Table(title=f"\n[bold yellow]Najlepsze wyniki (TOP {self.LEADERBOARD_TOP_N})[/bold yellow]", show_header=True, header_style="bold magenta", title_justify="left")
        table.add_column("Miejsce", style="dim", width=7, justify="center")
        table.add_column("Ruchy", justify="center", style="cyan")
        table.add_column("Trudność", justify="center")
        table.add_column("Data", style="green", justify="center")

        is_new_score_on_top = False
        new_score_rank = -1

        for i, score in enumerate(scores[:self.LEADERBOARD_TOP_N]):
            rank = str(i + 1)
            moves = str(score.get('moves', 'N/A'))
            difficulty_val = score.get('difficulty', 'N/A').capitalize()
            timestamp = score.get('timestamp', 'N/A')
            
            row_style = ""
            if new_score_timestamp and timestamp == new_score_timestamp:
                row_style = "bold yellow on dark_blue"
                if i == 0:
                    is_new_score_on_top = True
                new_score_rank = i + 1

            difficulty_style = "green" if difficulty_val == "łatwy" else "red"
            
            table.add_row(
                Text(rank, style=row_style),
                Text(moves, style=row_style),
                Text(difficulty_val, style=f"{difficulty_style} {row_style.split(' on ')[0]}" if row_style else difficulty_style),
                Text(timestamp, style=row_style)
            )
        
        self.rich_console.print(table)

        if new_score_timestamp:
            if is_new_score_on_top:
                self.rich_console.print(Panel("[bold green]🎉 Niesamowite! Nowy najlepszy wynik! Gratulacje! 🎉[/bold green]", title="[bold yellow]REKORD![/bold yellow]", border_style="yellow"))
            elif new_score_rank != -1 and new_score_rank <= self.LEADERBOARD_TOP_N:
                self.rich_console.print(Panel(f"[bold blue]Świetna gra! Twój wynik znalazł się na {new_score_rank}. miejscu w TOP {self.LEADERBOARD_TOP_N}![/bold blue]", title="[bold cyan]Gratulacje![/bold cyan]", border_style="cyan"))
        return True

    # Wyświetla menu główne i obsługuje wybór poziomu trudności
    def _display_main_menu(self):
        f = Figlet(font='slant')
        os.system('cls' if os.name == 'nt' else 'clear')
        self.rich_console.print(Text("===============================================", style="bold green"))
        self.rich_console.print(Text(f.renderText('PASJANS'), style="bold green"), end="")
        self.rich_console.print(Text("===============================================", style="bold green"))

        self.rich_console.print("\n[bold cyan]Witaj w grze Pasjans.[/bold cyan]")

        self.rich_console.print("\n[bold]Wybierz poziom trudności:[/bold]")
        self.rich_console.print("  [magenta]1.[/magenta] Łatwy (dobieranie 1 karty)")
        self.rich_console.print("  [magenta]2.[/magenta] Trudny (dobieranie 3 kart, używasz wierzchniej)")

        self._display_leaderboard()

        self.rich_console.print("\n[yellow]ESC[/yellow] - Wyjście")
        
        while True:
            choice = keyboard.read_key(suppress=True)
            os.system('cls' if os.name == 'nt' else 'clear')
            if choice == '1':
                self.difficulty = 'łatwy'
                break
            elif choice == '2':
                self.difficulty = 'trudny'
                break
            elif choice.lower() == 'esc':
                self.rich_console.print("\n[bold blue]Do zobaczenia![/bold blue]")
                exit()
            
            self.rich_console.print(Text("===============================================", style="bold green"))
            self.rich_console.print(Text(f.renderText('PASJANS'), style="bold green"), end="")
            self.rich_console.print(Text("===============================================", style="bold green"))
            self._display_leaderboard()
            self.rich_console.print("\n[bold cyan]Witaj w grze Pasjans.[/bold cyan]")
            self.rich_console.print("\n[bold]Wybierz poziom trudności:[/bold]")
            self.rich_console.print("  [magenta]1.[/magenta] Łatwy (dobieranie 1 karty)")
            self.rich_console.print("  [magenta]2.[/magenta] Trudny (dobieranie 3 kart, używasz wierzchniej)")
            self.rich_console.print("\n[yellow]ESC[/yellow] - Wyjście")
            self.rich_console.print(Panel("[bold red]Nieprawidłowy wybór, spróbuj ponownie.[/bold red]", border_style="red"))

    # Resetuje i przygotowuje stan gry do nowej rozgrywki
    def _initialize_game_state(self):
        self.deck_source_data = []
        self.tableau = [[] for _ in range(7)]
        self.reserve_stock = []
        self.waste_pile_draw1 = []
        self.waste_pile_draw3 = []
        self.final_stacks = [[] for _ in range(4)]
        self.current_reserve_card_obj = None
        self.visible_draw3_cards = [None, None, None]
        self.selected_cards_coords = []
        self.confirmed_selection = False
        self.original_selected_coords = []
        self.message = ""
        self.moving_final_card_obj = None
        self.move_count = 0
        self.game_over = False
        self.first_reveal_done = False
        self.game_state_history.clear()
        self.undo_actions_available = 0
        self._generate_deck_data()
        self._generate_tableau_and_reserve()
        if len(self.tableau) > 1 and len(self.tableau[1]) > 1:
            self.selected_cards_coords = [[1, 1]]
        elif self.tableau and self.tableau[0]:
            self.selected_cards_coords = [[0, 0]]
        else:
            self.selected_cards_coords = [[0,0]]
        
    # Rysuje kolumny tableau
    def display_tableau(self):
        col_blocks = []
        max_height = 0
        for col_idx, column in enumerate(self.tableau):
            block = []
            n = len(column)
            for row_idx, card_obj in enumerate(column):
                current_card_is_actually_hidden = card_obj.hidden
                
                if not column:
                    continue

                sel = [col_idx, row_idx] in self.selected_cards_coords
                hide_this_card_because_held_over_final = False
                if self.confirmed_selection and sel:
                    if self.original_selected_coords and \
                       [col_idx, row_idx] in self.original_selected_coords and \
                       self.selected_cards_coords and \
                       self.selected_cards_coords[0][1] == -1:
                        hide_this_card_because_held_over_final = True
                
                if hide_this_card_because_held_over_final:
                    if row_idx < n - 1:
                        block.extend([" " * self.CARD_WIDTH] * 3)
                    else:
                        block.extend([" " * self.CARD_WIDTH] * self.CARD_HEIGHT)
                    continue
                
                border_to_use = Fore.LIGHTBLACK_EX
                if not current_card_is_actually_hidden:
                    border_to_use = Fore.RED if card_obj.is_red() else Fore.WHITE
                
                if sel:
                    border_to_use = Fore.GREEN if self.confirmed_selection else Fore.YELLOW
                
                if current_card_is_actually_hidden:
                    full = [ border_to_use + "┌─────┐" + Style.RESET_ALL, border_to_use + "│││││││" + Style.RESET_ALL, border_to_use + "│││││││" + Style.RESET_ALL, border_to_use + "│││││││" + Style.RESET_ALL, border_to_use + "└─────┘" + Style.RESET_ALL, ]
                else:
                    color = Fore.RED if card_obj.is_red() else Fore.WHITE
                    pad = " " if card_obj.value != "10" else ""
                    full = [ border_to_use + "┌─────┐" + Style.RESET_ALL, border_to_use + "│" + color + f"{card_obj.value + pad}   " + border_to_use + "│" + Style.RESET_ALL, border_to_use + "│" + color + f"  {card_obj.suit}  " + border_to_use + "│" + Style.RESET_ALL, border_to_use + "│" + color + f"   {pad + card_obj.value}" + border_to_use + "│" + Style.RESET_ALL, border_to_use + "└─────┘" + Style.RESET_ALL, ]
                
                if row_idx < n - 1:
                    block.extend(full[:3])
                else:
                    block.extend(full)
            col_blocks.append(block)
            max_height = max(max_height, len(block))

        for block_item in col_blocks:
            block_item.extend([" " * self.CARD_WIDTH] * (max_height - len(block_item)))

        for line_idx in range(max_height):
            row_str = []
            for b_val in col_blocks:
                if line_idx < len(b_val):
                    row_str.append(b_val[line_idx])
                else:
                    row_str.append(" " * self.CARD_WIDTH)
            print("  ".join(row_str))

    # Tworzy nową, potasowaną talię kart
    def _generate_deck_data(self):
        self.deck_source_data.clear()
        _ = [self.deck_source_data.append([v,s]) for s in self.SUITS for v in self.VALUES]
        random.shuffle(self.deck_source_data)

    # Upewnia się, że istnieją dokładnie cztery kupki końcowe
    def _ensure_four_final_piles(self):
        while len(self.final_stacks) < 4:
            self.final_stacks.append([])
        while len(self.final_stacks) > 4:
            self.final_stacks.pop()

    # Generuje wygląd karty
    def _get_card_face_lines(self, card_obj, border_color_override=None, is_hidden_override=False, width=CARD_WIDTH):
        if width == self.DRAW3_PARTIAL_WIDTH:
            if not card_obj or is_hidden_override:
                border = Fore.LIGHTBLACK_EX if border_color_override is None else border_color_override
                return [border + "┌───" + Style.RESET_ALL,
                        border + "│││ " + Style.RESET_ALL,
                        border + "│││ " + Style.RESET_ALL,
                        border + "│││ " + Style.RESET_ALL,
                        border + "└───" + Style.RESET_ALL]
            else:
                color = Fore.RED if card_obj.is_red() else Fore.WHITE
                pad = " " if card_obj.value != "10" else ""
                border = border_color_override if border_color_override else color
                return [border + "┌───" + Style.RESET_ALL,
                        border + "│" + Style.RESET_ALL + color + f"{card_obj.value + pad}" + Style.RESET_ALL + border + " " + Style.RESET_ALL,
                        border + "│ " + Style.RESET_ALL + color + f"{card_obj.suit} " + Style.RESET_ALL + border + "" + Style.RESET_ALL,
                        border + "│   " + Style.RESET_ALL,
                        border + "└───" + Style.RESET_ALL]

        if not card_obj or is_hidden_override:
            border = Fore.LIGHTBLACK_EX if border_color_override is None else border_color_override
            return [ border + "┌─────┐" + Style.RESET_ALL, border + "│││││││" + Style.RESET_ALL, border + "│││││││" + Style.RESET_ALL, border + "│││││││" + Style.RESET_ALL, border + "└─────┘" + Style.RESET_ALL, ]
        else:
            color = Fore.RED if card_obj.is_red() else Fore.WHITE
            pad = " " if card_obj.value != "10" else ""
            border = border_color_override if border_color_override else color
            return [ border + "┌─────┐" + Style.RESET_ALL, border + "│" + Style.RESET_ALL + color + f"{card_obj.value + pad}   " + Style.RESET_ALL + border + "│" + Style.RESET_ALL, border + "│" + Style.RESET_ALL + color + f"  {card_obj.suit}  " + Style.RESET_ALL + border + "│" + Style.RESET_ALL, border + "│" + Style.RESET_ALL + color + f"   {pad + card_obj.value}" + Style.RESET_ALL + border + "│" + Style.RESET_ALL, border + "└─────┘" + Style.RESET_ALL, ]

    # Wyświetla obszar rezerwy i kupek końcowych
    def display_reserve_and_final_stacks(self):
        self._ensure_four_final_piles()
        blocks = []
        
        if self.reserve_stock or self.waste_pile_draw1 or self.waste_pile_draw3 or self.first_reveal_done:
            blocks.append([Fore.LIGHTBLACK_EX + l + Style.RESET_ALL for l in ["┌─────┐"]+["│││││││"]*3+["└─────┘"]])
        else:
            blocks.append([" " * self.CARD_WIDTH] * self.CARD_HEIGHT)
        
        is_sel_reserve_area = self.selected_cards_coords and self.selected_cards_coords[0] == [0, -1]
        reserve_border_color_for_empty_slot = Fore.LIGHTBLACK_EX
        if is_sel_reserve_area:
            reserve_border_color_for_empty_slot = Fore.GREEN if self.confirmed_selection else Fore.YELLOW
        
        if self.difficulty == 'trudny':
            draw3_block_lines = [""] * self.CARD_HEIGHT
            if not self.first_reveal_done: # Karty ukryte w rezerwie
                empty_partial = [" " * self.DRAW3_PARTIAL_WIDTH] * self.CARD_HEIGHT
                empty_full_slot_lines = [" " * (self.CARD_WIDTH - 2)] * self.CARD_HEIGHT
                if is_sel_reserve_area:
                    empty_full_slot_lines = [reserve_border_color_for_empty_slot+l+Style.RESET_ALL for l in ["┌─────┐"]+["│     │"]*3+["└─────┘"]]

                for i in range(self.CARD_HEIGHT):
                    draw3_block_lines[i] += empty_partial[i]
                    draw3_block_lines[i] += empty_partial[i]
                    draw3_block_lines[i] += empty_full_slot_lines[i]
            else: # Karty pokazane w rezerwie
                card1_disp = self.visible_draw3_cards[0]
                card2_disp = self.visible_draw3_cards[1]
                active_slot_content = self.current_reserve_card_obj

                if self.confirmed_selection and self.original_selected_coords and \
                   self.original_selected_coords[0] == [0, -1]:
                    card_held_from_reserve = self.current_reserve_card_obj
                    if self.selected_cards_coords[0][1] != -1:
                        pass
                    elif self.selected_cards_coords[0][0] != 0:
                        if card_held_from_reserve is self.visible_draw3_cards[0]:
                            card1_disp = None
                        if card_held_from_reserve is self.visible_draw3_cards[1]:
                            card2_disp = None
                        if card_held_from_reserve is active_slot_content:
                            active_slot_content = None

                card1_lines = self._get_card_face_lines(card1_disp, None, False, width=self.DRAW3_PARTIAL_WIDTH)
                for i in range(self.CARD_HEIGHT):
                    draw3_block_lines[i] += card1_lines[i]

                card2_lines = self._get_card_face_lines(card2_disp, None, False, width=self.DRAW3_PARTIAL_WIDTH)
                for i in range(self.CARD_HEIGHT):
                    draw3_block_lines[i] += card2_lines[i]
                
                border_for_active_slot = None
                if is_sel_reserve_area and not (self.confirmed_selection and self.original_selected_coords and self.original_selected_coords[0] == [0,-1] and self.selected_cards_coords[0] == [0,-1]):
                    border_for_active_slot = Fore.GREEN if self.confirmed_selection else Fore.YELLOW
                
                if self.confirmed_selection and self.original_selected_coords and self.original_selected_coords[0] == [0,-1] and is_sel_reserve_area:
                    card3_lines = self._get_card_face_lines(self.current_reserve_card_obj, Fore.GREEN, width=self.CARD_WIDTH)
                elif active_slot_content:
                    card3_lines = self._get_card_face_lines(active_slot_content, border_for_active_slot, width=self.CARD_WIDTH)
                else:
                    card3_lines = [reserve_border_color_for_empty_slot+l+Style.RESET_ALL for l in ["┌─────┐"]+["│     │"]*3+["└─────┘"]]
                
                for i in range(self.CARD_HEIGHT):
                    draw3_block_lines[i] += card3_lines[i]
            
            blocks.append(draw3_block_lines)

            if self.first_reveal_done:
                blocks.append([""] * self.CARD_HEIGHT) 
            else:
                blocks.append([" "] * self.CARD_HEIGHT)
        else: # Tryb łatwy
            if not self.first_reveal_done:
                if is_sel_reserve_area:
                    blocks.append([reserve_border_color_for_empty_slot+l+Style.RESET_ALL for l in ["┌─────┐"]+["│     │"]*3+["└─────┘"]])
                else:
                    blocks.append([" " * self.CARD_WIDTH] * self.CARD_HEIGHT)
            else:
                card_on_reserve_slot = self.current_reserve_card_obj
                if self.confirmed_selection and self.original_selected_coords and \
                   self.original_selected_coords[0] == [0,-1] and \
                   (self.selected_cards_coords[0][1] != -1 or self.selected_cards_coords[0][0] != 0):
                    card_on_reserve_slot = None

                border_easy_reserve = None
                if is_sel_reserve_area and not (self.confirmed_selection and self.original_selected_coords and self.original_selected_coords[0] == [0,-1] and self.selected_cards_coords[0] == [0,-1]):
                    border_easy_reserve = Fore.GREEN if self.confirmed_selection else Fore.YELLOW
                
                if self.confirmed_selection and self.original_selected_coords and \
                   self.original_selected_coords[0] == [0,-1] and \
                   is_sel_reserve_area:
                     blocks.append(self._get_card_face_lines(self.current_reserve_card_obj, Fore.GREEN))
                elif card_on_reserve_slot:
                    blocks.append(self._get_card_face_lines(card_on_reserve_slot, border_easy_reserve))
                else:
                    blocks.append([reserve_border_color_for_empty_slot+l+Style.RESET_ALL for l in ["┌─────┐"]+["│     │"]*3+["└─────┘"]])
            blocks.append([" " * self.CARD_WIDTH] * self.CARD_HEIGHT)
        
        for pile_idx in range(4):
            is_selected_this_final_pile = (self.selected_cards_coords and self.selected_cards_coords[0][0] == pile_idx + 1 and self.selected_cards_coords[0][1] == -1)
            card_natively_on_this_final_pile = self.final_stacks[pile_idx][-1] if self.final_stacks[pile_idx] else None
            
            ghost_to_show_on_this_pile = None
            if self.confirmed_selection and is_selected_this_final_pile:
                if self.original_selected_coords[0][1] == -1 and self.original_selected_coords[0][0] > 0:
                    ghost_to_show_on_this_pile = self.moving_final_card_obj
                elif self.original_selected_coords[0][1] == -1 and self.original_selected_coords[0][0] == 0:
                    ghost_to_show_on_this_pile = self.current_reserve_card_obj
                elif self.original_selected_coords[0][1] != -1:
                    if self.final_stacks[pile_idx]:
                        ghost_to_show_on_this_pile = self.final_stacks[pile_idx][-1]
            
            if ghost_to_show_on_this_pile is not None and card_natively_on_this_final_pile is ghost_to_show_on_this_pile:
                card_natively_on_this_final_pile = None
            elif self.moving_final_card_obj and card_natively_on_this_final_pile is self.moving_final_card_obj and \
                 self.original_selected_coords and self.original_selected_coords[0][0]-1 == pile_idx and \
                 not is_selected_this_final_pile:
                 card_natively_on_this_final_pile = None

            if ghost_to_show_on_this_pile:
                blocks.append(self._get_card_face_lines(ghost_to_show_on_this_pile, Fore.GREEN))
            elif card_natively_on_this_final_pile:
                border_final = Fore.RED if card_natively_on_this_final_pile.is_red() else Fore.WHITE
                if is_selected_this_final_pile:
                    border_final = Fore.GREEN if self.confirmed_selection else Fore.YELLOW
                blocks.append(self._get_card_face_lines(card_natively_on_this_final_pile, border_final))
            else:
                border_empty_final = Fore.LIGHTBLACK_EX
                if is_selected_this_final_pile:
                    border_empty_final = Fore.GREEN if self.confirmed_selection else Fore.YELLOW
                blocks.append([border_empty_final+l+Style.RESET_ALL for l in ["┌─────┐"]+["│     │"]*3+["└─────┘"]])
        
        # Wypisanie wszystkich bloków z odpowiednim odstępem
        for r in range(self.CARD_HEIGHT):
            current_line_output = ""
            for block_item_idx, block_item_content in enumerate(blocks):
                part_to_add = ""
                if self.difficulty == 'trudny' and block_item_idx == 1: # Blok draw3
                    if r < len(block_item_content):
                        part_to_add = block_item_content[r]
                    else:
                        part_to_add = " " * (self.DRAW3_PARTIAL_WIDTH * 2 + self.CARD_WIDTH)
                elif self.difficulty == 'trudny' and block_item_idx == 2: # Blok separatora
                    if r < len(block_item_content):
                        part_to_add = block_item_content[r]
                else: # Reszta bloków
                    if r < len(block_item_content):
                        part_to_add = block_item_content[r]
                    else:
                        part_to_add = " " * self.CARD_WIDTH
                
                if block_item_idx == 0:
                    current_line_output += part_to_add
                else:
                    if self.difficulty == 'trudny' and block_item_idx == 3 and \
                       blocks[2][r] == "" :
                        current_line_output += " " + part_to_add
                    else:
                        current_line_output += "  " + part_to_add

            if current_line_output.strip():
                print(current_line_output)

    # Rozdaje karty do kolumn tableau i tworzy stos rezerwowy
    def _generate_tableau_and_reserve(self):
        card_counter = 0
        self.tableau = [[] for _ in range(7)]
        self.waste_pile_draw1 = []
        self.waste_pile_draw3 = []
        for i in range(7):
            for j in range(i + 1):
                if card_counter < len(self.deck_source_data):
                    v,s = self.deck_source_data[card_counter]
                    self.tableau[i].append(Card(v,s,hidden=(j!=i)))
                    card_counter += 1
                else:
                    break
        self.reserve_stock = [Card(v,s) for v,s in self.deck_source_data[card_counter:]]
        self.current_reserve_card_obj = None
        self.visible_draw3_cards = [None,None,None]
        self.first_reveal_done = False

    # Sprawdza, czy daną kartę można umieścić na kupce końcowej
    def _can_place_on_final(self, card_obj_to_place, final_stack_list):
        if not card_obj_to_place or not isinstance(card_obj_to_place,Card):
            return False
        v,s = card_obj_to_place.value, card_obj_to_place.suit
        ci = self.VALUES.index(v) if v in self.VALUES else -1
        if ci == -1:
            return False
        if not final_stack_list:
            return v == "A"
        lc = final_stack_list[-1]
        if not lc or not isinstance(lc,Card):
            return False
        lv,ls = lc.value, lc.suit
        li = self.VALUES.index(lv) if lv in self.VALUES else -1
        if li == -1:
            return False
        return s == ls and ci == li + 1

    # Zapisuje aktualny stan gry na potrzeby funkcji cofania
    def _save_state_for_undo(self):
        if self.game_over:
            return
        state = {
            'tableau': [[card.get_raw_data() for card in col] for col in self.tableau],
            'final_stacks': [[card.get_raw_data() for card in stack] for stack in self.final_stacks],
            'reserve_stock': [card.get_raw_data() for card in self.reserve_stock],
            'waste_pile_draw1': [card.get_raw_data() for card in self.waste_pile_draw1],
            'waste_pile_draw3': [card.get_raw_data() for card in self.waste_pile_draw3],
            'visible_draw3_cards': [(card.get_raw_data() if card else None) for card in self.visible_draw3_cards],
            'current_reserve_card_obj': self.current_reserve_card_obj.get_raw_data() if self.current_reserve_card_obj else None,
            'move_count': self.move_count,
            'first_reveal_done': self.first_reveal_done,
        }
        self.game_state_history.append(copy.deepcopy(state))
        self.undo_actions_available = len(self.game_state_history)

    # Przywraca poprzedni stan gry z historii
    def _restore_state_from_undo(self, state):
        self.tableau = [[Card(val, suit, hidden) for val, suit, hidden in col_data] for col_data in state['tableau']]
        self.final_stacks = [[Card(val, suit, hidden) for val, suit, hidden in stack_data] for stack_data in state['final_stacks']]
        self.reserve_stock = [Card(val, suit, False) for val, suit, _ in state['reserve_stock']]
        self.waste_pile_draw1 = [Card(val, suit, False) for val, suit, _ in state['waste_pile_draw1']]
        self.waste_pile_draw3 = [Card(val, suit, False) for val, suit, _ in state['waste_pile_draw3']]
        
        self.visible_draw3_cards = []
        for card_data in state['visible_draw3_cards']:
            if card_data:
                self.visible_draw3_cards.append(Card(card_data[0], card_data[1], card_data[2]))
            else:
                self.visible_draw3_cards.append(None)
        
        crc_data = state['current_reserve_card_obj']
        if crc_data:
            self.current_reserve_card_obj = Card(crc_data[0], crc_data[1], crc_data[2])
        else:
            self.current_reserve_card_obj = None
            
        self.first_reveal_done = state['first_reveal_done']
        
        self.selected_cards_coords = []
        if len(self.tableau) > 1 and len(self.tableau[1]) > 1:
            self.selected_cards_coords = [[1, 1]]
        elif self.tableau and self.tableau[0]:
            self.selected_cards_coords = [[0, 0]]
        else:
            self.selected_cards_coords = [[0,0]]
        self.confirmed_selection = False
        self.original_selected_coords = []
        self.moving_final_card_obj = None
        self.message = "Ruch cofnięty."

    # Pomocnicza funkcja do cofania nieudanego ruchu w obrębie tableau
    def _undo_failed_tableau_move(self):
        if not self.original_selected_coords or not self.selected_cards_coords:
            if self.original_selected_coords:
                self.selected_cards_coords = [c[:] for c in self.original_selected_coords]
            return

        current_col = self.selected_cards_coords[0][0]
        current_min_row = min(r for _, r in self.selected_cards_coords)
        num_moved_cards = len(self.selected_cards_coords)

        if not (0 <= current_col < len(self.tableau) and \
                current_min_row + num_moved_cards <= len(self.tableau[current_col])):
            self.selected_cards_coords = [c[:] for c in self.original_selected_coords]
            return

        cards_to_put_back = self.tableau[current_col][current_min_row : current_min_row + num_moved_cards]
        
        self.tableau[current_col] = self.tableau[current_col][:current_min_row] + self.tableau[current_col][current_min_row + num_moved_cards:]

        original_col_src = self.original_selected_coords[0][0]
        
        if 0 <= original_col_src < len(self.tableau):
            self.tableau[original_col_src].extend(cards_to_put_back)
        else:
            self.message = "Błąd"

        self.selected_cards_coords = [c[:] for c in self.original_selected_coords]

    # Przesuwa zaznaczenie/kartę w poziomie (lewo/prawo)
    def move_selection_horizontal(self, is_right):
        if self.game_over:
            return
        if not self.selected_cards_coords:
            return
        
        direction = 1 if is_right else -1
        current_col_sel, current_row_sel = self.selected_cards_coords[0]

        def find_next_tableau_col_for_move(s, d):
            if 0 <= s + d < len(self.tableau):
                return s + d
            return None

        if self.confirmed_selection:
            orig_col_src, orig_row_type_src = self.original_selected_coords[0]

            if current_row_sel == -1: # Poruszanie się po górnym rzędzie (rezerwa, kupki końcowe)
                card_being_moved = None
                is_originally_from_reserve = (orig_row_type_src == -1 and orig_col_src == 0)
                is_originally_from_final = (orig_row_type_src == -1 and 1 <= orig_col_src <= 4)
                is_originally_from_tableau_to_final = (orig_row_type_src != -1)

                if is_originally_from_reserve:
                    card_being_moved = self.current_reserve_card_obj
                    if card_being_moved is None and current_col_sel > 0 and self.final_stacks[current_col_sel - 1]:
                        card_being_moved = self.final_stacks[current_col_sel - 1][-1]
                elif is_originally_from_final:
                    card_being_moved = self.moving_final_card_obj
                elif is_originally_from_tableau_to_final:
                    if current_col_sel > 0 and self.final_stacks[current_col_sel - 1]:
                        card_being_moved = self.final_stacks[current_col_sel - 1][-1]
                
                if card_being_moved:
                    new_target_zone_col_idx = current_col_sel + direction

                    if 0 <= new_target_zone_col_idx <= 4: # Sprawdzenie granic (0 dla rezerwy, 1-4 dla kupek końcowych)
                        if current_col_sel == 0 and is_originally_from_reserve and self.current_reserve_card_obj is card_being_moved:
                            self.current_reserve_card_obj = None
                        elif current_col_sel > 0: # Była na kupce końcowej
                            if self.final_stacks[current_col_sel - 1] and \
                               self.final_stacks[current_col_sel - 1][-1] is card_being_moved:
                                self.final_stacks[current_col_sel - 1].pop()
                        
                        self.selected_cards_coords = [[new_target_zone_col_idx, -1]]

                        # Dodaj kartę na nową pozycję
                        if new_target_zone_col_idx == 0:
                            if is_originally_from_reserve:
                                self.current_reserve_card_obj = card_being_moved
                            else:
                                self.selected_cards_coords = [[current_col_sel, -1]]
                                if current_col_sel > 0:
                                    self.final_stacks[current_col_sel - 1].append(card_being_moved)
                        elif new_target_zone_col_idx > 0:
                            self.final_stacks[new_target_zone_col_idx - 1].append(card_being_moved)
            elif current_row_sel != -1: # Poruszanie się po kolumnach tableau
                num_cards_in_sel = len(self.selected_cards_coords)
                min_row_on_tab = min(r for _,r in self.selected_cards_coords)
                if not (0 <= current_col_sel < len(self.tableau) and \
                        self.tableau[current_col_sel] and \
                        min_row_on_tab < len(self.tableau[current_col_sel]) and \
                        num_cards_in_sel <= len(self.tableau[current_col_sel]) - min_row_on_tab):
                    self.display_game()
                    return
                
                cards_to_move = self.tableau[current_col_sel][min_row_on_tab : min_row_on_tab + num_cards_in_sel]
                new_target_tab_col = find_next_tableau_col_for_move(current_col_sel, direction)
                
                if new_target_tab_col is not None:
                    self.tableau[current_col_sel] = self.tableau[current_col_sel][:min_row_on_tab] + self.tableau[current_col_sel][min_row_on_tab + num_cards_in_sel:]
                    new_start_row_in_target = len(self.tableau[new_target_tab_col])
                    self.tableau[new_target_tab_col].extend(cards_to_move)
                    self.selected_cards_coords = [[new_target_tab_col, new_start_row_in_target + i] for i in range(num_cards_in_sel)]
        else: # Nawigacja bez podniesionej karty
            if current_row_sel == -1: # Nawigacja w górnym rzędzie
                if current_col_sel == 0: # Z rezerwy
                    if is_right:
                        for i in range(4): # Szuka pierwszej zajętej kupki końcowej
                            if self.final_stacks[i]:
                                self.selected_cards_coords = [[i + 1, -1]]
                                break
                elif 1 <= current_col_sel <= 4: # Z kupek końcowych
                    current_final_idx = current_col_sel - 1
                    found_next_final_selection = False
                    temp_check_idx = current_final_idx

                    for _ in range(4):
                        temp_check_idx += direction
                        if not (0 <= temp_check_idx < 4):
                            break
                        if self.final_stacks[temp_check_idx]:
                            self.selected_cards_coords = [[temp_check_idx + 1, -1]]
                            found_next_final_selection = True
                            break
                    if not found_next_final_selection:
                        if direction == -1 and current_final_idx == 0: # Próba przejścia w lewo z pierwszej kupki końcowej
                            if self.first_reveal_done and (self.current_reserve_card_obj or (self.difficulty == 'trudny' and any(self.visible_draw3_cards))):
                                self.selected_cards_coords = [[0, -1]] # Na rezerwę
            else: # Nawigacja w tableau
                new_col_candidate = current_col_sel
                while True:
                    new_col_candidate += direction
                    if not (0 <= new_col_candidate < len(self.tableau)):
                        break
                    if self.tableau[new_col_candidate]: # Znajduje następną niepustą kolumnę
                        self.selected_cards_coords = [[new_col_candidate, len(self.tableau[new_col_candidate]) - 1]]
                        break
        self.display_game()

    # Sprawdza, czy warunki wygranej zostały spełnione
    def _check_win_condition(self):
        if self.game_over:
            return True
        for stack in self.final_stacks:
            if len(stack) != 13:
                return False
            if stack[-1].value != "K":
                return False
        
        self.game_over = True
        self.message = f"Gratulacje! Wygrałeś w {self.move_count} ruchach!"
        current_score_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        score_entry = {"moves": self.move_count, "timestamp": current_score_timestamp, "difficulty": self.difficulty}
        scores = []
        if os.path.exists(self.SCORES_FILE):
            try:
                with open(self.SCORES_FILE, 'r') as f:
                    scores = json.load(f)
                if not isinstance(scores, list):
                    scores = []
            except json.JSONDecodeError:
                scores = []
        scores.append(score_entry)
        try:
            with open(self.SCORES_FILE, 'w') as f:
                json.dump(scores, f, indent=4)
        except IOError:
            self.message += " (Nie udało się zapisać wyniku)"
        
        self.display_game()
        self._display_leaderboard(new_score_timestamp=current_score_timestamp)
        return True

    # Uzupełnia zestaw trzech kart w trybie trudnym.
    def _refill_draw3_window(self, card_just_used=None):
        if self.difficulty != 'trudny':
            return
        
        if card_just_used:
            for i in range(3):
                if self.visible_draw3_cards[i] is card_just_used:
                    self.visible_draw3_cards[i] = None
                    break
        
        current_visible = [card for card in self.visible_draw3_cards if card is not None]
        self.visible_draw3_cards = [None, None, None]

        current_idx = 2
        for card in reversed(current_visible):
            if current_idx >= 0:
                self.visible_draw3_cards[current_idx] = card
                current_idx -= 1
            else:
                break

        for i in range(3):
            if self.visible_draw3_cards[i] is None:
                if self.reserve_stock:
                    self.visible_draw3_cards[i] = self.reserve_stock.pop(0)
                elif self.waste_pile_draw3:
                    if not self.reserve_stock and self.waste_pile_draw3:
                        self.reserve_stock = self.waste_pile_draw3[:]
                        self.waste_pile_draw3 = []
                        if self.reserve_stock:
                            self.visible_draw3_cards[i] = self.reserve_stock.pop(0)
                        else:
                            break
                    else:
                        break
                else:
                    break

        new_active_card = None
        if self.visible_draw3_cards[2] is not None:
            new_active_card = self.visible_draw3_cards[2]
        elif self.visible_draw3_cards[1] is not None:
            new_active_card = self.visible_draw3_cards[1]
        elif self.visible_draw3_cards[0] is not None:
            new_active_card = self.visible_draw3_cards[0]
        
        self.current_reserve_card_obj = new_active_card

    # Obsługuje logikę podniesienia (pierwsze wciśnięcie Enter) i umieszczenia karty (drugie Enter)
    def confirm_selection(self):
        if self.game_over:
            return
        if not self.selected_cards_coords:
            self.display_game()
            return

        if not self.confirmed_selection: # Pierwsze wciśnięcie Enter - podniesienie karty
            sel_c, sel_r = self.selected_cards_coords[0]
            valid_pickup = False
            if sel_r == -1: # Podnoszenie z rezerwy lub kupki końcowej
                if (sel_c == 0 and self.first_reveal_done and self.current_reserve_card_obj) or \
                   (1 <= sel_c <= 4 and self.final_stacks[sel_c-1]):
                    valid_pickup = True
            else: # Podnoszenie z tableau
                all_visible_in_stack = True
                if not self.selected_cards_coords: # Powinno być zawsze true, ale dla bezpieczeństwa
                    all_visible_in_stack = False
                else:
                    for sc, sr in self.selected_cards_coords:
                        if not (0 <= sc < len(self.tableau) and 0 <= sr < len(self.tableau[sc])):
                            all_visible_in_stack = False
                            break
                        if self.tableau[sc][sr].hidden:
                            all_visible_in_stack = False
                            break
                if all_visible_in_stack and self.selected_cards_coords:
                    valid_pickup = True
            
            if valid_pickup:
                self._save_state_for_undo()
                self.original_selected_coords = [c[:] for c in self.selected_cards_coords]
                self.confirmed_selection = True
                self.moving_final_card_obj = None
                if self.original_selected_coords[0][1] == -1 and 1 <= self.original_selected_coords[0][0] <= 4:
                    # Jeśli podnosimy z kupki końcowej, zabierz kartę od razu
                    final_pile_idx = self.original_selected_coords[0][0] - 1
                    if self.final_stacks[final_pile_idx]:
                        self.moving_final_card_obj = self.final_stacks[final_pile_idx].pop()
            else:
                self.message = "Nie można podnieść."
            self.display_game()
            return
        
        # Drugie wciśnięcie Enter - umieszczenie karty
        source_col_orig, source_row_type_orig = self.original_selected_coords[0]
        target_col, target_row = self.selected_cards_coords[0]
        
        move_successful = False
        action_taken = False
        
        # Przypadek 1: z rezerwy na kupkę końcową
        if source_row_type_orig == -1 and source_col_orig == 0 and \
           target_row == -1 and 1 <= target_col <= 4:
            action_taken = True
            target_final_pile_idx = target_col - 1
            
            card_placed_on_final = None
            if self.final_stacks[target_final_pile_idx]:
                card_placed_on_final = self.final_stacks[target_final_pile_idx][-1]
            
            if not card_placed_on_final:
                self.selected_cards_coords = [[0, -1]]
            elif self._can_place_on_final(card_placed_on_final, self.final_stacks[target_final_pile_idx][:-1]):
                move_successful = True
                if self.difficulty == 'trudny':
                    self._refill_draw3_window(card_just_used=card_placed_on_final)
                self.selected_cards_coords = [[0, -1]]
            else: # Nie można umieścić
                self.message = "Nie można tutaj umieścić tej karty."
                if self.final_stacks[target_final_pile_idx] and self.final_stacks[target_final_pile_idx][-1] is card_placed_on_final:
                    self.final_stacks[target_final_pile_idx].pop()
                
                self.current_reserve_card_obj = card_placed_on_final
                if self.difficulty == 'trudny':
                    is_card_in_visible = any(self.visible_draw3_cards[i] is card_placed_on_final for i in range(3))
                    if not is_card_in_visible:
                        for i in range(2, -1, -1):
                            if self.visible_draw3_cards[i] is None:
                                self.visible_draw3_cards[i] = card_placed_on_final
                                is_card_in_visible = True
                                break
                        if not is_card_in_visible:
                            self.visible_draw3_cards[2] = card_placed_on_final
                    self._refill_draw3_window()
                self.selected_cards_coords = [[0, -1]]
        
        # Przypadek 2: z kupki końcowej na inną kupkę końcową
        elif source_row_type_orig == -1 and 1 <= source_col_orig <= 4 and target_row == -1 and 1 <= target_col <= 4:
            action_taken = True
            idx_final_target = target_col - 1
            original_final_pile_idx = source_col_orig - 1
            
            card_to_validate = None
            if self.final_stacks[idx_final_target] and self.final_stacks[idx_final_target][-1] is self.moving_final_card_obj:
                card_to_validate = self.moving_final_card_obj
            
            if not card_to_validate:
                if self.moving_final_card_obj:
                    self.final_stacks[original_final_pile_idx].append(self.moving_final_card_obj)
                self.selected_cards_coords = [[source_col_orig, -1]]
            elif self._can_place_on_final(card_to_validate, self.final_stacks[idx_final_target][:-1]):
                move_successful = True
            else:
                self.message = "Nie można tutaj umieścić tej karty."
                if self.final_stacks[idx_final_target] and self.final_stacks[idx_final_target][-1] is card_to_validate:
                    self.final_stacks[idx_final_target].pop()
                if self.moving_final_card_obj:
                    self.final_stacks[original_final_pile_idx].append(self.moving_final_card_obj)
                self.selected_cards_coords = [[source_col_orig, -1]]
        
        # Przypadek 3: z tableau na kupkę końcową
        elif source_row_type_orig != -1 and target_row == -1 and 1 <= target_col <= 4:
            action_taken = True
            idx_final_target = target_col - 1
            if not self.final_stacks[idx_final_target]:
                self.selected_cards_coords = [c[:] for c in self.original_selected_coords]
            else:
                card_moved_to_final = self.final_stacks[idx_final_target][-1]
                if self._can_place_on_final(card_moved_to_final, self.final_stacks[idx_final_target][:-1]):
                    move_successful = True
                    orig_tab_col_idx = self.original_selected_coords[0][0]
                    if self.tableau[orig_tab_col_idx] and self.tableau[orig_tab_col_idx][-1].hidden:
                        self.tableau[orig_tab_col_idx][-1].hidden = False
                else:
                    self.message = "Nie można tutaj umieścić tej karty."
                    card_to_return_to_tableau = self.final_stacks[idx_final_target].pop()
                    orig_tab_col_idx, orig_tab_row_idx = self.original_selected_coords[0]
                    if 0 <= orig_tab_col_idx < len(self.tableau):
                        insert_pos = min(orig_tab_row_idx, len(self.tableau[orig_tab_col_idx]))
                        self.tableau[orig_tab_col_idx].insert(insert_pos, card_to_return_to_tableau)
                    self.selected_cards_coords = [c[:] for c in self.original_selected_coords]
        
        # Przypadek 4: z tableau na tableau
        elif source_row_type_orig != -1 and target_row != -1:
            action_taken = True
            current_tableau_col, current_tableau_start_row = target_col, min(r for _,r in self.selected_cards_coords)
            
            valid_move_tableau = False
            if not (0 <= current_tableau_col < len(self.tableau) and 0 <= current_tableau_start_row <= len(self.tableau[current_tableau_col])):
                self.message = "Błąd"
            elif not self.tableau[current_tableau_col] or current_tableau_start_row == len(self.tableau[current_tableau_col]): # Przenoszenie na pustą kolumnę lub na koniec istniejącej
                is_target_col_empty_before_move = (len(self.tableau[current_tableau_col]) - len(self.selected_cards_coords) == 0)
                if self.tableau[current_tableau_col] and current_tableau_start_row < len(self.tableau[current_tableau_col]):
                    first_card_of_moved_stack = self.tableau[current_tableau_col][current_tableau_start_row]
                    if first_card_of_moved_stack.value == "K" and is_target_col_empty_before_move:
                        valid_move_tableau = True
            else: # Przenoszenie na istniejącą kartę
                top_card_of_stack = self.tableau[current_tableau_col][current_tableau_start_row]
                if current_tableau_start_row == 0:
                    if top_card_of_stack.value == "K":
                        valid_move_tableau = True
                else:
                    card_underneath = self.tableau[current_tableau_col][current_tableau_start_row - 1]
                    if not card_underneath.hidden:
                        val_idx_moved = self.VALUES.index(top_card_of_stack.value) if top_card_of_stack.value in self.VALUES else -1
                        val_idx_under = self.VALUES.index(card_underneath.value) if card_underneath.value in self.VALUES else -1
                        if val_idx_moved != -1 and val_idx_under != -1 and \
                           top_card_of_stack.is_red() != card_underneath.is_red() and \
                           val_idx_under - val_idx_moved == 1:
                            valid_move_tableau = True
            
            if valid_move_tableau:
                move_successful = True
                if self.tableau[source_col_orig] and self.tableau[source_col_orig][-1].hidden: # Odkryj kartę pod spodem w kolumnie źródłowej
                    self.tableau[source_col_orig][-1].hidden = False
            else:
                self.message = "Nie można tutaj umieścić tej karty."
                self._undo_failed_tableau_move() # Przywróć karty na oryginalne miejsce
        
        # Przypadek 5: z rezerwy na tableau LUB z kupki końcowej na tableau
        elif (source_row_type_orig == -1 and source_col_orig == 0 and target_row != -1) or \
             (source_row_type_orig == -1 and 1 <= source_col_orig <= 4 and target_row != -1):
            action_taken = True
            tableau_target_col = target_col
            if not self.tableau[tableau_target_col] or not self.tableau[tableau_target_col][-1]: # Karta powinna już tam być
                self.message = "Błąd"
                self.selected_cards_coords = [c[:] for c in self.original_selected_coords]
            else:
                card_moved_to_tableau = self.tableau[tableau_target_col][-1] # Karta, która została przeniesiona na tableau
                valid_move_to_tableau = False
                if len(self.tableau[tableau_target_col]) == 1: # Jeśli to jedyna karta w kolumnie
                    if card_moved_to_tableau.value == "K":
                        valid_move_to_tableau = True
                else: # Kładziemy na inną kartę
                    card_underneath_in_tableau = self.tableau[tableau_target_col][-2]
                    if not card_underneath_in_tableau.hidden:
                        val_idx_moved = self.VALUES.index(card_moved_to_tableau.value) if card_moved_to_tableau.value in self.VALUES else -1
                        val_idx_under = self.VALUES.index(card_underneath_in_tableau.value) if card_underneath_in_tableau.value in self.VALUES else -1
                        if val_idx_moved != -1 and val_idx_under != -1 and \
                           card_moved_to_tableau.is_red() != card_underneath_in_tableau.is_red() and \
                           val_idx_under - val_idx_moved == 1:
                            valid_move_to_tableau = True
                
                if valid_move_to_tableau:
                    move_successful = True
                    if source_row_type_orig == -1 and source_col_orig == 0 : # Jeśli z rezerwy
                        if self.difficulty == 'trudny':
                            self._refill_draw3_window(card_just_used=card_moved_to_tableau)
                else: # Nieprawidłowy ruch na tableau
                    self.message = "Nie można tutaj umieścić tej karty."
                    card_to_return_from_tableau = self.tableau[tableau_target_col].pop()
                    if source_row_type_orig == -1 and source_col_orig == 0: # Wróć do rezerwy
                        self.current_reserve_card_obj = card_to_return_from_tableau
                        if self.difficulty == 'trudny':
                            is_card_in_visible = any(self.visible_draw3_cards[i] is card_to_return_from_tableau for i in range(3))
                            if not is_card_in_visible:
                                for i in range(2, -1, -1):
                                    if self.visible_draw3_cards[i] is None:
                                        self.visible_draw3_cards[i] = card_to_return_from_tableau
                                        is_card_in_visible = True; break
                                if not is_card_in_visible: self.visible_draw3_cards[2] = card_to_return_from_tableau
                            self._refill_draw3_window()
                    elif source_row_type_orig == -1 and 1 <= source_col_orig <= 4: # Wróć na kupkę końcową
                        self.final_stacks[source_col_orig-1].append(card_to_return_from_tableau)
                    self.selected_cards_coords = [c[:] for c in self.original_selected_coords]

        if not action_taken: # Żaden z powyższych przypadków nie został dopasowany
            if self.original_selected_coords == self.selected_cards_coords: # Gracz kliknął Enter na tym samym miejscu
                if source_row_type_orig == -1 and 1 <= source_col_orig <= 4 and self.moving_final_card_obj:
                    self.final_stacks[source_col_orig-1].append(self.moving_final_card_obj)
                self.message = "Wybór odznaczony."
                if self.game_state_history: # Usunięcie stanu zapisanego przy podniesieniu
                    self.game_state_history.pop()
                    self.undo_actions_available = len(self.game_state_history)
            else: # Nieprawidłowy ruch, który nie pasuje do żadnej logiki
                self.message = "Nieprawidłowy ruch."
                if source_row_type_orig != -1 and target_row != -1: # Jeśli ruch był Tableau -> Tableau, cofnij
                    self._undo_failed_tableau_move()
                else: # Jeśli inaczej, zresetuj zaznaczenie do oryginalnego
                    self.selected_cards_coords = [c[:] for c in self.original_selected_coords]
                    if self.moving_final_card_obj and source_row_type_orig == -1 and 1 <= source_col_orig <= 4:
                        self.final_stacks[source_col_orig-1].append(self.moving_final_card_obj)
                if self.game_state_history and not action_taken: # Usunięcie stanu zapisanego przy podniesieniu
                    self.game_state_history.pop()
                    self.undo_actions_available = len(self.game_state_history)
        
        if move_successful:
            self.move_count += 1
        elif action_taken and not move_successful:
            # Jeśli podjęto próbę ruchu, ale się nie udała, usuń stan z historii (bo nieudany ruch nie powinien być cofnięty)
            if self.game_state_history:
                self.game_state_history.pop()
                self.undo_actions_available = len(self.game_state_history)
        
        if self._check_win_condition():
            return
        
        self.confirmed_selection = False
        self.original_selected_coords = []
        self.moving_final_card_obj = None
        self.display_game()

    # Rozszerza zaznaczenie w pionie (góra/dół) lub przenosi między strefami.
    def extend_selection(self, is_up):
        if self.game_over:
            return
        if not self.selected_cards_coords:
            return
        
        current_col_sel, current_row_sel = self.selected_cards_coords[0]

        if self.confirmed_selection: # Karta jest podniesiona
            orig_col_src, orig_row_type_src = self.original_selected_coords[0]
            current_target_col, current_target_row = self.selected_cards_coords[0]

            if is_up: # Ruch w górę z podniesioną kartą
                # Przypadek: Karta z rezerwy, obecnie na tableau, wraca do rezerwy/final
                if orig_row_type_src == -1 and orig_col_src == 0 and current_target_row != -1:
                    card_on_tableau_from_reserve = self.tableau[current_target_col][current_target_row]
                        
                    if 0 <= current_target_col <= 2: # Wróć do rezerwy (jeśli tableau col 0-2)
                        self.tableau[current_target_col].pop(current_target_row)
                        self.current_reserve_card_obj = card_on_tableau_from_reserve
                        if self.difficulty == 'trudny':
                            is_card_in_visible = any(self.visible_draw3_cards[i] is card_on_tableau_from_reserve for i in range(3))
                            if not is_card_in_visible:
                                for i in range(2, -1, -1):
                                    if self.visible_draw3_cards[i] is None:
                                        self.visible_draw3_cards[i] = card_on_tableau_from_reserve
                                        is_card_in_visible = True
                                        break
                                if not is_card_in_visible: 
                                    self.visible_draw3_cards[2] = card_on_tableau_from_reserve
                            self._refill_draw3_window()
                        self.selected_cards_coords = [[0, -1]]
                        self.message = "Karta wraca do Rezerwy (Enter/Esc)."
                    elif 3 <= current_target_col <= 6: # Przenieś na kupkę końcową (jeśli tableau col 3-6)
                        target_final_idx = current_target_col - 3
                        moved_card = self.tableau[current_target_col].pop(current_target_row)
                        self.final_stacks[target_final_idx].append(moved_card)
                        if self.difficulty == 'łatwy': 
                            self.current_reserve_card_obj = None
                        self.selected_cards_coords = [[target_final_idx + 1, -1]]
                    else:
                        self.message = "Nieprawidłowa kolumna Tableau."
                    self.display_game()
                    return

                # Przypadek: Karta z tableau/final, obecnie na tableau, próba przeniesienia na final
                elif (orig_row_type_src != -1 and current_target_row != -1) or \
                     (orig_row_type_src == -1 and 1 <= orig_col_src <= 4 and current_target_row != -1):
                    is_single_card = (orig_row_type_src != -1 and len(self.original_selected_coords) == 1) or \
                                     (orig_row_type_src == -1 and 1 <= orig_col_src <= 4) # Sprawdź, czy to pojedyncza karta
                    if not is_single_card:
                        self.message = "Tylko pojedynczą kartę można przenieść na kupkę końcową w ten sposób."
                    elif not (0 <= current_target_col < len(self.tableau) and \
                              0 <= current_target_row < len(self.tableau[current_target_col])):
                        self.message = "Błąd identyfikacji karty na tableau."
                    else:
                        target_final_idx = -1
                        if 3 <= current_target_col <= 6: # Mapowanie kolumn tableau 3-6 na kupki końcowe 0-3
                            target_final_idx = current_target_col - 3
                        if target_final_idx != -1:
                            moved_card = self.tableau[current_target_col].pop(current_target_row)
                            self.final_stacks[target_final_idx].append(moved_card)
                            self.selected_cards_coords = [[target_final_idx + 1, -1]]
                        
                    self.display_game()
                    return

                # Przypadek: kursor już jest na rezerwie/final
                elif current_target_row == -1:
                    pass
                    self.display_game()
                    return
            
            else: # Ruch w dół z podniesioną kartą
                if self.confirmed_selection:
                    orig_col_src, orig_row_type_src = self.original_selected_coords[0]
                    current_target_col, current_target_row = self.selected_cards_coords[0] # Gdzie kursor jest teraz

                    # Przypadek: oryginalnie z rezerwy, kursor nad rezerwą, przenosimy na tableau[0]
                    if orig_row_type_src == -1 and orig_col_src == 0 and self.current_reserve_card_obj is not None:
                        card_instance_from_reserve = self.current_reserve_card_obj
                        target_tab_col = 0 # Domyślnie na pierwszą kolumnę tableau
                        
                        self.tableau[target_tab_col].append(card_instance_from_reserve)
                        self.current_reserve_card_obj = None # Opróżnij rezerwę
                        self.selected_cards_coords = [[target_tab_col, len(self.tableau[target_tab_col]) - 1]]
                        self.display_game()
                        return
                    
                    # Przypadek: karta z final lub tableau (przez final) lub rezerwy (przez final), kursor nad final, przenosimy na tableau pod nim
                    elif \
                        (orig_row_type_src == -1 and 1 <= orig_col_src <= 4 and current_target_row == -1 and current_target_col == orig_col_src) or \
                        (orig_row_type_src != -1 and current_target_row == -1 and 1 <= current_target_col <= 4) or \
                        (orig_row_type_src == -1 and orig_col_src == 0 and current_target_row == -1 and 1 <= current_target_col <= 4 and self.current_reserve_card_obj is None):
                        
                        card_to_move_from_final_area = None
                        final_pile_idx_source_for_move = -1

                        # Karta była oryginalnie z Final i jest w self.moving_final_card_obj
                        if self.moving_final_card_obj and orig_row_type_src == -1 and 1 <= orig_col_src <= 4 and current_target_col == orig_col_src:
                            card_to_move_from_final_area = self.moving_final_card_obj
                            final_pile_idx_source_for_move = orig_col_src - 1
                            self.moving_final_card_obj = None
                        # Karta trafiła na Final pile (z tableau lub rezerwy) i jest na końcu stosu
                        elif current_target_row == -1 and 1 <= current_target_col <=4 and self.final_stacks[current_target_col-1]:
                            final_pile_idx_source_for_move = current_target_col -1
                            card_to_move_from_final_area = self.final_stacks[final_pile_idx_source_for_move].pop()
                            if self.moving_final_card_obj and self.moving_final_card_obj == card_to_move_from_final_area:
                                self.moving_final_card_obj = None # Jeśli to była ta sama karta co w moving_final_card_obj
                        
                        if card_to_move_from_final_area:
                            target_tab_col_to_place = final_pile_idx_source_for_move + 3 # Mapowanie kupki końcowej na kolumnę tableau
                            if 0 <= target_tab_col_to_place < len(self.tableau):
                                self.tableau[target_tab_col_to_place].append(card_to_move_from_final_area)
                                self.selected_cards_coords = [[target_tab_col_to_place, len(self.tableau[target_tab_col_to_place]) - 1]]
                            else: # Nie udało się przenieść
                                if orig_row_type_src == -1 and 1 <= orig_col_src <= 4: # Jeśli oryginalnie z Final, wraca do moving_final_card_obj
                                    self.moving_final_card_obj = card_to_move_from_final_area
                                else: # Inaczej (z tableau przez Final LUB z rezerwy przez Final) wraca na stos Final
                                    self.final_stacks[final_pile_idx_source_for_move].append(card_to_move_from_final_area)
                                self.message = "Brak odpowiedniej kolumny Tableau."
                                self.selected_cards_coords = [[current_target_col, -1]] # Kursor wraca na Final Pile
                        else:
                            self.message = "Błąd."
                            self.selected_cards_coords = [[current_target_col, -1]]

                        self.display_game(); return
        else: # Nawigacja bez podniesionej karty
            can_extend_further_up_in_tableau = False
            if current_row_sel != -1 and is_up: # Próba rozszerzenia zaznaczenia w górę w tej samej kolumnie tableau
                if current_row_sel > 0:
                    if 0 <= current_col_sel < len(self.tableau) and (current_row_sel - 1) < len(self.tableau[current_col_sel]):
                        card_above = self.tableau[current_col_sel][current_row_sel - 1]
                        if not card_above.hidden:
                            self.selected_cards_coords.insert(0, [current_col_sel, current_row_sel - 1])
                            can_extend_further_up_in_tableau = True
            
            if not can_extend_further_up_in_tableau: # Nie można rozszerzyć w górę lub ruch w dół
                special_reserve_interaction = False
                can_interact_with_reserve = self.first_reveal_done and \
                                            (self.current_reserve_card_obj or \
                                             (self.difficulty == 'trudny' and any(c for c in self.visible_draw3_cards if c is not None)))
                
                if can_interact_with_reserve: # Interakcja z rezerwą
                    if is_up and current_row_sel != -1 and (0 <= current_col_sel <= 2): # Z tableau (kolumny 0-2) na rezerwę
                        self.selected_cards_coords = [[0, -1]]
                        special_reserve_interaction = True
                    elif not is_up and current_col_sel == 0 and current_row_sel == -1: # Z rezerwy na tableau[0]
                        if self.tableau[0]:
                            self.selected_cards_coords = [[0, len(self.tableau[0])-1]]
                        else:
                            self.selected_cards_coords = [[0,0]] # Zaznacz miejsce na kartę
                        special_reserve_interaction = True
                
                if not special_reserve_interaction: # Inne przypadki nawigacji
                    if current_row_sel != -1: # Jesteśmy w tableau
                        if is_up: # Strzałka w górę z tableau (kolumny > 2) na kupkę końcową lub rezerwę
                            if current_col_sel > 2 :
                                target_final_idx = current_col_sel - 3
                                if 0 <= target_final_idx < 4 and self.final_stacks[target_final_idx]:
                                    self.selected_cards_coords = [[target_final_idx + 1, -1]]
                                elif can_interact_with_reserve:
                                    self.selected_cards_coords = [[0, -1]]
                            elif can_interact_with_reserve:
                                self.selected_cards_coords = [[0, -1]]
                        elif not is_up and len(self.selected_cards_coords) > 1: # Strzałka w dół, zmniejsz zaznaczenie w tableau
                            self.selected_cards_coords.pop(0)
                    else: # Górny rząd (rezerwa lub kupki końcowe)
                        target_tableau_col_non_confirmed = -1
                        if not is_up and 1 <= current_col_sel <= 4 : # Strzałka w dół z kupki końcowej
                            final_idx = current_col_sel - 1
                            target_tableau_col_non_confirmed = final_idx + 3 # Mapowanie na kolumnę tableau
                            if 0 <= target_tableau_col_non_confirmed < len(self.tableau):
                                if self.tableau[target_tableau_col_non_confirmed]:
                                    self.selected_cards_coords = [[target_tableau_col_non_confirmed, len(self.tableau[target_tableau_col_non_confirmed]) - 1]]
                                else: # Pusta kolumna tableau
                                    self.selected_cards_coords = [[target_tableau_col_non_confirmed, 0]]
        self.display_game()

    # Odkrywa nową kartę/karty z rezerwy.
    def reveal_reserve_card(self):
        if self.game_over:
            return
        if self.confirmed_selection:
            self.message = "Zakończ ruch."
            self.display_game()
            return
        
        self._save_state_for_undo()

        if not self.first_reveal_done:
            self.first_reveal_done = True
        
        self.move_count +=1
        
        if self.difficulty == 'łatwy':
            if self.current_reserve_card_obj is not None:
                self.waste_pile_draw1.append(self.current_reserve_card_obj)
                self.current_reserve_card_obj = None
            
            if not self.reserve_stock and self.waste_pile_draw1:
                self.reserve_stock = self.waste_pile_draw1[:]
                self.reserve_stock.reverse()
                self.waste_pile_draw1 = []
            
            if self.reserve_stock:
                self.current_reserve_card_obj = self.reserve_stock.pop(0)
            else:
                self.message = "Brak kart."
        
        elif self.difficulty == 'trudny':
            for card_in_window in reversed(self.visible_draw3_cards): # Przenieś widoczne karty do waste
                if card_in_window:
                    self.waste_pile_draw3.append(card_in_window)
            
            self.visible_draw3_cards = [None, None, None]
            drawn_this_turn = []
            
            for _ in range(3): # Dobierz do 3 kart
                if self.reserve_stock:
                    drawn_this_turn.append(self.reserve_stock.pop(0))
                elif self.waste_pile_draw3: # Jeśli rezerwa pusta, odwróć waste
                    if not self.reserve_stock and self.waste_pile_draw3:
                        self.reserve_stock = self.waste_pile_draw3[:]
                        self.waste_pile_draw3 = []
                        if self.reserve_stock:
                            drawn_this_turn.append(self.reserve_stock.pop(0))
                        else: break # Brak kart nawet po odwróceniu
                    else: break # Waste jest pusty
                else: break # Rezerwa i waste są puste
            
            for i in range(len(drawn_this_turn)):
                self.visible_draw3_cards[i] = drawn_this_turn[i]
            
            self._refill_draw3_window()
            
            if not self.current_reserve_card_obj and not self.reserve_stock and not self.waste_pile_draw3:
                self.message = "Brak kart."

        self.selected_cards_coords = [[0, -1]]
        self.display_game()

    # Główna funkcja odświeżająca i rysująca całe UI gry
    def display_game(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        self.display_reserve_and_final_stacks()
        print()
        self.display_tableau()
        
        status_line = Text()
        status_line.append(f"Ruchy: {self.move_count}\n", style="bold")
        
        self.rich_console.print(status_line)

        if self.game_over:
            self.rich_console.print(Panel(Text(self.message, justify="center"), title="[bold green]Koniec Gry![/bold green]", border_style="green", padding=(1,2)))
            self.rich_console.print("[bold yellow]Wciśnij Spację aby wyjść.[/bold yellow]")
        elif self.message:
            panel_style = "blue"
            if "Nie można" in self.message or "Błąd" in self.message:
                panel_style = "bold red"
            elif "udało się" in self.message.lower() or "przeniesiono" in self.message.lower() or "Karta na" in self.message or "Final -> Final" in self.message :
                panel_style = "bold green"
            self.rich_console.print(Panel(Text(self.message, justify="center"), border_style=panel_style ))
        elif self.confirmed_selection:
            self.rich_console.print(Text.assemble(
                ("Użyj ", "bold"),
                ("Strzałek", "bold magenta"),
                (", ", "bold"),
                ("Enter", "bold green"),
                (" aby umieścić, ", "bold"),
                ("Esc", "bold yellow"),
                (" aby anulować.", "bold")
            ))
        else:
            self.rich_console.print(Text.assemble(
                ("Użyj ", "bold"),
                ("Strzałek", "bold magenta"),
                (" do nawigacji. ", "bold"),
                ("Enter", "bold green"),
                (" aby podnieść.", "bold")
            ))
            self.rich_console.print(Text.assemble(
                ("\nNaciśnij: ", "bold"),
                ("'s'", "bold blue"), (" - Dobierz, ", "bold"),
                ("'c'", "bold yellow"), (" - Cofnij ", "bold"),
                ("(", "dim"), (f"{self.undo_actions_available}", "dim yellow" if self.undo_actions_available > 0 else "dim"), (")", "dim"),
                (", ", "bold"),
                ("Spacja", "bold red"), (" - Zakończ grę.", "bold")
            ))
        self.message = ""

    # Anuluje aktualnie podniesioną kartę (wciśnięcie Esc)
    def cancel_selection(self):
        if self.game_over:
            return
        if self.confirmed_selection:
            if self.game_state_history: # Usuń stan zapisany przy podniesieniu, bo ruch nie został dokonany
                self.game_state_history.pop()
                self.undo_actions_available = len(self.game_state_history)

            orig_c, orig_r_type = self.original_selected_coords[0]
            sel_c, sel_r = self.selected_cards_coords[0]
            src_tab = (orig_r_type != -1)
            src_res = (orig_r_type == -1 and orig_c == 0)
            src_fin = (orig_r_type == -1 and 1 <= orig_c <= 4)
            cur_fin = (sel_r == -1 and 1 <= sel_c <= 4)
            cur_tab = (sel_r != -1)
            
            if src_tab and cur_fin: # Z tableau na final -> karta wraca na tableau
                fin_idx_target = sel_c - 1
                if 0 <= fin_idx_target < len(self.final_stacks) and self.final_stacks[fin_idx_target]:
                    card_to_return = self.final_stacks[fin_idx_target].pop()
                    orig_tab_col, orig_tab_row = self.original_selected_coords[0]
                    self.tableau[orig_tab_col].insert(min(orig_tab_row, len(self.tableau[orig_tab_col])), card_to_return)
            
            elif src_res and cur_tab: # Z rezerwy na tableau -> karta wraca do rezerwy
                tab_col_where_card_is, tab_row_where_card_is = sel_c, sel_r
                if 0 <= tab_col_where_card_is < len(self.tableau) and \
                   0 <= tab_row_where_card_is < len(self.tableau[tab_col_where_card_is]) and \
                   self.tableau[tab_col_where_card_is][tab_row_where_card_is]:
                    
                    card_to_return = self.tableau[tab_col_where_card_is].pop(tab_row_where_card_is)
                    self.current_reserve_card_obj = card_to_return
                    if self.difficulty == 'trudny':
                        is_card_in_visible = any(self.visible_draw3_cards[i] is card_to_return for i in range(3))
                        if not is_card_in_visible:
                            for i in range(2, -1, -1):
                                if self.visible_draw3_cards[i] is None:
                                    self.visible_draw3_cards[i] = card_to_return
                                    is_card_in_visible = True; break
                            if not is_card_in_visible: self.visible_draw3_cards[2] = card_to_return
                        self._refill_draw3_window()
            
            elif src_fin and cur_tab: # Z final na tableau -> karta wraca na final
                tab_col_where_card_is, tab_row_where_card_is = sel_c, sel_r
                if 0 <= tab_col_where_card_is < len(self.tableau) and \
                   0 <= tab_row_where_card_is < len(self.tableau[tab_col_where_card_is]) and \
                   self.tableau[tab_col_where_card_is][tab_row_where_card_is]:
                    card_to_return = self.tableau[tab_col_where_card_is].pop(tab_row_where_card_is)
                    self.final_stacks[orig_c-1].append(card_to_return)
            
            elif src_tab and cur_tab and self.selected_cards_coords != self.original_selected_coords: # Z tableau na inne tableau
                self._undo_failed_tableau_move() # Przywróć karty na oryginalne miejsce w tableau
            
            elif self.moving_final_card_obj and src_fin: # Karta była na Final, została podniesiona (w moving_final_card_obj)
                if cur_fin and self.final_stacks[sel_c-1] and self.final_stacks[sel_c-1][-1] == self.moving_final_card_obj: # Jeśli jest na innej kupce final
                    self.final_stacks[sel_c-1].pop() # Usuń ją stamtąd
                elif sel_r == -1 and sel_c == 0: # Jeśli jest nad rezerwą
                    pass # Nic nie rób, current_reserve_card_obj powinien być None
                self.final_stacks[orig_c-1].append(self.moving_final_card_obj) # Przywróć na oryginalną kupkę final

            if self.original_selected_coords:
                self.selected_cards_coords = [c[:] for c in self.original_selected_coords]
            self.confirmed_selection = False
            self.original_selected_coords = []
            self.moving_final_card_obj = None
            self.message = "Anulowano."
        
        self.display_game()

    # Cofa ostatni wykonany ruch
    def undo_last_move(self):
        if self.game_over:
            return
        
        if self.confirmed_selection:
            self.message = "Zakończ lub anuluj (esc) obecny ruch przed cofnięciem."
            self.display_game()
            return
            
        if self.game_state_history:
            last_state = self.game_state_history.pop()
            self._restore_state_from_undo(last_state)
            self.undo_actions_available = len(self.game_state_history)
        else:
            self.message = "Brak ruchów do cofnięcia."

        self.display_game()

    # Główna pętla gry i obsługa klawiatury
    def run(self):
        self._display_main_menu()

        if self.difficulty is None:
            return
        
        self._initialize_game_state()
        self.display_game()
        kb_events = []

        def on_right(e):
            self.move_selection_horizontal(True)
        def on_left(e):
            self.move_selection_horizontal(False)
        def on_up(e):
            self.extend_selection(True)
        def on_down(e):
            self.extend_selection(False)
        def on_enter(e):
            self.confirm_selection()
        def on_s(e):
            self.reveal_reserve_card()
        def on_esc(e):
            self.cancel_selection()
        def on_c(e):
            self.undo_last_move()
        
        kb_events.append(keyboard.on_press_key("right", on_right, suppress=True))
        kb_events.append(keyboard.on_press_key("left", on_left, suppress=True))
        kb_events.append(keyboard.on_press_key("up", on_up, suppress=True))
        kb_events.append(keyboard.on_press_key("down", on_down, suppress=True))
        kb_events.append(keyboard.on_press_key("enter", on_enter, suppress=True))
        kb_events.append(keyboard.on_press_key("s", on_s, suppress=True))
        kb_events.append(keyboard.on_press_key("esc", on_esc, suppress=True))
        kb_events.append(keyboard.on_press_key("c", on_c, suppress=True))
        
        try:
            keyboard.wait('space')
        except Exception as e:
            print(f"Błąd: {e}")
        finally:
            for hook in kb_events:
                keyboard.unhook(hook)

        if not self.game_over:
            self.rich_console.print("\n[bold blue]Do zobaczenia![/bold blue]")


if __name__ == "__main__":
    game = Game()
    game.run()
