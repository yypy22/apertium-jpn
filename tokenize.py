#!/usr/bin/env python3

# to run you'll need to 'sudo apt-get install python3-hfst' or equivalent
# pip might also work though see https://github.com/hfst/hfst/issues/448

# usage:
# copy to directory and in modes.xml add as first step:
# <program name="python3">
#   <file name="tokenize.py"/>
#   <file name="[code].automorf.hfst"/>
# </program>
# this will insert spaces so that analysis won't get stuck

import hfst
from itertools import product

def list_options(spans, start, wlen):
    def ls_op_recurse(i):
        nonlocal spans, wlen
        if i in spans:
            for j in spans[i]:
                for op in list_options(spans, j, wlen):
                    yield [(i,j)] + op
    got_any = False
    for i in range(start, wlen):
        if i in spans:
            yield from ls_op_recurse(i)
            got_any = True
    if not got_any:
        yield []

def weight_options(spans, wlen):
    for op in list_options(spans, 0, wlen):
        unk_count = len(op)-1
        if len(op) == 0:
            unk_count = 1
        else:
            if op[0][0] != 0:
                unk_count += 1
            if op[-1][1] != wlen:
                unk_count += 1
        n = 0
        unk_len = 0
        for i,j in op:
            if (i - n) > 0:
                unk_len += (i - n)
            n = j
        if n < wlen:
            unk_len += (wlen - n)
        yield (op, unk_count, unk_len)

def closure(analyzer, states):
    if not states:
        return ([], False)
    ls = []
    todo = states
    any_final = False
    while todo:
        s = todo.pop()
        if s in ls:
            continue
        ls.append(s)
        if analyzer.is_final_state(s):
            any_final = True
        tr = analyzer.transitions(s)
        for t in tr:
            if t.get_input_symbol() == '@_EPSILON_SYMBOL_@':
                dest = t.get_target_state()
                if dest not in ls:
                    ls.append(dest)
                    todo.append(dest)
    return (ls, any_final)

def step(analyzer, states, c):
    ls = []
    for s in states:
        for t in analyzer.transitions(s):
            if t.get_input_symbol() == c:
                ls.append(t.get_target_state())
    return closure(analyzer, ls)
        
def find_spans(word, analyzer):
    spans = {}
    init_state, _ = closure(analyzer, [0])
    for i in range(len(word)):
        states = init_state[:]
        ends = []
        for j in range(i+1, len(word)+1):
            states, final = step(analyzer, states, word[j-1])
            if final:
                ends.append(j)
            if len(states) == 0:
                break
        if ends:
            spans[i] = list(reversed(ends))
            # put the longest option first
            # so we can approximate LRLM when we randomize
    return spans

def process_word_tok(word, tokenizer, sout):
    spans = find_spans(word, tokenizer)
    if len(spans) == 0:
        sout.write(word)
        return
    mins = []
    min_count = len(word)
    min_len = len(word)
    for op, count, ln in weight_options(spans, len(word)):
        if ln > min_len:
            continue
        elif (ln == min_len) and (count > min_count):
            continue
        elif (ln == min_len) and (count == min_count):
            mins.append(op)
        else:
            mins = []
            mins.append(op)
            min_count = count
            min_len = ln
    sout.write(' ')
    n = 0
    for i,j in mins[0]:
        if n < i:
            sout.write(word[n:i] + ' ')
        sout.write(word[i:j] + ' ')
        n = j
    if n < len(word):
        sout.write(word[n:] + ' ')

def lattice(spans):
    ret = [] # [ chunk, chunk, chunk ]
    # chunk => (total_span, [ option, option, option ])
    # option => [ span, span, span ]
    last_start = max(spans.keys())
    start = 0
    end = 0
    while start <= last_start:
        unk = start
        while start not in spans or len(spans[start]) == 0:
            start += 1
        if start > unk:
            ret.append(((unk, start), [[(unk, start)]]))
        options = [] # [ (option, total_span) ]
        for e in spans[start]:
            options.append(([(start, e)], e))
            end = max(end, e)
        updated = True
        while updated:
            updated = False
            options2 = []
            for path, e in options:
                if e == end:
                    options2.append((path, e))
                    continue
                for i in range(e, end):
                    if i in spans and len(spans[i]) > 0:
                        if i > e:
                            path.append((e,i))
                        for n in spans[i]:
                            options2.append((path[:] + [(i,n)], n))
                            update = True
                            end = max(n, end)
                        break
                else:
                    options2.append((path + [(e, end)], end))
            options, options2 = options2, []
        ret.append(((start, end), [x[0] for x in options]))
        start = end
    return ret

def string_op(op):
    ret = ''
    last_unk = False
    for s in op:
        if s[0] == '*':
            if last_unk:
                ret += s[1:]
            elif ret:
                ret += '+' + s
            else:
                ret += s
            last_unk = True
        else:
            if ret:
                ret += '+'
            ret += s
    return ret

def process_word_morf(word, tokenizer, sout, analyzer):
    spans = find_spans(word, tokenizer)
    if len(spans) == 0:
        sout.write('^' + word + '/*' + word + '$')
        return
    lat = lattice(spans)
    for sp, ops in lat:
        analyses = []
        for op in ops:
            an = []
            for s in op:
                w = word[s[0]:s[1]]
                d = analyzer.lookup(w)
                if len(d) == 0:
                    an.append(['*' + w])
                else:
                    ls = []
                    for k in d:
                        for a, w in d[k]:
                            ls.append(a.replace('@_EPSILON_SYMBOL_@', ''))
                    an.append(ls)
            analyses += list(product(*an))
        sout.write('^' + word[sp[0]:sp[1]])
        for op in analyses:
            sout.write('/' + string_op(op))
        sout.write('$')
        
def process_stream(tokenizer, sin, sout, analyzer=None):
    alpha = tokenizer.get_alphabet()
    cur_word = ''
    while True:
        c = sin.read(1)
        if c in alpha:
            cur_word += c
        else:
            if cur_word:
                if analyzer:
                    process_word_morf(cur_word, tokenizer, sout, analyzer)
                else:
                    process_word_tok(cur_word, tokenizer, sout)
            if c:
                cur_word = ''
                sout.write(c)
            else:
                break

if __name__ == '__main__':
    import argparse
    prs = argparse.ArgumentParser(description='Segment input stream using HFST')
    prs.add_argument('transducer')
    prs.add_argument('analyzer', nargs='?')
    args = prs.parse_args()
    stream_tok = hfst.HfstInputStream(args.transducer)
    tokenizer = hfst.HfstBasicTransducer(stream_tok.read())
    analyzer = None
    if args.analyzer:
        stream_morf = hfst.HfstInputStream(args.analyzer)
        analyzer = hfst.HfstBasicTransducer(stream_morf.read())
    import sys
    process_stream(tokenizer, sys.stdin, sys.stdout, analyzer)
