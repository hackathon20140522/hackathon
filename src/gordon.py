#!/usr/bin/python

import subprocess


def parseArguments():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('targetObjects')
    parser.add_argument('startingPoint')

    args = parser.parse_args()

    print 'target objects: {}'.format(args.targetObjects)
    print 'starting point: {}'.format(args.startingPoint)
    return args


def findFilesAtPoint(startingPoint, targetObjects):
    foundFiles = subprocess.check_output(['git', 'ls-tree', '--name-only', '-r', startingPoint, targetObjects])
    return foundFiles.splitlines()


def countLinesInFile(targetFile):
    wcResult = subprocess.check_output(['wc', '-l', targetFile])
    firstColumn = wcResult.split()[0]

    print 'lines in current file: {}'.format(firstColumn)
    return int(firstColumn)


def processStartingPoint(startingPoint, targetObjects):
    foundFiles = findFilesAtPoint(startingPoint, targetObjects)
    sumOfLines = sum(countLinesInFile(f) for f in foundFiles)

    print 'number of lines in all files: {}'.format(sumOfLines)
    return sumOfLines, foundFiles


def findChangedFiles(startingPoint, targetPoint):
    foundFiles = subprocess.check_output(['git', 'diff-tree', '--no-commit-id', '--name-only', '-r', startingPoint, targetPoint])
    return foundFiles.splitlines()


def statDiffOnFiles(startingPoint, targetPoint, interestingFiles):
    interestingDiff = subprocess.check_output(['git', 'diff', '--numstat', startingPoint, targetPoint] + list(interestingFiles))
    return interestingDiff.splitlines()


def extractCountOfChangedLines(diffLine):
    removedOrChangedLines = diffLine.split()[1]
    countOfChangedLines = 0
    try:
        countOfChangedLines += int(removedOrChangedLines)
    except ValueError:
        pass

    return countOfChangedLines


def countChangedLines(startingPoint, targetPoint, filesAtStartingPoint):
    changedFiles = findChangedFiles(startingPoint, targetPoint)
    interestingFiles = set(changedFiles).intersection(filesAtStartingPoint)
    interestingDiff = statDiffOnFiles(startingPoint, targetPoint, interestingFiles)

    sumOfChangedLines = sum(extractCountOfChangedLines(line) for line in interestingDiff)

    print 'sumOfChangedLines: {}'.format(sumOfChangedLines)
    return sumOfChangedLines


def getNextTargetPoint(startingPoint, endPoint):
    logResult = subprocess.check_output(['git', 'rev-list', '--reverse', startingPoint + '..' + endPoint])
    logLines = logResult.splitlines()

    for line in logLines:
        yield line.split()[0]


def main():
    args = parseArguments()

    linesAtStart, filesAtStartingPoint = processStartingPoint(args.startingPoint, args.targetObjects)

    endPoint = 'HEAD'
    for targetPoint in list(getNextTargetPoint(args.startingPoint, endPoint)):
        linesChangedAtTarget = countChangedLines(args.startingPoint, targetPoint, filesAtStartingPoint)
        print 'changed lines: {} / all lines: {}'.format(linesChangedAtTarget, linesAtStart)


if __name__ == "__main__":
    main()
