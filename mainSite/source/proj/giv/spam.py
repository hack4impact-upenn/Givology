'''
for detecting if things are spam or not

see: http://www.larsen-b.com/Article/244.html
'''


from proj.giv.reverend.thomas import Bayes
from proj.settings import SPAM_DB



class TriTokenizer:
    def __init__(self):
        return
    def tokenize(self, s):
        if len(s) < 3:
            yield 'short'
        for i in xrange(len(s)-2):
            t = s[i:i+3]
            if ord(t[0]) > 255 or ord(t[1]) > 255 or ord(t[2]) > 255:
                yield 'special'
            else:
                yield t.lower()


_guesser = None

def load_guesser():
    tmpguesser = Bayes(tokenizer=TriTokenizer())
    try:
        tmpguesser.load(SPAM_DB)
    except IOError:
        print "Creating a new spam filter database"
        tmpguesser.save(SPAM_DB)
    return tmpguesser

_guesser = load_guesser()

def train(kind,text):
    global _guesser
    # kind should be 'spam' or 'ham'.
    try:
        tmpguesser = load_guesser()
        tmpguesser.train(kind,text)
        tmpguesser.save(SPAM_DB)
        _guesser = load_guesser()
    except: pass
    return

def untrain(kind,text):
    global _guesser
    # kind should be 'spam' or 'ham'.
    try:
        tmpguesser = load_guesser()
        tmpguesser.untrain(kind,text)
        tmpguesser.save(SPAM_DB)
        _guesser = load_guesser()
    except: pass
    return

# try to guess the spam / ham ratio of a text
def guess(text):
    spam = 0
    ham = 0
    value = _guesser.guess(text)
    for o in value:
        if o[0] == 'ham': ham = o[1]
        if o[0] == 'spam': spam = o[1]
    return (ham,spam)











