import os
import glob
import ntpath
import datetime as dt


by_date = True
tweet_date = 20190616
_path_to_classify = 'news\\bbc\\noFilters\\3_keywords'

total_count = 0
related_count = 0
not_related_count = 0
if not by_date:
    for filepath in glob.glob(os.path.join(_path_to_classify, '#2019*')):
        with open(filepath, encoding='utf-8', mode='r') as f:
            content = f.read()

            content = content.lower()
            if '_$related$' in content:
                related_count += 1
            else:
                not_related_count += 1
            total_count += 1

            f.close()
    print('Total tweets: ' + str(total_count))
    print('Related: ' + str(related_count))
    print('Not Related: ' + str(not_related_count))
    print('Precisao da busca: ' + str(related_count / total_count))

else:
    for i in range(tweet_date, tweet_date+8):
        related_count = 0
        for filepath in glob.glob(os.path.join(_path_to_classify, '#' + str(i) + '*')):
            with open(filepath, encoding='utf-8', mode='r') as f:
                content = f.read()

                content = content.lower()
                if '_$related$' in content:
                    related_count += 1

                f.close()
        print('Total tweets of ' + str(i))
        print('Related: ' + str(related_count))

print('Counting finished.')
