import MeCab
import sys

def process_text(sin, sout):
    text = sin.read()
    mecab = MeCab.Tagger("-Owakati")
    buffer = ""
    tokenized = ""
    in_bracket = False

    for char in text:
        if char == "[":
            if buffer.strip():
                tokenized += mecab.parse(buffer.strip()).rstrip() + ' '
            tokenized += '['
            buffer = ""
            in_bracket = True
        elif char == "]":
            if in_bracket:
                tokenized += ''.join(mecab.parse(buffer.strip()).split()) + ']'
                buffer = ""
            in_bracket = False
        else:
            buffer += char

    if buffer.strip():
        tokenized += mecab.parse(buffer.strip()).rstrip()

    sout.write(tokenized)

if __name__ == '__main__':
    process_text(sys.stdin, sys.stdout)