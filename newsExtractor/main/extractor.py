import feedparser as fp
import newspaper
import json
import objectpath
import os
import tweepy
import operator
import datetime
import dateutil.relativedelta
from time import mktime
# from tkinter import *
# from tkinter import ttk
from newspaper import Article
from datetime import datetime
from collections import defaultdict
from collections import namedtuple
from nltk.corpus import stopwords
from difflib import SequenceMatcher

import constants
import twitterAuthentic
import run_parameters as param


def _json_object_hook(d):
    return namedtuple('X', d.keys())(*d.values())


def json2obj(in_data):
    return json.loads(in_data, object_hook=_json_object_hook)


def remove_extra_chars(in_str):
    out_str = str(in_str)
    out_str = out_str.replace(',', '')
    out_str = out_str.replace('.', '')
    out_str = out_str.replace('!', '')
    out_str = out_str.replace('?', '')
    out_str = out_str.replace('"', '')
    out_str = out_str.replace(':', '')
    out_str = out_str.replace('(', '')
    out_str = out_str.replace(')', '')
    return out_str


def is_valid_word(in_word):
    return in_word != '-'


def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()


data = {}
data['newspapers'] = {}

news_dir = 'news/'
keywords_dir = str(param.mostFreqKeywords) + '_keywords/'
sources_urls = 'NewsPapers.json'
str_retweet_filter = ' -filter:retweets'


# ==============================================================
# ============  Extracting news from sources  ==================
# ==============================================================

# Loads the JSON files with news sites
if param._comments:
    print('Loading news sources ...')
with open(sources_urls) as data_file:
    companies = json.load(data_file)


if param._do_extract_news:
    # checking if folder exists and warning about overwritting
    if not os.path.exists(news_dir):
        if param._comments:
            print('Creating folder ' + news_dir + ' ...')
            os.makedirs(news_dir)
    else:
        if param._comments:
            print('Folder ' + news_dir + ' already exists, same name files will be overwritten.')

    count = 1

    # Iterate through each news company
    for company, value in companies.items():
        company_dir = news_dir + str(company) + '/'
        if not os.path.exists(company_dir):
            if param._comments:
                print('Creating folder ' + company_dir)
            os.makedirs(company_dir)

        # If a RSS link is provided in the JSON file, this will be the first choice.
        # Reason for this is that, RSS feeds often give more consistent and correct data.
        if 'rss' in value:
            d = fp.parse(value['rss'])
            if param._comments:
                print("Downloading articles from ", company)
            newsPaper = {
                "rss": value['rss'],
                "link": value['link'],
                "articles": []
            }
            for entry in d.entries:
                # Check if publish date is provided, if no the article is skipped.
                # This is done to keep consistency in the data and to keep the script from crashing.
                if hasattr(entry, 'published'):
                    if count > param.num_of_articles:
                        break
                    article = {}
                    article['link'] = entry.link
                    date = entry.published_parsed
                    article['published'] = datetime.fromtimestamp(mktime(date)).isoformat()
                    try:
                        content = Article(entry.link)
                        content.download()
                        content.parse()
                    except Exception as e:
                        # If the download for some reason fails (ex. 404) the script will continue downloading
                        # the next article.
                        print(e)
                        print("continuing...")
                        continue
                    article['title'] = content.title
                    article['text'] = content.text
                    newsPaper['articles'].append(article)
                    if param._comments:
                        print(count, "articles downloaded from", company, ", url: ", entry.link)
                    count = count + 1
        else:
            # This is the fallback method if a RSS-feed link is not provided.
            # It uses the python newspaper library to extract articles
            if param._comments:
                print("Building site for ", company)
            paper = newspaper.build(value['link'], memoize_articles=False)
            newsPaper = {
                "link": value['link'],
                "articles": []
            }
            noneTypeCount = 0
            for content in paper.articles:
                if count > param.num_of_articles:
                    break
                try:
                    content.download()
                    content.parse()
                except Exception as e:
                    print(e)
                    print("continuing...")
                    continue
                # Again, for consistency, if there is no found publish date the article will be skipped
                # After 10 downloaded articles from the same newspaper without publish date, the company will be skipped
                if content.publish_date is None:
                    if param._comments:
                        print(count, " Article has date of type None...")
                    noneTypeCount = noneTypeCount + 1
                    if noneTypeCount > 10:
                        if param._comments:
                            print("Too many noneType dates, aborting...")
                        noneTypeCount = 0
                        break
                    count = count + 1
                    continue
                article = {}
                article['title'] = content.title
                article['text'] = content.text
                article['link'] = content.url
                article['published'] = content.publish_date.isoformat()
                newsPaper['articles'].append(article)
                if param._comments:
                    print(count, "articles downloaded from", company, " using newspaper, url: ", content.url)
                count = count + 1
                noneTypeCount = 0
        count = 1
        data['newspapers'][company] = newsPaper

        # Finally it saves the articles as a JSON-file.
        try:
            with open(company_dir + company + '.json', 'w') as outfile:
                json.dump(data, outfile)
        except Exception as e:
            print(e)

        data['newspapers'] = {}

    if param._comments:
        print('News extraction finished.\n')

else:
    with open(sources_urls) as data_file:
        companies = json.load(data_file)
    if param._comments:
        print("Using existing news file.\n")

# ==============================================================
# ===========  Extracting keywords from news  ==================
# ==============================================================

for company, value in companies.items():
    company_dir = news_dir + str(company) + '/'
    if param._comments:
        print('Extracting keywords from ' + company_dir + company + '.json')
    # extracting only text part of news json structure into an array/tuple
    with open(company_dir + company + '.json', 'r', encoding="utf-8") as myfile:
        data = json.loads(myfile.read())
        news_struct = objectpath.Tree(data['newspapers'])
        # extracting news links titles and text from news_struct
        result_tuple = tuple(news_struct.execute('$..text'))
        news_links = tuple(news_struct.execute('$..link'))
        news_titles = tuple(news_struct.execute('$..title'))
        news_pub_dates = tuple(news_struct.execute('$..published'))

    # remove common words and tokenize
    stopWordsList = set(stopwords.words('english'))
    texts = [[word for word in document.lower().split() if word not in stopWordsList and is_valid_word(word)]
              for document in result_tuple]

    frequency = defaultdict(int)
    text_index = 0
    set_of_keywords = []
    for text in texts:
        for token in text:
            frequency[token] += 1

        # Select #n most used keywords and save to file
        for counter in range(param.mostFreqKeywords):
            # Get the top one used word in text
            single_word = max(frequency.items(), key=operator.itemgetter(1))[0]
            del frequency[single_word]
            single_word = remove_extra_chars(single_word)
            set_of_keywords.append(single_word)

        # printing news text and keywords to file
        if not os.path.exists(company_dir + keywords_dir):
            if param._comments:
                print('Creating folder ' + company_dir + keywords_dir)
            os.makedirs(company_dir + keywords_dir)

        with open(company_dir + keywords_dir + "news" + str(text_index+1) + ".txt", "w", encoding="utf-8") as news_text_file:
            # lets remove the first link which regards to the source link
            # print(str(news_links[text_index + 1]) + '\n\n', file=news_text_file)
            news_text_file.write(str(news_links[text_index + 1]))
            news_text_file.write('\n')
            news_text_file.write('_date: ' + str(news_pub_dates[text_index]))
            news_text_file.write('\n\n')
            # print('***' + str(news_titles[text_index]) + '***\n', file=news_text_file)
            news_text_file.write('***' + str(news_titles[text_index]) + '***')
            news_text_file.write('\n')
            news_text_file.write(str(result_tuple[text_index]))
        with open(company_dir + keywords_dir + "news" + str(text_index+1) + "_keywords.txt", "w", encoding="utf-8") as keywords_text_file:
            for keyword in set_of_keywords:
                print(keyword, file=keywords_text_file)
        text_index += 1
        set_of_keywords = []
        frequency.clear()

    print("Keywords extracted to " + company_dir + keywords_dir + "keywords.txt\n")


# ==============================================================
# ============  Extracting news from Twitter  ==================
# ==============================================================

auth = tweepy.OAuthHandler(twitterAuthentic.consumer_key, twitterAuthentic.consumer_secret)
auth.set_access_token(twitterAuthentic.access_token, twitterAuthentic.access_token_secret)
api = tweepy.API(auth)


user = api.me()
print('Tweepy API user: ' + user.name)

for company, value in companies.items():
    company_dir = news_dir + str(company) + '/'

    for article_index in range(param.num_of_articles):
        print('Opening ' + company_dir + 'keywords' + str(article_index+1) + '.txt')
        str_search_term = ''
        with open(company_dir + keywords_dir + "news" + str(article_index + 1) + "_keywords.txt", 'r', encoding="utf-8") as keyword_file:
            if param._search_by_hashtags:
                str_search_term = '#'
                str_search_term = str_search_term + keyword_file.read().replace('\n', ' #')
                # str_search_term.strip()
            else:
                # creating keywords by appending most freq words
                str_search_term = keyword_file.read().replace('\n', ' ')
                str_search_term = str_search_term.strip()

        # str_search_term = str_search_term[:-2]
        print('Searching for news of ' + str(company) + ' on Twitter using \'' + str_search_term + '\' ...')

        tweets_index = 0
        search_results = []
        if param._do_filter_retweets:
            str_search_term = str_search_term + str_retweet_filter

        last30Days = datetime.today()
        last30Days = last30Days.replace(month=int(last30Days.month)-1)
        for tweet in tweepy.Cursor(api.search, tweet_mode='extended', q=str_search_term).items():
            tweets_index += 1
            duplicated_result = False

            # Check time window limit
            date_obj = datetime.strptime(str(tweet.created_at), '%Y-%m-%d %H:%M:%S')
            if date_obj.date() <= last30Days.date():
                print('Time window reached!')
                break

            print('==========================================')
            print('==========================================')
            print(tweet.created_at)
            print('Screen name = ' + str(tweet.user.screen_name))
            print('  ' + tweet.full_text)

            print('search_results contains ' + str(len(search_results)) + ' tweets')
            if len(search_results) > 0:
                for single_tweet in search_results:
                    # print('similarity with #' + str(search_results.index(single_tweet)+1) +' = ' + str(similar(single_tweet, tweet.full_text)))
                    if similar(single_tweet, tweet.full_text) > param._min_similar_rate:
                        print('There is similar tweet in the results already.')
                        duplicated_result = True
                        break

            if not duplicated_result:
                print('Adding tweet to search_results...')
                search_results.append(tweet.full_text)
                # print(tweet.created_at)
                # print('  ' + tweet.full_text)
                # print('Printing tweet to text file\n')
                with open(company_dir + keywords_dir + "news" + str(article_index+1) + '_tweet' + str(tweets_index) +
                          '.txt', "w", encoding="utf-8") as tweet_file:
                    tweet_file.write('_date: ' + str(tweet.created_at))
                    tweet_file.write('\n')
                    tweet_file.write('_user: ' + str(tweet.user.screen_name))
                    tweet_file.write('\n\n')
                    tweet_file.write(str(tweet.full_text))



# verificar se o conteudo do tweet contem keywords da query
