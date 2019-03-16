import feedparser as fp
import newspaper
import json
import objectpath
import os
import tweepy
import operator
from time import mktime
from tkinter import *
from tkinter import ttk
from newspaper import Article
from datetime import datetime
from collections import defaultdict
from collections import namedtuple
from nltk.corpus import stopwords

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


data = {}
data['newspapers'] = {}

news_dir = 'news/'
keywords_dir = str(param.mostFreqKeywords) + '_keywords/'
sources_urls = 'NewsPapers.json'
str_retweet_filter = ' -filter:retweets'


# ==============================================================
# ============  Extracting news from sources  ==================
# ==============================================================
if param._do_extract_news:
    # checking if folder exists and warning about overwritting
    if not os.path.exists(news_dir):
        if param._comments:
            print('Creating folder ' + news_dir + ' ...')
            os.makedirs(news_dir)
    else:
        if param._comments:
            print('Folder ' + news_dir + ' already exists, same name files will be overwritten.')

    # Loads the JSON files with news sites
    if param._comments:
        print('Loading news sources ...')
    with open(sources_urls) as data_file:
        companies = json.load(data_file)

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
            print(str(news_links[text_index + 1]) + '\n\n', file=news_text_file)
            print('***' + str(news_titles[text_index]) + '***\n', file=news_text_file)
            print(str(result_tuple[text_index]), file=news_text_file)
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

        print('Searching for news of ' + str(company) + ' on Twitter using \'' + str_search_term + '\' ...')

        tweets_index = 0
        if param._do_filter_retweets:
            str_search_term = str_search_term + str_retweet_filter
        for tweet in tweepy.Cursor(api.search, tweet_mode='extended', q=str_search_term,
                                   since=param.str_from_date).items(param.num_of_tweets_search):
            tweets_index += 1
            print(tweet.created_at)
            print('  ' + tweet.full_text)
            print('Printing tweet to text file\n')
            with open(company_dir + keywords_dir + "news" + str(article_index+1) + '_tweet' + str(tweets_index) +
                      '.txt', "w", encoding="utf-8") as tweet_file:
                tweet_file.write(str(tweet.created_at))
                tweet_file.write('\n')
                tweet_file.write(str(tweet.full_text))


# printing news and tweets from search result in a window for comparing
if param._display_results:
    window = Tk()
    window.title("Twitter News Processing")
    window.geometry('350x200')
    for company, value in companies.items():
        company_dir = news_dir + str(company) + '/'
        for article_index in range(param.num_of_articles):
            print('Opening ' + company_dir + 'news' + str(article_index + 1) + '.txt')
            with open(company_dir + "news" + str(article_index + 1) + ".txt", 'r', encoding="utf-8") as news_text_file:
                str_news_text = str(news_text_file.read()).replace('\n', '')
            for tweets_index in range(param.num_of_tweets_search):
                with open(company_dir + keywords_dir + "news" + str(article_index + 1) + "_tweet" + str(tweets_index+1) +
                          ".txt", 'r', encoding="utf-8") as tweet_text_file:
                    str_tweet_text = str(tweet_text_file.read()).replace('\n', '')
                    # str_tweet_text = ' '.join(e for e in str_tweet_text if e.isalnum())
                    str_tweet_text = [re.sub(r"[^a-zA-Z0-9]+", ' ', k) for k in str_tweet_text.split("\n")]

                tab_control = ttk.Notebook(window)
                tab1 = ttk.Frame(tab_control)
                tab2 = ttk.Frame(tab_control)

                tab_control.add(tab1, text='News' + str(article_index+1))
                txt1 = Text(tab1)
                txt1.pack()
                txt1.insert(END, str_news_text)
                txt1.config(state=DISABLED)
                txt1.grid(column=0, row=0)

                tab_control.add(tab2, text='Tweet' + str(tweets_index+1))
                txt2 = Text(tab2)
                txt2.pack()
                txt2.insert(END, str_tweet_text)
                txt2.config(state=DISABLED)
                txt2.grid(column=0, row=0)

                tab_control.pack(expand=1, fill='both')
                window.mainloop()

