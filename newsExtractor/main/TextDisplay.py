from tkinter import *
import json

master = Tk()
Label(master, text="First Name").grid(row=0)

e1 = Entry(master)
e2 = Entry(master)

e1.grid(row=1)

# with open('scraped_articles.json') as data_file:
#     articles = json.load(data_file)
#
# for newsObject in articles.items():



mainloop( )