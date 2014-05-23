#!/usr/bin/python

import subprocess
import math


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
    parser.add_argument('-f', '--fast', action="store_true", help='use fast (logarithmic) algorithm')

    args = parser.parse_args()

    log(args.verbosity, 1, 'target objects: {}'.format(args.targetObjects))
    log(args.verbosity, 1, 'starting point: {}'.format(args.startingPoint))
    log(args.verbosity, 1, 'end point: {}'.format(args.endPoint))
    log(args.verbosity, 1, 'verbosity: {}'.format(args.verbosity))
    log(args.verbosity, 1, 'fast: {}'.format(args.fast))
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

def openCsvFile(csvFileName):
    try:
        csvFile = open(csvFileName, "w")
    except IOError:
        csvFile = None
    return csvFile

def closeCsvFile(csvFile):
    if (csvFile != None):
        csvFile.close()


def writeToCsvFile(csvFile, line):
    if (csvFile != None):
        csvFile.write(line)


def checkTarget(startingPoint, targetPoint, filesAtStartingPoint, linesAtStart, verbosity):
    linesChangedAtTarget = countChangedLines(startingPoint, targetPoint, filesAtStartingPoint)

    log(verbosity, 1, 'changed lines / all lines: {} / {}'.format(linesChangedAtTarget, linesAtStart))
    halfPointReached = linesChangedAtTarget > (linesAtStart / 2)
    if halfPointReached:
        return targetPoint

    return None;


def announceHalfPoint(startingPoint, targetPoint, csvFile, verbosity):
    dateOfStart = getDateOfPoint(startingPoint)
    dateOfHalfPoint = getDateOfPoint(targetPoint)
    commitsFromStartToHalfPoint = len(getPointsInInterval(startingPoint, targetPoint))

    writeToCsvFile(csvFile, '{},{},{},{}\n'.
        format(startingPoint, dateOfStart, dateOfHalfPoint, commitsFromStartToHalfPoint))
    log(verbosity, 0, 'reached half point for {} from {} at {} ({} commits)'.format
        (startingPoint, dateOfStart, dateOfHalfPoint, commitsFromStartToHalfPoint))


def findHalfLife(startingPoint, endPoint, targetObjects, fast, verbosity, csvFile):
    linesAtStart, filesAtStartingPoint = processStartingPoint(startingPoint, targetObjects, verbosity)
    targetPoints = getTargetPoints(startingPoint, endPoint)
    if len(targetPoints) == 0:
        return None
    if checkTarget(startingPoint, targetPoints[len(targetPoints) - 1], filesAtStartingPoint, linesAtStart, verbosity) is None:
        return None

    if fast:
        beginning = 0
        end = len(targetPoints) - 1
        while beginning < end:
            currentTarget = (beginning + end) // 2
            result = checkTarget(startingPoint, targetPoints[currentTarget], filesAtStartingPoint, linesAtStart, verbosity)
            if result is not None:
                end = currentTarget
            else:
                if beginning != currentTarget:
                    beginning = currentTarget
                else:
                    beginning += 1

        return targetPoints[beginning]

    else:
        for targetPoint in targetPoints:
            result = checkTarget(startingPoint, targetPoint, filesAtStartingPoint, linesAtStart, verbosity)
            if result is not None:
                return result

    return None

#TODO integrate it to the tool-set
#The "time" unit is number of commits
def estimateHalfLife(startingPoint, endPoint, targetObjects, verbosity):
    linesAtStart, filesAtStartingPoint = processStartingPoint(startingPoint, targetObjects, verbosity)
    linesChangedAtTarget = countChangedLines(startingPoint, endPoint, filesAtStartingPoint)
    commitsFromStart = len(getPointsInInterval(startingPoint, endPoint))
    log(verbosity, 2, 'linesAtSTart {}, linesChangedAtTarget {}, commitsFromStart {}'.
        format(linesAtStart, linesChangedAtTarget, commitsFromStart))
    return (float(commitsFromStart)*float(math.log(2)))/(float(math.log(linesAtStart))-float(math.log(linesAtStart-linesChangedAtTarget)))
    
    
def main():
    args = parseArguments()
    
    points = getPointsInInterval(args.startingPoint, args.endPoint)
    points.insert(0, args.startingPoint)
    
    #TODO: make command line input for it.
    csvFile = openCsvFile("output.csv")
    writeToCsvFile(csvFile, "startingGitHash,dateOfStart,dateOfHalfPoint,numOfCommits\n")
    
    #log(args.verbosity, 0, 'Estimated code half-life: {}'. format(estimateHalfLife(args.startingPoint, args.endPoint, args.targetObjects, args.verbosity)))
    
    if args.single_commit:
        findHalfLife(args.startingPoint, args.endPoint, args.targetObjects, args.fast, args.verbosity, csvFile)

    elif args.linear:
        points = getPointsInInterval(args.startingPoint, args.endPoint)
        points.insert(0, args.startingPoint)
        for currentPoint in points:
            result = findHalfLife(currentPoint, args.endPoint, args.targetObjects, args.fast, args.verbosity, csvFile)
            if result is not None:
                nextPointToStartFrom = result
                announceHalfPoint(currentPoint, result, csvFile, args.verbosity)
            else:
                log(args.verbosity, 0, 'no half point found for {}'.format(currentPoint))

    elif args.logarithmic:
        points = getPointsInInterval(args.startingPoint, args.endPoint)
        points.insert(0, args.startingPoint)
        nextPointToStartFrom = args.startingPoint
        for currentPoint in points:
            if currentPoint == nextPointToStartFrom:
                result = findHalfLife(currentPoint, args.endPoint, args.targetObjects, args.fast, args.verbosity, csvFile)
                if result is not None:
                    nextPointToStartFrom = result
                    announceHalfPoint(currentPoint, result, csvFile, args.verbosity)
                else:
                    log(args.verbosity, 0, 'no half point found for {}'.format(currentPoint))

    closeCsvFile(csvFile)


if __name__ == "__main__":
    main()
