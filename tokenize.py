import MeCab
import sys

def process_text(sin, sout):
    text = sin.read()
    mecab = MeCab.Tagger("-Owakati")
    buffer = ""
    tokenized = ""
    in_blancket = False

    for i in text:
        buffer += i
        if i == "[":
            buffer = mecab.parse(buffer.strip()).rstrip()
            tokenized += buffer
            buffer = ""
            in_blancket = True
        elif in_blancket:
            tokenized += i
        elif i == "]":
            in_blancket = False
    sout.write(tokenized)

if __name__ == '__main__':
    process_text(sys.stdin, sys.stdout)
