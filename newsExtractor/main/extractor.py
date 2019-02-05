import feedparser as fp
import newspaper
import json
import objectpath
import os
import tweepy
import csv
import operator
from newspaper import Article
from time import mktime
from datetime import datetime
from collections import defaultdict
from collections import namedtuple
from nltk.corpus import stopwords


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

# =======================
# === Main parameters ===
# =======================

# Set the limit for number of articles to download
num_of_articles = 3
# Minimum frequency of a word to be consider as keyword
minFrequence = 8
# Number of tweets search
num_of_tweets_search = 4
# Toggle for cmd line runtime comments
_comments = True
# To extract new news from source
_do_extract_news = False
# Number of most frequent keywords to be used in tweets search
num_of_most_freq_keywords = 4

# Tweepy authentication info
consumer_key = 'Jrn5QqyUTfPZFfn91kqHLDFTi'
consumer_secret = 'TmdWDiEwgdJnnNXxVsnqhOB5CizN5pqseUz4wPiraODr216RjM'
access_token = '1058701211745091584-2SL7tz0JyhjkXhjzfwrt9TnyS31TvZ'
access_token_secret = 'd96xByA6Uqlyt7uRo0iSzGWr1H5uIIn8ghCR6PRIiXRf0'

# Write Twitter search results in csv file
_write_to_file = False

data = {}
data['newspapers'] = {}

news_dir = 'news/'
sources_urls = 'NewsPapers.json'


# ==============================================================
# ============  Extracting news from sources  ==================
# ==============================================================
if _do_extract_news:
    # checking if folder exists and warning about overwritting
    if not os.path.exists(news_dir):
        if _comments:
            print('Creating folder ' + news_dir + ' ...')
            os.makedirs(news_dir)
    else:
        if _comments:
            print('Folder ' + news_dir + ' already exists, same name files will be overwritten.')

    # Loads the JSON files with news sites
    if _comments:
        print('Loading news sources ...')
    with open(sources_urls) as data_file:
        companies = json.load(data_file)

    count = 1

    # Iterate through each news company
    for company, value in companies.items():
        company_dir = news_dir + str(company) + '/'
        if not os.path.exists(company_dir):
            if _comments:
                print('Creating folder ' + company_dir)
            os.makedirs(company_dir)

        # If a RSS link is provided in the JSON file, this will be the first choice.
        # Reason for this is that, RSS feeds often give more consistent and correct data.
        if 'rss' in value:
            d = fp.parse(value['rss'])
            if _comments:
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
                    if count > num_of_articles:
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
                    if _comments:
                        print(count, "articles downloaded from", company, ", url: ", entry.link)
                    count = count + 1
        else:
            # This is the fallback method if a RSS-feed link is not provided.
            # It uses the python newspaper library to extract articles
            if _comments:
                print("Building site for ", company)
            paper = newspaper.build(value['link'], memoize_articles=False)
            newsPaper = {
                "link": value['link'],
                "articles": []
            }
            noneTypeCount = 0
            for content in paper.articles:
                if count > num_of_articles:
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
                    if _comments:
                        print(count, " Article has date of type None...")
                    noneTypeCount = noneTypeCount + 1
                    if noneTypeCount > 10:
                        if _comments:
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
                if _comments:
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

    if _comments:
        print('News extraction finished.\n')

else:
    with open(sources_urls) as data_file:
        companies = json.load(data_file)
    if _comments:
        print("Using existing news file.\n")

# ==============================================================
# ===========  Extracting keywords from news  ==================
# ==============================================================

for company, value in companies.items():
    company_dir = news_dir + str(company) + '/'
    if _comments:
        print('Extracting keywords from ' + company_dir + company + '.json')
    # extracting only text part of news json structure into an array/tuple
    with open(company_dir + company + '.json', 'r') as myfile:
        data = json.loads(myfile.read())
        news_struct = objectpath.Tree(data['newspapers'])
        result_tuple = tuple(news_struct.execute('$..text'))

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

    # remove words that appear only minFreq times
    # texts = [[token for token in text if frequency[token] > minFrequence]
    #           for text in texts]

    # for text in texts:
    #     for single_word in set(text):
    #         single_word = remove_extra_chars(single_word)
    #         if single_word not in sets_of_keywords:
    #             sets_of_keywords.append(single_word)

        # Select most used keywords and save to file
        for counter in range(num_of_most_freq_keywords):
            # Get the top one used word in text
            single_word = max(frequency.items(), key=operator.itemgetter(1))[0]
            del frequency[single_word]
            single_word = remove_extra_chars(single_word)
            set_of_keywords.append(single_word)

        with open(company_dir + "news" + str(text_index+1) + ".txt", "w", encoding="utf-8") as news_text_file:
            print(str(result_tuple[text_index]), file=news_text_file)
        with open(company_dir + "news" + str(text_index+1) + "_keywords.txt", "w", encoding="utf-8") as keywords_text_file:
            for keyword in set_of_keywords:
                print(keyword, file=keywords_text_file)
        text_index += 1
        set_of_keywords = []
        frequency.clear()

    print("Keywords extracted to " + company_dir + "keywords.txt\n")


# ==============================================================
# ============  Extracting news from Twitter  ==================
# ==============================================================

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)


user = api.me()
print('Tweepy API user: ' + user.name)

for company, value in companies.items():
    company_dir = news_dir + str(company) + '/'
    str_from_date = '2019-01-23'

    for article_index in range(num_of_articles):
        print('Opening ' + company_dir + 'keywords' + str(article_index+1) + '.txt')
        with open(company_dir + "news" + str(article_index+1) + "_keywords.txt", 'r') as keyword_file:
            str_search_term = keyword_file.read().replace('\n', ' ')
        str_search_term.strip()

        if _write_to_file:
            # Open/Create a file to append data
            csvFile = open(company_dir + str_search_term, 'a')
            # Use csv Writer
            csvWriter = csv.writer(csvFile)

        print('Searching for news of ' + str(company) + ' on Twitter using \'' + str_search_term + '\' ...')

        tweets_index = 0
        for tweet in tweepy.Cursor(api.search, tweet_mode='extended',
                                   q=str_search_term, since=str_from_date).items(num_of_tweets_search):
            tweets_index += 1
            print(tweet.created_at)
            print('  ' + tweet.full_text)
            print('Printing to text file...\n')
            with open(company_dir + "news" + str(article_index+1) + '_tweet' + str(tweets_index) +
                      '.txt', "w", encoding="utf-8") as tweet_file:
                tweet_file.write(str(tweet.created_at))
                tweet_file.write('\n')
                tweet_file.write(str(tweet.full_text))

            if _write_to_file:
                csvWriter.writerow([tweet.created_at, tweet.full_text.encode('utf-8')])


