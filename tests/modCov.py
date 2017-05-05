#!/usr/bin/env python3

import argparse, subprocess, logging, urllib, tempfile, collections, sys

def getFileType(filePath):
    magicNumbers = {
        '\x1f\x8b\x08': 'gz',
        '\x42\x5a\x68': 'bz2',
        '\x50\x4b\x03\x04': 'zip'
    }

    with open(filePath, 'rb') as f:
        fileStart = f.read(max(map(lambda x: len(x), magicNumbers.values())))
    for magicNumber, fileType in magicNumbers.items():
        if fileStart.decode('utf-8').startswith(magicNumber):
            return fileType

    return 'txt'

def getFile(corpusUri):
    if 'http' in corpusUri:
        try:
            corpusPath, _ = urllib.request.urlretrieve(args.corpusUri)
        except urllib.error.HTTPError:
            logger.critical('Corpus %s not found' % args.corpusUri)
            sys.exit(-1)
    else:
        corpusPath = corpusUri

    return corpusPath

def tokenize(corpusPath):
    corpusType = getFileType(corpusPath)
    logger.info('Treating corpus as %s' % corpusType)

    catCommands = {
        'txt': 'cat',
        'gz': 'zcat',
        'bz2': 'bzcat',
        'zip': 'unzip -p'
    }

    tokenizedCorpus = tempfile.TemporaryFile()

    pipeline([
        [catCommands[corpusType], corpusPath],
        ['apertium-destxt'],
        ['lt-proc', '-w', args.automorfPath],
        ['apertium-retxt'],
        ['sed', r's/\$\W*\^/$\n^/g']
    ], tokenizedCorpus)

    return tokenizedCorpus

def getTotal(tokenizedCorpus):
    tokenizedCorpus.seek(0)
    return int(subprocess.check_output(['wc', '-l'], stdin=tokenizedCorpus))

def getKnown(tokenizedCorpus):
    tokenizedCorpus.seek(0)
    p1 = subprocess.Popen(['grep', '-v', '*'], stdout=subprocess.PIPE, stdin=tokenizedCorpus)
    return int(subprocess.check_output(['wc', '-l'], stdin=p1.stdout))

def getTopUnknown(tokenizedCorpus, numUnknown):
    tokenizedCorpus.seek(0)
    unknownTokens = collections.Counter(filter(lambda x: b'*' in x, tokenizedCorpus))
    return unknownTokens.most_common(numUnknown)

def getStats(corpusPath, numUnknown):
    tokenizedCorpus = tokenize(corpusPath)
    known, total, unknownTokens = getKnown(tokenizedCorpus), getTotal(tokenizedCorpus), getTopUnknown(tokenizedCorpus, numUnknown)
    tokenizedCorpus.close()
    return known, total, unknownTokens

def pipeline(commands, procOut, procIn=None):
    proc = None
    for n, command in enumerate(commands):
        lastCommand = n == len(commands) - 1
        stdin = proc.stdout if proc is not None else procIn
        stdout = subprocess.PIPE if not lastCommand else procOut
        logging.debug('Running %s with stdin=%s, stdout=%s' % (command, stdin, stdout))
        proc = subprocess.Popen(command, stdin=stdin, stdout=stdout)
        if lastCommand:
            return proc.communicate()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Determine coverage of a transducer on a corpus')
    parser.add_argument('automorfPath', help='path to automorf binary')
    parser.add_argument('corpusUri', help='corpus uri')
    parser.add_argument('-n', '--numUnknown', default=10, type=int, help='number of top unknown tokens to show')
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help='verbose mode')
    args = parser.parse_args()

    logger = logging.getLogger("coverage")
    logging.basicConfig(level=(logging.DEBUG if args.verbose else logging.INFO))

    corpusPath = getFile(args.corpusUri)
    known, total, unknownTokens = getStats(corpusPath, args.numUnknown)

    print(corpusPath)
    print('Coverage: %.10f%%' % float(known / total * 100.0))
'''
    for token, count in unknownTokens:
        print('%s\t%s' % (count, token.decode('utf-8', errors='ignore').strip()))
'''
