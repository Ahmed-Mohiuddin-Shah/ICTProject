"""
Part by: Muhammad Hamza
"""

import csv
import os
import cv2 as cv
import calendar
from config import *
import sqlite3
from tkinter.filedialog import asksaveasfile
from tkinter.messagebox import showwarning


def printTable(table):
    """This function prints the table in a tkinter treeview widget in a nice way.
    Args:
        table (Treeview): This is the widget in which we're print the data.
    """
    con = sqlite3.connect(databaseName)
    cur = con.cursor()

    cur.execute(f"SELECT * FROM {tableName}")
    data = cur.fetchall()
    data.sort(key=lambda d: d[1].upper())
    for id, name, semester in data:
        percentageSum = 0
        for course in courses:
            percentageSum += getAttendancePercentageFor(id, course)

        table.insert(parent='', index='end', iid=id, text='',
                     values=(id, name, semester, f'{percentageSum/8:.2f}%'))

    cur.close()
    con.close()


def downloadReport(id):
    """
    This function will download the attendance report of a student
    """
    files = [('Excel files', '*.xlsx'), ('All files', '*.*')]
    attendanceReport = getAttendanceTableFor(id)
    filename = asksaveasfile(
        filetypes=files, defaultextension=files, initialfile=f'{id}')
    if filename:
        attendanceReport.to_excel(filename.name, index=False)


def getColumnNames(table: str):
    """
    This function get table name as argument.
    Then it returns user the list of columns which
    that table have.
    """
    con = sqlite3.connect(databaseName)
    cursor = con.cursor()

    cursor.execute(
        f"PRAGMA table_info({table});")
    columnNames = [n for _, n, *_ in cursor.fetchall()]

    cursor.close()
    con.close()

    return columnNames


def markAttendance(students: list, course: str, dayTime: str) -> None:
    """
    This function accepts a list of student ids which are supposed to be marked as present.
    Second argument is the course for which this attendance is to be marked.
    Third is the unique Identifier for this day and this time of this class.
    (Example: 15-12-2022-900)
    """
    course = course.upper()
    columns = getColumnNames(course)

    db = sqlite3.connect(databaseName)
    cursor = db.cursor()

    columnsString = ["dayTime"]
    valuesString = [f"'{dayTime}'"]
    for column in columns[1:]:
        if column in students:
            columnsString.append(f"'{column}'")
            valuesString.append("'P'")
        else:
            columnsString.append(f"'{column}'")
            valuesString.append("'A'")

    columnsString = ", ".join(columnsString)
    valuesString = ",".join(valuesString)

    query = f"INSERT INTO {course} ({columnsString}) VALUES ({valuesString});"
    cursor.execute(query)
    db.commit()

    cursor.close()
    db.close()


def getTotalNumberOfRecords(table):
    """This function will return total number of records in a table.

    Args:
        table (string): This is the table name for which we want to get the total number of records.

    Returns:
        number: number of records in the table
    """
    db = sqlite3.connect(databaseName)
    cursor = db.cursor()

    cursor.execute(f"SELECT COUNT(*) FROM {table};")
    totalNumberOfRecords = cursor.fetchone()[0]

    cursor.close()
    db.close()
    return totalNumberOfRecords


def getAttendancePercentageFor(id: int, course: str) -> float:
    """This function will return percentage of presence of a student
    whose id is passed in the current course.

    Args:
        id (int): CMS ID of student
        course (str): Course code

    Returns:
        float: Percentage of attendance
    """
    course = course.upper()
    db = sqlite3.connect(databaseName)
    cursor = db.cursor()
    query = f"SELECT `{id}` FROM `{course}`;"
    cursor.execute(query)
    data = cursor.fetchall()
    # getting first item from the data returned from sql
    # That is either 'A' or 'P'
    data = [d for d, in data]
    cursor.close()
    db.close()

    totalRecordsCount = getTotalNumberOfRecords(course)
    presentCount = data.count('P')
    try:
        percentage = presentCount / totalRecordsCount * 100
    except ZeroDivisionError:
        return 0

    return percentage


def getWeekDay(date: str, sep: str = '-') -> str:
    """This function takes a date in form of string and an optional separator which the date is separated by. Then it return the weekday for that date.

    Args:
        date (str): The date string in form of day[sep]month[sep]year
        sep (str): The [sep] that separates the entities of date

    Returns:
        str: Week day at that date
    """
    day, month, year = date.split(sep)
    return calendar.day_name[calendar.weekday(
        int(year), int(month), int(day))]


def getAttendanceTableFor(id: str) -> pd.DataFrame:
    """This function takes a student cms Id, then create a table for his attendance in all courses and return it as a DataFrame object.

    Args:
        id (str): Id of student

    Returns:
        pd.DataFrame: DataFrame object for attendance of student.
    """
    db = sqlite3.connect(databaseName)
    cur = db.cursor()
    tableOfAttendance = {}

    timeTableWeekDays = timeTable.to_dict('tight')['index']
    timeTableTimes = timeTable.to_dict('tight')['columns']
    timeTableClasses = timeTable.to_dict('tight')['data']

    for course in courses:
        cur.execute(f"SELECT `dayTime`, `{id}` FROM `{course}`;")
        records = cur.fetchall()

        # dayTime is in form of date-month-year-time
        # So first 3 are date and last one is time
        dates = list(["-".join(date.split('-')[:3])
                      for date, _ in records])
        times = list([date.split('-')[-1]
                      for date, _ in records])
        attendances = list([attendance
                           for _, attendance in records])
        for time in times:
            if len(time) == 3:
                times[times.index(time)] = '0' + time
        for date in dates:
            if tableOfAttendance.get(date) is None:
                tableOfAttendance[date] = ['-'] * len(timeTableTimes)

        for date in dates:

            for time, attendance in zip(times, attendances):
                weekDayIndex = timeTableWeekDays.index(getWeekDay(date))
                timeIndex = timeTableTimes.index(time)
                tableOfAttendance[date][timeIndex] = f"{timeTableClasses[weekDayIndex][timeIndex]}: {attendance}"

    tableOfAttendance = [[key, *value]
                         for key, value in tableOfAttendance.items()]

    cur.close()
    db.close()
    attendanceDataFrame = pd.DataFrame(tableOfAttendance,
                                       columns=(['Date'] + timeTableTimes))
    return attendanceDataFrame


def loadName(id):
    """This function will return name of student whose id is passed.

    Args:
        id (number): CMS ID of student

    Returns:
        string: Name of student
    """
    db = sqlite3.connect(databaseName)
    cursor = db.cursor()
    query = f"SELECT * FROM {tableName} WHERE cmsId={id}"
    cursor.execute(query)
    _, name, _ = cursor.fetchall()[0]
    cursor.close()
    return name


def getFrameInRGB(capture):
    """This function will return a frame from the capture object in RGB format.

    Args:
        capture (frame): This is the capture object from which we want to get the frame.

    Returns:
        frame: This is the frame in RGB format.
    """
    success, frame = capture.read()
    return cv.cvtColor(frame, cv.COLOR_BGR2RGB) if success else None


def getDefaultAttendanceRecord(today):
    """This function will return a default attendance record for a day.

    Args:
        today (string): This is the date for which we want to create a default attendance record.

    Returns:
        dict: This is the default attendance record for a day.
    """
    return {
        "day": today,
        "0900": 0, "1000": 0, "1100": 0, "1200": 0, "1300": 0, "1400": 0, "1500": 0, "1600": 0
    }


def getCSV(filename):
    """This function will return a list of encodings from a csv file.

    Args:
        filename (string): This is the name of the csv file from which we want to get the encodings.

    Returns:
        list: This is the list of encodings.
    """
    with open(f"./{directoryName}/{filename}") as f:
        reader = csv.reader(f)
        encodings = []
        for code in reader:
            encodings.extend(code)
        encodings = [float(code) for code in encodings]
    return encodings


def getKnownEncodings():
    """This function will return a dictionary of known encodings.

    Returns:
        Series: This is the dictionary of known encodings.
    """
    knownEncodingFiles = os.listdir(f"./{directoryName}")
    knownEncodings = pd.Series(dtype='float64')
    for file in knownEncodingFiles:
        knownEncodings[file[:-4]] = getCSV(file)

    return knownEncodings


def showMessage(text):
    """This function will show a message box with the text passed."""
    showwarning("Warning", text)


def truncateWidget(widget):
    """This function will remove all the children of a widget."""
    for child in widget.winfo_children():
        child.destroy()
