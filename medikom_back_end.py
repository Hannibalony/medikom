"""
    medikom is a simple GUI program for organizing tasks and information.
    Copyright (C) 2016 Georg Alexander Murzik (murzik@mailbox.org)

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

import time
import sqlite3
import logging

class Medikom(object):
    """ This class provides the back-end functionality of Medikom: data
    management of tasks and information."""
    def __init__(self):
        logging.basicConfig(
            filename="medikom.log",
            level=logging.INFO,
            style="{",
            format="{asctime} [{levelname}] {message}",
            datefmt="%d.%m.%Y %H:%M:%S")
        self.con = sqlite3.connect('medikom.sqlite')
        self.cursor = self.con.cursor()
        try:
            self.current_id()
        except sqlite3.OperationalError:
            self.install()

    def install(self):
        with self.con:
            logging.info("Installiere Datenbank ...")
            # install medikom database
            self.cursor.execute("CREATE TABLE configuration(option TEXT, value INT)")
            self.cursor.execute((
                "CREATE TABLE entries( "
                "id INT, type INT, ts INT, title TEXT, notes TEXT, "
                "PRIMARY KEY(id))"))
            self.cursor.execute((
                "CREATE TABLE attachments("
                "id INT, attachment TEXT, "
                "PRIMARY KEY(id, attachment), "
                "FOREIGN KEY(id) REFERENCES entries)"))

            # insert default value(s)
            self.cursor.execute("INSERT INTO configuration VALUES('current_id', '0')")
            logging.info("Datenbankinstallation abgeschlossen.")
            

    def current_id(self):
        """Gets id value for new entry."""
        self.cursor.execute('SELECT * FROM configuration')
        __, current_id = self.cursor.fetchone()
        return int(current_id)

    def add_entry(self, entry_type, title, notes):
        with self.con:
            id = self.current_id()
            ts = time.time()
            query = "INSERT INTO entries VALUES(?, ?, ?, ?, ?)"
            sqlinsert = (id, entry_type, ts, title, notes)
            self.cursor.execute(query, sqlinsert)
            self.cursor.execute((
                "UPDATE configuration "
                "SET value = %i "
                "WHERE option = 'current_id'" % (id + 1)))
            if entry_type == 0:
                logging.info(
                    "Neue Aufgabe '{title}' #{id} erstellt.".format(title=title, id=id))
            else:
                logging.info(
                    "Neue Info '{title}' #{id} erstellt.".format(title=title, id=id))

    def rm_entry(self, id):
        with self.con:
            self.cursor.execute("DELETE FROM attachments WHERE id = ?", (id,))
            self.cursor.execute("DELETE FROM entries WHERE id = ?", (id,))
            logging.info("Eintrag #{id} gelöscht.".format(id=id))

    def edit_title(self, id, new_title):
        with self.con:
            ts = time.time()
            query = "UPDATE entries SET title = ?, ts = ? WHERE id = ?"
            sqlinsert = (new_title, ts, id)
            self.cursor.execute(query, sqlinsert)
            logging.info("Eintrag #{id} zu '{title}' umbenannt.".format(id=id, title=new_title))

    def edit_notes(self, id, new_notes):
        with self.con:
            ts = time.time()
            query = "UPDATE entries SET notes = ?, ts = ? WHERE id = ?"
            sqlinsert = (new_notes, ts, id)
            self.cursor.execute(query, sqlinsert)
            logging.info("Eintrag #{id} editiert.".format(id=id))

    def add_attachment(self, id, attachment):
        with self.con:
            ts = time.time()
            self.cursor.execute("INSERT INTO attachments VALUES(?, ?)", (id, attachment))
            self.cursor.execute("UPDATE entries SET ts = ? WHERE id = ?", (ts, id))
            logging.info("Anhang '{attachment}' zu #{id} hinzugefügt.".format(id=id, attachment=attachment))

    def rm_attachment(self, id, attachment):
        with self.con:
            ts = time.time()
            self.cursor.execute("DELETE FROM attachments WHERE attachment = ?", (attachment,))
            self.cursor.execute("UPDATE entries SET ts = ? WHERE id = ?", (ts, id))
            logging.info("Anhang '{attachment}' von #{id} entfernt.".format(id=id, attachment=attachment))

    def get_titles(self):
        with self.con:
            self.cursor.execute(
                "SELECT id, ts, title FROM entries WHERE type = 0 ORDER BY ts DESC")
            tasks_results = self.cursor.fetchall()
            self.cursor.execute(
                "SELECT id, ts, title FROM entries WHERE type = 1 ORDER BY ts DESC")
            information_results = self.cursor.fetchall()
            return tasks_results, information_results

    def get_entry(self, id):
        with self.con:
            self.cursor.execute((
                "SELECT ts, title, notes FROM entries "
                "WHERE id = ? ORDER BY ts"), (id,))
            entry_results = self.cursor.fetchone()
            self.cursor.execute(
                "SELECT attachment FROM attachments WHERE id = ?", (id,))
            attachments = self.cursor.fetchall()
            return entry_results, attachments

