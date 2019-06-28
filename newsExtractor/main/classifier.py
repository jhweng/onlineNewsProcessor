import os
import glob
import ntpath
import datetime as dt

_path_to_classify = 'news\\bbcbrasil\\stem_noduplic\\3_keywords'
str_extra_check = ''

keywords = []
related_count = 0
not_related_count = 0
changed_back_count = 0
with open(_path_to_classify + '\\news1_keywords.txt', encoding='utf-8', mode='r') as f1:
    for line in f1:
        line = line.replace('\n', '')
        keywords.append(line)
    f1.close()

for filepath in glob.glob(os.path.join(_path_to_classify, '2019*')):
    filename = ntpath.basename(filepath)

    with open(filepath, encoding='utf-8', mode='r+') as f:
        content = f.read().lower()
        f.seek(0, 0)
        # print(content)

        contain_all_keywords = False
        keyword_missing = False
        for keyword in keywords:
            if not (keyword in content):
                contain_all_keywords = False
                keyword_missing = True
                break
            else:
                contain_all_keywords = True

        # if str_extra_check in content:
        #     contain_all_keywords = True
        # else:
        #     contain_all_keywords = False

        if contain_all_keywords:
            related_count += 1
            # print('====================================')
            # print(content)
            # f.write('_$related$\n\n' + content)
            # print('RELATED')
        else:
            not_related_count += 1
            # print('====================================')
            # print(content)
            # f.write('_$not_related$\n\n' + content)
            # print('NOT RELATED')
        f.close()
        # input()
    # if keyword_missing:
    #     os.rename(filepath, _path_to_classify + '\\#' + filename)


    # relation = ''
    # filename = ntpath.basename(filepath)
    # if filename.startswith('2019'):
    #     with open(filepath, encoding="utf-8", mode='r+') as f:
    #         content = f.read()
    #         f.seek(0, 0)
    #         print('-----------------------------------------')
    #         print(content)
    #         relation = input('Is it related? (Y/n) ')
    #         if relation == 'n':
    #             f.write('_$not_related$\n\n' + content)
    #         else:
    #             f.write('_$related$\n\n' + content)
    #         f.close()
    #
    #     os.rename(filepath, _path_to_classify + '\\#' + filename)

print('Classification finished.')
print('related: ' + str(related_count))
print('Not related: ' + str(not_related_count))
# print('Precision: ' + str(related_count/(related_count + not_related_count)))
