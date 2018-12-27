from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords

data = "Mr Trump had planned to spend Christmas at his private golf club in Florida, but stayed behind in Washington because of the current partial government shutdown."
stopWords = set(stopwords.words('english'))
words = word_tokenize(data)
wordsFiltered = []

for w in words:
    if w not in stopWords:
        wordsFiltered.append(w)

print(wordsFiltered)