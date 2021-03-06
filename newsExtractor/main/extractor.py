import feedparser as fp
import newspaper
import json
import objectpath
import os
import tweepy
import operator
import sys
import time
import jsonpickle
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
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize
from difflib import SequenceMatcher

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
    out_str = out_str.replace('”', '')
    return out_str


def is_valid_word(in_word):
    return (in_word != '-') and \
           (in_word != 'said') and \
           (in_word != 'also') and \
           (in_word != 'é')


def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()


# ==============================================================
# =================  Start of Pipeline  ========================
# ==============================================================

data = {}
data['newspapers'] = {}

news_dir = 'news/'
keywords_dir = str(param.mostFreqKeywords) + '_keywords/'
sources_urls = 'NewsPapers.json'
str_retweet_filter = ' -filter:retweets'
ps = PorterStemmer()


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
                        print("proceeding...")
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
                    print("proceeding...")
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
    stopWordsList = set(stopwords.words(param._lang))
    texts = [[word for word in document.lower().split() if word not in stopWordsList and is_valid_word(word)]
              for document in result_tuple]

    frequency = defaultdict(int)
    text_index = 0
    set_of_keywords = []
    for text in texts:
        # print(' '.join(text))
        for token in text:
            token = remove_extra_chars(token)
            # ============= Apply stemming ====================
            if param.do_apply_stemming and (len(frequency) > 0):
                similar_word_in_list = False
                for listKeyword in frequency:
                    if ps.stem(token) == ps.stem(listKeyword):
                        similar_word_in_list = True
                        frequency[listKeyword] += 1
                        print(str(token) + ' counted as ' + str(listKeyword))

                if not similar_word_in_list:
                    frequency[token] += 1
            else:
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

        with open(company_dir + keywords_dir + "news" + str(text_index+1) + "_keywords.txt", "w", encoding="utf-8") as\
                  keywords_text_file:

            # Saving keywords to file
            for keyword in set_of_keywords:
                print(keyword, file=keywords_text_file)

        text_index += 1
        set_of_keywords = []
        frequency.clear()

    print("Keywords extracted to " + company_dir + keywords_dir + "keywords.txt\n")


# ==============================================================
# ============  Extracting news from Twitter  ==================
# ==============================================================

auth = tweepy.AppAuthHandler(twitterAuthentic.consumer_key, twitterAuthentic.consumer_secret)
api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)

if not api:
    print("Can't Authenticate")
    sys.exit(-1)

for company, value in companies.items():
    company_dir = news_dir + str(company) + '/'

    for article_index in range(param.num_of_articles):
        print('Opening ' + company_dir + keywords_dir + 'news' + str(article_index + 1) + '_keywords.txt')
        str_search_term = ''
        with open(company_dir + keywords_dir + 'news' + str(article_index + 1) + '_keywords.txt', 'r', encoding="utf-8") as keyword_file:
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

        # initializing timeWindow30d value and published date
        timeWindow30d = datetime.today()
        published_date = datetime.today()
        with open(company_dir + keywords_dir + "news" + str(article_index + 1) + ".txt", 'r',
                  encoding="utf-8") as news_file:
            for line in news_file:
                if '_date: ' in line:
                    str_published_date = line[7:17]
                    published_date = datetime.strptime(str_published_date, '%Y-%m-%d')
                    timeWindow30d = published_date.replace(day=int(published_date.day) + param._timewindow_size)

                    if param.do_filter_timewindow:
                        print('Gathering tweets between {} and {}'.format(published_date, timeWindow30d))

                    break

        tweetCount = 0
        savedTweetCount = 0
        # sinceId = None
        # max_id = -1
        # while tweetCount < param.num_of_tweets_search:
        #     try:
        #         new_tweets = api.search(q=str_search_term, count=param.tweetsPerQry, tweet_mode='extended', sinceId = max_id)
        #
        #         if not new_tweets:
        #             print("No more tweets found")
        #             break
        #         for tweet in new_tweets:
        #             tweets_index += 1
        #
        #             json1_data = json.loads(jsonpickle.encode(tweet._json, unpicklable=False))
        #
        #             # break search loop after find tweet creation date before news published date
        #             date_obj = datetime.strptime(json1_data['created_at'], '%a %b %d %H:%M:%S +0000 %Y')
        #             if date_obj.date() <= published_date.date():
        #                 print('Reached news published date. Breaking search loop...')
        #                 break

        for tweet in tweepy.Cursor(api.search, tweet_mode='extended', q=str_search_term, lang='').\
                                   items(param.num_of_tweets_search):
            tweets_index += 1
# =====================================================================================================================
                # CHECK TIME WINDOW
# =====================================================================================================================
            date_obj = datetime.strptime(str(tweet.created_at), '%Y-%m-%d %H:%M:%S')

            if date_obj.date() < published_date.date():
                print('News published date reached. Finalizing search...')
                break

            is_in_timewindow = True
            # if param.do_filter_timewindow and (date_obj.date() > timeWindow30d.date()):
            if param.do_filter_timewindow and (date_obj.date() > timeWindow30d.date()):
                is_in_timewindow = False

# =====================================================================================================================
#                         CHECK DUPLICATION
# =====================================================================================================================
            duplicated_result = False
            if (len(search_results) > 0) and param.do_check_duplication:
                # Check if there is similar tweet already stored in list
                for single_tweet in search_results:
                    # if similar(single_tweet, json1_data['full_text']) > param._min_similar_rate:
                    if similar(single_tweet, tweet.full_text) > param._min_similar_rate:
                        # print('There is similar tweet in the results already.')
                        duplicated_result = True
                        break

# =====================================================================================================================
#                         SAVE RESULTS TO FILE
# =====================================================================================================================
            if (not duplicated_result) and is_in_timewindow:
                # search_results.append(json1_data['full_text'])
                search_results.append(tweet.full_text)
                str_tweet_date = date_obj.date().strftime('%Y%m%d')
                with open(company_dir + keywords_dir + str_tweet_date + "_news" + str(article_index + 1) + '_tweet' + str(
                        tweets_index) +
                          '.txt', "w", encoding="utf-8") as tweet_file:
                    # tweet_file.write('_date: ' + json1_data['created_at'])
                    tweet_file.write('_date: ' + str(tweet.created_at))
                    tweet_file.write('\n\n')
                    # tweet_file.write(json1_data['full_text'])
                    tweet_file.write(str(tweet.full_text))
                    savedTweetCount += 1

            # tweetCount += len(new_tweets)
            tweetCount += 1
            print("Downloaded {0} tweets".format(tweetCount))
            print("Saved {0} tweets to file".format(savedTweetCount))
            # max_id = new_tweets[-1].id
        # except tweepy.RateLimitError as e:
        #     # Just exit if any error
        #     print("Some error : " + str(e))
        #     time.sleep(60 * 15)
        #     continue
        # except StopIteration:
        #     break
