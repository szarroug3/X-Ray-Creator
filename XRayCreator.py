import os
import sys
import ctypes
import urllib
import json as m_json
import shutil
import subprocess
from bs4 import BeautifulSoup

# Drive types
DRIVE_UNKNOWN     = 0  # The drive type cannot be determined.
DRIVE_NO_ROOT_DIR = 1  # The root path is invalid; for example, there is no volume mounted at the specified path.
DRIVE_REMOVABLE   = 2  # The drive has removable media; for example, a floppy drive, thumb drive, or flash card reader.
DRIVE_FIXED       = 3  # The drive has fixed media; for example, a hard disk drive or flash drive.
DRIVE_REMOTE      = 4  # The drive is a remote (network) drive.
DRIVE_CDROM       = 5  # The drive is a CD-ROM drive.
DRIVE_RAMDISK     = 6  # The drive is a RAM disk.
books_updated = []
books_skipped = []
spoilers = False

# Map drive types to strings
DRIVE_TYPE_MAP = { DRIVE_UNKNOWN     : 'DRIVE_UNKNOWN',
                   DRIVE_NO_ROOT_DIR : 'DRIVE_NO_ROOT_DIR',
                   DRIVE_REMOVABLE   : 'DRIVE_REMOVABLE',
                   DRIVE_FIXED       : 'DRIVE_FIXED',
                   DRIVE_REMOTE      : 'DRIVE_REMOTE',
                   DRIVE_CDROM       : 'DRIVE_CDROM',
                   DRIVE_RAMDISK     : 'DRIVE_RAMDISK'}
    
# Return drive letter of kindle if found or None if not found
def findKindle():
	print "Checking for kindle..."
	drive_info = get_drive_info()
	removable_drives = [drive_letter for drive_letter, drive_type in drive_info if drive_type == DRIVE_REMOVABLE]
	for drive in removable_drives:
		for dirName, subDirList, fileList in os.walk(drive):
			if dirName == drive + "system\.mrch":
				for fName in fileList:
					if "amzn1_account" in fName:
						"Kindle found!"
						return drive
	return None

# Return list of tuples mapping drive letters to drive types
def get_drive_info():
    result = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for i in range(26):
        bit = 2 ** i
        if bit & bitmask:
            drive_letter = '%s:' % chr(65 + i)
            drive_type = ctypes.windll.kernel32.GetDriveTypeA('%s\\' % drive_letter)
            result.append((drive_letter, drive_type))
    return result

# Get list of books
def getBooks(drive):
	books_directory = drive + "documents"
	books = []
	index = 1
	print "Searching for books..."
	for dirName, subDirList, fileList in os.walk(books_directory):
		for fName in fileList:
			if ".mobi" in fName:
				books.append(
					{'book number' : str(index),
					'book name' : fName[:-5],
					'book filepath' : dirName[:2] + '\\' + dirName[2:] + '\\' + fName,
					'book ASIN' : "",
					'X-Ray directory' : dirName[:2] + '\\' + dirName[2:] + '\\' + fName[:-4] + "sdr"})
				index = index + 1
	return books

# Remove books that already have X-Ray files
def removeBooksWithXRay(drive, books):
	books_directory = drive + "documents"
	for dirName, subDirList, fileList in os.walk(books_directory):
		if ".sdr" in dirName:
			for fName in fileList:
				if ".asc" in fName:
					for book in books:
						if book['book name'] == dirName[dirName.rfind("\\") + 1:-4]:
							books.remove(book)
							continue
	return books

# Get ASIN from Amazon
def getASIN(book):
	ASIN = -1
	query = urllib.urlencode ( { 'q' : "amazon kindle \"ebook\" " + book } )
	response = urllib.urlopen ( 'http://ajax.googleapis.com/ajax/services/search/web?v=1.0&' + query).read()
	json = m_json.loads ( response )
	results = json [ 'responseData' ] [ 'results' ]
	for result in results:
		title = result['title']
		url = result['url']
		if "amazon" in url:
			if "/dp/" in url:
				index = url.find("/dp/")
				ASIN = url[index + 4 : index + 14]
				print "Found book on amazon..."
				print "ASIN: " + ASIN
	 			return ASIN
			else:
				for i in range(10):
					amazon_page = urllib.urlopen(url)
					page_source = amazon_page.read()
					index = page_source.find("ASIN.0")
					if index > 0:
						ASIN = page_source[index + 15 : index + 25]
						print "Found book on amazon..."
						print "ASIN: " + ASIN
			 			return ASIN
	 		return ASIN

# Update ASIN in book using mobi2mobi
def updateASIN(book):
	current_directory = os.path.dirname(os.path.abspath(__file__)) + '\\'
	mobi2mobi_path = current_directory + "MobiPerl\\mobi2mobi.exe"
	command = mobi2mobi_path + " \"" + book['book filepath'] + "\" --outfile \"" + book['book filepath'] + "_NEW\" --exthtype asin --exthdata " + book['book ASIN']
	execute(command)
	os.remove(book['book filepath'])
	os.rename(book['book filepath'] + "_NEW", book['book filepath'])

# Update books' ASIN and create x-ray file in appropriate directory
def updateBooksASIN(books):
	for book in books:
		print "Book: " + book['book name']
		ASIN = getASIN(book['book name'])
		if ASIN == -1:
			print "ASIN not found. Skipping book..."
			books_skipped.append(book)
		else:
			book['book ASIN'] = ASIN
			updateASIN(book)
			url = getShelfariURL(book)
			if url == -1:
				print "Shelfari book not found. Skipping book..."
				books_skipped.append(book)
			else:
				print "Creating X-Ray file..."
				createXRayFile(book, url)
				books_updated.append(book)
		print ""
	return

# Searches for shelfari url for book
def getShelfariURL(book):
	response = urllib.urlopen ( 'http://www.shelfari.com/search/books?Keywords=' + book['book ASIN'] ).read()
	page_source = BeautifulSoup(response, "html.parser")
	for link in page_source.find_all("a"):
		url = link.get('href')
		if "http://www.shelfari.com/books/" in url and url.count('/') == 5:
			shelfari_id = url[30:url[30:].find('/') + 30]
			if shelfari_id.isdigit():
				return url
	return -1

# Creates X-Ray file using XRayBuilder
def createXRayFile(book, url):
	current_directory = os.path.dirname(os.path.abspath(__file__)) + '\\'
	temp_directory = current_directory + "temp" + '\\'
	temp_book_file = temp_directory + book['book name'].replace(" ", "") + ".mobi"
	xray_builder_directory = current_directory + "XRayBuilder\\"
	mobi_unpack_path = xray_builder_directory + "dist\\kindleunpack.exe"
	xray_builder_temp_directory = current_directory + "out\\"
	xray_builder_ext_directory = current_directory + "ext\\"
	if not os.path.exists(temp_directory):
		os.makedirs(temp_directory)
	shutil.copy2(book['book filepath'], temp_book_file )
	command = xray_builder_directory + "XRayBuilder.exe -o \"" + book['X-Ray directory'] + "\" -s " + url + " \"" + temp_book_file + "\" -u \"" + mobi_unpack_path + "\" --unattended"
	if spoilers:
		command = command + " --spoilers"
	execute(command)
	xray_file_name = "XRAY.entities." + book['book ASIN'] + ".asc"
	xray_file_name_and_dir = book['X-Ray directory'] + '\\' + xray_file_name
	command = '\"' + xray_builder_directory + "XRay2Converter.exe\" \"" + xray_file_name_and_dir + "\" " + url
	execute(command)
	for dirName, subDirList, fileList in os.walk(xray_builder_temp_directory):
		for fName in fileList:
			if book['book ASIN'] in fName:
				shutil.copy2(dirName + fName, xray_file_name_and_dir)
	shutil.rmtree(temp_directory)
	shutil.rmtree(xray_builder_temp_directory)
	shutil.rmtree(xray_builder_ext_directory)

# Remove X-Ray file for book from kindle
def removeXRayFile(book):
	print book['X-Ray directory']
	for dirName, subDirList, fileList in os.walk(book['X-Ray directory']):
		for fName in fileList:
			print fName
			if ".asc" in fName:
				print "Deleting X-Ray file for " + book['book name']
				os.remove(dirName + '\\' + fName)

# Remove all X-Ray Files from kindle
def removeAllXRayFiles(books):
	for book in books:
		removeXRayFile(book)

# Execute command line prompt
def execute(command):
	popen = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
	lines_iterator = iter(popen.stdout.readline, b"")
	for line in lines_iterator:
		print line
		if "Press Enter to exit" in line:
			popen.communicate("\n")[0]

# Create X-Ray files for book without one
def normalOperation(books):
	print "Removing books that already have X-Ray files..."
	books = removeBooksWithXRay(drive_letter, books)
	print
	print "Books without X-Ray files: "
	for book in books:
		print book['book name']
	print
	if not books:
		print "All books already have X-Ray files..."
	else:
		print "Updating ASIN for books..."
		updateBooksASIN(books)
	print "Done..."
	if books_updated:
		print "Books updated: "
		for book in books_updated:
			print "\t " + book['book name']
	if books_skipped:
		print "Books skipped: "
		for book in books_skipped:
				print "\t " + book['book name']

# Update X-Ray files for all books
def updateAllBooks(books):
	removeAllXRayFiles(books)
	print "Updating ASIN for books..."
	updateBooksASIN(books)
	print "Done..."
	if books_updated:
		print "Books updated: "
		for book in books_updated:
			print "\t " + book['book name']
	if books_skipped:
		print "Books skipped: "
		for book in books_skipped:
				print "\t " + book['book name']

# Create a list of books from user input
def createListOfBooksToUpdate(books, book_numbers):
	books_to_update = []
	print book_numbers
	for number in book_numbers:
		books_to_update.append(books[int(number) - 1])
	return books_to_update

# Update X-Ray file for specified books
def updateBooks(books):
	for book in books:
		removeXRayFile(book)
	print "Updating ASIN for books..."
	updateBooksASIN(books)
	print "Done..."
	if books_updated:
		print "Books updated: "
		for book in books_updated:
			print "\t " + book['book name']
	if books_skipped:
		print "Books skipped: "
		for book in books_skipped:
				print "\t " + book['book name']

# Get arguments from command line
def getUpdateArguments(args, books):
	if args.count == 1:
		return "none"
	if "--spoilers" in args:
		spoilers = true
	if "-ua" in args:
		return "all"
	elif "-u" in args:
		print
		for book in books:
			print book['book number'] + ". " + book['book name']
		print
		books_to_update = raw_input("Please enter book number(s) of the book(s) you'd like to update in a comma separated list: ")
		books_to_update = books_to_update.replace(" ", "")
		return books_to_update.split(',')
	else:
		return "none"

# Print help
def printHelp():
	print "python xraycreatory.py [-u] [-ua]"
	print
	print "Not using any switches will search the kindle for books without X-Ray Files,"
	print "update the books' ASIN then create an X-Ray file for it on the kindle."
	print
	print "-ua\t\tDeletes all X-Ray files and recreates them"
	print "-u\t\tWill give you a list of all books on kindle and asks you to"
	print "\t\treturn a list of book numbers for the books you want to update"
	print "--spoilers\t\tUse descriptions that contain spoilers"
	print "\t\tDefault behaviour is to use spoiler-free descriptions"
	print
	print "*NOTE: You must have kindle connected before running program."
	print "*NOTE: -ua will take precedence over -u"

# Main
if "-h" in sys.argv or "-help" in args or "-?" in args:
	printHelp()
else:
	drive_letter = findKindle()
	if drive_letter is None:
		print "Error: Kindle not found."
	else:
		print "Kindle found..."
		print "Getting list of books..."
		books = getBooks(drive_letter)
		update = getUpdateArguments(sys.argv, books)
		print update
		if update == "none": normalOperation(books)
		elif update == "all": updateAllBooks(books)
		else:
			books_to_update = createListOfBooksToUpdate(books, update)
			updateBooks(books_to_update)