"""
    medikom is a simple GUI program for organizing tasks and information.
    Copyright (C) 2015 Georg Alexander Murzik (murzik@mailbox.org)

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import time
import sqlite3
import subprocess
from tkinter import *
from tkinter.messagebox import askyesno, showinfo
from tkinter.filedialog import askopenfilename


class Callable(object):
    """ This class is taken from Allen B. Downey (availiable at
    http://www.greenteapress.com/thinkpython/code/Gui.py), who adapted it from
    from the Python Cookbook 9.1, page 302."""
    def __init__(self, func, *args, **kwds):
        self.func = func
        self.args = args
        self.kwds = kwds

    def __call__(self, *args, **kwds):
        d = dict(self.kwds)
        d.update(kwds)
        return self.func(*self.args+args, **d)

    def __str__(self):
        return self.func.__name__


class Medikom(object):
    """ This class provides the back-end functionality of Medikom (data
    management of tasks and information) and creates a Gui instance."""
    def __init__(self):
        try:
            self.current_id()
        except sqlite3.OperationalError:
            self.install()
        finally:
            tk = Tk()
            gui = Gui(tk, self)
            gui.overview(tk, self)
            tk.mainloop()

    def install(self):
        with con:
            # install medikom database
            cursor.execute("CREATE TABLE configuration(option TEXT, value INT)")
            cursor.execute((
                "CREATE TABLE entries( "
                "id INT, type INT, ts INT, title TEXT, notes TEXT, "
                "PRIMARY KEY(id))"))
            cursor.execute((
                "CREATE TABLE attachments("
                "id INT, attachment TEXT, "
                "PRIMARY KEY(id, attachment), "
                "FOREIGN KEY(id) REFERENCES entries)"))

            # insert default value(s)
            cursor.execute("INSERT INTO configuration VALUES('current_id', '0')")

    def current_id(self):
        cursor.execute('SELECT * FROM configuration')
        __, current_id = cursor.fetchone()
        return int(current_id)

    def add_entry(self, entry_type, title, notes):
        with con:
            id = self.current_id()
            ts = time.time()
            query = "INSERT INTO entries VALUES(?, ?, ?, ?, ?)"
            sqlinsert = (id, entry_type, ts, title, notes)
            cursor.execute(query, sqlinsert)
            cursor.execute((
                "UPDATE configuration "
                "SET value = %i "
                "WHERE option = 'current_id'" % (id + 1)))

    def rm_entry(self, id):
        with con:
            cursor.execute("DELETE FROM attachments WHERE id = ?", (id,))
            cursor.execute("DELETE FROM entries WHERE id = ?", (id,))

    def edit_title(self, id, new_title):
        with con:
            ts = time.time()
            query = "UPDATE entries SET title = ?, ts = ? WHERE id = ?"
            sqlinsert = (new_title, ts, id)
            cursor.execute(query, sqlinsert)

    def edit_notes(self, id, new_notes):
        with con:
            ts = time.time()
            query = "UPDATE entries SET notes = ?, ts = ? WHERE id = ?"
            sqlinsert = (new_notes, ts, id)
            cursor.execute(query, sqlinsert)

    def add_attachment(self, id, attachment):
        with con:
            ts = time.time()
            cursor.execute("INSERT INTO attachments VALUES(?, ?)", (id, attachment))
            cursor.execute("UPDATE entries SET ts = ? WHERE id = ?", (ts, id))

    def rm_attachment(self, id, attachment):
        with con:
            ts = time.time()
            cursor.execute("DELETE FROM attachments WHERE attachment = ?", (attachment,))
            cursor.execute("UPDATE entries SET ts = ? WHERE id = ?", (ts, id))

    def get_titles(self):
        """Mal schauen, ob das richtig (absteigend) sortiert ist!"""
        with con:
            cursor.execute(
                "SELECT id, ts, title FROM entries WHERE type = 0 ORDER BY ts DESC")
            tasks_results = cursor.fetchall()
            cursor.execute(
                "SELECT id, ts, title FROM entries WHERE type = 1 ORDER BY ts DESC")
            information_results = cursor.fetchall()
            return tasks_results, information_results

    def get_entry(self, id):
        with con:
            cursor.execute((
                "SELECT ts, title, notes FROM entries "
                "WHERE id = ? ORDER BY ts"), (id,))
            entry_results = cursor.fetchone()
            cursor.execute(
                "SELECT attachment FROM attachments WHERE id = ?", (id,))
            attachments = cursor.fetchall()
            return entry_results, attachments


class Gui():
    """ This class provides static GUI functionalities for Medikom."""
    # General GUI settings
    WIN_WIDTH = 1200    # 1600
    WIN_HIGHT = 600    # 900
    ROW_HIGHT = 26
    ROW_SPACE = 2.5
    SPACE_ONE = 60
    SPACE_TWO = 30
    TEXT_FRAME_LINES = 8    # 16
    selected_id = None

    def __init__(self, Tk, Medikom):
        # set title and window size
        Tk.title('Informationsverwaltung der Mediathek 2.0')
        Tk.geometry('{width}{sep}{hight}'.format(
            width=self.WIN_WIDTH, sep='x', hight=self.WIN_HIGHT))
        self.update_n(Medikom)

    def update_n(self, Medikom):
        # return the maximum of task and information entries
        tasks_results, information_results = Medikom.get_titles()
        self.n = max(len(tasks_results), len(information_results)) + 1

    def format_ts(self, ts):
        date = time.strftime('%d.%m.%Y', time.gmtime(ts))
        day = ''
        if time.gmtime(ts)[6] == 0:
            day = 'Mo '
        elif time.gmtime(ts)[6] == 1:
            day = 'Di '
        elif time.gmtime(ts)[6] == 2:
            day = 'Mi '
        elif time.gmtime(ts)[6] == 3:
            day = 'Do '
        elif time.gmtime(ts)[6] == 4:
            day = 'Fr '
        elif time.gmtime(ts)[6] == 5:
            day = 'Sa '
        elif time.gmtime(ts)[6] == 6:
            day = 'So '
        return '{day}{date}{sep}'.format(day=day, date=date, sep=' | ')

    def list_entries(self, Tk, Medikom, results, entry_type):
        if entry_type == 0:   # tasks (left column)
            x = self.SPACE_TWO
        else:   # information (right column)
            x = self.WIN_WIDTH / 2 + (.25 * self.SPACE_ONE)
        for i, (id, ts, title) in enumerate(results):
            ts = self.format_ts(ts)
            task_button = Button(
                Tk, text=ts + title, font='Courier 10', anchor='w',
                command=Callable(self.view_details, Tk, Medikom, id))
            task_button.place(
                x=x, y=(i + 1) * (self.ROW_HIGHT + self.ROW_SPACE),
                width=(self.WIN_WIDTH / 2) - (1.25 * self.SPACE_ONE),
                height=self.ROW_HIGHT)
            rm_task_button = Button(
                Tk, text='√',
                command=Callable(self.rm_entry, Tk, Medikom, id, title))
            rm_task_button.place(
                x=x + (self.WIN_WIDTH / 2) - (1.25 * self.SPACE_ONE),
                y=(i + 1) * (self.ROW_HIGHT + self.ROW_SPACE),
                width=self.SPACE_TWO, height=self.ROW_HIGHT)

            # highlight selected entries and those with priority
            if self.selected_id and (id == self.selected_id):
                task_button.config(bg='lightblue')
                rm_task_button.config(bg='lightblue')
            if title.startswith('!'):
                task_button.config(bg='IndianRed2')
                rm_task_button.config(bg='IndianRed2')

    def add_entry(self, Tk, Medikom, entry_type, title):
        notes = ''
        Medikom.add_entry(entry_type, title, notes)
        self.update_n(Medikom)
        id = Medikom.current_id()-1
        self.view_details(Tk, Medikom, id)

    def rm_entry(self, Tk, Medikom, id, title):
        question_title = "Löschbestätigung"
        question = "Soll Eintrag '%s' wirklich gelöscht werden?" % title
        if askyesno(question_title, question):
            Medikom.rm_entry(id)
            self.update_n(Medikom)
            self.overview(Tk, Medikom)

    def update_entry_title(self, Tk, Medikom, id, title):
        Medikom.edit_title(id, title)
        self.view_details(Tk, Medikom, id)

    def update_entry_notes(self, Tk, Medikom, id, title):
        Medikom.edit_notes(id, title)
        self.view_details(Tk, Medikom, id)

    def attach_file(self, Tk, Medikom, id):
        attachment = askopenfilename()
        if attachment:
            try:
                Medikom.add_attachment(id, attachment)
                self.view_details(Tk, Medikom, id)
            except sqlite3.IntegrityError:
                pass

    def unattach_file(self, Tk, Medikom, id, attachment, __):
        Medikom.rm_attachment(id, attachment)
        self.view_details(Tk, Medikom, id)

    def open_attachment(self, attachment):
        if os.name == 'posix':
            subprocess.call(['xdg-open', attachment])
        elif sys.platform.startswith('darwin'):
            subprocess.call(['open', attachment])
        elif os.name == 'nt':
            os.startfile(attachment)

    def overview(self, Tk, Medikom):
        # get content
        tasks_results, information_results = Medikom.get_titles()

        # clear screen
        canvas = Canvas(Tk, width=self.WIN_WIDTH, height=self.WIN_HIGHT * 2)
        canvas.place(x=0, y=0)

        # headers
        tasks_label = Label(Tk, text='Aufgaben', font='Liberation 14')
        tasks_label.place(
            x=0, y=0, width=self.WIN_WIDTH/2, height=self.ROW_HIGHT)
        info_label = Label(Tk, text='Informationen', font='Liberation 14')
        info_label.place(
            x=self.WIN_WIDTH/2, y=0,
            width=self.WIN_WIDTH/2, height=self.ROW_HIGHT)

        self.list_entries(Tk, Medikom, tasks_results, 0)
        self.list_entries(Tk, Medikom, information_results, 1)

        # lower window part
        canvas.create_line(
            self.SPACE_ONE, (self.n + 1.5) * (self.ROW_HIGHT + self.ROW_SPACE),
            self.WIN_WIDTH - self.SPACE_ONE, (self.n + 1.5) * (self.ROW_HIGHT + self.ROW_SPACE),
            fill='#000001', width=1)

        add_task_button = Button(Tk, text='+',
            command=Callable(self.view_new_title, Tk, Medikom, 0))
        add_task_button.place(
            x=self.WIN_WIDTH / 4 - self.SPACE_TWO / 2,
            y=self.n * (self.ROW_HIGHT + self.ROW_SPACE),
            width=self.SPACE_TWO, height=self.ROW_HIGHT)

        add_info_button = Button(Tk, text='+',
            command=Callable(self.view_new_title, Tk, Medikom, 1))
        add_info_button.place(
            x=0.75 * self.WIN_WIDTH - self.SPACE_TWO / 2,
            y=self.n * (self.ROW_HIGHT + self.ROW_SPACE),
            width=self.SPACE_TWO, height=self.ROW_HIGHT)

        if self.selected_id is None:
            selection_label = Label(
                Tk, text='Kein Eintrag ausgewählt.', font='Liberation 10')
            selection_label.place(
                x=self.WIN_WIDTH / 2 - 0.125 * self.WIN_WIDTH,
                y=(self.n + 1) * (self.ROW_HIGHT + self.ROW_SPACE),
                width=self.WIN_WIDTH / 4, height=self.ROW_HIGHT)

    def view_new_title(self, Tk, Medikom, entry_type):
        self.selected_id = False
        self.overview(Tk, Medikom)
        if entry_type == 0:
            text = "Titel der neuen Aufgabe:"
        elif entry_type == 1:
            text = "Titel der neuen Information:"
        details_label = Label(
            Tk, text=text, font='Liberation 10',
            fg='Black')
        details_label.place(
            x=self.SPACE_TWO / 2,
            y=(self.n + 2) * (self.ROW_HIGHT + self.ROW_SPACE),
            width=self.WIN_WIDTH - self.SPACE_TWO, height=self.ROW_HIGHT)
        textframe = Text(Tk, font='Liberation 12', height=1, width=int(self.WIN_WIDTH / 4))
        textframe.place(
            x=self.SPACE_TWO, y=(self.n + 3) * (self.ROW_HIGHT + self.ROW_SPACE),
            width=self.WIN_WIDTH - self.SPACE_ONE - 10, height=self.ROW_HIGHT)
        create_button = Button(
            Tk, text='Erstellen',
            command=lambda: self.add_entry(Tk, Medikom, entry_type, textframe.get(1.0, END).strip()))
        create_button.place(
            x=(self.WIN_WIDTH / 2) - (self.WIN_WIDTH / 16),
            y=(self.n + 4) * (self.ROW_HIGHT + self.ROW_SPACE),
            width=self.WIN_WIDTH / 8, height=self.ROW_HIGHT)

    def view_edit_title(self, Tk, Medikom, id, old_title, *__):
        self.overview(Tk, Medikom)
        text = "Neuer Titel des Eintrags:"
        details_label = Label(
            Tk, text=text, font='Liberation 10',
            fg='Black')
        details_label.place(
            x=self.SPACE_TWO / 2,
            y=(self.n + 2) * (self.ROW_HIGHT + self.ROW_SPACE),
            width=self.WIN_WIDTH - self.SPACE_TWO, height=self.ROW_HIGHT)
        textframe = Text(Tk, font='Liberation 12', height=1, width=int(self.WIN_WIDTH / 4))
        textframe.place(
            x=self.SPACE_TWO, y=(self.n + 3) * (self.ROW_HIGHT + self.ROW_SPACE),
            width=self.WIN_WIDTH - self.SPACE_ONE - 10, height=self.ROW_HIGHT)
        textframe.insert(END, old_title)
        create_button = Button(
            Tk, text='Aktualisieren',
            command=lambda: self.update_entry_title(Tk, Medikom, id, textframe.get(1.0, END).strip()))
        create_button.place(
            x=(self.WIN_WIDTH / 2) - (self.WIN_WIDTH / 16),
            y=(self.n + 4) * (self.ROW_HIGHT + self.ROW_SPACE),
            width=self.WIN_WIDTH / 8, height=self.ROW_HIGHT)

    def view_details(self, Tk, Medikom, id):
        self.selected_id = id
        self.overview(Tk, Medikom)
        entry_results, attachments = Medikom.get_entry(id)
        ts, title, notes = entry_results
        ts = self.format_ts(ts)[:-3]
        details_text = 'Details zu %s (zuletzt geändert am %s)' % (title, ts)
        details_label = Label(
            Tk, text=details_text, font='Liberation 10', fg='Black', anchor='w')
        details_label.place(
            x=self.SPACE_TWO,
            y=(self.n + 2) * (self.ROW_HIGHT + self.ROW_SPACE),
            width=self.WIN_WIDTH - self.SPACE_TWO, height=self.ROW_HIGHT)

        details_label.bind(sequence='<Button-1>',
            func=Callable(self.view_edit_title, Tk, Medikom, id, title))

        # add attachment button and list attachments
        attach_button = Button(
            Tk, text='Neuer Anhang',
            command=lambda: self.attach_file(Tk, Medikom, id))
        attach_button.place(
            x=self.SPACE_TWO,
            y=(self.n + 3) * (self.ROW_HIGHT + self.ROW_SPACE),
            width=self.WIN_WIDTH / 8, height=self.ROW_HIGHT)
        if attachments:
            xpos = (1.5 * self.SPACE_TWO) + (self.WIN_WIDTH / 8)
            for i, attachment in enumerate(attachments):
                attachment = attachment[0]
                filename = ''
                if '\\' in attachment:
                    filename = attachment.split('\\')[-1]
                elif '/' in attachment:
                    filename = attachment.split('/')[-1]
                width = len(filename) * 7.2
                attachment_button = Button(
                    Tk, text=filename, font='Courier 9', fg="blue",
                    command=Callable(self.open_attachment, attachment))
                attachment_button.place(
                    x=xpos,
                    y=(self.n + 3) * (self.ROW_HIGHT + self.ROW_SPACE),
                    width=width, height=self.ROW_HIGHT)
                xpos = xpos + width + (self.SPACE_TWO/2)
                attachment_button.config(relief='flat')
                attachment_button.bind(sequence='<Button-3>',
                    func=Callable(self.unattach_file, Tk, Medikom, id, attachment))

        # text element and scrollbar
        textframe = Text(
            Tk, font='Liberation 12', height=self.TEXT_FRAME_LINES,
            width=int(self.WIN_WIDTH / 4))
        scrollbar = Scrollbar(Tk)
        textframe.place(
            x=self.SPACE_TWO,
            y=(self.n + 4) * (self.ROW_HIGHT + self.ROW_SPACE),
            width=self.WIN_WIDTH - self.SPACE_ONE - 10,
            height=self.ROW_HIGHT * self.TEXT_FRAME_LINES)
        scrollbar.place(
            x=self.SPACE_TWO + self.WIN_WIDTH - self.SPACE_ONE - 10,
            y=(self.n + 4) * (self.ROW_HIGHT + self.ROW_SPACE),
            width=10,
            height=self.ROW_HIGHT * self.TEXT_FRAME_LINES)
        scrollbar.config(command=textframe.yview)
        textframe.config(yscrollcommand=scrollbar.set)
        textframe.insert(END, notes)

        # update button
        update_button = Button(
            Tk, text='Text Aktualisieren',
            command=lambda: self.update_entry_notes(
                Tk, Medikom, id, textframe.get(1.0, END)))
        update_button.place(
            x=self.WIN_WIDTH / 2 - 0.125 * self.WIN_WIDTH,
            y=(self.n + 4) * (self.ROW_HIGHT + self.ROW_SPACE) + (self.ROW_HIGHT * self.TEXT_FRAME_LINES + 5),
            width=self.WIN_WIDTH/4, height=self.ROW_HIGHT)


if __name__ == '__main__':
    con = sqlite3.connect('medikom.sqlite')
    cursor = con.cursor()
    medikom = Medikom()
