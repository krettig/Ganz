import random
import time
from datetime import datetime
from ganz_utils import print_colored
from ganz_utils import get_colored_string
#from ganz_utils import calculate_remaining_dice

import os

from ganz_strategies import LoadStrategy, InteractiveStrategy, ConservativeStrategy, AggressiveStrategy, BasicStrategy, BasicStrategy2, RankStrategy


class GanzSchonClever:
    NUM_SIDES = 6  # Constant for the number of sides on each die

    def __init__(self, debug_level=5, seed=None):
        self.DEBUG_LEVEL = debug_level

        if seed is not None:
            self.seed_value = seed
        else:
            self.seed_value = time.time_ns() + random.randint(1, 1000)
       
        random.seed(self.seed_value)
        
        if debug_level > 2:
            print(f"Seed: {self.seed_value}")

        self.strategy = None  # Default strategy
        self.rounds = 6  # Total rounds in a game
        self.turns_per_round = 4  # Turns per round
        self.dice_colors = [ 'yellow', 'blue', 'green', 'orange', 'purple','white']
        # Initialize dice with the value and "In Play" status
        self.dice = {color: (0, True) for color in self.dice_colors}  # Value is set to 0 initially

        self.reroll_counter = 0  # Initialize reroll counter
        self.extra_die_counter = 0  # Initialize extra_die counter
        self.fox_counter = 0  # Initialize fox counter

        self.most_recently_scored_box = None  # Format: (color, index)


        self.score_sheet = {
            'yellow': [(val == 0, val) for val in [3, 6, 5, 0, 2, 1, 0, 5, 1, 0, 2, 4, 0, 3, 4, 6]],
            'blue': [(False, i + 2) for i in range(11)],  # Values from 2 to 12
            'green': [(False, (i % 5) + 1) if i != 10 else (False, 6) for i in range(11)],  # Values 1,2,3,4,5,1,2,3,4,5,6
            # Not sure why orange and purple boxes are being treated differntly right here.  TODO: make them work the same
            'orange': [None for _ in range(11)],  # Initialize with None values
            'purple': [None for _ in range(11)],  # Initialize with None values
        }
        
        self.score_multipliers = {
            'orange': {
                3: 2,  # Double the score for box 3
                6: 2,  # Double the score for box 6
                8: 2,  # Double the score for box 8
                10: 3  # Triple the score for box 10
            } 
        }
        
        self.bonuses = {
            'yellow': {
                (0, 1, 2, 3): {'bonus': 'blue'},
                (4, 5, 6, 7): {'bonus': 'orange', 'value': 4},
                (8, 9, 10, 11): { 'bonus': 'green'},
                (12, 13, 14, 15): { 'bonus': 'fox'},
                (0, 4, 8, 12): {'bonus': 'points', 'value': 10},
                (1, 5, 9, 13): {'bonus': 'points', 'value': 14},
                (2, 6, 10, 14): {'bonus': 'points', 'value': 16},
                (3, 7, 11, 15): {'bonus': 'points', 'value': 20},
                (0, 5, 10, 15): {'bonus': 'extra_die'}
            },
            'blue': {
                (0, 1, 2): { 'bonus': 'orange', 'value': 5},
                (3, 4, 5, 6): { 'bonus': 'yellow'},
                (7, 8, 9, 10): { 'bonus': 'fox'},
                (3,7): { 'bonus': 'reroll'},
                (0,4,8): { 'bonus': 'green'},
                (1,5,9): { 'bonus': 'purple', 'value': 6},
                (2,6,10): {'bonus': 'extra_die'}
            },
            'green': {
                3: { 'bonus': 'extra_die'},
                5: { 'bonus': 'blue'},
                6: { 'bonus': 'fox'},
                8: { 'bonus': 'purple', 'value': 6},
                9: { 'bonus': 'reroll'}
            },
            'orange': {
                2: { 'bonus': 'reroll'},
                #3: { 'bonus': 'x2'},
                4: { 'bonus': 'yellow'},
                5: { 'bonus': 'extra_die'},
                #6: { 'bonus': 'x2'},
                7: { 'bonus': 'fox'},
                #8: { 'bonus': 'x2'},
                9: { 'bonus': 'purple', 'value': 6}
                #10: { 'bonus': 'x3'}
            },
            'purple': {
                2: { 'bonus': 'reroll'},
                3: { 'bonus': 'blue'},
                4:{ 'bonus': 'extra_die'},
                5:{ 'bonus': 'yellow'},
                6:{ 'bonus': 'fox'},
                7:{ 'bonus': 'reroll'},
                8: { 'bonus': 'green'},
                9: { 'bonus': 'orange', 'value': 6},
                10: { 'bonus': 'extra_die'}
            } ,
            'round_bonuses': {
                1: {'bonus': 'reroll'},
                2: {'bonus': 'extra_die'},
                3: {'bonus': 'reroll'},
                4: {'bonus': 'black'}
            }
        }

        self.applied_bonuses = set()

        # self.fox_emoji = '🦊'
        # self.extra_die_emoji = '🎲'
        # self.reroll_emoji = '🔁'


        self.current_round = 1
        self.current_turn = 0
    
    def set_strategy(self, strategy):
        self.strategy = strategy

    def print_header(self):    
        
        if self.DEBUG_LEVEL > 2:
            current_datetime = datetime.now()
            formatted_datetime = f"{'*' * 40} {current_datetime} {'*' * 40}"
            print(formatted_datetime)
    def handle_round_start_bonuses(self):
        if self.current_round in self.bonuses['round_bonuses']:
            bonus_info = self.bonuses['round_bonuses'][self.current_round]
            bonus_type = bonus_info['bonus']
            if bonus_type == 'reroll':
                self.reroll_counter += 1
                print_colored("Bonus: Reroll", debug_level=self.DEBUG_LEVEL, min_debug_level=3)
            elif bonus_type == 'extra_die':
                self.extra_die_counter += 1
                print_colored("Bonus: extra_die", debug_level=self.DEBUG_LEVEL, min_debug_level=3)
            elif bonus_type == 'black':
                # Handle the black bonus
                legal_plays = self.find_legal_plays_for_black_bonus()
                if legal_plays:
                    chosen_play = self.call_strategy(legal_plays, is_bonus=True)
                    self.update_score_sheet(chosen_play)
                    # self.check_for_bonuses(chosen_play) handling this at the end of update_score_sheet
                else:
                    print_colored("No legal plays for black bonus", debug_level=self.DEBUG_LEVEL, min_debug_level=3)
        
  
    def roll_dice(self):
        # Simulate rolling the dice that are in play
        for color in self.dice:
            if self.dice[color][1]:  # Check if the die is in play
                self.dice[color] = (random.randint(1, self.NUM_SIDES), True)
    def print_dice_status(self):
        if self.DEBUG_LEVEL > 3:
            # Separate dice into 'in play' and 'not in play' lists
            in_play_dice = [(color, value) for color, (value, in_play) in self.dice.items() if in_play]
            not_in_play_dice = [(color, value) for color, (value, in_play) in self.dice.items() if not in_play]

            # Sort each list by the value of the dice
            in_play_dice.sort(key=lambda x: x[1])
            not_in_play_dice.sort(key=lambda x: x[1])

            # Calculate the total of the blue and white dice
            #blue_white_total = sum(value for color, (value, _) in self.dice.items() if color in ('blue', 'white'))
            # Format the lists into strings
            # in_play_str = ', '.join([get_colored_string(f"{color.upper()} ({value}/{blue_white_total})", color) if color in ('blue', 'white') else get_colored_string(f"{color.upper()} ({value})", color)
            #             for color, value in in_play_dice])
            # not_in_play_str = ', '.join([get_colored_string(f"{color} ({value})", color) for color, value in not_in_play_dice])

            # Format the lists into strings
            in_play_str = ', '.join([
                f"{get_colored_string(str(value), color)}/{get_colored_string(str(self.dice['white'][0]), 'white')}" if color == 'blue' else get_colored_string(str(value), color) for color, value in in_play_dice ])
            not_in_play_str = ', '.join([get_colored_string(str(value), color) for color, value in not_in_play_dice])


            in_play_str = ', '.join([
                f"{get_colored_string(str(value), color)}/{get_colored_string(str(self.dice['blue'][0]), 'blue')}" if color == 'white' else 
                f"{get_colored_string(str(value), color)}/{get_colored_string(str(self.dice['white'][0]), 'white')}" if color == 'blue' else 
                get_colored_string(str(value), color) 
                for color, value in in_play_dice
            ])
            not_in_play_str = ', '.join([get_colored_string(str(value), color) for color, value in not_in_play_dice])



            # Print the formatted strings
            if self.DEBUG_LEVEL > 2:
                if not_in_play_dice:
                    print(f"IN PLAY: {in_play_str} ---- NOT IN PLAY: {not_in_play_str}")
                else:
                    print(f"IN PLAY: {in_play_str}")


    def find_legal_play(self, color, value, legal_plays):
            if color in ('yellow', 'white'):
                for i, box in enumerate(self.score_sheet['yellow']):
                    scored, required = box  # Unpack the tuple for these colors
                    if not scored and (value is None or value == required):
                        legal_plays.append((color, value, 'yellow', i))
            if color in ('blue', 'white'):
                play_value = self.dice['white'][0] + self.dice['blue'][0] # Add the value of the white die
                for i, box in enumerate(self.score_sheet['blue']):
                    scored, required = box  # Unpack the tuple for these colors
                    if not scored and (value is None or play_value == required):    
                        legal_plays.append((color, value, 'blue' , i))
            if color in ('green', 'white'):
                for i, box in enumerate(self.score_sheet['green']):
                    scored, required = box  # Unpack the tuple for these colors
                    if not scored:
                        if value >= required:
                            legal_plays.append((color, value, 'green', i))  
                        break
            if color in ('orange', 'white'):
                for i, box in enumerate(self.score_sheet['orange']):
                    if box is None:  # Check if the box is empty
                        legal_plays.append((color, value, 'orange', i))
                        break  # Exit after finding the first empty box
            if color in ('purple', 'white'):
                # Find the last non-None value in the purple score sheet
                last_value = next((val for val in reversed(self.score_sheet['purple']) if val is not None), 0)
                if not self.score_sheet['purple'] or value > last_value or last_value == 6:
                    next_index = next((i for i, box in enumerate(self.score_sheet['purple']) if box is None), None)
                    if next_index is not None:
                        legal_plays.append((color, value, 'purple', next_index))  # Index is the next None position


            # if color in ('purple', 'white'):
            #     last_value = max(self.score_sheet['purple'] + [0])  # Get the last non-None value or 0 if the list is empty

            #     if not self.score_sheet['purple'] or value > self.score_sheet['purple'][-1] or self.score_sheet['purple'][-1] == 6:
            #         legal_plays.append((color, value, 'purple', len(self.score_sheet['purple'])))  # Index is the next position
   

    def find_legal_plays_from_dice(self,include_reroll=True):
        legal_plays = []
        for color, (value, in_play) in self.dice.items():
            if not in_play:
                continue  # Skip dice that are not in play
            self.find_legal_play(color, value, legal_plays)
        
        # Add reroll as a legal play if available
        if self.reroll_counter > 0 and self.current_turn < 4 and include_reroll:
            legal_plays.append(('reroll', self.reroll_counter, None, None))

        self.print_legal_plays(legal_plays)
        return legal_plays


    def print_legal_plays(self,legal_plays):
        if self.DEBUG_LEVEL >=6:
            # Print all legal scores
            print("Legal plays:")
            for score in legal_plays:
                print(f"  Die: {score[0]}, Value: {score[1]}, Score Color: {score[2]}, Box Index: {score[3]}")

    def find_legal_plays_for_black_bonus(self):
        legal_plays = []
        # Yellow and blue boxes
        for color in ['yellow', 'blue']:
            for i, box in enumerate(self.score_sheet[color]):
                if not box[0]:
                    legal_plays.append(('black', None, color, i))

        # Green, orange, and purple boxes
        for color in ['green', 'orange', 'purple']:
            next_index = next((i for i, box in enumerate(self.score_sheet[color]) if box is None or (color == 'green' and not box[0])), None)
            if next_index is not None:
                value = 6 if color in ['orange', 'purple'] else None
                legal_plays.append(('black', value, color, next_index))

        return legal_plays
           


    def call_strategy(self, legal_plays, is_bonus):
        if self.strategy:
            context = {
                'current_round': self.current_round,
                'current_turn': self.current_turn,
                'score_sheet': self.score_sheet, 
                'dice': self.dice,  # Include the dice in the context
                'debug_level': self.DEBUG_LEVEL,  # Include DEBUG_LEVEL in the context
                'reroll_counter' : self.reroll_counter,
                'is_bonus' : is_bonus           
            }
            
            return self.strategy.choose_play(legal_plays,context)
        else:
            # Default behavior or throw an error
            raise ValueError("Strategy not set!")
        

    def update_score_sheet(self, chosen_play):
        die_color, value, score_color, index = chosen_play

        if score_color is None:
            if self.DEBUG_LEVEL > 2:
                print("NO LEGAL PLAYS")
            return

        print_colored(f"Playing: {die_color.upper().ljust(6)} ({value})  ", color=die_color, debug_level=self.DEBUG_LEVEL, min_debug_level=3, end='\n' if self.DEBUG_LEVEL >= 3 else '')

        # Use the new method to apply the score and any multipliers
        self.apply_score_and_multiplier(score_color, index, value)     
        if self.DEBUG_LEVEL >=4:
            self.print_score_sheet()
        # Check for bonuses after every update to the score sheet
        self.check_for_bonuses(chosen_play)

    def apply_score_and_multiplier(self, score_color, index, value):
        #box_identifier = f"{score_color[0].upper()}{index + 1}"
        box_identifier = f"{score_color[0].upper()}{index}" # stick with 0 based
        # Save most recently scored box so we can highlight it on scorecard
        self.most_recently_scored_box = (score_color, index)
        # Apply the score to the score sheet
        if score_color in ['yellow', 'blue', 'green']:
            # Simply mark the box as scored for yellow, blue, and green
            self.score_sheet[score_color][index] = (True, self.score_sheet[score_color][index][1])  # Tuples are immutable
            required_value = self.score_sheet[score_color][index][1]
            box_identifier += f"-{required_value}"
            print_colored(f"Scored box: {box_identifier} [X]", color=score_color, debug_level=self.DEBUG_LEVEL, min_debug_level=3)
        elif score_color == 'orange':
            self.score_sheet[score_color][index] = value
            print_colored(f"Scored box: {box_identifier} [{value}]", color=score_color, debug_level=self.DEBUG_LEVEL, min_debug_level=3)
        # elif score_color == 'purple':
        #     self.score_sheet[score_color].append(value)
        #     print_colored(f"Scored box: {box_identifier} [{value}]", color=score_color, debug_level=self.DEBUG_LEVEL, min_debug_level=3)
        elif score_color == 'purple':
            next_index = next((i for i, box in enumerate(self.score_sheet['purple']) if box is None), None)
            if next_index is not None:
                self.score_sheet[score_color][next_index] = value
                print_colored(f"Scored box: {box_identifier} [{value}]", color=score_color, debug_level=self.DEBUG_LEVEL, min_debug_level=3)



        # Apply multipliers for orange score sheet
        if score_color == 'orange':
            multiplier = self.score_multipliers.get(score_color, {}).get(index, 1)
            if multiplier > 1:
                self.score_sheet[score_color][index] *= multiplier
                if self.DEBUG_LEVEL > 2:
                    print(f"Applied {multiplier}x multiplier to {score_color} box {index + 1}")

    def print_score_sheet(self):
        if self.DEBUG_LEVEL < 3:
            return

        # Initialize strings for each row
        row1 = get_colored_string("Yellow", 'yellow') + "\t\t" + get_colored_string("Blue", 'blue')
        row2 = ""
        row3 = ""
        row4 = ""
        row5 = ""


        # def triggers_bonus_color(color, index):
        #     if color in self.bonuses:
        #         for pattern, bonus_info in self.bonuses[color].items():
        #             if isinstance(pattern, tuple) and index in pattern:
        #                 return bonus_info['bonus']  # Return the bonus type
        #     return None

        # Function to check if a box triggers a bonus
        def triggers_bonus(color, index):
            if color in self.bonuses:
                for pattern, bonus_info in self.bonuses[color].items():
                    if isinstance(pattern, tuple):
                        if index in pattern and all(self.score_sheet[color][i][0] for i in pattern if i != index):
                            return bonus_info['bonus']
                    elif index == pattern:
                        return bonus_info['bonus']
            return False
        def get_bonus_icon(bonus_type):
            if bonus_type == 'reroll':
                #return self.reroll_emoji
                return '@'
            elif bonus_type == 'extra_die':
                #return self.extra_die_emoji
                return '+'
            elif bonus_type == 'fox':
                #return self.fox_emoji
                return '^'  # fox ear
            else:
                return None

        # Fill in the strings with the score sheet values
        for i in range(4):  # Four rows for yellow
            yellow_row = ""
            for j in range(4):  # Four columns for yellow
                index = i * 4 + j
                if index < len(self.score_sheet['yellow']):
                    scored, required = self.score_sheet['yellow'][index]
                    is_recently_scored = ('yellow' == self.most_recently_scored_box[0] and index == self.most_recently_scored_box[1])
                    #bonus_color = 'cyan' if triggers_bonus('yellow', index) else None - No individual boxes in yellow or blue
                    background_color = 'yellow' if is_recently_scored else None
                    yellow_row += get_colored_string('X ', 'yellow', background_color=background_color) if scored else f"{required} "
            if i == 0:
                row2 += yellow_row + "\t"
            elif i == 1:
                row3 += yellow_row + "\t"
            elif i == 2:
                row4 += yellow_row + "\t"
            elif i == 3:
                row5 += yellow_row

        for i in range(3):  # Three rows for blue
            blue_row = ""
            for j in range(4):  # Four columns for blue
                # This index should loop from -1 to 11, but the -1 is skipped, so 0 to 11 which is the blue index range (zero based)
                index = i * 4 + j - 1 #if i > 0 else 0)  # Adjust index for the first row having only three boxes
                if i == 0 and j == 0:  # Skip the first box in the first row
                    blue_row += '   '  # Blank placeholder for the missing box
                    continue
                if index <= len(self.score_sheet['blue']):
                    scored, required = self.score_sheet['blue'][index]
                    is_recently_scored = ('blue' == self.most_recently_scored_box[0] and index == self.most_recently_scored_box[1])
                    background_color = 'blue' if is_recently_scored else None
                    blue_row += get_colored_string(f"{required:2} ", 'blue',background_color=background_color) if scored else f"{required:2} "
            if i == 0:
                row2 += blue_row + "\t"
            elif i == 1:
                row3 += blue_row + "\t"
            elif i == 2:
                row4 += blue_row + "\t"

        

        green_str = get_colored_string("Green: ", 'green')
        for index, box in enumerate(self.score_sheet['green']):
            
            if box[0]:  # Box has already been scored
                is_recently_scored = ('green' == self.most_recently_scored_box[0] and index == self.most_recently_scored_box[1])
                green_str += get_colored_string('X ', 'green', background_color='green' if is_recently_scored else 'default')
            else:  # Box has not been scored
                bonus_type = triggers_bonus('green', index)
                bonus_icon = None  # Initialize bonus_icon
                if bonus_type:
                        bonus_icon=get_bonus_icon(bonus_type)
                green_str += get_colored_string(f"{bonus_icon if bonus_icon else '>'}{box[1]} ", foreground_color=bonus_type if bonus_type else 'default', background_color=background_color)
        row2 += green_str



        for color in ['orange', 'purple']:
            score_str = get_colored_string(f"{color.capitalize()}: ", color)
            for index, value in enumerate(self.score_sheet[color]):
                is_recently_scored = (self.most_recently_scored_box is not None and color == self.most_recently_scored_box[0] and index == self.most_recently_scored_box[1])
                background_color = color if is_recently_scored else 'default'
                # If the box has already been scored
                if value is not None:
                    score_str += get_colored_string(f"{value} ", color, background_color=background_color)
                else: # It's an unscored box
                    # Check if this square would trigger a bonus
                    bonus_type = triggers_bonus(color, index)
                    if bonus_type:
                        bonus_icon=get_bonus_icon(bonus_type)
                        score_str += get_colored_string(f"{bonus_icon if bonus_icon else '*'} ", bonus_type, background_color='default')                        
                    else:
                        score_str += get_colored_string("* ", 'default', background_color=background_color)                        
            if color == 'orange':
                row3 += score_str
            else:  # color == 'purple':
                for _ in range(len(self.score_sheet[color]), 11):
                    score_str += "* "  # Add empty spaces for purple, Hmm... not totally sure why this is necessary
                row4 += score_str
            

        # orange_str = get_colored_string("Orange: ", 'orange')
        # for i, box in enumerate(self.score_sheet['orange']):
        #     is_recently_scored = (self.most_recently_scored_box is not None and 'orange' == self.most_recently_scored_box[0] and i == self.most_recently_scored_box[1])
        #     bonus_color = 'cyan' if triggers_bonus('orange', index) else None             
        #     background_color = 'orange' if is_recently_scored else bonus_color
        #     orange_str += get_colored_string(f"{box} ", 'orange', background_color=background_color) if box is not None else "* "
        # row3 += orange_str


        # purple_str = get_colored_string("Purple: ", 'purple')
        # for index, value in enumerate(self.score_sheet['purple']):
        #     is_recently_scored = ('purple' == self.most_recently_scored_box[0] and index == self.most_recently_scored_box[1])
        #     bonus_color = 'cyan' if triggers_bonus('purple', index) else None
        #     background_color = 'purple' if is_recently_scored else bonus_color
        #     purple_str += get_colored_string(f"{value} ", 'purple',background_color=background_color)
        # for _ in range(len(self.score_sheet['purple']), 11):
        #     purple_str += "* "  # O for empty spaces in purple
        # row4 += purple_str

        # Print the combined strings
        print(row1)
        print(row2)
        print(row3)
        print(row4)
        print(row5)
        print()  # Additional newline for separatio

    def check_for_bonuses(self, chosen_play):
        die_color, value, score_color, index = chosen_play
        print_colored(f"Checking for Bonuses: {chosen_play}", debug_level=self.DEBUG_LEVEL, min_debug_level=9)

        # Check for bonuses based on the selected die
        for pattern, bonus_info in self.bonuses[score_color].items():
            bonus_type = None
            if score_color in ['yellow','blue']: #TUPLE BONUS
                if index in pattern and all(self.score_sheet[score_color][i][0] for i in pattern):
                    bonus_type = bonus_info['bonus']
            else:  #It's Green / Orange / Purple - integer bonus type
                if index == pattern:
                    bonus_type = bonus_info['bonus']
            if bonus_type is None:
                continue # This was "next"  That might have been the error
            # This check should not be needed, but when we had chained bonuses, with recursion, It seems like Python got confused and checked the same bonuses again (
            # (and gave the same bonuses again).  Yes, I'm blaming Python and not my debugging skills
            elif (bonus_type, pattern)  in self.applied_bonuses:
                print_colored(f"Bonus {bonus_type} for pattern {pattern} already applied.", debug_level=self.DEBUG_LEVEL, min_debug_level=3)
                continue
            else:
                print_colored(f"{'*' * 40} Bonus Found: {bonus_type} {'*' * 40}", debug_level=self.DEBUG_LEVEL, min_debug_level=3)
                self.applied_bonuses.add(bonus_type)

                if bonus_type in ['green', 'orange', 'purple']:
                    # Score the next box for green, orange, or purple
                    if bonus_type == 'green':
                        next_index = next((i for i, box in enumerate(self.score_sheet[bonus_type]) if not box[0]), None)
                    else:
                        next_index = next((i for i, box in enumerate(self.score_sheet[bonus_type]) if box is None), None)
                    if next_index is not None:
                        self.update_score_sheet((bonus_type, bonus_info.get('value', value), bonus_type, next_index))
                        #self.check_for_bonuses((bonus_type, bonus_info.get('value', value), bonus_type, next_index)) handling in update_score_sheet
                        print_colored(f"BONUS scored: {bonus_type}", debug_level=self.DEBUG_LEVEL, min_debug_level=3)
                elif bonus_type in ['yellow', 'blue']:
                    legal_plays = []
                    self.find_legal_play(bonus_type, None, legal_plays)
                    if legal_plays:
                        self.print_legal_plays(legal_plays)
                        chosen_play = self.call_strategy(legal_plays, is_bonus=True)
                        self.update_score_sheet(chosen_play)
                        #self.check_for_bonuses(chosen_play) handling in update_score_sheet                               
                    else: 
                        print_colored(f"No legal plays for {bonus_type} bonus", debug_level=self.DEBUG_LEVEL, min_debug_level=3)
                elif bonus_type == 'reroll':
                    self.reroll_counter += 1
                    print_colored("Bonus: Reroll", debug_level=self.DEBUG_LEVEL, min_debug_level=3)
                elif bonus_type == 'extra_die':
                    self.extra_die_counter += 1
                    print_colored("Bonus: extra_die", debug_level=self.DEBUG_LEVEL, min_debug_level=3)
                elif bonus_type == 'fox':
                    self.fox_counter += 1
                    print_colored("Bonus: Fox", debug_level=self.DEBUG_LEVEL, min_debug_level=3)
                elif bonus_type == "points":
                    print_colored(f"You just got {bonus_info['value']} bonus points in {score_color}", debug_level=self.DEBUG_LEVEL, min_debug_level=3)
                else:
                    print_colored(f"Unhandled BONUS TYPE: {bonus_type} !!!", debug_level=self.DEBUG_LEVEL, min_debug_level=3)
        # else:
        #     print_colored("No Bonus Found", debug_level=self.DEBUG_LEVEL, min_debug_level=10)
        
    def prepare_passive_round(self):
        # Sort all dice by their value in ascending order
        sorted_dice = sorted(self.dice.items(), key=lambda x: x[1][0])

        # Mark the lowest three dice as in play
        for color, _ in sorted_dice[:3]:
            self.dice[color] = (self.dice[color][0], True)  # Set "In Play" to True

        # Mark the highest three dice as not in play
        for color, _ in sorted_dice[-3:]:
            self.dice[color] = (self.dice[color][0], False)  # Set "In Play" to False

        
    def handle_extra_die_bonuses(self):
        if self.extra_die_counter > 0:
            # Set all dice to in-play
            for color in self.dice:
                self.dice[color] = (self.dice[color][0], True)

            while self.extra_die_counter > 0:
                # Find all legal plays
                if self.DEBUG_LEVEL > 2:
                    print(f"{'*' * 40}  Playing an extra_die  {'*' * 40}")
                self.print_dice_status()
                legal_plays = self.find_legal_plays_from_dice(include_reroll=False)

                # Add the option to decline playing the extra_die
                legal_plays.append(('Decline Extra Die', 0, None, None)) # Using 0 as Die Value for sort order in Interactive

                if legal_plays:
                    chosen_play = self.call_strategy(legal_plays, is_bonus=False) # Even though it's the extra die bonus, the player is choosing, not the bonus
                    
                    if chosen_play[0] == 'Decline Extra Die':
                        if self.DEBUG_LEVEL > 2:
                            print("Declined to play extra_die")
                        return  # Exit the method without decrementing the extra_die counter

                    
                    self.update_score_sheet(chosen_play)
                    #self.check_for_bonuses(chosen_play) - handling in update_score_sheet

                    # Mark the chosen die as not in play.  This does not affect lower dice
                    self.dice[chosen_play[0]] = (self.dice[chosen_play[0]][0], False)  # Set "In Play" to False, keep the value

                else:
                    if self.DEBUG_LEVEL > 2:
                        print("No legal plays for extra_die bonus")
                    return

                # Decrement the extra_die bonus
                self.extra_die_counter -= 1
    



    def calculate_score(self):
        # Yellow scoring
        yellow_score = 0
        yellow_patterns = [(0, 4, 8, 12, 10), (1, 5, 9, 13, 14), (2, 6, 10, 14, 16), (3, 7, 11, 15, 20)]
        for pattern in yellow_patterns:
            if all(self.score_sheet['yellow'][i][0] for i in pattern[:-1]):
                yellow_score += pattern[-1]

        # Blue scoring
        blue_score = [0, 1, 2, 4, 7, 11, 16, 22, 29, 37, 46, 56][sum(box[0] for box in self.score_sheet['blue'])]

        # Green scoring
        green_score = [0, 1, 3, 6, 10, 15, 21, 28, 36, 45, 55, 66][sum(box[0] for box in self.score_sheet['green'])]

        # Orange scoring
        orange_score = sum(value for i, value in enumerate(self.score_sheet['orange']) if value is not None)
        # Don't need to double or triple Orange value here since it was already done before it was put in the score box
        # orange_score += sum(value for i, value in enumerate(self.score_sheet['orange']) if value is not None and i in (3, 6, 8))  # Double scoring for boxes 3, 6, and 8
        # orange_score += 2 * sum(value for i, value in enumerate(self.score_sheet['orange']) if value is not None and i == 10)  # Triple scoring for box 10

        # Purple scoring
        # Not sure why this is not identical to Orange above
        purple_score = sum(value for value in self.score_sheet['purple'] if value is not None)

        #purple_score = sum(self.score_sheet['purple'])

        foxes = {
        'yellow': all(self.score_sheet['yellow'][i][0] for i in [12, 13, 14, 15]),
        'blue': all(self.score_sheet['blue'][i][0] for i in [7, 8, 9, 10]),
        'green': self.score_sheet['green'][6][0],
        'orange': self.score_sheet['orange'][7] is not None,
        'purple': self.score_sheet['purple'][6] is not None
        }

        # Count the total number of foxes achieved
        total_foxes = sum(foxes.values())

        lowest_score = min(yellow_score, blue_score, green_score, orange_score, purple_score)
        # Calculate the fox points
        fox_points = total_foxes * lowest_score

        # Print which color foxes were achieved
        if self.DEBUG_LEVEL > 3:          
            print("Foxes achieved:")
            for color, achieved in foxes.items():
                if achieved:
                    print(f"  {color.capitalize()} fox")

            # Print the total number of foxes and fox points
            print(f"Total foxes: {total_foxes}")
        

        # Total score
        total_score = yellow_score + blue_score + green_score + orange_score + purple_score + fox_points
        if self.DEBUG_LEVEL > 2:
            print(f"Yellow Score: {yellow_score}")
            print(f"Blue Score: {blue_score}")
            print(f"Green Score: {green_score}")
            print(f"Orange Score: {orange_score}")
            print(f"Purple Score: {purple_score}")
            print(f"Fox points: {fox_points}")
          # Clear the terminal output (cross-platform)
        if self.DEBUG_LEVEL > 2:
            print(f"Total Score: {total_score}")

        return total_score
    
    

        
    




       

    
    def play_turn(self):
        self.current_turn += 1
        if self.DEBUG_LEVEL>3:
            print()  # This will print an extra line
       
        turn_output = f"{'*' * 40}  Round {self.current_round}, "
        turn_output += "Passive Turn" if self.current_turn == 4 else f"Turn {self.current_turn}"

        # Add indicators for extra_die and rerolls
        extra_die_indicator = '+' * self.extra_die_counter
        reroll_indicator = '@' * self.reroll_counter
        turn_output += f"  {extra_die_indicator}{reroll_indicator}"
        turn_output += f"   {'*' * 40}"

        if self.DEBUG_LEVEL > 2:
            print(turn_output, end='\n' if self.DEBUG_LEVEL >= 2 else ' - ')
        
        self.roll_dice()
        
        if self.current_turn==4:
            self.prepare_passive_round()

        self.print_dice_status()
        # Find legal plays from the current dice
        legal_plays = self.find_legal_plays_from_dice()

        if legal_plays:  # If there are legal plays, select a die
            
            chosen_play = self.call_strategy(legal_plays, is_bonus=False)  # This is the main place we play the dice
        else:  # If there are no legal plays
            if self.current_turn <= 3:  # In ACTIVE MODE, there are no legal plays
                if self.DEBUG_LEVEL > 2:
                    print("NO LEGAL PLAYS")
                chosen_play = (None, None, None, None)
            else:  # In PASSIVE MODE, handle the SPECIAL CASE
                if self.DEBUG_LEVEL > 2:
                    print("SPECIAL CASE !!!")
                # Set all dice to in play
                for color in self.dice:
                    self.dice[color] = (self.dice[color][0], True)
                # Find legal plays again and select a die
                legal_plays = self.find_legal_plays_from_dice()
                if legal_plays:
                    chosen_play = self.call_strategy(legal_plays, is_bonus=False) # Passive Play die choice
                else:
                    if self.DEBUG_LEVEL > 2:
                        print("STILL NO LEGAL PLAYS -- EVEN IN SPECIAL CASE")
                    chosen_play = (None, None, None, None)

        #print(f"Selected die: {chosen_play}")
        
        if chosen_play[0] == 'reroll':
            self.roll_dice()
            self.reroll_counter -= 1
            if self.DEBUG_LEVEL > 2:
                print("Reroll used. Remaining rerolls:", self.reroll_counter)
            self.print_dice_status()
            # Re-evaluate legal plays after reroll and select a new play
            legal_plays = self.find_legal_plays_from_dice()
            chosen_play = self.call_strategy(legal_plays, is_bonus=False) # is re-roll


        self.update_score_sheet(chosen_play)

        # Check for bonuses after updating the score sheet
        #self.check_for_bonuses(chosen_play) handlng in update_score_sheet

        # Remove selected die and any lower valued dice
        if chosen_play != (None, None, None, None):
            for color in self.dice:
                die_value, in_play = self.dice[color]
                if in_play and (die_value < chosen_play[1] or color == chosen_play[0]):
                    self.dice[color] = (die_value, False)  # Set "In Play" to False, keep the value


    def play_round(self):
        if self.DEBUG_LEVEL > 2:
            print(f"\nStarting Round {self.current_round}")
        
        self.handle_round_start_bonuses()  # Handle round start bonuses


        for _ in range(self.turns_per_round):
            self.play_turn()
            # Handle extra_die bonuses at the end of rounds 3 and 4
            if self.current_turn in [3, 4] and self.extra_die_counter > 0:
                #print_colored("PLAYING extra_die !!!")
                self.handle_extra_die_bonuses()
        
        self.current_round += 1

        self.dice = {color: (0, True) for color in self.dice_colors}  # Reset dice for the new round
        self.current_turn = 0

    def play_game(self):

        self.print_header()        

        for _ in range(self.rounds):
            self.play_round()
        
        self.print_score_sheet()

        return self.calculate_score()

def print_summary(start_time, end_time, elapsed_time, i, average_score, debug_level, lowest_score, lowest_score_seed, highest_score, highest_score_seed):
    end_time = datetime.now()
    elapsed_time = end_time - start_time
    print(f"End Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}, Elapsed Time: {elapsed_time}, Games Played: {i + 1}, Average Score: {average_score:.2f}, debug_level: {debug_level}")
    if debug_level > 1:
        print(f"Lowest Score: {lowest_score}, Seed: {lowest_score_seed} -- Highest Score: {highest_score}, Seed: {highest_score_seed}")


def calculate_average_score(total_score, i):
    return total_score / (i + 1)

def update_minmix_scores(score, seed_value, lowest_score, lowest_score_seed, highest_score, highest_score_seed, debug_level):
    if score < lowest_score:
        lowest_score = score
        lowest_score_seed = seed_value
    if score > highest_score:
        highest_score = score
        highest_score_seed = seed_value
    if debug_level > 1:
        print(f"Random seed: {seed_value}, Score: {score}")

def should_break_early(i, total_score, highest_average_score):
    if (i + 1) % 1000 == 0:
        average_score = total_score / (i + 1)
        if average_score < highest_average_score:
            print(f"Breaking early... Game number: {i + 1}, Average score: {average_score:.2f}")
            return True
    return False

def execute_manipulate_strategy():
    strategy = LoadStrategy()
    strategy.randomly_manipulate_strategy_data()

def initialize_game(debug_level, seed):
    game = GanzSchonClever(debug_level=debug_level, seed=seed)
    game.set_strategy(LoadStrategy())
    return game

# Function to play the game num_games times and calculate average score
def play_games(num_games, seed=None, manipulate_strategy=False):
    #os.system('cls' if os.name == 'nt' else 'clear')
    # Add a small delay to allow the terminal to reset its scroll position
    #time.sleep(0.1)
    
    if manipulate_strategy:
        execute_manipulate_strategy()

    total_score = 0
    lowest_score = float('inf')
    lowest_score_seed = None
    highest_score = 0
    highest_score_seed = None
    

    #Debug Levels
    # 0 = Not using this since it could happen in error
    # 1 = Only display time, games played, average
    # 2 = Same as above, plus Game with minimum score and seed (to investigate further)
    # 3 = EAch game's seed and score
    # 4 = Game Summary.  See the rolls and plays, but not the calculations
    # 5 = Everything
    # 10 = Even more - could be annoying
    debug_level = 5 if num_games == 1 else (2 if num_games <= 10 else 1)
    
    if num_games > 1:
        seed = None

    start_time = datetime.now()
    print(f"Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    for i in range(num_games):
        game = initialize_game(debug_level, seed)
        score = game.play_game()
        total_score += score
        update_minmix_scores(score, game.seed_value, lowest_score, lowest_score_seed, highest_score, highest_score_seed, debug_level)

        if should_break_early(i, total_score, highest_average_score):
            break

    average_score = calculate_average_score(total_score, i)
    end_time = datetime.now()
    elapsed_time = end_time - start_time
    print_summary(start_time, end_time, elapsed_time, i, average_score, debug_level, lowest_score, lowest_score_seed, highest_score, highest_score_seed)
    return average_score if i + 1 > 9000 else 0

    
#################### Main loop ##################
os.system('cls' if os.name == 'nt' else 'clear')

#Imporant Variables, switch here instead of elsewhere
run_forever = True
manipulate_strategy = False # If true, it will pull highest score from SCORES folder
highest_average_score = 0

if run_forever:
    while True:
        average_score = play_games(10000, manipulate_strategy=manipulate_strategy)
        if average_score > highest_average_score:
            highest_average_score = average_score
            strategy = LoadStrategy()
            strategy.save_strategy_with_score(average_score)
else:
    play_games(1, manipulate_strategy=manipulate_strategy)



