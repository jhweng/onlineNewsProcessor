# =======================
# === Main parameters ===
# =======================

# Set the limit for number of articles to download
num_of_articles = 1
# Number of tweets search
num_of_tweets_search = 20000
# Max tweets the API permits
tweetsPerQry = 100
# Toggle for cmd line runtime comments
_comments = True
# To extract new news from source
_do_extract_news = False
# To display the final result in a window
_display_results = False
# to filter out retweets from search results
_do_filter_retweets = True
# Tweets searching method
_search_by_hashtags = False
# minimum similarity of tweets to be considered as duplicated
_min_similar_rate = 0.7
# Number of most frequent keywords to be used in tweets search
mostFreqKeywords = 3
# Searching tweets from date
str_from_date = '2019-01-01'
# Duplication filter
do_check_duplication = True
# Time window filter
do_filter_timewindow = True
# To apply stemming technique during keywords generation
do_apply_stemming = True
# Time window size in days
_timewindow_size = 7
_lang = 'portuguese'
