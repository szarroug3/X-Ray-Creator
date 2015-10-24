*** X-Ray Creator ***  
A console application that searches updates ASIN  
and creates or updates X-Ray files for books on a kindle  
Created by S. Zarroug  
Original X-Ray Builder script  by Nick Niemi - ephemeral.vilification@gmail.com  
https://github.com/Ephemerality/xray-builder  
Original X-Ray script by shinew  
http://www.mobileread.com/forums/showthread.php?t=157770  
http://www.xunwang.me/xray/  
Original mobi2mobi and mobiconverter scripts by Jad  
http://www.mobileread.com/forums/showthread.php?t=21763  
  
**********************
   
Requirements:  
* Python 2.7  
  * https://www.python.org/downloads/release/python-279/  
  
Program usage:  
python xraycreatory.py [-u] [-ua]  
*NOTE: -ua will take precedence over -u  
-ua				Deletes all X-Ray files and recreates them  
-u 				Will give you a list of all books on kindle and asks you to  
				return a list of book numbers for the books you want to update  
--spoilers		Use descriptions that contain spoilers  
				Default behaviour is to use spoiler-free descriptions  
  
Books should be DRM-free. If you create an X-Ray file for a book, but still use the DRM copy on your Kindle,  
you will run into issues where the excerpts do not line up do where they are in the DRM-free version.  
Chapter detection on DRM books is not supported.  

Will only work for mobi files.  
