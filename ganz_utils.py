import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import winsound





# Define color codes for each die
COLOR_CODES = {
    'yellow': '\033[33m',
    'blue': '\033[34m',
    'green': '\033[32m',
    'orange': '\033[31m', 
    'purple': '\033[35m',
    'white': '\033[37m',
    'black': '\033[90m',  # Dark gray for visibility on black background
    'reroll': '\033[0m',  # Default
    'Decline Extra Die': '\033[96m',  # Cyan
    'extra_die': '\033[0m',  # Default
    'fox': '\033[0m',  # Default
    'default': '\033[0m'  # Resets the color
}

BACKGROUND_COLOR_CODES = {
    'yellow': '\033[43m',
    'blue': '\033[44m',
    'green': '\033[42m',
    'orange': '\033[41m',
    'purple': '\033[45m',
    'white': '\033[47m',
    'black': '\033[40m',
    'reroll': '\033[46m',  # Cyan background
    'Decline Extra Die': '\033[46m',  # Cyan background
    'default': '\033[49m'  # Default background color
}


def print_colored(message, color='default', min_debug_level=0, debug_level=0, end='\n'):
    #Sometimes debug_level is not getting set properly, so in those cases, let's just print it
    if debug_level == 0 or debug_level>= min_debug_level:
        color_code = COLOR_CODES.get(color, COLOR_CODES['default'])
        print(f"{color_code}{message}{COLOR_CODES['default']}", end=end)

def calculate_remaining_dice(chosen_play, dice):
    chosen_color, chosen_value = chosen_play[:2]
    remaining_dice = 0
    for color, (value, in_play) in dice.items():
        if in_play and value >= chosen_value:
            remaining_dice += 1
    remaining_dice -= 1 # Remove the die that was played
    return remaining_dice

# def get_colored_string(message, color, background=False):
#     background_code = '\033[41m' if background else ''
#     return f"{background_code}{COLOR_CODES[color]}{message}{COLOR_CODES['default']}"

def get_colored_string(message, foreground_color, background_color=None):
    foreground_code = COLOR_CODES[foreground_color]
    background_code = BACKGROUND_COLOR_CODES.get(background_color, '')
    return f"{background_code}{foreground_code}{message}{COLOR_CODES['default']}"

def send_email(email_body="This is the body"):
    # Your email credentials
    email = "krettig@gmail.com"
    password = "ijbe zylt jrfh ypjt"
    to_email="9372419474@vtext.com"
    #to_email="9372125786@vtext.com"

    # Email content
    subject = "PY"
    #email_body = "Your Python Script is done.  Yay!"

    # Creating the email message
    msg = MIMEText(email_body, 'plain')
    msg['From'] = email
    msg['To'] = to_email
    msg['Subject'] = subject

    # # Creating the email message
    # msg = MIMEMultipart()
    # msg['From'] = email
    # msg['To'] = to_email
    # msg['Subject'] = subject
    # msg.attach(MIMEText(body, 'plain'))

    # Sending the email
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(email, password)
    text = msg.as_string()
    server.sendmail(email, to_email, text)
    server.quit()

def playsound():
    # Play a sound at the end of the script
    #winsound.Beep(frequency, duration)

    # Example: Play a beep sound with a frequency of 1000 Hz for 1 second
    winsound.Beep(1000, 500)

#playsound()

#send_email()