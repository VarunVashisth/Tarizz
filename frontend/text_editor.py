from tkinter import *
from tkinter import scrolledtext 
from tkinter import filedialog
import ctypes
import sys

appname = 'Tarizz'
notfileOpenedString = 'New File'

currentfilepath = notfileOpenedString

fileTypes = [("Text Files", "*.txt" ) , ("Markdown","*.md")]

#setting up tkinter windows 
window = Tk()
window.title(appname + "-" + currentfilepath)

window.geometry('600x800')  
window.grid_columnconfigure(0 , weight= 1)

#Handler Functions

def filedropdownhandeler(action):

    global currentfilepath

    if action == "Open":
        file = filedialog.askopenfilename(filetypes=fileTypes)
        window.title(appname + '-' + file)
        currentfilepath = file

        with open(file,'r') as f:
            txt.delete(1.0,END)
            txt.insert(INSERT,f.read())

    #making new file

    elif action == "New":
        currentfilepath = notfileOpenedString
        txt.delete(1.0,END)
        window.title(appname + "-" + file)

    #Saving a file
    elif action == "Save" or action == "SaveAs":
        if currentfilepath == notfileOpenedString or action == "SaveAs" :
            currentfilepath = filedialog.asksaveasfilename(filetypes=fileTypes)

        with open(currentfilepath,'w') as f:
            f.write(txt.get('1.0','end'))
        
        window.title(appname + "-" + currentfilepath)

def textchange(event):
    window.title(appname + '-' + currentfilepath)


#adding widgets 


#text area

txt = scrolledtext.ScrolledText(window,height=999)
txt.grid(row=1, sticky=N+S+E+W)

txt.bind('<KeyPress>',textchange)


# Menu
menu = Menu(window)
# set tearoff to 0
fileDropdown = Menu(menu, tearoff=False)
# Add Commands and and their callbacks
fileDropdown.add_command(label='New', command=lambda: filedropdownhandeler("new"))
fileDropdown.add_command(label='Open', command=lambda: filedropdownhandeler("open"))
# Adding a seperator between button types.
fileDropdown.add_separator()
fileDropdown.add_command(label='Save', command=lambda: filedropdownhandeler("save"))
fileDropdown.add_command(label='Save as', command=lambda: filedropdownhandeler("saveAs"))
menu.add_cascade(label='File', menu=fileDropdown)
# Set Menu to be Main Menu
window.config(menu=menu)

if len(sys.argv) == 2:
    currentFilePath = sys.argv[1]
    window.title(appName + " - " + currentFilePath)
    with open(currentFilePath, 'r') as f:
        txt.delete(1.0,END)
        txt.insert(INSERT,f.read())

window.mainloop()