import os
import glob
import ntpath
import datetime as dt

_path_to_classify = 'news\\reuters\\noFilters\\3_keywords_noFilters_8days\\'


for filepath in glob.glob(os.path.join(_path_to_classify, '2019*')):
    # filename = ntpath.basename(filepath)
    #
    # with open(filepath, encoding='utf-8', mode='r') as f:
    #     for line in f:
    #         if '_date: ' in line:
    #             str_published_date = line[7:17]
    #             str_date = str(dt.datetime.strptime(str_published_date, '%Y-%m-%d')).replace('-', '')[:8]
    #             # print(str_date)
    #             # input('stoping...')
    #             break
    #     f.close()
    #
    # os.rename(filepath, _path_to_classify + str_date + '_' + filename)

    relation = ''
    filename = ntpath.basename(filepath)
    if filename.startswith('2019'):
        with open(filepath, encoding="utf-8", mode='r+') as f:
            content = f.read()
            f.seek(0, 0)
            print('-----------------------------------------')
            print(content)
            relation = input('Is it related? (Y/n) ')
            if relation == 'n':
                f.write('_$not_related$\n\n' + content)
            else:
                f.write('_$related$\n\n' + content)
            f.close()

        os.rename(filepath, _path_to_classify + '\\#' + filename)

print('Classification finished.')
