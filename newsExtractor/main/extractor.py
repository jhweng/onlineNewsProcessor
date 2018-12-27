import feedparser as fp
import newspaper
from newspaper import Article
from time import mktime
from datetime import datetime
from gensim import corpora
from collections import defaultdict
from pprint import pprint
import json
import objectpath
from collections import namedtuple
import os
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize, word_tokenize



def _json_object_hook(d): return namedtuple('X', d.keys())(*d.values())
def json2obj(data): return json.loads(data, object_hook=_json_object_hook)



# Set the limit for number of articles to download
LIMIT = 1
_comments = True

data = {}
data['newspapers'] = {}

news_dir = 'news_json/'
sources_urls = 'NewsPapers.json'


# checking if folder exists and warning about overwritting
if not os.path.exists(news_dir):
    if _comments:
        print('Creating folder '+ news_dir +' ...')
        os.makedirs(news_dir)
else:
    if _comments:
        print('Folder '+news_dir +' already exists, same name files will be overwritten.')

# Loads the JSON files with news sites
if _comments:
    print('Loading news sources ...')
with open(sources_urls) as data_file:
    companies = json.load(data_file)

count = 1

# Iterate through each news company
for company, value in companies.items():
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
                if count > LIMIT:
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
            if count > LIMIT:
                break
            try:
                content.download()
                content.parse()
            except Exception as e:
                print(e)
                print("continuing...")
                continue
            # Again, for consistency, if there is no found publish date the article will be skipped.
            # After 10 downloaded articles from the same newspaper without publish date, the company will be skipped.
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
        with open(news_dir + company + '.json', 'w') as outfile:
            json.dump(data, outfile)
    except Exception as e:
        print(e)

    data['newspapers'] = {}

if _comments:
    print('News extraction finished.')

# ==============================================================
# ==============================================================
# ==============================================================

for company, value in companies.items():
    if _comments:
        print('Extracting keywords from ' + news_dir + company + '.json')
    # extracting only text part of news json structure into an array/tuple
    with open(news_dir + company + '.json', 'r') as myfile:
        data = json.loads(myfile.read())
        news_struct = objectpath.Tree(data['newspapers'])
        result_tuple = tuple(news_struct.execute('$..text'))

    # remove common words and tokenize
    stopWordsList = set(stopwords.words('english'))
    texts = [[word for word in document.lower().split() if word not in stopWordsList]
              for document in result_tuple]

    frequency = defaultdict(int)
    for text in texts:
        for token in text:
            frequency[token] += 1

    # remove words that appear only minFreq times
    minFrequence = 2
    texts = [[token for token in text if frequency[token] > minFrequence]
              for text in texts]


    pprint(set(texts[0]))




