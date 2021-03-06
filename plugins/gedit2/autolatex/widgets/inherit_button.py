#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# autolatex/widgets/inherit_button.py
# Copyright (C) 2013  Stephane Galland <galland@arakhne.org>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

#---------------------------------
# IMPORTS
#---------------------------------

# Standard libraries
import weakref
# Include the Gtk libraries
from gi.repository import Gtk

#---------------------------------
# INTERNATIONALIZATION
#---------------------------------

import gettext
_T = gettext.gettext

#---------------------------------
# CLASS InheritButton
#---------------------------------

# Gtk button that is managing the inheriting flag
class InheritButton(Gtk.ToggleButton):
	__gtype_name__ = "AutoLaTeXInheritButton"

	def __init__(self, container, *widgets):
		Gtk.ToggleButton.__init__(self)
		self._is_init = False
		self._container = container
		self._widgets = list(widgets)
		self._inherit_icon = Gtk.Image.new_from_stock(Gtk.STOCK_DISCONNECT, Gtk.IconSize.BUTTON)
		self._override_icon = Gtk.Image.new_from_stock(Gtk.STOCK_CONNECT, Gtk.IconSize.BUTTON)
		self.set_relief(Gtk.ReliefStyle.NONE)
		self.set_active(False)
		#
		for widget in self._widgets:
			widget.set_data(
				'autolatex_overriding_configuration_value',
				weakref.ref(self))
		

	def on_button_toggled(self, widget, data=None):
		self._update_icon()
		self._update_widget_sensitivities(True)

	def bind_widget(self, widget):
		if widget:
			widget.set_data(
				'autolatex_overriding_configuration_value',
				weakref.ref(self))
			self._widgets.append(widget)

	def unbind_widget(self, widget):
		if widget and widget in self._widgets:
			self._widgets.remove(widget)
			widget.set_data(
				'autolatex_overriding_configuration_value',
				None)

	def get_overriding_value(self):
		return self.get_active()

	def set_overriding_value(self, override):
		self.set_active(override)
		if not self._is_init:
			self._is_init = True
			self._update_icon(override)
			self._update_widget_sensitivities(False, override)
			self.connect('toggled', self.on_button_toggled)

	def _update_icon(self, is_over=None):
		if is_over is None:
			is_over = self.get_overriding_value()
		if is_over:
			self.set_tooltip_text(_T("Overriding the value in the current configuration"))
			self.set_image(self._override_icon)
		else:
			self.set_tooltip_text(_T("Get the value from the inherited configuration"))
			self.set_image(self._inherit_icon)

	def _update_widget_sensitivities(self, update_container, is_over=None):
		if is_over is None:
			is_over = self.get_overriding_value()
		for widget in self._widgets:
			widget.set_sensitive(is_over)
		if update_container:
			self._container.update_widget_states()

	def set_widget_sensitivity(self, is_sensitive):
		override_value = self.get_overriding_value()
		if not override_value:
			is_sensitive = False
		for widget in self._widgets:
			widget.set_sensitive(is_sensitive)
		return is_sensitive

	def get_widget_sensitivity(self, widget):
		override_value = self.get_overriding_value()
		if override_value:
			return widget.get_sensitive()
		else:
			return False

