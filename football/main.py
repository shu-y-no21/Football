#!/usr/bin/python3
'''
   Copyright 2017 Mirko Brombin (brombinmirko@gmail.com)

   This file is part of Football.

    Football is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Football is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with Football.  If not, see <http://www.gnu.org/licenses/>.
'''

import gi
import sys
import json
import requests
from datetime import datetime, timedelta
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

API_KEY = "cb3a6fe9d9284af79a13661ff6191ea6"
headers = {'X-Auth-Token':API_KEY, 'X-Response-Control': 'minified'}
stylesheet = """
    @define-color colorPrimary #249C5F;
    @define-color textColorPrimary #f2f2f2;
    @define-color textColorPrimaryShadow #197949;
""";

class Football(Gtk.Window):

    def __init__(self):
        Gtk.Window.__init__(self, title="Football")
        
        self.header_bar()

        self.show_latest = False

        #grid
        self.grid = Gtk.Grid()
        self.grid.set_column_homogeneous(True)
        self.grid.set_row_homogeneous(True)

        self.gen_competitions()
        self.gen_fixtures("446")

        #setting up the layout
        self.scrollable_treelist = Gtk.ScrolledWindow()
        self.scrollable_treelist.set_vexpand(True)
        self.grid.attach(self.scrollable_treelist, 0, 0, 8, 10)
        self.scrollable_treelist.add(self.treeview)

        #paned
        self.paned = Gtk.Paned()
        self.paned.add1(self.grid)
        self.add(self.paned)
        
        #hbox
        self.hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.hbox.add(self.competitions_combo)
        self.hbar.pack_start(self.hbox)

        # last
        self.last = Gtk.Button("Last played")
        self.last = Gtk.Button.new_from_icon_name("document-open-recent", Gtk.IconSize.LARGE_TOOLBAR)
        self.last.connect("clicked", self.on_last_clicked)
        self.last.set_property("tooltip-text", "Last 7 days")
        self.hbar.pack_end(self.last)

    def header_bar(self):
        self.hbar = Gtk.HeaderBar()
        self.hbar.set_show_close_button(True)
        self.hbar.props.title = "Football"
        self.set_titlebar(self.hbar)
        Gtk.StyleContext.add_class(self.hbar.get_style_context(), "FootballHeader")

    def gen_competitions(self):
        #competition json
        competitions = requests.get("http://api.football-data.org/v1/competitions",headers=headers)
        competitions_obj = json.loads(competitions.text)
        competitions_list = []
        for c in competitions_obj:
            try:
                competitions_list.append((c['id'], c['caption']))
            except(KeyError):
                print("Error for JSON: " + str(f))

        #competition selector
        self.competitions_liststore = Gtk.ListStore(int, str)
        for competition in competitions_list:
            self.competitions_liststore.append(list(competition))

        self.competitions_combo = Gtk.ComboBox.new_with_model_and_entry(self.competitions_liststore)
        self.competitions_combo.connect("changed", self.on_competitions_combo_changed)
        self.competitions_combo.set_entry_text_column(1)

    def gen_fixtures(self, competition_id, update=False):
         #fixtures json
        self.fixtures = requests.get(
            "http://api.football-data.org/v1/competitions/" + str(competition_id) + "/fixtures",headers=headers
        )
        self.fixtures_obj = json.loads(self.fixtures.text)
        print("N of fixtures: " + str(self.fixtures_obj['count']))
        self.fixtures_list = []
        for f in self.fixtures_obj['fixtures']:
            match_date = datetime.strptime(f['date'], '%Y-%m-%dT%H:%M:%SZ')
            if str(f['result']['goalsHomeTeam']) == "None":
                match_results = "n/a"
            else:
                match_results = str(f['result']['goalsHomeTeam'])+" - "+str(f['result']['goalsAwayTeam'])
            if f['status'] == "FINISHED":
                match_status = "Finished"
            elif f['status'] == "TIMED":
                match_status = "Timed"
            elif f['status'] == "SCHEDULED":
                match_status = "Programmed"
            try:
                self.fixtures_list.append((
                    f['homeTeamName'], 
                    f['matchday'],
                    match_results, 
                    f['awayTeamName'], match_status, match_date.strftime('%Y %B %d %H:%M')))
            except(KeyError):
                print("Error for JSON: " + str(f))

        #fixtures selector
        if update == False:
            self.fixtures_liststore = Gtk.ListStore(str, int, str, str, str, str)
            self.last_filter = self.fixtures_liststore.filter_new()
            self.last_filter.set_visible_func(self.set_last_filter)
        else:
            self.fixtures_liststore.clear()
        for fixtures in self.fixtures_list:
            self.fixtures_liststore.append(list(fixtures))
        self.fixtures_sorted = Gtk.TreeModelSort(model=self.fixtures_liststore)
        self.fixtures_sorted.set_sort_column_id(1, Gtk.SortType.ASCENDING)
        self.treeview = Gtk.TreeView.new_with_model(self.last_filter)
        for i, column_title in enumerate(["Home team", "Day", "Results", "Away team", "Status", "Date"]):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(column_title, renderer, text=i)
            column.set_reorderable(True)
            column.set_resizable(True)
            column.set_sort_column_id(i)
            self.treeview.append_column(column)
    
    def on_competitions_combo_changed(self, combo):
        tree_iter = combo.get_active_iter()
        if tree_iter != None:
            model = combo.get_model()
            row_id, name = model[tree_iter][:2]
            self.gen_fixtures(row_id, True)
            print("Selected: ID=%d, name=%s" % (row_id, name))
        else:
            entry = combo.get_child()
            print("Entered: %s" % entry.get_text())

    def set_last_filter(self, model, iter, data):
        if self.show_latest == True:
            today = datetime.now()
            latest = today - timedelta(days=7) # Last 7 days
            col_date = datetime.strptime(model[iter][5], '%Y %B %d %H:%M')
            return col_date <= today and col_date >= latest
        else:
            return True

    def on_last_clicked(self, widget):
        if self.show_latest == True:
            self.show_latest = False
            self.last.set_property("tooltip-text", "Last 7 days")
        else:
            self.show_latest = True
            self.last.set_property("tooltip-text", "Show all days")
        self.last_filter.refilter()

style_provider = Gtk.CssProvider()
style_provider.load_from_data(bytes(stylesheet.encode()))
Gtk.StyleContext.add_provider_for_screen(
    Gdk.Screen.get_default(), style_provider,
    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
)
win = Football()
win.set_default_size(900, 680) 
win.connect("delete-event", Gtk.main_quit)
win.show_all()
Gtk.main()
