import os
import json
import random
import time
import numpy as np


from ganz_utils import print_colored
from ganz_utils import get_colored_string
from ganz_utils import calculate_remaining_dice
from abc import ABC, abstractmethod

class Strategy(ABC):
    @abstractmethod
    def choose_play(self, legal_plays, context):
        pass
# This is the main strategy I've been using -- loading various data from disk
class LoadStrategy(Strategy):
    def __init__(self, data=None):
        if data is None:
            # Load the strategy data from a JSON file
            success = False
            while not success:
                try:                    
                    current_directory = os.getcwd()
                    print("Current working directory:", current_directory)
                    with open('data\\strategy_data.json', 'r') as file:
                        self.data = json.load(file)
                    success = True  # If file opens successfully, set success to True
                except PermissionError:
                    print("Permission denied when trying to open strategy_data.json. Retrying in 1 second...")
                    time.sleep(1)  # Pause for 1 second before retrying
        else:
            self.data = data    
        
        # with open('data\\strategy_data.json', 'r') as file:
        #     self.data = json.load(file)

        self.color_scores = self.data['color_scores']
        self.turn_1_adjustments = self.data['turn_1_adjustments']
        self.turn_2_adjustments = self.data['turn_2_adjustments']
        self.turn_1_bonus_with_reroll = self.data['turn_1_bonus_with_reroll']
        self.turn_2_bonus_with_reroll = self.data['turn_2_bonus_with_reroll']
        self.white_die_bonus = {int(k): v for k, v in self.data['white_die_bonus'].items()}
        self.box_adjustments = self.data['box_adjustments']
        self.value_adjustments = self.data['value_adjustments']
        self.additional_purple_adjustments = self.data['additional_purple_adjustments']
        self.reroll_value = self.data['reroll_value']
        self.starting_goals = self.data['starting_goals']
        self.remaining_boxes_multiplier = self.data['remaining_boxes_multiplier']
        self.remaining_boxes_power = self.data['remaining_boxes_power']
        self.decline_extra_die_value = self.data['decline_extra_die_value']
        # Initialize the number of times each color has been scored
        #self.color_scores_count = {color: 0 for color in self.starting_goals}

    def start_new_game(self):
        self.color_scores_count = {color: 0 for color in self.starting_goals}
        self.no_legal_plays = 0



    def choose_play(self, legal_plays, context):
        debug_level = context['debug_level']
        current_round = context['current_round']
        current_turn = context['current_turn']
        rerolls_available = context['reroll_counter']
        is_bonus = context.get('is_bonus', False)  # Get is_bonus from the context, default to False

        remaining_scores = {color: self.starting_goals[color] - self.color_scores_count[color] for color in self.starting_goals}
        # Calculate the average remaining scores
        average_remaining_scores = sum(remaining_scores.values()) / len(remaining_scores)


        #print(remaining_scores)
        # Print the remaining scores in their respective colors
        remaining_scores_str = ', '.join([get_colored_string(str(remaining_scores[color]), color) for color in remaining_scores])
        if debug_level >4:
            print(f"Remaining scores: {remaining_scores_str}")

        rated_plays = []
        for play in legal_plays:
            color, value, score_color, index = play
            
#             if score_color is None:
# .                print ("Score color is none")

            
            if color == "Decline Extra Die":
                rating = self.decline_extra_die_value
                rating_details = ["Decline Extra Die"]
            elif color == 'reroll':
                rating = self.reroll_value
                rating_details = [f"Rerolls: {value}"]
            else: # it's a color
                rating = self.color_scores[score_color]
                rating_details = [f"Base: {round(rating)}"]

                # Adjust rating based on the number of dice left for turns 1 and 2
                if context['current_turn'] in [1, 2] and value is not None:
                    remaining_dice = calculate_remaining_dice(play, context['dice'])
                    if context['current_turn'] == 1:
                        adjustment = self.turn_1_adjustments[remaining_dice]
                        rating += adjustment
                        rating_details.append(f"T1: {round(adjustment)}")
                        # if rerolls_available > 0:
                        #     adjustment = self.turn_1_bonus_with_reroll[remaining_dice]
                        #     rating_details.append(f"R1: {adjustment}")
                        #     rating += adjustment
                    elif context['current_turn'] == 2:
                        adjustment = self.turn_2_adjustments[remaining_dice]
                        rating += adjustment
                        rating_details.append(f"T2: {round(adjustment)}")
                        if rerolls_available > 0:
                            adjustment = self.turn_2_bonus_with_reroll[remaining_dice] 
                            rating_details.append(f"R2: {round(adjustment)}")
                            rating += adjustment
                    #Add bonus if white die is remaining
                    # if color != 'white' and 'white' in [color for color, (value, in_play) in context['dice'].items() if in_play]:
                    #     adjustment = self.white_die_bonus[context['current_turn']]
                    #     rating += adjustment
                    #     rating_details.append(f"White: {adjustment}")
                    white_die_value = context['dice']['white'][0]
                    if color != 'white' and 'white' in [color for color, (value, in_play) in context['dice'].items() if in_play] and white_die_value >= value:
                        adjustment = self.white_die_bonus[context['current_turn']]
                        rating += adjustment
                        rating_details.append(f"White: {round(adjustment)}")



                # Apply adjustments for each color
                if score_color in self.box_adjustments and index < len(self.box_adjustments[score_color]):
                    adjustment = self.box_adjustments[score_color][index]
                    rating += adjustment
                    rating_details.append(f"Box: {round(adjustment)}")
                # Apply value adjustments for orange and purple
                if score_color in self.value_adjustments and 1 <= value <= 6:
                    adjustment = self.value_adjustments[score_color][value - 1]
                    rating += adjustment
                    rating_details.append(f"Value: {round(adjustment)}")

                # Apply additional adjustments for purple 6 based on the last filled purple box
                # if score_color == 'purple' and value == 6 and context['score_sheet']['purple']:
                #     last_filled_box_value = context['score_sheet']['purple'][-1]
                #     adjustment = self.additional_purple_adjustments[last_filled_box_value - 1]
                #     rating += adjustment
                #     rating_details.append(f"Purple6: {adjustment}")

                # Apply additional adjustments for purple 6 based on the last filled purple box
                if score_color == 'purple' and value == 6 and context['score_sheet']['purple']:
                    last_filled_box_value = next((val for val in reversed(context['score_sheet']['purple']) if val is not None), 0)
                    adjustment = self.additional_purple_adjustments[last_filled_box_value - 1]
                    rating += adjustment
                    rating_details.append(f"Purple6: {round(adjustment)}")


                # Add a bonus for high-value dice if a reroll is available
                # if rerolls_available > 0 and color in ['orange','purple'] and value is not None and value == 6:
                #     rating += self.reroll_bonus

                 # Adjust ranking based on the remaining scores needed for each color
                for color, remaining in remaining_scores.items():
                    if score_color == color:
                        difference = abs(remaining - average_remaining_scores)
                        if difference == 0:
                            adjustment = 0
                        else:                        
                            adjustment = round((difference ** self.remaining_boxes_power) * self.remaining_boxes_multiplier[current_round - 1])
                        # This actually lowers our average score, dispite that it shouldn't
                        if remaining < average_remaining_scores:
                            adjustment *= -1                        
                        rating += adjustment
                        rating_details.append(f"Remaining: {round(adjustment)}")

            rated_plays.append((play, rating, ' + '.join(rating_details)))



        # Check if rated_plays is empty
        if not rated_plays:
            self.no_legal_plays += 1
            return (None, None, None, None)  # Return a play indicating no legal moves
        
        # Sort plays by rating in descending order and display them
        rated_plays.sort(key=lambda x: x[1], reverse=True)

        if debug_level > 4:  # changed from 2 on 2/24 at 2:34 pm
            max_play_length = max(len(str(play)) for play, _, _ in rated_plays)
            max_rating_length = max(len(str(rating)) for _, rating, _ in rated_plays)
            for play, rating, details in rated_plays:
                play_str = f"{play[0]} {play[1]} {play[2]} {play[3]}"
                formatted_play = f"{play_str:{max_play_length}}"
                rounded_rating = round(rating)  # Round the rating to the nearest integer
                formatted_rating = f"{rounded_rating:{max_rating_length}}"
                #print_colored(f"Play: {formatted_play}, Rating: {formatted_rating} ({details})", color=play[0], debug_level=context['debug_level'], min_debug_level=5)
                print_colored(f"Play: {formatted_play}, Rating: {formatted_rating} ({details})", color=play[0], debug_level=context['debug_level'], min_debug_level=5)

        
        chosen_play = rated_plays[0][0]
        # if debug_level > 2:
        #     for play, rating, details in rated_plays:  
        #         print_colored(f"Play: {play}, Rating: {rating} ({details})", color=play[0], debug_level=context['debug_level'], min_debug_level=3)              

       # Update color_scores_count based on the chosen play
        if chosen_play[2] in self.color_scores_count:  # It could be reroll or decline extra die which have a color of None
            if not is_bonus:
                self.color_scores_count[chosen_play[2]] += 1
        # else:
        #     print(f"Internal Logic Error {chosen_play[2]} not a valid color on the scoresheet")

        # Return the chosen play
        return chosen_play
    
    def save_strategy_with_score(self, average_score):
        #filename = f"scores\Ganz Strategy Score {average_score:.2f}.json"
        
        folder_name = "scores"
        filename = os.path.join(folder_name, f"Ganz Strategy Score {average_score:.2f}.json")

        # Check if the folder exists, if not, create it
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)

        # Convert NumPy int32 values to Python int
        def convert_numpy(obj):
            if isinstance(obj, dict):
                return {k: convert_numpy(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy(v) for v in obj]
            elif isinstance(obj, np.int32):
                return int(obj)
            else:
                return obj

        data_converted = convert_numpy(self.data)

        with open(filename, 'w') as file:
            json.dump(data_converted, file, indent=4)
    
    # Temporarily Turning this off, beucase I'm worried it's messing with my random seed
    # def perform_genetic_algorithm(self, file1, file2):
    #     with open(file1, 'r') as f1, open(file2, 'r') as f2:
    #         data1 = json.load(f1)
    #         data2 = json.load(f2)

    #     merged_data = {}
    #     for key in data1:
    #         if random.random() < 0.5:
    #             merged_data[key] = data1[key]
    #         else:
    #             merged_data[key] = data2[key]

    #     with open('data\strategy_data.json', 'w') as outfile:
    #         json.dump(merged_data, outfile, indent=4)

    # Temporarily Turning this off, beucase I'm worried it's messing with my random seed
    # def randomly_manipulate_strategy_data(self):
        
    #     # List all JSON files in the data folder
    #     files = [f for f in os.listdir('scores') if f.endswith('.json')]
    #     # Extract the scores from the file names and find the file with the highest score
    #     highest_score_file = max(files, key=lambda x: float(x.split(' ')[3][:-5]))

    #     # Load the strategy data from the JSON file with the highest score
    #     with open(f'scores/{highest_score_file}', 'r') as file:
    #         data = json.load(file)

    #     print(f"Loading and manipulating {highest_score_file}")

    #     # Function to randomly adjust a value by -10% to +10%
    #     def adjust_value(value, parent_key=None):
    #         if isinstance(value, list):
    #             return [adjust_value(item, parent_key) for item in value]
    #         elif isinstance(value, dict):
    #             return {k: adjust_value(v, parent_key) for k, v in value.items()}
    #         elif isinstance(value, (int, float)):
    #             if parent_key != 'starting_goals':
    #                 offset = random.uniform(-1, 1)  # Random offset between -1 and 1
    #                 #return (value + offset) * (1 + random.uniform(-0.1, 0.1)) - offset
    #                 return (value) * (1 + random.uniform(-0.1, 0.1)) 
    #                 #return (value) * (1 + random.uniform(-0.01, 0.01)) 
    #                 #return random.uniform(-10,10) # - completely random.  Not related to original numbers
    #                 #return random.uniform(0,10) # - completely random.  Not related to original numbers - POSITIVE ONLY
    #             else:
    #                 return value
    #         else:
    #             return value

    #     # Randomly adjust the values in the strategy data
    #     adjusted_data = {key: adjust_value(value, key) for key, value in data.items()}

    #     # Save the adjusted strategy data back to the JSON file
    #     with open('data\\strategy_data.json', 'w') as file:
    #         json.dump(adjusted_data, file, indent=4)
    #         file.flush()  # Flush the data to disk

    def end_game_summary(self):
        overplayed_colors = {color: 0 for color in ['yellow', 'blue', 'green', 'orange', 'purple']}
        underplayed_colors = {color: 0 for color in ['yellow', 'blue', 'green', 'orange', 'purple']}
        remaining_scores = {color: self.starting_goals[color] - self.color_scores_count[color] for color in self.starting_goals}


        for color, score in remaining_scores.items():
            if score < 0:
                overplayed_colors[color] = abs(score)
            elif score > 0:
                underplayed_colors[color] = score

        return {
            'no_legal_plays': self.no_legal_plays,
            'overplayed_colors': overplayed_colors,
            'underplayed_colors': underplayed_colors
        }


class InteractiveStrategy(Strategy):
    def choose_play(self, legal_plays, context):
        if not legal_plays:
            return (None, None, None, None)

        # Sort legal plays by the value of the dice, in ascending order
        #sorted_legal_plays = sorted(legal_plays, key=lambda x: x[1])
        # Sort legal plays by the value of the dice, in ascending order
        sorted_legal_plays = sorted(legal_plays, key=lambda x: x[1] if x[1] is not None else float('inf'))


        print("\nLegal plays:")
        for i, play in enumerate(sorted_legal_plays):
            color, value, score_color, index = play
            score_color_str = "None" if score_color is None else score_color.upper()
            play_str = f"{color.upper()} ({value}) -> {score_color_str} {index + 1 if index is not None else ''}"
            # Change the foreground color of the text to the appropriate color
            colored_play_str = get_colored_string(play_str, color)
            print(f"{i + 1}: {colored_play_str}")

        while True:
            choice = input("Select a play (1-{}): ".format(len(sorted_legal_plays)))
            if choice.isdigit() and 1 <= int(choice) <= len(sorted_legal_plays):
                return sorted_legal_plays[int(choice) - 1]
            else:
                print("Invalid choice. Please try again.")




class ConservativeStrategy(Strategy):
    def choose_play(self, legal_plays, context):
        # Implement a conservative strategy here
        return min(legal_plays, key=lambda x: x[1])

class AggressiveStrategy(Strategy):
    def choose_play(self, legal_plays, context):
        # Implement an aggressive strategy here
        return max(legal_plays, key=lambda x: x[1])


class BasicStrategy(Strategy):
    # This averages around 83 points per game
    def choose_play(self, legal_plays, context):
        # Choose the lowest value for rounds 1 and 2, and the highest value for round 3
        if legal_plays:
            # Check if it's a blue or yellow bonus by looking for a value of None
            if any(play[1] is None for play in legal_plays):
                # For blue or yellow bonuses, choose the play with the highest "required" value
                return max(legal_plays, key=lambda x: (context['score_sheet'][x[2]][x[3]][1], x[1]))
            else:
                # For regular plays, choose based on the current turn
                if context['current_turn'] in [1, 2]:
                    return min(legal_plays, key=lambda x: x[1])
                else:
                    return max(legal_plays, key=lambda x: x[1])
        else:
            return (None, None, None, None)

class BasicStrategy2(Strategy):
    # Same as basic strategy, but picks the 2nd lowest die for roudns 1 and 2.  As expected this gives a lower average sclore.  Around 78 points
    def choose_play(self, legal_plays, context):
        # Choose the lowest value for rounds 1 and 2, and the highest value for round 3
        if legal_plays:
            # Check if it's a blue or yellow bonus by looking for a value of None
            if any(play[1] is None for play in legal_plays):
                # For blue or yellow bonuses, choose the play with the highest "required" value
                return max(legal_plays, key=lambda x: (context['score_sheet'][x[2]][x[3]][1], x[1]))
            else:
                # For regular plays, choose based on the current turn
                if context['current_turn'] in [1, 2]:
                    sorted_plays = sorted(legal_plays, key=lambda x: x[1])
                    if len(sorted_plays) >= 2:
                        return sorted_plays[1]  # Return the second lowest die
                    else:
                        return sorted_plays[0]  # Return the lowest die if there's only one
                else:
                    return max(legal_plays, key=lambda x: x[1])
        else:
            return (None, None, None, None)

