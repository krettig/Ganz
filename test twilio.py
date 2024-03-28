from twilio.rest import Client
import os

# Your Twilio account SID and auth token
account_sid = 'AC844699c44666b9de0587721ce99856ae'
auth_token = '31913677b583356a2b5787e53967bb13'

# Your Twilio phone number and your personal phone number
twilio_number = '+19378136648'
your_number = '+19372419474'

# Initialize the Twilio client
client = Client(account_sid, auth_token)

os.system('cls')

# Send a text message
message = client.messages.create(
    body='Your Python script has finished running!',
    from_=twilio_number,
    to=your_number
)

print(f'Message sent: {message.sid}')
