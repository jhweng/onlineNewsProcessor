import tweepy
import Tkinter

import csv

consumer_key = 'Jrn5QqyUTfPZFfn91kqHLDFTi'
consumer_secret = 'TmdWDiEwgdJnnNXxVsnqhOB5CizN5pqseUz4wPiraODr216RjM'
access_token = '1058701211745091584-2SL7tz0JyhjkXhjzfwrt9TnyS31TvZ'
access_token_secret = 'd96xByA6Uqlyt7uRo0iSzGWr1H5uIIn8ghCR6PRIiXRf0'
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)


user = api.me()
print (user.name)


#####United Airlines
# Open/Create a file to append data
csvFile = open('qatar.csv', 'a')
#Use csv Writer
csvWriter = csv.writer(csvFile)

for tweet in tweepy.Cursor(api.search,q="QatarAirways",count=20,
                           lang="en",
                           since="2018-11-03").items():
    # print (tweet.created_at, tweet.text)
    csvWriter.writerow([tweet.created_at, tweet.text.encode('utf-8')])