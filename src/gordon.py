#!/usr/bin/python

import subprocess


def log(verbosity, level, message):
    if verbosity >= level:
        print message


def parseArguments():
    import argparse

    parser = argparse.ArgumentParser()
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-s", "--single-commit", action="store_true")
    group.add_argument("-l", "--linear", action="store_true")
    group.add_argument("-ll", "--logarithmic", action="store_true")

    parser.add_argument('targetObjects', help='the files/directories you want to analyze')
    parser.add_argument('startingPoint', help='the treeish you want to start on')
    parser.add_argument('endPoint', help='the treeish you want to run to')
    
    parser.add_argument('-v', '--verbosity', type=int, choices=[0, 1, 2], help='verbosity level')

    args = parser.parse_args()

    log(args.verbosity, 1, 'target objects: {}'.format(args.targetObjects))
    log(args.verbosity, 1, 'starting point: {}'.format(args.startingPoint))
    log(args.verbosity, 1, 'end point: {}'.format(args.endPoint))
    log(args.verbosity, 1, 'verbosity: {}'.format(args.verbosity))
    if args.single_commit:
        log(args.verbosity, 1, 'single commit mode')
    elif args.linear:
        log(args.verbosity, 1, 'linear mode')
    elif args.logarithmic:
        log(args.verbosity, 1, 'logarithmic mode')
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


def processStartingPoint(startingPoint, targetObjects, verbosity):
    foundFiles = findFilesAtPoint(startingPoint, targetObjects)
    sumOfLines = sum(countLinesInOldFile(f, startingPoint) for f in foundFiles)

    log(verbosity, 1, 'number of lines in all files: {}'.format(sumOfLines))
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


def findHalfLife(startingPoint, endPoint, targetObjects, verbosity):
    linesAtStart, filesAtStartingPoint = processStartingPoint(startingPoint, targetObjects, verbosity)

    for targetPoint in getTargetPoints(startingPoint, endPoint):
        linesChangedAtTarget = countChangedLines(startingPoint, targetPoint, filesAtStartingPoint)

        log(verbosity, 1, 'changed lines / all lines: {} / {}'.format(linesChangedAtTarget, linesAtStart))
        halfPointReached = linesChangedAtTarget > (linesAtStart / 2)
        if halfPointReached:
            dateOfStart = getDateOfPoint(startingPoint)
            dateOfHalfPoint = getDateOfPoint(targetPoint)
            commitsFromStartToHalfPoint = len(getPointsInInterval(startingPoint, targetPoint))

            log(verbosity, 0, 'reached half point for {} from {} at {} ({} commits)'.format
                (startingPoint, dateOfStart, dateOfHalfPoint, commitsFromStartToHalfPoint))
            return targetPoint

    log(verbosity, 0, 'no half point found for {}'.format(startingPoint))
    return None


def main():
    args = parseArguments()
    
    if args.single_commit:
        findHalfLife(args.startingPoint, args.endPoint, args.targetObjects, args.verbosity)

    elif args.linear:
        points = getPointsInInterval(args.startingPoint, args.endPoint)
        points.insert(0, args.startingPoint)
        for currentPoint in points:
            findHalfLife(currentPoint, args.endPoint, args.targetObjects, args.verbosity)

    elif args.logarithmic:
        points = getPointsInInterval(args.startingPoint, args.endPoint)
        points.insert(0, args.startingPoint)
        nextPointToStartFrom = args.startingPoint
        for currentPoint in points:
            if currentPoint == nextPointToStartFrom:
                result = findHalfLife(currentPoint, args.endPoint, args.targetObjects, args.verbosity)
                if result is not None:
                    nextPointToStartFrom = result


if __name__ == "__main__":
    main()
