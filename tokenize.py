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
        if i == text[-1]:
            buffer = mecab.parse(buffer.strip()).rstrip()
            tokenized += buffer

        if i == "[":
            buffer = buffer[:-1]
            buffer = mecab.parse(buffer.strip()).rstrip()
            tokenized += buffer
            buffer = ""
            in_blancket = True

        if in_blancket:
            tokenized += i

        if i == "]":
            in_blancket = False
            buffer = ""
    sout.write(tokenized)
if __name__ == '__main__':
    process_text(sys.stdin, sys.stdout)