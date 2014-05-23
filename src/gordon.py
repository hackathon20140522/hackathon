#!/usr/bin/python

import subprocess


def parseArguments():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('targetObjects')
    parser.add_argument('startingPoint')
    parser.add_argument('endPoint')

    args = parser.parse_args()

    print 'target objects: {}'.format(args.targetObjects)
    print 'starting point: {}'.format(args.startingPoint)
    print 'end point: {}'.format(args.endPoint)
    return args


def findFilesAtPoint(startingPoint, targetObjects):
    command = ['git', 'ls-tree', '--name-only', '-r', startingPoint, targetObjects]
    foundFiles = subprocess.check_output(command)
    return foundFiles.splitlines()


def countLinesInOldFile(targetFile, oldPoint):
    showCommand = ['git', 'show', oldPoint + ':' + targetFile]
    oldFileContent = subprocess.check_output(showCommand)
    lineCount = len(oldFileContent.splitlines())

    return lineCount


def processStartingPoint(startingPoint, targetObjects):
    foundFiles = findFilesAtPoint(startingPoint, targetObjects)
    sumOfLines = sum(countLinesInOldFile(f, startingPoint) for f in foundFiles)

    print 'number of lines in all files: {}'.format(sumOfLines)
    return sumOfLines, foundFiles


def findChangedFiles(startingPoint, targetPoint):
    command = ['git', 'diff-tree', '--no-commit-id', '--name-only', '-r', startingPoint, targetPoint]
    foundFiles = subprocess.check_output(command)
    return foundFiles.splitlines()


def statDiffOnFiles(startingPoint, targetPoint, interestingFiles):
    if not interestingFiles:
        return []
    command = ['git', 'diff', '--numstat', startingPoint, targetPoint, '--'] + list(interestingFiles)
    interestingDiff = subprocess.check_output(command)
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

    return sumOfChangedLines


def getPointsInInterval(startingPoint, endPoint):
    command = ['git', 'rev-list', '--reverse', startingPoint + '..' + endPoint]
    logResult = subprocess.check_output(command)
    return logResult.splitlines()


def getTargetPoints(startingPoint, endPoint):
    logLines = getPointsInInterval(startingPoint, endPoint)

    return [line.split()[0] for line in logLines]


def getDateOfPoint(point):
    command = ['git', 'show', '-s', '--format=%ci', point]
    return subprocess.check_output(command).splitlines()[0]


def findHalfLife(startingPoint, endPoint, targetObjects):
    linesAtStart, filesAtStartingPoint = processStartingPoint(startingPoint, targetObjects)

    for targetPoint in getTargetPoints(startingPoint, endPoint):
        linesChangedAtTarget = countChangedLines(startingPoint, targetPoint, filesAtStartingPoint)

        print 'changed lines / all lines: {} / {}'.format(linesChangedAtTarget, linesAtStart)
        halfPointReached = linesChangedAtTarget > (linesAtStart / 2)
        if halfPointReached:
            dateOfStart = getDateOfPoint(startingPoint)
            dateOfHalfPoint = getDateOfPoint(targetPoint)
            commitsFromStartToHalfPoint = len(getPointsInInterval(startingPoint, targetPoint))
            print 'reached half point from {} at {} ({} commits)'.format(dateOfStart, dateOfHalfPoint, commitsFromStartToHalfPoint)
            return
    print 'no half point found'


def main():
    args = parseArguments()
    
    points = getPointsInInterval(args.startingPoint, args.endPoint)
    points.insert(0, args.startingPoint)
    for currentPoint in points:
        findHalfLife(currentPoint, args.endPoint, args.targetObjects)


if __name__ == "__main__":
    main()
